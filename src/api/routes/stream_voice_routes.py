"""
实时语音识别服务模块

本模块提供基于WebSocket的实时语音识别服务，主要功能包括：
1. 实时语音转文本：支持流式音频数据的实时识别
2. 支持多种音频格式：pcm, wav
3. 支持实时流式传输：通过WebSocket连接持续发送音频数据
4. 提供增量识别结果：支持实时返回部分识别结果

WebSocket 事件说明：
1. 连接事件：
   - 事件名：connect
   - 功能：建立WebSocket连接
   - 响应：返回connection_established事件，包含client_id

2. 开始识别：
   - 事件名：start_recognition
   - 功能：开始新的语音识别会话
   - 响应：返回session_created事件，包含session_id

3. 音频数据：
   - 事件名：audio_chunk
   - 功能：发送音频数据块
   - 参数：
     * session_id：会话ID
     * audio_data：Base64编码的音频数据
   - 响应：返回audio_received事件

4. 识别结果：
   - 事件名：partial_result
   - 功能：返回部分识别结果
   - 数据：
     * partial_text：当前识别的文本
     * full_text：完整的识别文本
     * is_final：是否为最终结果
     * sequence：序列号

5. 结束识别：
   - 事件名：end_recognition
   - 功能：结束当前识别会话
   - 参数：session_id
   - 响应：返回session_ended事件

使用示例：
1. 建立连接：
   const socket = io('http://localhost:9020');

2. 开始识别：
   socket.emit('start_recognition', {}, (response) => {
     const sessionId = response.session_id;
   });

3. 发送音频数据：
   socket.emit('audio_chunk', {
     session_id: sessionId,
     audio_data: base64AudioData
   });

4. 接收识别结果：
   socket.on('partial_result', (data) => {
     console.log('识别结果:', data.partial_text);
   });

5. 结束识别：
   socket.emit('end_recognition', {
     session_id: sessionId
   });
"""

import base64
import time
import logging
import uuid
import threading
import queue
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from flask import Flask, request
from flask_socketio import SocketIO, emit
from src.core.voice.doubao_stream_voice_extractor import AsrWsClient

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("voice_recognition_api")

@dataclass
class RecognitionSession:
    """语音识别会话"""
    session_id: str  # 会话ID
    sid: str  # Socket.IO会话ID
    asr_client: Optional[AsrWsClient] = None
    ws_conn: Optional[Any] = None
    last_active: float = 0.0
    is_active: bool = True
    audio_queue: queue.Queue = field(default_factory=queue.Queue)


