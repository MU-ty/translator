# 自动翻译项目

1. **Markdown解析和元数据处理** (`markdown_parser.py`)

2. **文本分块** (`text_chunker.py`) 

3. **摘要生成** (`summary_generator.py`)

4. **翻译** (`translator.py`)

5. **翻译代理** (`translation_agent.py`)

6. **命令行** (`main.py`)


### 命令行使用
```bash

python main.py --model qwen-plus --provider qwen translate tests/ldm.md -o tests/ldm_translated.md #示例

```
