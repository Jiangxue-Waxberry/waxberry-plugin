"""
图像处理路由模块

本模块提供图像处理相关的API接口，主要功能包括：
1. 文本生成图像 (textToImage)：根据文本描述生成图像
2. 图像编辑 (editImage)：对现有图像进行编辑和修改
3. 支持多种图像格式：jpg, png, webp
4. 提供详细的生成参数配置

API 接口说明：
1. /api/v1/textToImage (POST)
   - 功能：根据文本描述生成图像
   - 请求格式：application/json
   - 参数：
     * text：图像描述文本

   - 响应格式：
     * 成功：返回生成的图像URL或Base64数据
     * 失败：返回错误信息

2. /api/v1/imageToText (POST)
   - 功能：编辑现有图像
   - 请求格式：multipart/form-data
   - 参数：
     * file：原始图像文件
   - 响应格式：
     * 成功：返回编辑后的图像
     * 失败：返回错误信息

使用示例：
1. 文本生成图像：
    curl -X POST "http://localhost:9020/api/v1/textToImage" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"%E4%B8%80%E5%8F%AA%E5%9C%A8%E8%8D%89%E5%9C%B0%E4%B8%8A%E5%A5%94%E8%B7%91%E7%9A%84%E9%87%91%E6%AF%9B%E7%8A%AC\"}"

2. 图像编辑：
    curl -X POST http://localhost:9020/api/v1/imageToText \
         -F "file=@C:/test/test.jpg" \
         -F "question=图片里有什么？" \
         -H "Content-Type: multipart/form-data"
"""

from flask import Blueprint, request, jsonify
from PIL import Image
import io
from src.api.services.image_service import ImageService
from src.config.settings import Settings
from flask_restx import Resource, Namespace
from src.utils.logging import get_logger

# 创建蓝图
image_bp = Blueprint('image', __name__)

# 创建命名空间
ns = Namespace('image', description='图像处理接口')

# 创建日志记录器
logger = get_logger(__name__)

# 创建服务实例
image_service = ImageService()
settings = Settings()

@ns.route('/api/v1/textToImage')
class ImageProcess(Resource):
    @ns.doc('process_image',
        responses={
            200: '成功',
            400: '请求参数错误',
            500: '服务器错误'
        }
    )
    def post(self):
        """
        图像处理接口

        处理上传的图像文件

        Returns:
            dict: 处理结果
        """
        try:
            # 获取上传的文件
            if 'file' not in request.files:
                return {'error': '没有上传文件'}, 400

            file = request.files['file']
            if file.filename == '':
                return {'error': '没有选择文件'}, 400

            # 处理图像
            result = image_service.generate_image_from_text(file)
            return result

        except Exception as e:
            logger.error(f"图像处理失败: {str(e)}")
            return {'error': str(e)}, 500

@ns.route('/api/v1/imageToText')
class ImageOCR(Resource):
    @ns.doc('ocr_image',
        responses={
            200: '成功',
            400: '请求参数错误',
            500: '服务器错误'
        }
    )
    def post(self):
        """
        OCR文字识别接口

        识别图像中的文字

        Returns:
            dict: 识别结果
        """
        try:
            # 获取上传的文件
            if 'file' not in request.files:
                return {'error': '没有上传文件'}, 400

            file = request.files['file']
            if file.filename == '':
                return {'error': '没有选择文件'}, 400

            # 执行OCR
            result = image_service.extract_text_from_image(file)
            return result

        except Exception as e:
            logger.error(f"OCR识别失败: {str(e)}")
            return {'error': str(e)}, 500

@image_bp.route('/api/v1/imageToText', methods=['POST'])
def image_to_text():
    """
    图像文字识别接口
    
    功能：
    1. 接收图片文件并识别其中的文字
    2. 支持回答关于图片的问题
    
    支持两种上传方式：
    1. 表单文件上传 (multipart/form-data)
       - 通过 'file' 字段上传图片
       - 可选通过 'question' 字段提问
    2. 二进制流直接上传 (application/octet-stream)
       - 直接发送图片二进制数据
       - 通过 '?question=...' query 参数提问
    
    请求参数：
    - file: 图片文件（表单上传时）
    - question: 关于图片的问题（可选）
    
    响应格式：
    {
        "success": true/false,
        "code": 200/400/500,
        "data": {
            "text": "识别的文字内容",
            "answer": "问题的回答"（如果有问题）
        },
        "message": "错误信息"（如果有错误）
    }
    """
    img = None
    question = request.args.get('question')  # 优先从 query 参数获取 question

    # 方式1：检查表单文件上传
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "code": 400,
                "message": "未选择文件"
            }), 400

        # 如果 query 参数没有 question，尝试从 form data 获取
        if not question:
            question = request.form.get('question')

        # 验证文件类型
        filename = file.filename.lower()
        if not any(filename.endswith(fmt) for fmt in settings.supported_image_formats):
            return jsonify({
                "success": False,
                "code": 400,
                "message": f"仅支持以下图片格式: {', '.join(settings.supported_image_formats)}"
            }), 400

        # 将文件流转换为PIL图像
        try:
            img = Image.open(io.BytesIO(file.read()))
        except Exception as e:
            return jsonify({
                "success": False,
                "code": 400,
                "message": f"无法处理上传的图片文件: {str(e)}"
            }), 400

    # 方式2：检查二进制流上传
    elif request.content_type and request.content_type.startswith('application/octet-stream'):
        try:
            logger.info(f"处理二进制流上传，Content-Type: {request.content_type}")
            logger.info(f"请求数据大小: {len(request.get_data())} bytes")
            img = Image.open(io.BytesIO(request.get_data()))
            logger.info(f"成功解析图片，模式: {img.mode}, 尺寸: {img.size}")
        except Exception as e:
            logger.error(f"二进制流处理失败: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "code": 400,
                "message": f"无法处理上传的图片数据: {str(e)}"
            }), 400

    # 如果没有找到有效的图片数据
    if img is None:
        return jsonify({
            "success": False,
            "code": 400,
            "message": "请上传图片文件或提供图片数据"
        }), 400

    # 处理图片并返回结果
    try:
        result = image_service.extract_text_from_image(img, question)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "code": 500,
            "message": f"处理图片时出错: {str(e)}"
        }), 500

@image_bp.route('/api/v1/textToImage', methods=['POST'])
def text_to_image():
    """
    文本生成图像接口
    
    功能：
    1. 根据文本描述生成图像
    2. 自动上传生成的图像到文件服务器
    
    请求格式：
    {
        "text": "图像描述文本"
    }
    
    响应格式：
    {
        "success": true/false,
        "code": 200/400/500,
        "data": {
            "fileMsg": {
                "MD5": "文件MD5值",
                "code": 1,
                "fileActionMsg": "操作成功",
                "fileId": "文件ID",
                "fileName": "文件名",
                "fileSize": 文件大小
            }
        },
        "message": "错误信息"（如果有错误）
    }
    
    处理流程：
    1. 调用文心一言API生成图像
    2. 下载生成的图像
    3. 上传到文件服务器
    4. 返回文件服务器响应
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                "success": False,
                "code": 400,
                "message": "Missing 'text' in request body",
                "data": None
            }), 400
        
        response = image_service.generate_image_from_text(data['text'])
        return jsonify(response), response.get('code', 500)
        
    except Exception as e:
        logger.error(f"生成图片失败: {str(e)}")
        return jsonify({
            "success": False,
            "code": 500,
            "message": str(e),
            "data": None
        }), 500

# 导出命名空间供app.py使用
__all__ = ['image_bp', 'ns'] 