class VoiceRecognitionService:
    """语音识别服务"""

    def __init__(self, app: Flask, socketio: SocketIO):
        self.app = app
        self.socketio = socketio
        self.sessions: Dict[str, RecognitionSession] = {}
        self.asr_task_queue = queue.Queue()
        self.asr_thread = None
        # 创建全局事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.setup_routes()

    def setup_routes(self):
        """设置路由和事件处理器"""

        @self.socketio.on('connect')
        def handle_connect():
            """处理客户端连接"""
            client_id = request.sid
            logger.info(f"客户端连接: {client_id}")
            emit('connection_established', {
                'client_id': client_id,
                'timestamp': time.time()
            }, namespace='/')
            logger.info(f"已发送connection_established事件到客户端 {client_id}")

        @self.socketio.on('join')
        def handle_join(data):
            """处理加入房间请求"""
            room = data.get('room')
            if not room:
                logger.warning(f"客户端 {request.sid} 尝试加入房间时未提供房间名")
                return {'error': '未提供房间名'}

            try:
                # 使用socketio.server.enter_room添加客户端到房间
                self.socketio.server.enter_room(request.sid, room, namespace='/')
                logger.info(f"客户端 {request.sid} 已加入房间 {room}")
                return {'status': 'success', 'room': room}
            except Exception as e:
                logger.error(f"加入房间失败: {str(e)}")
                return {'error': str(e)}

        @self.socketio.on('error')
        def handle_error(error):
            """处理错误事件"""
            logger.error(f"收到错误事件: {error}")
            emit('error', {
                'message': 'Error received',
                'details': error,
                'timestamp': time.time()
            }, namespace='/')

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """处理客户端断开连接"""
            logger.info(f"客户端已断开连接: {request.sid}")
            self.cleanup_client_sessions(request.sid)

        @self.socketio.on('start_recognition')
        def handle_start_recognition(data):
            """开始识别会话"""
            try:
                # 生成新的会话ID
                session_id = str(uuid.uuid4())
                logger.info(f"创建新会话: {session_id}, 客户端: {request.sid}")

                # 创建会话对象
                session = RecognitionSession(session_id, request.sid)
                self.sessions[session_id] = session

                # 初始化ASR客户端
                session.asr_client = self.create_asr_client(session_id)

                # 发送会话创建事件
                emit('session_created', {
                    'session_id': session_id,
                    'timestamp': time.time()
                }, namespace='/')
                logger.info(f"已发送session_created事件到客户端 {request.sid}")

                # 添加客户端到会话房间
                self.socketio.server.enter_room(request.sid, session_id, namespace='/')
                logger.info(f"已将客户端 {request.sid} 添加到会话房间 {session_id}")

            except Exception as e:
                logger.error(f"创建会话失败: {str(e)}", exc_info=True)
                emit('error', {
                    'message': '创建会话失败',
                    'details': str(e)
                }, namespace='/')

        @self.socketio.on('audio_chunk')
        def handle_audio_chunk(data):
            """处理音频数据"""
            try:
                session_id = data.get('session_id')
                if not session_id:
                    raise ValueError("未提供会话ID")

                if session_id not in self.sessions:
                    raise ValueError(f"会话不存在: {session_id}")

                session = self.sessions[session_id]
                if not session.is_active:
                    raise ValueError(f"会话已结束: {session_id}")

                audio_data = data.get('audio_data')
                if not audio_data:
                    logger.error(f"收到空的音频数据，会话ID: {session_id}")
                    raise ValueError("未提供音频数据")

                # 解码Base64音频数据
                try:
                    audio_bytes = base64.b64decode(audio_data)
                    logger.info(f"收到音频数据: {len(audio_bytes)} 字节")
                except Exception as e:
                    logger.error(f"解码音频数据失败: {str(e)}")
                    raise ValueError(f"音频数据解码失败: {str(e)}")

                # 处理音频数据
                self.process_audio_data(audio_bytes, session_id)

                # 发送成功响应
                emit('audio_received', {
                    'status': 'success',
                    'timestamp': time.time()
                }, namespace='/')
                logger.info(f"已发送audio_received事件到客户端 {request.sid}")

            except Exception as e:
                logger.error(f"处理音频数据失败: {str(e)}", exc_info=True)
                emit('error', {
                    'message': '处理音频数据失败',
                    'details': str(e)
                }, namespace='/')
                logger.info(f"已发送错误事件到客户端 {request.sid}")

        @self.socketio.on('end_recognition')
        def handle_end_recognition(data):
            """结束识别会话"""
            session_id = data.get('session_id')
            if session_id in self.sessions:
                # 等待一小段时间，确保最后的音频数据被处理
                time.sleep(1)
                self.cleanup_session(session_id)
                emit('session_ended', {
                    'session_id': session_id,
                    'timestamp': time.time()
                }, namespace='/')
                logger.info(f"已发送session_ended事件到客户端 {request.sid}")
            else:
                logger.warning(f"尝试结束不存在的会话: {session_id}")
                emit('error', {'message': f"会话不存在: {session_id}"}, namespace='/')

    def process_audio_data(self, audio_bytes: bytes, session_id: str):
        """处理音频数据"""
        try:
            if session_id not in self.sessions:
                logger.error(f"会话不存在: {session_id}")
                return

            session = self.sessions[session_id]
            if not session.asr_client:
                logger.error(f"ASR客户端未初始化: {session_id}")
                return

            # 处理音频数据
            try:
                # 使用全局事件循环处理音频数据
                coro = session.asr_client.process_chunk(audio_bytes)
                result = self.loop.run_until_complete(coro)

                logger.info(f"音频处理结果: {result}")

                # 发送识别结果
                if result and ('partial_text' in result or 'full_text' in result):
                    # 只有当有新的增量文本时才发送事件
                    if result.get('partial_text'):
                        self.socketio.emit('partial_result', {
                            'partial_text': result['partial_text'],
                            'full_text': result.get('full_text', ''),
                            'sequence': result.get('sequence', 0),
                            'is_final': result.get('is_final', False),
                            'timestamp': time.time(),
                            'session_id': session_id
                        }, room=session_id, namespace='/')
                        logger.info(f"已发送partial_result事件到会话 {session_id}")
                elif result and 'error' in result:
                    logger.error(f"ASR处理错误: {result['error']}")
                    self.socketio.emit('error', {
                        'message': 'ASR处理错误',
                        'details': result['error']
                    }, room=session_id, namespace='/')
                else:
                    logger.warning(f"未收到有效的识别结果: {result}")

            except Exception as e:
                logger.error(f"处理音频数据失败: {str(e)}", exc_info=True)
                self.socketio.emit('error', {
                    'message': '处理音频数据失败',
                    'details': str(e)
                }, room=session_id, namespace='/')

        except Exception as e:
            logger.error(f"处理音频数据时发生错误: {str(e)}", exc_info=True)

    def create_asr_client(self, session_id: str) -> AsrWsClient:
        """创建ASR客户端"""
        try:
            logger.info(f"为会话 {session_id} 创建ASR客户端")
            client = AsrWsClient(
                audio_path=None,
                streaming=True,
                seg_duration=100,
                format='pcm',
                rate=16000,
                channel=1,
                bits=16,
                codec='raw',
                uid="test_user",
                auth_method="none",
                ws_url="wss://openspeech.bytedance.com/api/v3/sauc/bigmodel",
                hot_words=None
            )
            # 使用全局事件循环初始化ASR客户端
            self.loop.run_until_complete(client.process_chunk(b''))
            logger.info(f"ASR客户端创建成功: {session_id}")
            return client
        except Exception as e:
            logger.error(f"创建ASR客户端失败: {str(e)}", exc_info=True)
            raise

    def create_result_callback(self, session_id: str):
        """创建结果回调函数"""

        def callback(result):
            try:
                if 'error' in result:
                    logger.error(f"ASR处理错误: {result['error']}")
                    self.socketio.emit('error', {
                        'message': 'ASR处理错误',
                        'details': result['error']
                    }, room=session_id, namespace='/')  # 使用session_id作为room
                    return

                if session_id not in self.sessions:
                    logger.warning(f"会话 {session_id} 已不存在")
                    return

                session = self.sessions[session_id]
                text = result.get('partial_text', '')
                logger.info(f"识别结果: {text}")

                # 使用self.socketio.emit发送事件
                self.socketio.emit('partial_result', {
                    'partial_text': text,
                    'is_final': result.get('is_final', False),
                    'timestamp': time.time(),
                    'session_id': session_id
                }, room=session_id, namespace='/')  # 使用session_id作为room
                logger.info(f"已发送partial_result事件到会话 {session_id}")

                # 添加调试信息
                logger.debug(f"事件发送详情:")
                logger.debug(f"- 事件名称: partial_result")
                logger.debug(f"- 会话ID: {session_id}")
                logger.debug(f"- 房间: {session_id}")
                logger.debug(f"- 命名空间: /")
                logger.debug(f"- 数据: {text}")

            except Exception as e:
                logger.error(f"处理ASR结果错误: {str(e)}", exc_info=True)
                try:
                    self.socketio.emit('error', {
                        'message': '处理ASR结果错误',
                        'details': str(e)
                    }, room=session_id, namespace='/')  # 使用session_id作为room
                except:
                    pass

        return callback

    def cleanup_session(self, session_id: str):
        """清理会话资源"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if session.asr_client:
                try:
                    # 使用全局事件循环关闭WebSocket连接
                    self.loop.run_until_complete(session.asr_client.process_chunk(b''))
                    logger.info(f"已关闭ASR客户端WebSocket连接: {session_id}")
                except Exception as e:
                    logger.error(f"关闭ASR客户端WebSocket连接失败: {str(e)}")

            session.asr_client = None
            session.is_active = False
            del self.sessions[session_id]
            logger.info(f"会话已清理: {session_id}")

    def cleanup_client_sessions(self, sid: str):
        """清理客户端的所有会话"""
        sessions_to_remove = [
            session_id for session_id, session in self.sessions.items()
            if session.sid == sid
        ]
        for session_id in sessions_to_remove:
            self.cleanup_session(session_id)

    def asr_worker(self):
        """ASR工作线程"""
        while True:
            try:
                task = self.asr_task_queue.get()
                if task is None:  # 收到停止信号
                    break
                # 处理任务
                self.asr_task_queue.task_done()
            except Exception as e:
                logger.error(f"ASR工作线程错误: {str(e)}", exc_info=True)

    def start_asr_worker(self):
        """启动ASR工作线程"""
        if self.asr_thread is None or not self.asr_thread.is_alive():
            self.asr_thread = threading.Thread(target=self.asr_worker, daemon=True)
            self.asr_thread.start()

    def stop_asr_worker(self):
        """停止ASR工作线程"""
        if self.asr_thread and self.asr_thread.is_alive():
            self.asr_task_queue.put(None)
            self.asr_thread.join(timeout=5)
            logger.info("ASR工作线程已停止")