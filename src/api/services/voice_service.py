"""
语音处理服务
提供语音转文本、语音处理等功能
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import requests
import base64
from src.utils.logging import get_logger

# 配置日志
logger = get_logger(__name__)

# 配置参数
APPID = "2681841047"      # 替换为你的AppID
TOKEN = ''

@dataclass
class RecognitionSession:
    """语音识别会话"""
    session_id: str  # 会话ID
    sid: str  # Socket.IO会话ID
    asr_client: Optional[Any] = None
    ws_conn: Optional[Any] = None
    last_active: float = 0.0
    is_active: bool = True
    audio_queue: List[bytes] = field(default_factory=list)

class VoiceService:
    """语音处理服务"""
    
    def __init__(self):
        """初始化服务"""
        self.sessions: Dict[str, RecognitionSession] = {}
        self.loop = asyncio.new_event_loop()
    
    def voice_to_text(self, audio_bytes: bytes, file_format: str = "mp3") -> Dict[str, Any]:
        """
        将语音文件转换为文本
        
        Args:
            audio_bytes: 音频数据
            file_format: 文件格式（mp3, wav, pcm, ogg）
            
        Returns:
            Dict[str, Any]: 转换结果，包含以下字段：
                - success: 是否成功
                - text: 识别的文本内容（如果成功）
                - file_type: 文件格式
                - metadata: 元数据
                    - duration_seconds: 音频时长（秒）
                    - paragraphs_count: 段落数量
                    - paragraphs_info: 段落信息列表
                    - word_count_total: 总词数
                - error: 错误信息（如果失败）
        """
        try:
            # 记录开始处理时间
            start_time = time.time()
            logger.info(f"开始处理音频文件，大小: {len(audio_bytes) / 1024:.2f}KB，格式: {file_format}")

            # 提交任务
            task_id, log_id = self._submit_task(audio_bytes, file_format)
            logger.info(f"获取到 task_id: {task_id}, log_id: {log_id}")

            # 轮询查询结果
            max_retries = 30  # 最大重试次数
            retry_interval = 1  # 重试间隔（秒）

            for i in range(max_retries):
                try:
                    logger.info(f"第 {i + 1} 次调用 query_task 函数")
                    result = self._query_task(task_id, log_id)
                    if not result:
                        logger.warning("query_task 返回空结果")
                        time.sleep(retry_interval)
                        continue

                    status_code = result.headers.get('X-Api-Status-Code')
                    logger.info(f"获取到状态码: {status_code}")

                    if status_code == '20000000':  # 成功
                        response_data = result.json()

                        # 解析返回结果
                        full_text = response_data.get("result", {}).get("text", "")
                        utterances = response_data.get("result", {}).get("utterances", [])
                        audio_duration = response_data.get("audio_info", {}).get("duration", 0) / 1000  # ms转秒

                        # 计算处理时间
                        process_time = time.time() - start_time
                        logger.info(f"音频处理完成，耗时: {process_time:.2f}秒, 音频时长: {audio_duration:.2f}秒")

                        # 计算段落时长信息
                        paragraphs_info = []
                        for utterance in utterances:
                            paragraphs_info.append({
                                "text": utterance.get("text", ""),
                                "start_time": utterance.get("start_time", 0) / 1000,
                                "end_time": utterance.get("end_time", 0) / 1000,
                                "word_count": len(utterance.get("words", []))
                            })

                        return {
                            "success": True,
                            "text": full_text,
                            "file_type": file_format,
                            "metadata": {
                                "duration_seconds": audio_duration,
                                "paragraphs_count": len(utterances),
                                "paragraphs_info": paragraphs_info,
                                "word_count_total": sum(len(u.get("words", [])) for u in utterances),
                                "process_time_seconds": process_time
                            }
                        }
                    elif status_code in ('20000001', '20000002'):  # 处理中
                        logger.info(f"音频处理中，重试次数: {i + 1}/{max_retries}")
                        time.sleep(retry_interval)
                        continue
                    else:  # 失败
                        logger.error(f"音频处理失败，状态码: {status_code}")
                        return {
                            "success": False,
                            "error": result.headers.get('X-Api-Message', '处理失败'),
                            "file_type": file_format
                        }
                except Exception as e:
                    logger.error(f"查询任务状态失败: {str(e)}", exc_info=True)
                    return {
                        "success": False,
                        "error": f"查询任务状态失败: {str(e)}",
                        "file_type": file_format
                    }

            # 超过最大重试次数
            logger.error(f"音频处理超时，已重试 {max_retries} 次")
            return {
                "success": False,
                "error": "处理超时，请稍后重试或使用较短的音频",
                "file_type": file_format
            }

        except Exception as e:
            logger.error(f"语音转文本失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "file_type": file_format
            }
    
    def _submit_task(self, audio_bytes: bytes, file_format: str) -> tuple:
        """
        提交语音识别任务
        
        Args:
            audio_bytes: 音频数据
            file_format: 文件格式
            
        Returns:
            tuple: (task_id, log_id)
        """
        submit_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
        
        task_id = str(uuid.uuid4())
        headers = {
            "X-Api-App-Key": APPID,
            "X-Api-Access-Key": TOKEN,
            "X-Api-Resource-Id": "volc.bigasr.auc",
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": "-1",
            "Content-Type": "application/json"
        }

        # 将字节流编码为Base64字符串
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        request = {
            "user": {"uid": "fake_uid"},
            "audio": {
                "data": audio_base64,
                "format": file_format,
                "codec": "raw",
                "rate": 16000,
                "bits": 16,
                "channel": 1
            },
            "request": {
                "model_name": "bigmodel",
                "show_utterances": True,
                "corpus": {"correct_table_name": "", "context": ""}
            }
        }

        logger.info(f'提交任务: {task_id}')
        response = requests.post(submit_url, data=json.dumps(request), headers=headers)
        
        if response.headers.get("X-Api-Status-Code") == "20000000":
            log_id = response.headers.get("X-Tt-Logid")
            logger.info(f'提交成功. Logid: {log_id}')
            return task_id, log_id
        else:
            error_msg = f'提交失败: {response.headers}'
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _query_task(self, task_id: str, log_id: str) -> Optional[requests.Response]:
        """
        查询语音识别任务结果
        
        Args:
            task_id: 任务ID
            log_id: 日志ID
            
        Returns:
            Optional[requests.Response]: 响应对象，如果失败则返回None
        """
        query_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
        headers = {
            "X-Api-App-Key": APPID,
            "X-Api-Access-Key": TOKEN,
            "X-Api-Resource-Id": "volc.bigasr.auc",
            "X-Api-Request-Id": task_id,
            "X-Tt-Logid": log_id,
            "Content-Type": "application/json"
        }
        
        request = {
            "task_id": task_id
        }
        
        response = requests.post(query_url, data=json.dumps(request), headers=headers)
        
        if response.status_code == 200:
            return response
        else:
            logger.error(f"查询失败: {response.status_code}")
            return None