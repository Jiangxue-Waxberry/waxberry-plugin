# coding:utf-8
import os
import base64
import mimetypes
import logging
from typing import Dict, Any, Optional, Union
from openai import OpenAI
from src.config.config import BASE_URL, API_KEY, MODEL_NAME

logger = logging.getLogger(__name__)

def encode_image_with_prefix(image_path: str) -> str:
    """
    读取图片并转为带 data:image/xxx;base64, 前缀的 base64 字符串
    """
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"  # 默认
    with open(image_path, "rb") as image_file:
        base64_str = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{base64_str}"

def process_image_with_doubao(
    image_path: str,
    detail: str = "high",
    question: Optional[str] = "请描述这张图片的内容"
) -> Union[str, Dict[str, Any]]:
    """
    用豆包大模型处理图片，返回识别结果
    """
    try:
        # 初始化 Ark 客户端
        client = OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY,
        )

        image_url = encode_image_with_prefix(image_path)
        logger.info(f"图片已编码，准备发送请求，图片路径: {image_path}")

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            },
                        },
                        {
                            "type": "text",
                            "text": question,
                        },
                    ],
                }
            ],
        )

        content = response.choices[0].message.content
        logger.info(f"模型返回内容: {content}")

        return {
            "success": True,
            "code": 200,
            "data": content,
            "message": ""
        }

    except Exception as e:
        logger.error(f"处理图片时出错: {str(e)}", exc_info=True)
        return {
            "success": False,
            "code": 500,
            "message": str(e)
        }