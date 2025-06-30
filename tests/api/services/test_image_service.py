"""
图片服务测试模块
测试图片服务的各项功能，包括图片转文本和文本转图片
"""

import pytest
from src.api.services.image_service import ImageService
from src.utils.logging import get_logger
import os
import tempfile
from pathlib import Path
import json
from src.api.app import create_app
from PIL import Image
import io

# 创建日志记录器
logger = get_logger(__name__)

# 测试数据目录
TEST_DATA_DIR = Path(__file__).parent / 'uploads'

@pytest.fixture
def app():
    """创建Flask应用实例"""
    app = create_app()
    app.config.update({
        'TESTING': True,
    })
    return app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def test_files():
    """准备测试文件"""
    # 确保测试数据目录存在
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 创建测试文件
    files = {}

    # 使用已存在的图片文件
    image_file = TEST_DATA_DIR / 'test.jpg'
    if image_file.exists():
        files['image'] = image_file

    yield files

    # 清理测试文件
    for file in files.values():
        if file.exists() and file.name not in ['test.jpg']:  # 不删除已存在的图片文件
            file.unlink()
    if TEST_DATA_DIR.exists() and not any(TEST_DATA_DIR.iterdir()):  # 只在目录为空时删除
        TEST_DATA_DIR.rmdir()

def test_api_image_to_text_form_upload(client, test_files):
    """测试图片转文本接口 - 表单文件上传方式 /api/v1/imageToText"""
    print("\n=== 测试图片转文本接口 - 表单文件上传方式 ===")

    # 测试图片文件
    if 'image' in test_files:
        print("\n1. 测试不带问题的上传")
        # 测试不带问题的上传
        with open(test_files['image'], 'rb') as f:
            response = client.post('/api/v1/imageToText',
                                 data={'file': (f, 'test.jpg')},
                                 content_type='multipart/form-data')
        assert response.status_code == 200
        data = json.loads(response.data)
        print(f"响应状态码: {response.status_code}")
        print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        assert data['success'] is True
        assert 'text' in data

        print("\n2. 测试带问题的上传")
        # 测试带问题的上传
        with open(test_files['image'], 'rb') as f:
            response = client.post('/api/v1/imageToText',
                                 data={
                                     'file': (f, 'test.jpg'),
                                     'question': '这张图片是什么？'
                                 },
                                 content_type='multipart/form-data')
        assert response.status_code == 200
        data = json.loads(response.data)
        print(f"响应状态码: {response.status_code}")
        print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        assert data['success'] is True
        assert 'text' in data

    print("\n3. 测试错误情况")
    # 测试错误情况
    # 1. 没有上传文件
    print("\n3.1 没有上传文件")
    response = client.post('/api/v1/imageToText')
    assert response.status_code == 400
    data = json.loads(response.data)
    print(f"响应状态码: {response.status_code}")
    print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    assert data['success'] is False
    assert '请上传图片文件或提供图片数据' in data['error']

    # 2. 上传空文件
    print("\n3.2 上传空文件")
    response = client.post('/api/v1/imageToText',
                          data={'file': (io.BytesIO(b''), 'test.jpg')},
                          content_type='multipart/form-data')
    assert response.status_code == 400
    data = json.loads(response.data)
    print(f"响应状态码: {response.status_code}")
    print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    assert data['success'] is False
    assert '无法处理上传的图片文件' in data['error']

    # 3. 上传不支持的文件类型
    print("\n3.3 上传不支持的文件类型")
    if 'image' in test_files:
        with open(test_files['image'], 'rb') as f:
            response = client.post('/api/v1/imageToText',
                                 data={'file': (f, 'test.xyz')},
                                 content_type='multipart/form-data')
        assert response.status_code == 400
        data = json.loads(response.data)
        print(f"响应状态码: {response.status_code}")
        print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        assert data['success'] is False
        assert '仅支持以下图片格式' in data['error']

def test_api_image_to_text_binary_upload(client, test_files):
    """测试图片转文本接口 - 二进制流上传方式 /api/v1/imageToText"""
    # 测试图片文件
    if 'image' in test_files:
        # 测试不带问题的上传
        with open(test_files['image'], 'rb') as f:
            content = f.read()
        response = client.post('/api/v1/imageToText',
                             data=content,
                             content_type='application/octet-stream')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'text' in data

        # 测试带问题的上传
        response = client.post('/api/v1/imageToText',
                             data=content,
                             content_type='application/octet-stream',
                             query_string={'question': '这张图片是什么？'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'text' in data

    # 测试错误情况
    # 1. 没有数据
    response = client.post('/api/v1/imageToText',
                         data=b'',
                         content_type='application/octet-stream')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert '未接收到图片数据' in data['error']

    # 2. 无效的图片数据
    response = client.post('/api/v1/imageToText',
                         data=b'invalid image data',
                         content_type='application/octet-stream')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert '无法处理二进制流中的图片数据' in data['error']

def test_api_text_to_image(client):
    """测试文本转图片接口 /api/v1/textToImage"""
    # 测试正常情况
    test_prompt = "一只可爱的猫咪"
    response = client.post('/api/v1/textToImage',
                         json={'prompt': test_prompt})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'image_url' in data

    # 测试错误情况
    # 1. 没有提供prompt
    response = client.post('/api/v1/textToImage',
                         json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert "Missing 'prompt' in request body" in data['error']

    # 2. prompt为空
    response = client.post('/api/v1/textToImage',
                         json={'prompt': ''})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'prompt cannot be empty' in data['error']