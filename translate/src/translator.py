"""
翻译器
"""

from typing import List, Dict, Tuple
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseOutputParser
from tqdm import tqdm
import re
import os

from .text_chunker import TextChunk, MarkdownChunker
from .summary_generator import SummaryGenerator
from .markdown_parser import Metadata
from .llm_factory import LLMFactory


class TranslationOutputParser(BaseOutputParser):
    """翻译输出解析"""
    
    def parse(self, text) -> str:
        if hasattr(text, 'content'):
            return text.content.strip()
        elif hasattr(text, 'text'):
            return text.text.strip()
        else:
            return str(text).strip()


class SmartTranslator:
    """翻译"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.1, provider: str = None, 
                 openai_api_key: str = None, openai_base_url: str = None, qwen_api_key: str = None):

        # 使用LLM_factory创建模型实例
        self.llm = LLMFactory.create_llm(
            model_name=model_name,
            provider=provider,
            temperature=temperature,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            qwen_api_key=qwen_api_key
        )
        self.model_name = model_name
        
        self.chunker = MarkdownChunker(max_tokens=800, model=model_name)
        self.summary_generator = SummaryGenerator(
            model_name, temperature=0.2, provider=provider,
            openai_api_key=openai_api_key, openai_base_url=openai_base_url, qwen_api_key=qwen_api_key
        )
        
        # 翻译prompt模板
        self.translation_template = ChatPromptTemplate.from_template(
            """你是一个专业的英译汉翻译专家，具有深厚的语言功底和跨文化理解能力。

翻译要求：
1. 准确传达原文的含义和语调
2. 保持Markdown格式完全不变（标题、列表、代码块、链接等）
3. 使用地道的中文表达，符合中文阅读习惯
4. 保持专业术语的准确性和一致性
5. 对于代码、URL、专有名词等，保持原文不变
6. 确保翻译的流畅性和可读性

请翻译以下内容，只输出翻译结果，不要添加任何解释或说明：

{content}

翻译结果："""
        )
        
        # 重新翻译prompt模板（用于处理遗漏内容）
        self.retranslation_template = ChatPromptTemplate.from_template(
            """你是一个专业的英译汉翻译专家。现在需要你重新翻译以下内容，特别注意包含所有重要信息。

原文：
{original_text}

之前的翻译存在遗漏，缺少以下内容：
{missing_content}

请重新进行完整翻译，确保：
1. 包含所有原文信息，特别是上述缺失的内容
2. 保持Markdown格式完全不变
3. 使用地道的中文表达
4. 确保翻译的准确性和完整性

只输出翻译结果："""
        )
        
        # 创建处理链
        self.translation_chain = (
            self.translation_template 
            | self.llm 
            | TranslationOutputParser()
        )
        
        self.retranslation_chain = (
            self.retranslation_template 
            | self.llm 
            | TranslationOutputParser()
        )
    
    def translate_chunk(self, chunk: TextChunk) -> str:
        """
        翻译单个文本块
        """
        try:
            if chunk.chunk_type == 'code':
                # 代码块特殊处理 - 只翻译注释
                return self._translate_code_block(chunk.content)
            
            translation = self.translation_chain.invoke({
                "content": chunk.content
            })
            
            return translation
            
        except Exception as e:
            print(f"翻译文本块时出错: {e}")
            return f"翻译失败: {chunk.content}"
    
    def _translate_code_block(self, code_content: str) -> str:
        """
        翻译代码块，只翻译注释部分
        """
        lines = code_content.split('\n')
        translated_lines = []
        
        for line in lines:
            # 如果是注释行，进行翻译
            if line.strip().startswith('#') or line.strip().startswith('//'):
                try:
                    comment_translation = self.translation_chain.invoke({
                        "content": line.strip()
                    })
                    # 保持原有的缩进
                    indent = len(line) - len(line.lstrip())
                    translated_lines.append(' ' * indent + comment_translation)
                except:
                    translated_lines.append(line)
            else:
                translated_lines.append(line)
        
        return '\n'.join(translated_lines)
    
    def translate_content(self, content: str) -> Tuple[str, Dict]:
        """
        翻译完整内容
        """
        print("开始分析和翻译文档...")

        print("正在生成原文摘要...")
        original_summary = self.summary_generator.generate_original_summary(content)

        print("正在分割文本...")
        chunks = self.chunker.chunk_text(content)
        print(f"文本已分割为 {len(chunks)} 个块")
        
        print("正在翻译各个文本块...")
        translated_chunks = []
        
        for i, chunk in enumerate(tqdm(chunks, desc="翻译进度")):
            translated_content = self.translate_chunk(chunk)
            translated_chunks.append(translated_content)

        translated_content = self._merge_translated_chunks(translated_chunks)

        print("正在生成译文摘要...")
        translated_summary = self.summary_generator.generate_translated_summary(translated_content)

        print("正在检查翻译完整性...")
        comparison_result = self.summary_generator.compare_summaries(
            original_summary, translated_summary
        )
        
        if comparison_result["completeness_score"] < 8 and comparison_result["missing_content"] != "无":
            print(f"检测到可能的遗漏内容，完整性评分: {comparison_result['completeness_score']}/10")
            print(f"遗漏内容: {comparison_result['missing_content']}")
            print("正在重新翻译...")
            
            retranslated_content = self._retranslate_with_focus(
                content, comparison_result["missing_content"]
            )
            
            if retranslated_content:
                translated_content = retranslated_content

                translated_summary = self.summary_generator.generate_translated_summary(translated_content)
                
                comparison_result = self.summary_generator.compare_summaries(
                    original_summary, translated_summary
                )
                print(f"重新翻译后的完整性评分: {comparison_result['completeness_score']}/10")
        
        stats = {
            "original_summary": original_summary,
            "translated_summary": translated_summary,
            "comparison_result": comparison_result,
            "chunk_count": len(chunks),
            "completeness_score": comparison_result["completeness_score"]
        }
        
        return translated_content, stats
    
    def _merge_translated_chunks(self, translated_chunks: List[str]) -> str:
        """
        合并文本块
        """
        # 简单合并，用双换行分隔
        return '\n\n'.join(chunk.strip() for chunk in translated_chunks if chunk.strip())
    
    def _retranslate_with_focus(self, original_content: str, missing_content: str) -> str:
        """
        重新翻译缺失内容
        """
        try:
            retranslated = self.retranslation_chain.invoke({
                "original_text": original_content,
                "missing_content": missing_content
            })
            return retranslated
        except Exception as e:
            print(f"重新翻译时出错: {e}")
            return None
    
    def translate_with_context(self, content: str, context: str = "") -> str:
        """
        带上下文的翻译
        """
        if context:
            enhanced_prompt = ChatPromptTemplate.from_template(
                """你是一个专业的英译汉翻译专家。

上下文信息：
{context}

请翻译以下内容，考虑上下文的连贯性：

{content}

翻译结果："""
            )
            
            enhanced_chain = enhanced_prompt | self.llm | TranslationOutputParser()
            
            try:
                return enhanced_chain.invoke({
                    "content": content,
                    "context": context
                })
            except Exception as e:
                print(f"带上下文翻译时出错: {e}")
                return self.translate_chunk(TextChunk(content, 'paragraph'))
        else:
            return self.translate_chunk(TextChunk(content, 'paragraph'))