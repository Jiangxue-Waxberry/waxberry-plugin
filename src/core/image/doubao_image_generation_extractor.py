import requests
import logging
from datetime import datetime
from typing import Dict, Any, Tuple
from openai import OpenAI
from src.config.config import FILESERVER_UPLOAD_URL, BASE_URL, API_KEY, IMAGE_MODEL_NAME
import uuid

logger = logging.getLogger(__name__)

class ImageGenerator:
    @staticmethod
    def _download_image(image_url: str) -> Tuple[bool, Any]:
        try:
            logger.info(f"开始下载图片: {image_url}")
            resp = requests.get(image_url, timeout=30)
            resp.raise_for_status()
            logger.info("图片下载成功")
            return True, resp.content
        except Exception as e:
            logger.exception("下载图片失败")
            return False, f"下载图片失败: {str(e)}"

    @staticmethod
    def _upload_to_file_server(image_content: bytes) -> Tuple[bool, Any]:
        try:
            file_name = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
            logger.info(f"准备上传文件: {file_name}")
            files = {'file': (file_name, image_content)}
            data = {
                'creator': 'waxberry',
                'client': 'pluginClient',
                'securityLevel': 'normal',
                'encrypt': 'false',
                'product': 'plug'
            }
            resp = requests.post(FILESERVER_UPLOAD_URL, files=files, data=data, timeout=30)
            resp.raise_for_status()
            resp_json = resp.json()
            logger.info("文件服务器上传成功")
            return True, resp_json.get('data')
        except Exception as e:
            logger.exception("文件服务器上传失败")
            return False, f"文件服务器上传失败: {str(e)}"

    @staticmethod
    def generate_image(prompt: str) -> Tuple[Dict[str, Any], int]:
        try:
            logger.info(f"开始生成图片: prompt={prompt}")
            client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
            response = client.images.generate(
                model=IMAGE_MODEL_NAME,
                prompt=prompt,
                size="1024x1024",
                response_format="url"
            )
            image_url = response.data[0].url
            logger.info(f"获取到图片URL: {image_url}")

            success, result = ImageGenerator._download_image(image_url)
            if not success:
                return {"success": False, "code": 500, "message": result}, 500

            success, result = ImageGenerator._upload_to_file_server(result)
            if not success:
                return {"success": False, "code": 500, "message": result}, 500

            logger.info("图片生成流程完成")
            logger.info(f"文件服务器返回: {result}")
            return {"success": True, "code": 200, "data": result, "message": ""}, 200

        except Exception as e:
            logger.exception("生成图片失败")
            return {"success": False, "code": 500, "message": f"生成图片失败: {str(e)}"}, 500