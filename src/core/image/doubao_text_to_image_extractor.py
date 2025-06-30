# coding:utf-8
from __future__ import print_function
import requests
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from volcengine.visual.VisualService import VisualService

from src.api.routes.image_routes import settings
from src.config.config import FILESERVER_UPLOAD_URL

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageGenerator:
    """图像生成器类"""
    
    def __init__(self, ak: Optional[str] = None, sk: Optional[str] = None):
        """
        初始化图像生成器
        
        Args:
            ak: 访问密钥ID
            sk: 访问密钥
        """
        logger.info("初始化 ImageGenerator")
        self.visual_service = VisualService()
        if ak and sk:
            logger.info(f"设置访问密钥: AK={ak[:10]}..., SK={sk[:10]}...")
            self.visual_service.set_ak(ak)
            self.visual_service.set_sk(sk)
        else:
            logger.warning("未提供访问密钥")
        
        # 默认配置
        self.default_config = {
            "req_key": "high_aes_general_v21_L",
            "model_version": "general_v2.1_L",
            "req_schedule_conf": "general_v20_9B_pe",
            "llm_seed": -1,
            "seed": -1,
            "scale": 3.5,
            "ddim_steps": 25,
            "width": 512,
            "height": 512,
            "use_pre_llm": True,
            "use_sr": True,
            "return_url": True,
            "logo_info": {
                "add_logo": True,
                "position": 0,
                "language": 0,
                "opacity": 0.3,
                "logo_text_content": "杨梅工业"
            }
        }
        logger.info("默认配置已设置")
    
    def _build_request_form(self, prompt: str) -> Dict[str, Any]:
        """
        构建请求参数
        
        Args:
            prompt: 文本描述
            
        Returns:
            Dict[str, Any]: 请求参数
        """
        form = self.default_config.copy()
        form["prompt"] = prompt
        logger.info(f"构建请求参数: prompt={prompt}")
        return form
    
    def _download_image(self, image_url: str) -> Tuple[bool, Any]:
        """
        下载图片
        
        Args:
            image_url: 图片URL
            
        Returns:
            Tuple[bool, Any]: (是否成功, 图片内容或错误信息)
        """
        try:
            logger.info(f"开始下载图片: {image_url}")
            img_resp = requests.get(image_url)
            if img_resp.status_code != 200:
                logger.error(f"下载图片失败: HTTP {img_resp.status_code}")
                return False, f"下载图片失败: HTTP {img_resp.status_code}"
            logger.info("图片下载成功")
            return True, img_resp.content
        except Exception as e:
            logger.error(f"下载图片失败: {str(e)}")
            return False, f"下载图片失败: {str(e)}"
    
    def _upload_to_file_server(self, image_content: bytes) -> Tuple[bool, Any]:
        """
        上传图片到文件服务器
        
        Args:
            image_content: 图片内容
            
        Returns:
            Tuple[bool, Any]: (是否成功, 响应数据或错误信息)
        """
        try:
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"output_{timestamp}.png"
            logger.info(f"准备上传文件: {file_name}")
            
            # 准备上传数据
            files = {
                'file': (file_name, image_content)
            }

            # 准备其他表单字段
            data = {
                'creator': 'waxberry',
                'client': 'waxberry',
                'securityLevel': 'normal',
                'encrypt': 'false',
                'product': 'plug'
            }

            # 上传到文件服务器
            upload_api_url = FILESERVER_UPLOAD_URL
            logger.info(f"上传到文件服务器: {upload_api_url}")
            upload_resp = requests.post(
                upload_api_url,
                files=files,
                data=data,
                timeout=1000
            )
            
            if upload_resp.status_code != 200:
                logger.error(f"文件服务器上传失败: HTTP {upload_resp.status_code}")
                return False, f"文件服务器上传失败: HTTP {upload_resp.status_code}"

            resp_json = upload_resp.json()
            logger.info("文件服务器上传成功")
            return True, resp_json.get('data')
            
        except Exception as e:
            logger.error(f"文件服务器上传失败: {str(e)}")
            return False, f"文件服务器上传失败: {str(e)}"
    
    def generate_image(self, prompt: str) -> Tuple[Dict[str, Any], int]:
        """
        根据文本生成图片
        
        Args:
            prompt: 文本描述
            
        Returns:
            Tuple[Dict[str, Any], int]: (响应数据, HTTP状态码)
        """
        try:
            logger.info(f"开始生成图片: prompt={prompt}")
            
            # 构建请求参数
            form = self._build_request_form(prompt)
            
            # 调用API生成图片
            logger.info("调用文心一言API生成图片")
            resp = self.visual_service.cv_process(form)

            # 检查响应状态
            if resp.get('code') != 10000:
                error_msg = f"生成图片失败: {resp.get('message')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "code": 500,
                    "message": error_msg
                }, 500
            
            # 获取图片URL
            image_url = resp['data']['image_urls'][0]
            logger.info(f"获取到图片URL: {image_url}")
            
            # 下载图片
            success, result = self._download_image(image_url)
            if not success:
                return {
                    "success": False,
                    "code": 500,
                    "message": result
                }, 500
            
            # 上传到文件服务器
            success, result = self._upload_to_file_server(result)
            if not success:
                return {
                    "success": False,
                    "code": 500,
                    "message": result
                }, 500
            
            # 返回成功响应
            logger.info("图片生成流程完成")
            logger.info(f"文件服务器返回: {result}")
            
            return {
                "success": True,
                "code": 200,
                "data": result,
                "message": ""
            }, 200
            
        except Exception as e:
            error_msg = f"生成图片失败: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "code": 500,
                "message": error_msg
            }, 500

# 创建默认实例，使用默认的访问密钥
default_generator = ImageGenerator(
    ak= settings.doubao_ak,
    sk= settings.doubao_sk
)

def generate_image(prompt: str, ak: Optional[str] = None, sk: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
    """
    根据文本生成图片的便捷函数
    
    Args:
        prompt: 文本描述
        ak: 可选，访问密钥ID
        sk: 可选，访问密钥
        
    Returns:
        Tuple[Dict[str, Any], int]: (响应数据, HTTP状态码)
    """
    generator = default_generator if not (ak and sk) else ImageGenerator(ak, sk)
    return generator.generate_image(prompt)