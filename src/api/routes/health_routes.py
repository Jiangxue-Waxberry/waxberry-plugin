"""
健康检查路由
提供API服务状态检查接口
"""

from flask import Blueprint, jsonify
from flask_restx import Resource, Namespace

# 创建蓝图
health_bp = Blueprint('health', __name__)

# 创建命名空间
ns = Namespace('health', description='健康检查接口')

@ns.route('/')
class HealthCheck(Resource):
    @ns.doc('health_check',
        responses={
            200: '成功',
            500: '服务器错误'
        }
    )
    def get(self):
        """
        健康检查接口
        
        用于检查API服务是否正常运行
        
        Returns:
            dict: 包含服务状态的响应
        """
        return {
            "status": "ok",
            "message": "API service is running",
            "version": "1.0.0"
        }

# 添加直接的健康检查路由
@health_bp.route('/health')
def health_check():
    """
    健康检查接口
    
    用于检查API服务是否正常运行
    
    Returns:
        dict: 包含服务状态的响应
    """
    return jsonify({
        "status": "ok",
        "message": "API service is running",
        "version": "1.0.0"
    })

# 导出命名空间供app.py使用
__all__ = ['health_bp', 'ns'] 