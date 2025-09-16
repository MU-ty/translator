"""
智能翻译代理
"""

import os
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import json

from .markdown_parser import MarkdownParser, Metadata
from .translator import SmartTranslator
from .text_chunker import MarkdownChunker


class TranslationAgent:
    """智能翻译代理"""
    
    def __init__(self, 
                 model_name: str = "gpt-3.5-turbo",
                 translator_id: str = "FILL_YOUR_GITHUB_ID_HERE",
                 max_tokens: int = 800,
                 provider: str = None,
                 openai_api_key: str = None,
                 openai_base_url: str = None,
                 qwen_api_key: str = None):
        """
        初始化翻译代理
        """
        self.translator_id = translator_id
        self.model_name = model_name
        self.provider = provider
        self.parser = MarkdownParser()
        self.translator = SmartTranslator(
            model_name, provider=provider,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            qwen_api_key=qwen_api_key
        )
        
    def translate_file(self, 
                      input_file: str, 
                      output_file: Optional[str] = None,
                      save_stats: bool = True) -> Dict:
        """
        翻译Markdown文件
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"输入文件不存在: {input_file}")
        
        print(f"正在处理文件: {input_file}")

        metadata, content = self.parser.parse_file(input_file)
        
        print(f"文档标题: {metadata.title}")
        print(f"原作者: {metadata.author}")
        print(f"文档长度: {len(content)} 字符")
        
        translated_content, stats = self.translator.translate_content(content)

        updated_metadata = self.parser.update_translation_metadata( #元数据更新1
            metadata, self.translator_id
        )
        
        if output_file is None:
            input_path = Path(input_file)
            output_file = str(input_path.parent / f"{input_path.stem}_translated.md")
        
        final_output = self.parser.format_output(updated_metadata, translated_content)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_output)
        
        print(f"翻译完成，输出文件: {output_file}")
        
        #统计信息
        if save_stats:
            stats_file = str(Path(output_file).with_suffix('.stats.json'))
            self._save_translation_stats(stats, stats_file)
        
        # 添加文件路径到统计信息
        stats.update({
            "input_file": input_file,
            "output_file": output_file,
            "translator_id": self.translator_id
        })
        
        return stats
    
    def translate_text(self, 
                      text: str, 
                      title: str = "FILL_THE_TITLE_HERE",
                      author: str = "FILL_THE_AUTHOR_HERE") -> Tuple[str, Dict]:
        """
        翻译文本字符串
        """
        metadata, content = self.parser.parse_text(text)

        if metadata.title == "FILL_THE_TITLE_HERE":
            metadata.title = title
        if metadata.author == "FILL_THE_AUTHOR_HERE":
            metadata.author = author
        
        print(f"正在翻译文档: {metadata.title}")

        translated_content, stats = self.translator.translate_content(content)

        updated_metadata = self.parser.update_translation_metadata(
            metadata, self.translator_id   #元数据更新
        )

        final_output = self.parser.format_output(updated_metadata, translated_content)
        
        return final_output, stats
    
    def batch_translate(self, 
                       input_dir: str, 
                       output_dir: str,
                       file_pattern: str = "*.md") -> List[Dict]:
        """
        批量翻译文件
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        output_path.mkdir(parents=True, exist_ok=True)

        files = list(input_path.glob(file_pattern))
        
        if not files:
            print(f"在 {input_dir} 中没有找到匹配 {file_pattern} 的文件")
            return []
        
        print(f"找到 {len(files)} 个文件需要翻译")
        
        results = []
        
        for file_path in files:
            print(f"\n处理文件 {len(results) + 1}/{len(files)}: {file_path.name}")
            
            try:
                output_file = output_path / f"{file_path.stem}_translated.md"
                stats = self.translate_file(str(file_path), str(output_file))
                results.append(stats)
                
            except Exception as e:
                print(f"翻译文件 {file_path} 时出错: {e}")
                results.append({
                    "input_file": str(file_path),
                    "error": str(e),
                    "completeness_score": 0
                })

        report_file = output_path / "batch_translation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n批量翻译完成，报告保存至: {report_file}")
        
        return results
    
    def _save_translation_stats(self, stats: Dict, stats_file: str):
        """
        保存翻译统计信息
        """
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            print(f"翻译统计信息已保存至: {stats_file}")
        except Exception as e:
            print(f"保存统计信息时出错: {e}")
    
    def get_translation_report(self, stats: Dict) -> str:
        """
        生成翻译报告
        """
        report = f"""
翻译完成报告
================

📊 基本信息
- 翻译者: {self.translator_id}
- 文本块数: {stats.get('chunk_count', 0)}
- 完整性评分: {stats.get('completeness_score', 0)}/10

📝 原文摘要
{stats.get('original_summary', '无')}

🔍 译文摘要  
{stats.get('translated_summary', '无')}

✅ 质量评估
- 完整性: {stats.get('completeness_score', 0)}/10
- 遗漏内容: {stats.get('comparison_result', {}).get('missing_content', '无')}
- 改进建议: {stats.get('comparison_result', {}).get('suggestions', '无')}

"""
        return report
    
    def validate_translation(self, original_file: str, translated_file: str) -> Dict:
        """
        验证翻译质量
        """
        # 读取原文和译文
        _, original_content = self.parser.parse_file(original_file)
        _, translated_content = self.parser.parse_file(translated_file)
        
        # 生成摘要并比较
        original_summary = self.translator.summary_generator.generate_original_summary(original_content)
        translated_summary = self.translator.summary_generator.generate_translated_summary(translated_content)
        
        comparison_result = self.translator.summary_generator.compare_summaries(
            original_summary, translated_summary
        )
        
        return {
            "original_summary": original_summary,
            "translated_summary": translated_summary,
            "comparison_result": comparison_result,
            "validation_score": comparison_result["completeness_score"]
        }