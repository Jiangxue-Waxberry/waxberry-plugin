"""
外部配置加载器
从项目外部读取配置文件，实现配置与项目分离
"""
import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional

class ExternalConfigLoader:
    """外部配置加载器"""
    
    def __init__(self):
        self.config_cache: Optional[Dict[str, Any]] = None
        self.config_paths = [
            # 1. 环境变量指定的路径（优先级最高）
            os.environ.get('WAXBERRY_CONFIG_PATH', 'c:/'),
            # 2. 用户自定义目录
            str(Path.home() / ''),
        ]
    
    def find_config_file(self, config_name: str = 'plugin.py') -> Optional[Path]:
        """
        查找配置文件
        
        Args:
            config_name: 配置文件名
            
        Returns:
            Path: 配置文件路径，如果未找到返回None
        """
        for path_str in self.config_paths:
            if not path_str:
                continue
                
            path = Path(path_str)
            config_file = path / config_name
            
            if path.exists() and config_file.exists():
                print(f"✓ 找到配置文件: {config_file}")
                return config_file
        
        print("✗ 未找到配置文件，尝试的路径:")
        for i, path_str in enumerate(self.config_paths, 1):
            if path_str:
                print(f"  {i}. {path_str}")
        return None
    
    def load_config(self, config_name: str = 'plugin.py') -> Dict[str, Any]:
        """
        加载外部配置文件
        
        Args:
            config_name: 配置文件名
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        if self.config_cache is not None:
            return self.config_cache
        
        config_file = self.find_config_file(config_name)
        if not config_file:
            raise FileNotFoundError(f"找不到配置文件: {config_name}")
        
        try:
            # 动态加载配置文件
            spec = importlib.util.spec_from_file_location("external_config", config_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"无法加载配置文件: {config_file}")
            
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # 提取配置变量
            config_dict = {}
            for attr_name in dir(config_module):
                if not attr_name.startswith('_'):
                    attr_value = getattr(config_module, attr_name)
                    if not callable(attr_value):
                        config_dict[attr_name] = attr_value
            
            print(f"✓ 成功加载 {len(config_dict)} 个配置项")
            self.config_cache = config_dict
            return config_dict
            
        except Exception as e:
            raise ImportError(f"加载配置文件失败 {config_file}: {e}")
    
    def reload_config(self, config_name: str = 'plugin.py') -> Dict[str, Any]:
        """
        重新加载配置文件
        
        Args:
            config_name: 配置文件名
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        self.config_cache = None
        return self.load_config(config_name)

# 全局配置加载器实例
config_loader = ExternalConfigLoader()

def load_external_config(config_name: str = 'plugin.py') -> Dict[str, Any]:
    """
    加载外部配置的便捷函数
    
    Args:
        config_name: 配置文件名
        
    Returns:
        Dict[str, Any]: 配置字典
    """
    return config_loader.load_config(config_name)

def reload_external_config(config_name: str = 'plugin.py') -> Dict[str, Any]:
    """
    重新加载外部配置的便捷函数
    
    Args:
        config_name: 配置文件名
        
    Returns:
        Dict[str, Any]: 配置字典
    """
    return config_loader.reload_config(config_name) 