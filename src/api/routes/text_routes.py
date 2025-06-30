"""
文本处理路由模块

本模块提供文本处理相关的API接口，主要功能包括：
1. 解析文件内容 (extract)：支持多种文件格式的解析
2. 流式解析文件内容 (extract/bytes)：支持直接传输文件字节流
3. 支持多种文件格式：docx, pdf, txt等
4. 提供详细的解析参数配置

API 接口说明：
1. api/v1/extract (POST)
   - 功能：解析文件内容
   - 请求格式：multipart/form-data
   - 参数：
     * file：提示词文本
   - 响应格式：
     * 成功：返回生成的文本内容
     * 失败：返回错误信息

2. http://localhost:9020/api/v1/extract/bytes (POST)
   - 功能：解析文件内容
   - 请求格式：application/octet-stream
   - 参数：
     * 文件字节流
   - 响应格式：
     * 成功：返回生成的文本内容
     * 失败：返回错误信息

使用示例：
1. 普通文本生成：
   curl -X POST "http://localhost:9020/api/v1/extract" \
       -F "file=@C:/test/test.docx" \
       -H "Content-Type: multipart/form-data" \

2. 流式文本生成：
   curl -X POST "http://localhost:9020/api/v1/extract/bytes?file_type=docx" \
       -H "Content-Type: application/octet-stream" \
       --data-binary "@C:/test/test.docx"
"""

from flask import Blueprint, request, jsonify
from flask_restx import Resource, Namespace, fields
from src.api.services.text_service import TextService
from src.utils.logging import get_logger
import tempfile
import os

# 创建蓝图
text_bp = Blueprint('text', __name__)

# 创建命名空间
ns = Namespace('text', description='文本处理接口')

# 创建日志记录器
logger = get_logger(__name__)

# 创建文本服务实例
text_service = TextService()

# 定义响应模型
error_model = ns.model('Error', {
    'error': fields.String(description='错误信息')
})

success_model = ns.model('Success', {
    'success': fields.Boolean(description='是否成功'),
    'message': fields.String(description='处理结果信息'),
    'data': fields.Raw(description='处理结果数据')
})

@ns.route('/api/v1/extract')
class TextExtract(Resource):
    @ns.doc('extract_text',
        responses={
            200: ('成功', success_model),
            400: ('请求参数错误', error_model),
            500: ('服务器错误', error_model)
        }
    )
    @ns.expect(ns.parser().add_argument('file', type='FileStorage', location='files', required=True, help='要提取文本的文件'))
    def post(self):
        """
        从上传的文件中提取文本
        
        功能：
        1. 接收上传的文件
        2. 提取文件中的文本内容
        3. 返回提取的文本和元数据
        
        支持的文件类型：
        - Word文档 (.docx)
        - Excel表格 (.xlsx)
        - PDF文件 (.pdf)
        - 文本文件 (.txt)
        
        请求格式：
        - Content-Type: multipart/form-data
        - 参数：
          - file: 要提取文本的文件
        
        响应格式：
        {
            "success": true/false,
            "message": "处理结果信息",
            "data": {
                "text": "提取的文本内容",
                "metadata": {
                    "filename": "文件名",
                    "file_type": "文件类型",
                    "file_size": "文件大小",
                    "page_count": "页数"（如果适用）
                }
            }
        }
        
        错误响应：
        - 400: 请求参数错误（未提供文件或文件为空）
        - 500: 服务器错误（文件处理失败）
        """
        if 'file' not in request.files:
            return {'error': 'No file part in the request'}, 400
            
        file = request.files['file']
        if file.filename == '':
            return {'error': 'No file selected'}, 400
        
        try:
            # 创建临时文件
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, file.filename)
            file.save(temp_file_path)
            
            try:
                # 提取文本
                result = text_service.extract_text_from_file(temp_file_path)
                return result
            finally:
                # 清理临时文件
                os.remove(temp_file_path)
                os.rmdir(temp_dir)
            
        except Exception as e:
            logger.error(f"文本提取失败: {str(e)}")
            return {'error': str(e)}, 500

