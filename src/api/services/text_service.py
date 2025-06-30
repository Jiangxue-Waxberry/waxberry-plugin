from typing import Dict, Any
from src.core.file.office_file_extractor import OfficeTextExtractor

class TextService:
    """文本处理服务"""
    
    def __init__(self):
        """初始化服务"""
        self.extractor = OfficeTextExtractor()
    
    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        从文件中提取文本
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 包含提取的文本和元数据
        """
        return self.extractor.extract_text(file_path)
    
    def extract_text_from_bytes(self, data: bytes, file_type: str) -> Dict[str, Any]:
        """
        从二进制数据中提取文本
        
        Args:
            data: 二进制数据
            file_type: 文件类型 (例如 docx, xlsx, pdf)
            
        Returns:
            Dict[str, Any]: 包含提取的文本和元数据
        """
        return self.extractor.extract_text_from_bytes(data, file_type) 