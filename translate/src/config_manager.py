"""
配置管理器 - 支持配置文件和直接参数两种方式
"""

import os
import configparser
from typing import Dict, Optional
from pathlib import Path


class ConfigManager:
    
    def __init__(self, config_file: str = None):
        """
        初始化配置管理
        """
        if config_file is None:

            current_dir = Path(__file__).parent.parent
            config_file = current_dir / "config.ini"

            if not config_file.exists():
                example_config = current_dir / "config.ini.example"
                if example_config.exists():
                    print(f"⚠️  配置文件不存在，请复制 {example_config} 为 {config_file} 并填入您的API密钥")
                config_file = None
        
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        if config_file and os.path.exists(config_file):
            self.config.read(config_file, encoding='utf-8')
            print(f"已加载配置文件: {config_file}")
        else:
            print("📝 未找到配置文件，将使用参数传递模式")
    
    def get_openai_config(self, api_key: str = None, base_url: str = None) -> Dict[str, Optional[str]]:

        config = {
            'api_key': api_key,
            'base_url': base_url
        }

        if not api_key and self.config.has_section('openai'):
            config['api_key'] = self.config.get('openai', 'api_key', fallback=None)
            if config['api_key'] == 'your_openai_api_key_here':
                config['api_key'] = None
        
        if not base_url and self.config.has_section('openai'):
            config['base_url'] = self.config.get('openai', 'base_url', fallback='https://api.openai.com/v1')

        if not config['api_key']:
            config['api_key'] = os.getenv('OPENAI_API_KEY')
        if not config['base_url']:
            config['base_url'] = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        return config
    
    def get_qwen_config(self, api_key: str = None) -> Dict[str, Optional[str]]:
        """
        Qwen配置
        """
        config = {
            'api_key': api_key
        }

        if not api_key and self.config.has_section('qwen'):
            config['api_key'] = self.config.get('qwen', 'api_key', fallback=None)
            if config['api_key'] == 'your_dashscope_api_key_here':
                config['api_key'] = None

        if not config['api_key']:
            config['api_key'] = os.getenv('DASHSCOPE_API_KEY')
        
        return config
    
    def get_default_config(self) -> Dict[str, str]:
        """
        获取默认配置
        """
        defaults = {
            'model_name': 'gpt-3.5-turbo',
            'provider': 'auto',
            'translator_id': 'FILL_YOUR_GITHUB_ID_HERE',
            'max_tokens': '800'
        }
        
        if self.config.has_section('default'):
            for key in defaults:
                value = self.config.get('default', key, fallback=defaults[key])
                defaults[key] = value

        defaults['model_name'] = os.getenv('MODEL_NAME', defaults['model_name'])
        defaults['provider'] = os.getenv('MODEL_PROVIDER', defaults['provider'])
        
        return defaults
    
    def validate_config(self, provider: str, **kwargs) -> bool:
        """
        验证配置是否完整
        """
        if provider.lower() == 'openai':
            openai_config = self.get_openai_config(
                api_key=kwargs.get('openai_api_key'),
                base_url=kwargs.get('openai_base_url')
            )
            return bool(openai_config['api_key'])
        
        elif provider.lower() == 'qwen':
            qwen_config = self.get_qwen_config(
                api_key=kwargs.get('qwen_api_key')
            )
            return bool(qwen_config['api_key'])
        
        elif provider.lower() == 'auto':
            openai_valid = bool(self.get_openai_config(
                api_key=kwargs.get('openai_api_key')
            )['api_key'])
            qwen_valid = bool(self.get_qwen_config(
                api_key=kwargs.get('qwen_api_key')
            )['api_key'])
            return openai_valid or qwen_valid
        
        return False
    
    def create_sample_config(self, config_path: str = None):

        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.ini"
        
        sample_config = """# 智能翻译代理配置文件
# 请根据需要配置相应的API密钥

[openai]
# OpenAI API配置
api_key = your_openai_api_key_here
base_url = https://api.openai.com/v1

[qwen]
# 阿里云Qwen API配置
api_key = your_dashscope_api_key_here

[default]
# 默认配置
model_name = gpt-3.5-turbo
provider = auto
translator_id = FILL_YOUR_GITHUB_ID_HERE
max_tokens = 800
"""
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(sample_config)
        
        print(f"已创建示例配置文件: {config_path}")
        print("   编辑该文件并填入API密钥")

config_manager = ConfigManager()