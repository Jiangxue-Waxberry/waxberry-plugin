from typing import Dict, Any, Optional
from PIL import Image
import tempfile
import os
#from src.core.image.doubao_text_from_image_extractor import process_image_with_doubao
#from src.core.image.doubao_text_to_image_extractor import generate_image
from src.core.image.doubao_visual_understanding_extractor import process_image_with_doubao
from src.core.image.doubao_image_generation_extractor import ImageGenerator

class ImageService:
    """图像处理服务"""
    
    def extract_text_from_image(self, image: Image.Image, question: Optional[str] = None) -> Dict[str, Any]:
        """
        处理图像并回答问题
        
        Args:
            image: PIL图像对象
            question: 关于图像的问题（可选）
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        image_path = os.path.join(temp_dir, "temp_image.png")
        
        try:
            # 处理RGBA模式，转换为RGB
            if image.mode == 'RGBA':
                # 创建白色背景
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])  # 使用alpha通道作为mask
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 保存图像
            image.save(image_path)
            
            # 处理图像，使用 "high" 作为默认的 detail 参数
            result = process_image_with_doubao(image_path, detail="high", question=question)
            
            # 如果结果是字典（新的响应格式），直接返回
            if isinstance(result, dict):
                return result
                
            # 否则，包装成新的响应格式
            return {
                "success": True,
                "code": 200,
                "data": result,
                "message": ""
            }

        except Exception as e:
            return {
                "success": False,
                "code": 500,
                "message": str(e)
            }
        finally:
            # 清理临时文件
            if os.path.exists(image_path):
                os.remove(image_path)
            os.rmdir(temp_dir)
    
    def generate_image_from_text(self, prompt: str) -> Dict[str, Any]:
        """
        根据文本生成图像
        
        Args:
            prompt: 图像生成提示文本
            
        Returns:
            Dict[str, Any]: 生成的图像信息
        """
        response, _ = ImageGenerator.generate_image(prompt)
        return response

    def visual_understanding(self, image: Image.Image, question: Optional[str] = None) -> Dict[str, Any]:
        """
        处理图像并回答问题

        Args:
            image: PIL图像对象
            question: 关于图像的问题（可选）

        Returns:
            Dict[str, Any]: 处理结果
        """
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        image_path = os.path.join(temp_dir, "temp_image.png")

        try:
            # 处理RGBA模式，转换为RGB
            if image.mode == 'RGBA':
                # 创建白色背景
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])  # 使用alpha通道作为mask
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 保存图像
            image.save(image_path)

            # 处理图像，使用 "high" 作为默认的 detail 参数
            #result = process_image_with_doubao(image_path, detail="high", question=question)
            result = process_image_with_doubao(image_path, detail="high", question=question)
            # 如果结果是字典（新的响应格式），直接返回
            if isinstance(result, dict):
                return result

            # 否则，包装成新的响应格式
            return {
                "success": True,
                "code": 200,
                "data": result,
                "message": ""
            }

        except Exception as e:
            return {
                "success": False,
                "code": 500,
                "message": str(e)
            }
        finally:
            # 清理临时文件
            if os.path.exists(image_path):
                os.remove(image_path)
            os.rmdir(temp_dir)