@ns.route('/api/v1/extract/bytes')
class TextExtractBytes(Resource):
    @ns.doc('extract_text_bytes',
        responses={
            200: ('成功', success_model),
            400: ('请求参数错误', error_model),
            500: ('服务器错误', error_model)
        }
    )
    @ns.expect(ns.parser().add_argument('file_type', type=str, location='query', required=True, help='文件类型 (例如 docx, xlsx, pdf)'))
    def post(self):
        """
        从二进制数据中提取文本
        
        功能：
        1. 接收文件的二进制数据
        2. 根据指定的文件类型提取文本
        3. 返回提取的文本和元数据
        
        支持的文件类型：
        - docx: Word文档
        - xlsx: Excel表格
        - pdf: PDF文件
        - txt: 文本文件
        
        请求格式：
        - Content-Type: application/octet-stream
        - 请求体: 文件的二进制数据
        - 查询参数：
          - file_type: 文件类型（必填）
        
        响应格式：
        {
            "success": true/false,
            "message": "处理结果信息",
            "data": {
                "text": "提取的文本内容",
                "metadata": {
                    "file_type": "文件类型",
                    "file_size": "文件大小",
                    "page_count": "页数"（如果适用）
                }
            }
        }
        
        错误响应：
        - 400: 请求参数错误（未提供数据或文件类型）
        - 500: 服务器错误（文件处理失败）
        """
        if not request.data:
            return {'error': 'No data in the request body'}, 400
            
        file_type = request.args.get('file_type')
        if not file_type:
            return {'error': "Missing 'file_type' parameter"}, 400
        
        try:
            # 提取文本
            result = text_service.extract_text_from_bytes(request.data, file_type)
            
            # 检查是否成功
            if not result.get('success', False):
                return jsonify({
                    "success": False,
                    "error": result.get('error', 'Unknown error')
                }), 500
            
            # 返回结果
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"文本提取失败: {str(e)}")
            return {'error': str(e)}, 500

# 保留原有的API路由
@text_bp.route('/api/v1/extract', methods=['POST'])
def text_routes():
    """
    从上传的文件中提取文本的API接口
    
    功能：
    1. 接收上传的文件
    2. 提取文件中的文本内容
    3. 返回提取的文本和元数据
    
    请求格式：
    - Content-Type: multipart/form-data
    - 参数：
      - file: 要提取文本的文件
    
    响应格式：
    {
        "success": true/false,
        "message": "处理结果信息",
        "data": {
            "text": "提取的文本内容",
            "metadata": {
                "filename": "文件名",
                "file_type": "文件类型",
                "file_size": "文件大小",
                "page_count": "页数"（如果适用）
            }
        }
    }
    """
    if 'file' not in request.files:
        return jsonify({
            "success": False,
            "error": "No file part in the request"
        }), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "success": False,
            "error": "No file selected"
        }), 400
    
    try:
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        file.save(temp_file_path)
        
        try:
            # 提取文本
            result = text_service.extract_text_from_file(temp_file_path)
            return jsonify(result)
        finally:
            # 清理临时文件
            os.remove(temp_file_path)
            os.rmdir(temp_dir)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@text_bp.route('/api/v1/extract/bytes', methods=['POST'])
def extract_text_from_bytes():
    """
    从请求体中的二进制数据提取文本
    
    功能：
    1. 接收文件的二进制数据
    2. 根据指定的文件类型提取文本
    3. 返回提取的文本和元数据
    
    请求格式：
    - Content-Type: application/octet-stream
    - 请求体: 文件的二进制数据
    - 查询参数：
      - file_type: 文件类型（必填）
    
    响应格式：
    {
        "success": true/false,
        "message": "处理结果信息",
        "data": {
            "text": "提取的文本内容",
            "metadata": {
                "file_type": "文件类型",
                "file_size": "文件大小",
                "page_count": "页数"（如果适用）
            }
        }
    }
    """
    if not request.data:
        return jsonify({
            "success": False,
            "error": "No data in the request body"
        }), 400
        
    file_type = request.args.get('file_type')
    if not file_type:
        return jsonify({
            "success": False,
            "error": "Missing 'file_type' parameter"
        }), 400
    
    try:
        # 提取文本
        result = text_service.extract_text_from_bytes(request.data, file_type)
        
        # 检查是否成功
        if not result.get('success', False):
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error')
            }), 500
        
        # 返回结果
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 导出命名空间供app.py使用
__all__ = ['text_bp', 'ns'] 