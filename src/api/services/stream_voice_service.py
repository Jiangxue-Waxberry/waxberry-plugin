# import asyncio
# import logging
# import queue
# import threading
# import time
# import uuid
# from dataclasses import dataclass, field
# from typing import Dict, Any, Optional
# 
# from src.core.voice.doubao_stream_voice_extractor import DoubaoStreamVoiceExtractor
# 
# # 配置日志
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger("voice_recognition_service")
# 
# @dataclass
# class RecognitionSession:
#     """语音识别会话"""
#     session_id: str  # 会话ID
#     sid: str  # Socket.IO会话ID
#     asr_client: Optional[DoubaoStreamVoiceExtractor] = None
#     ws_conn: Optional[Any] = None
#     last_active: float = 0.0
#     is_active: bool = True
#     audio_queue: queue.Queue = field(default_factory=queue.Queue)
# 
# class StreamVoiceService:
#     """语音识别服务"""
# 
#     def __init__(self):
#         self.sessions: Dict[str, RecognitionSession] = {}
#         self.asr_task_queue = queue.Queue()
#         self.asr_loop = None
#         self.asr_thread = None
#         # 创建全局事件循环
#         self.loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(self.loop)
# 
#     def create_asr_client(self, session_id: str) -> DoubaoStreamVoiceExtractor:
#         """创建ASR客户端"""
#         max_retries = 3
#         retry_count = 0
#         
#         while retry_count < max_retries:
#             try:
#                 logger.info(f"为会话 {session_id} 创建ASR客户端 (尝试 {retry_count + 1}/{max_retries})")
#                 client = DoubaoStreamVoiceExtractor(
#                     streaming=True,
#                     seg_duration=100,
#                     format='pcm',
#                     rate=16000,
#                     channel=1,
#                     bits=16,
#                     codec='raw',
#                     uid="test_user",
#                     auth_method="none",
#                     ws_url="wss://openspeech.bytedance.com/api/v3/sauc/bigmodel",
#                     hot_words=None
#                 )
#                 
#                 # 使用全局事件循环初始化ASR客户端
#                 try:
#                     logger.info(f"初始化ASR客户端: {session_id}")
#                     self.loop.run_until_complete(client.process_chunk(b''))
#                     logger.info(f"ASR客户端创建成功: {session_id}")
#                     return client
#                 except Exception as init_error:
#                     logger.error(f"初始化ASR客户端失败: {str(init_error)}", exc_info=True)
#                     retry_count += 1
#                     if retry_count < max_retries:
#                         logger.info(f"等待重试 ({retry_count}/{max_retries})...")
#                         time.sleep(1)  # 等待1秒后重试
#                         continue
#                     raise
#                     
#             except Exception as e:
#                 logger.error(f"创建ASR客户端失败: {str(e)}", exc_info=True)
#                 retry_count += 1
#                 if retry_count < max_retries:
#                     logger.info(f"等待重试 ({retry_count}/{max_retries})...")
#                     time.sleep(1)  # 等待1秒后重试
#                     continue
#                 raise Exception(f"创建ASR客户端失败 (已重试 {retry_count} 次): {str(e)}")
# 
#     def process_audio_data(self, audio_bytes: bytes, session_id: str):
#         """处理音频数据"""
#         try:
#             if session_id not in self.sessions:
#                 logger.error(f"会话不存在: {session_id}")
#                 return {
#                     'error': '会话不存在',
#                     'details': f"会话ID: {session_id}"
#                 }
# 
#             session = self.sessions[session_id]
#             if not session.asr_client:
#                 logger.error(f"ASR客户端未初始化: {session_id}")
#                 return {
#                     'error': 'ASR客户端未初始化',
#                     'details': f"会话ID: {session_id}"
#                 }
# 
#             # 处理音频数据
#             try:
#                 # 使用全局事件循环处理音频数据
#                 coro = session.asr_client.process_chunk(audio_bytes)
#                 result = self.loop.run_until_complete(coro)
# 
#                 logger.info(f"音频处理结果: {result}")
# 
#                 # 发送识别结果
#                 if result and ('partial_text' in result or 'full_text' in result):
#                     # 只有当有新的增量文本时才发送事件
#                     if result.get('partial_text'):
#                         return {
#                             'partial_text': result['partial_text'],
#                             'full_text': result.get('full_text', ''),
#                             'sequence': result.get('sequence', 0),
#                             'is_final': result.get('is_final', False),
#                             'timestamp': time.time(),
#                             'session_id': session_id
#                         }
#                 elif result and 'error' in result:
#                     logger.error(f"ASR处理错误: {result['error']}")
#                     return {
#                         'error': 'ASR处理错误',
#                         'details': result['error']
#                     }
#                 else:
#                     logger.warning(f"未收到有效的识别结果: {result}")
#                     return None
# 
#             except Exception as e:
#                 logger.error(f"处理音频数据失败: {str(e)}", exc_info=True)
#                 # 尝试重新初始化ASR客户端
#                 try:
#                     logger.info(f"尝试重新初始化ASR客户端: {session_id}")
#                     session.asr_client = self.create_asr_client(session_id)
#                     return {
#                         'error': 'ASR客户端已重新初始化',
#                         'details': str(e)
#                     }
#                 except Exception as reinit_error:
#                     logger.error(f"重新初始化ASR客户端失败: {str(reinit_error)}", exc_info=True)
#                     return {
#                         'error': '处理音频数据失败',
#                         'details': f"原始错误: {str(e)}, 重新初始化错误: {str(reinit_error)}"
#                     }
# 
#         except Exception as e:
#             logger.error(f"处理音频数据时发生错误: {str(e)}", exc_info=True)
#             return {
#                 'error': '处理音频数据时发生错误',
#                 'details': str(e)
#             }
# 
#     def create_session(self, sid: str) -> str:
#         """创建新的识别会话"""
#         try:
#             # 生成新的会话ID
#             session_id = str(uuid.uuid4())
#             logger.info(f"创建新会话: {session_id}, 客户端: {sid}")
# 
#             # 创建会话对象
#             session = RecognitionSession(session_id, sid)
#             self.sessions[session_id] = session
# 
#             # 初始化ASR客户端
#             session.asr_client = self.create_asr_client(session_id)
# 
#             return session_id
# 
#         except Exception as e:
#             logger.error(f"创建会话失败: {str(e)}", exc_info=True)
#             raise
# 
#     def cleanup_session(self, session_id: str):
#         """清理会话资源"""
#         if session_id in self.sessions:
#             session = self.sessions[session_id]
#             if session.asr_client:
#                 try:
#                     # 使用全局事件循环关闭WebSocket连接
#                     self.loop.run_until_complete(session.asr_client.process_chunk(b''))
#                     logger.info(f"已关闭ASR客户端WebSocket连接: {session_id}")
#                 except Exception as e:
#                     logger.error(f"关闭ASR客户端WebSocket连接失败: {str(e)}")
# 
#             session.asr_client = None
#             session.is_active = False
#             del self.sessions[session_id]
#             logger.info(f"会话已清理: {session_id}")
# 
#     def cleanup_client_sessions(self, sid: str):
#         """清理客户端的所有会话"""
#         sessions_to_remove = [
#             session_id for session_id, session in self.sessions.items()
#             if session.sid == sid
#         ]
#         for session_id in sessions_to_remove:
#             self.cleanup_session(session_id)
# 
#     def get_session(self, session_id: str) -> Optional[RecognitionSession]:
#         """获取会话对象"""
#         return self.sessions.get(session_id)