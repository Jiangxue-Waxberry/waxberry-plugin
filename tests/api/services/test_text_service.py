"""
文本服务测试模块
测试文本服务的各项功能
"""

import pytest
from src.api.services.text_service import TextService
from src.utils.logging import get_logger
import os
import tempfile
from pathlib import Path
import json
from src.api.app import create_app

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
    
    # 创建文本文件
    text_file = TEST_DATA_DIR / 'test.txt'
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write('这是一个测试文本文件\n包含多行内容\n用于测试文本提取功能')
    files['text'] = text_file
    
    # 使用已存在的DOCX文件
    docx_file = TEST_DATA_DIR / 'test.docx'
    if docx_file.exists():
        files['docx'] = docx_file
    
    # 使用已存在的PDF文件
    pdf_file = TEST_DATA_DIR / 'test.pdf'
    if pdf_file.exists():
        files['pdf'] = pdf_file
    
    yield files
    
    # 清理测试文件
    for file in files.values():
        if file.exists() and file.name not in ['test.docx', 'test.pdf']:  # 不删除已存在的文件
            file.unlink()
    if TEST_DATA_DIR.exists() and not any(TEST_DATA_DIR.iterdir()):  # 只在目录为空时删除
        TEST_DATA_DIR.rmdir()

def test_api_extract_file(client, test_files):
    """测试文件上传接口 /api/v1/extract"""
    # 测试文本文件
    with open(test_files['text'], 'rb') as f:
        response = client.post('/api/v1/extract',
                             data={'file': (f, 'test.txt')},
                             content_type='multipart/form-data')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert '这是一个测试文本文件' in data['text']
    
    # 测试DOCX文件
    if 'docx' in test_files:
        with open(test_files['docx'], 'rb') as f:
            response = client.post('/api/v1/extract',
                                 data={'file': (f, 'test.docx')},
                                 content_type='multipart/form-data')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    # 测试PDF文件
    if 'pdf' in test_files:
        with open(test_files['pdf'], 'rb') as f:
            response = client.post('/api/v1/extract',
                                 data={'file': (f, 'test.pdf')},
                                 content_type='multipart/form-data')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    # 测试错误情况
    # 1. 没有上传文件
    response = client.post('/api/v1/extract')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'No file part in the request' in data['error']
    
    # 2. 没有选择文件
    response = client.post('/api/v1/extract',
                         data={'file': (None, '')},
                         content_type='multipart/form-data')
    assert response.status_code == 400
    data = json.loads(response.data)
    print(data)
    assert data['success'] is False
    assert 'No file selected' in data['error']

def test_api_extract_bytes(client, test_files):
    """测试二进制数据接口 /api/v1/extract/bytes"""

    # 测试DOCX文件
    if 'docx' in test_files:
        with open(test_files['docx'], 'rb') as f:
            content = f.read()
        response = client.post('/api/v1/extract/bytes',
                             data=content,
                             content_type='application/octet-stream',
                             query_string={'file_type': 'docx'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    # 测试PDF文件
    if 'pdf' in test_files:
        with open(test_files['pdf'], 'rb') as f:
            content = f.read()
        response = client.post('/api/v1/extract/bytes',
                             data=content,
                             content_type='application/octet-stream',
                             query_string={'file_type': 'pdf'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    # 测试错误情况
    # 1. 没有二进制数据
    response = client.post('/api/v1/extract/bytes')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'No data in the request body' in data['error']
    
    # 2. 没有文件类型
    response = client.post('/api/v1/extract/bytes',
                         data=b'test content',
                         content_type='application/octet-stream')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert "Missing 'file_type' parameter" in data['error']
    
    # 3. 不支持的文件类型
    response = client.post('/api/v1/extract/bytes',
                         data=b'test content',
                         content_type='application/octet-stream',
                         query_string={'file_type': 'xyz'})
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data['success'] is False
    assert '不支持的文件类型' in data['error']