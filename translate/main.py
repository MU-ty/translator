#!/usr/bin/env python3
"""
智能翻译代理 - 命令行界面
使用LangChain实现的长文本英译汉智能体
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.translation_agent import TranslationAgent


def setup_environment():
    """设置环境"""
    # 加载.env文件（向后兼容）
    load_dotenv()
    
    # 导入配置管理器
    from src.config_manager import config_manager
    
    # 检查配置文件
    config_file = Path("config.ini")
    if not config_file.exists():
        example_file = Path("config.ini.example")
        if example_file.exists():
            print(f"📝 未找到配置文件，请复制 {example_file} 为 {config_file}")
            print("   或者通过命令行参数直接传递API密钥")
        else:
            print("📝 未找到配置文件，请通过命令行参数传递API密钥")
            print("   或使用环境变量配置（向后兼容）")
    else:
        print(f"✅ 已找到配置文件: {config_file}")


def translate_single_file(args):
    """翻译单个文件"""
    print(f"🚀 启动智能翻译代理...")
    print(f"📁 输入文件: {args.input}")
    
    # 创建翻译代理
    agent = TranslationAgent(
        model_name=args.model,
        translator_id=args.translator,
        max_tokens=args.max_tokens,
        provider=args.provider,
        openai_api_key=getattr(args, 'openai_api_key', None),
        openai_base_url=getattr(args, 'openai_base_url', None),
        qwen_api_key=getattr(args, 'qwen_api_key', None)
    )
    
    try:
        # 执行翻译
        stats = agent.translate_file(
            input_file=args.input,
            output_file=args.output,
            save_stats=True
        )
        
        # 打印翻译报告
        report = agent.get_translation_report(stats)
        print(report)
        
        print(f"✅ 翻译成功完成!")
        
    except Exception as e:
        print(f"❌ 翻译过程中发生错误: {e}")
        sys.exit(1)


def translate_batch(args):
    """批量翻译"""
    print(f"🚀 启动批量翻译...")
    print(f"📁 输入目录: {args.input}")
    print(f"📁 输出目录: {args.output}")
    
    # 创建翻译代理
    agent = TranslationAgent(
        model_name=args.model,
        translator_id=args.translator,
        max_tokens=args.max_tokens,
        provider=args.provider,
        openai_api_key=getattr(args, 'openai_api_key', None),
        openai_base_url=getattr(args, 'openai_base_url', None),
        qwen_api_key=getattr(args, 'qwen_api_key', None)
    )
    
    try:
        # 执行批量翻译
        results = agent.batch_translate(
            input_dir=args.input,
            output_dir=args.output,
            file_pattern=args.pattern
        )
        
        # 统计结果
        successful = sum(1 for r in results if 'error' not in r)
        total = len(results)
        avg_score = sum(r.get('completeness_score', 0) for r in results if 'error' not in r)
        avg_score = avg_score / successful if successful > 0 else 0
        
        print(f"\n📊 批量翻译完成:")
        print(f"   成功: {successful}/{total} 个文件")
        print(f"   平均完整性评分: {avg_score:.1f}/10")
        
    except Exception as e:
        print(f"❌ 批量翻译过程中发生错误: {e}")
        sys.exit(1)


def validate_translation(args):
    """验证翻译质量"""
    print(f"🔍 验证翻译质量...")
    
    # 创建翻译代理
    agent = TranslationAgent(
        translator_id=args.translator, 
        provider=args.provider,
        openai_api_key=getattr(args, 'openai_api_key', None),
        openai_base_url=getattr(args, 'openai_base_url', None),
        qwen_api_key=getattr(args, 'qwen_api_key', None)
    )
    
    try:
        result = agent.validate_translation(args.original, args.translated)
        
        print(f"\n📊 翻译质量报告:")
        print(f"   质量评分: {result['validation_score']}/10")
        print(f"   遗漏内容: {result['comparison_result'].get('missing_content', '无')}")
        print(f"   改进建议: {result['comparison_result'].get('suggestions', '无')}")
        
    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="智能翻译代理 - 长文本英译汉工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 翻译单个文件
  python main.py translate input.md -o output.md
  
  # 批量翻译
  python main.py batch input_dir output_dir
  
  # 验证翻译质量
  python main.py validate original.md translated.md
  
环境配置:
  请复制.env.example为.env并配置您的OpenAI API密钥
        """
    )
    
    parser.add_argument(
        '--model', 
        default='gpt-3.5-turbo',
        help='使用的模型名称 (默认: gpt-3.5-turbo)'
    )
    
    parser.add_argument(
        '--provider',
        choices=['openai', 'qwen', 'auto'],
        default='auto',
        help='模型提供商 (openai, qwen, auto) (默认: auto)'
    )
    
    parser.add_argument(
        '--translator',
        default='FILL_YOUR_GITHUB_ID_HERE',
        help='翻译者ID (默认: FILL_YOUR_GITHUB_ID_HERE)'
    )
    
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=800,
        help='每个文本块的最大token数 (默认: 800)'
    )
    
    parser.add_argument(
        '--openai-api-key',
        help='OpenAI API密钥（优先级高于配置文件）'
    )
    
    parser.add_argument(
        '--openai-base-url',
        help='OpenAI API基础URL（优先级高于配置文件）'
    )
    
    parser.add_argument(
        '--qwen-api-key',
        help='Qwen API密钥（优先级高于配置文件）'
    )
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 单文件翻译命令
    translate_parser = subparsers.add_parser('translate', help='翻译单个Markdown文件')
    translate_parser.add_argument('input', help='输入的Markdown文件路径')
    translate_parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    
    # 批量翻译命令
    batch_parser = subparsers.add_parser('batch', help='批量翻译Markdown文件')
    batch_parser.add_argument('input', help='输入目录路径')
    batch_parser.add_argument('output', help='输出目录路径')
    batch_parser.add_argument('--pattern', default='*.md', help='文件匹配模式 (默认: *.md)')
    
    # 验证命令
    validate_parser = subparsers.add_parser('validate', help='验证翻译质量')
    validate_parser.add_argument('original', help='原始文件路径')
    validate_parser.add_argument('translated', help='翻译文件路径')
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 设置环境
    setup_environment()
    
    # 执行相应的命令
    if args.command == 'translate':
        translate_single_file(args)
    elif args.command == 'batch':
        translate_batch(args)
    elif args.command == 'validate':
        validate_translation(args)


if __name__ == "__main__":
    main()