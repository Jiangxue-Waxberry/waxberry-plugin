import json
import time
import uuid
import requests
import base64
import logging
from typing import Dict, Any, Optional, Tuple, Union
from pathlib import Path
from src.config.settings import settings

# 配置日志
logger = logging.getLogger(__name__)

class VoiceFileConfig:
    """语音文件处理配置类"""
    def __init__(
        self,
        app_id: str = settings.doubao_app_id,
        token: str = settings.doubao_token,
        base_url: str = settings.doubao_base_url,
        default_uid: str = "fake_uid",
        default_format: str = "mp3",
        default_rate: int = 16000,
        default_bits: int = 16,
        default_channel: int = 1
    ):
        """
        初始化配置
        
        Args:
            app_id: 应用ID
            token: 访问令牌
            base_url: API基础URL
            default_uid: 默认用户ID
            default_format: 默认音频格式
            default_rate: 默认采样率
            default_bits: 默认位深度
            default_channel: 默认声道数
        """
        self.app_id = app_id
        self.token = token
        self.base_url = base_url
        self.default_uid = default_uid
        self.default_format = default_format
        self.default_rate = default_rate
        self.default_bits = default_bits
        self.default_channel = default_channel

class VoiceFileClient:
    """语音文件处理客户端"""
    
    def __init__(self, config: Optional[VoiceFileConfig] = None):
        """
        初始化语音文件处理客户端
        
        Args:
            config: 配置对象，如果为None则使用默认配置
        """
        self.config = config or VoiceFileConfig()
        self._submit_url = f"{self.config.base_url}/submit"
        self._query_url = f"{self.config.base_url}/query"
        
    def _get_common_headers(self, task_id: str, x_tt_logid: Optional[str] = None) -> Dict[str, str]:
        """
        获取通用请求头
        
        Args:
            task_id: 任务ID
            x_tt_logid: 日志ID
            
        Returns:
            Dict[str, str]: 请求头字典
        """
        headers = {
            "X-Api-App-Key": self.config.app_id,
            "X-Api-Access-Key": self.config.token,
            "X-Api-Resource-Id": "volc.bigasr.auc",
            "X-Api-Request-Id": task_id,
            "Content-Type": "application/json"
        }
        
        if x_tt_logid:
            headers["X-Tt-Logid"] = x_tt_logid
        else:
            headers["X-Api-Sequence"] = "-1"
            
        return headers
    
    def _construct_audio_request(
        self,
        audio_base64: str,
        audio_format: Optional[str] = None,
        rate: Optional[int] = None,
        bits: Optional[int] = None,
        channel: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        构造音频请求数据
        
        Args:
            audio_base64: Base64编码的音频数据
            audio_format: 音频格式
            rate: 采样率
            bits: 位深度
            channel: 声道数
            
        Returns:
            Dict[str, Any]: 请求数据字典
        """
        return {
            "user": {"uid": self.config.default_uid},
            "audio": {
                "data": audio_base64,
                "format": audio_format or self.config.default_format,
                "codec": "raw",
                "rate": rate or self.config.default_rate,
                "bits": bits or self.config.default_bits,
                "channel": channel or self.config.default_channel
            },
            "request": {
                "model_name": "bigmodel",
                "show_utterances": True,
                "corpus": {"correct_table_name": "", "context": ""}
            }
        }
    
    def submit_task(self, audio_bytes: bytes, **kwargs) -> Tuple[str, str]:
        """
        提交音频处理任务
        
        Args:
            audio_bytes: 音频数据字节流
            **kwargs: 其他音频参数
            
        Returns:
            Tuple[str, str]: (任务ID, 日志ID)
            
        Raises:
            Exception: 提交任务失败时抛出异常
        """
        task_id = str(uuid.uuid4())
        headers = self._get_common_headers(task_id)
        
        # 将字节流编码为Base64字符串
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        request_data = self._construct_audio_request(audio_base64, **kwargs)
        
        logger.info(f'提交任务 ID: {task_id}')
        response = requests.post(
            self._submit_url,
            data=json.dumps(request_data),
            headers=headers
        )
        
        if response.headers.get("X-Api-Status-Code") == "20000000":
            log_id = response.headers.get("X-Tt-Logid")
            logger.info(f'提交成功. 日志ID: {log_id}')
            return task_id, log_id
        else:
            error_msg = f'提交失败: {response.headers}'
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def query_task(self, task_id: str, x_tt_logid: str) -> Optional[requests.Response]:
        """
        查询任务状态
        
        Args:
            task_id: 任务ID
            x_tt_logid: 日志ID
            
        Returns:
            Optional[requests.Response]: 响应对象，如果查询失败则返回None
        """
        headers = self._get_common_headers(task_id, x_tt_logid)
        request_data = {"task_id": task_id}
        
        try:
            response = requests.post(
                self._query_url,
                data=json.dumps(request_data),
                headers=headers
            )
            
            if response.status_code == 200:
                return response
            else:
                logger.error(f"查询失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"查询请求异常: {str(e)}")
            return None
    
    def process_audio_file(
        self,
        file_path: Union[str, Path],
        poll_interval: float = 1.0,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        处理音频文件
        
        Args:
            file_path: 音频文件路径
            poll_interval: 轮询间隔（秒）
            timeout: 超时时间（秒），None表示不超时
            
        Returns:
            Dict[str, Any]: 处理结果
            
        Raises:
            Exception: 处理失败时抛出异常
        """
        start_time = time.time()
        
        # 读取音频文件
        try:
            with open(file_path, "rb") as f:
                audio_bytes = f.read()
        except Exception as e:
            error_msg = f"读取音频文件失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 提交任务
        task_id, x_tt_logid = self.submit_task(audio_bytes)
        
        # 轮询任务状态
        while True:
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"处理超时: {timeout}秒")
            
            query_response = self.query_task(task_id, x_tt_logid)
            if not query_response:
                raise Exception("查询任务状态失败")
            
            code = query_response.headers.get('X-Api-Status-Code')
            if code == '20000000':   # 任务完成
                result = query_response.json()
                logger.info("处理成功")
                return result
            elif code not in ('20000001', '20000002'):  # 任务失败
                error_msg = f"处理失败: {code}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            time.sleep(poll_interval)

def main():
    """主函数"""
    # 创建客户端实例
    client = VoiceFileClient()
    
    # 处理音频文件
    try:
        result = client.process_audio_file("test_audios/武极天下01.mp3")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("SUCCESS!")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        exit(1)

if __name__ == '__main__':
    main()