import asyncio
import datetime
import gzip
import json
import time
import uuid
import wave
from io import BytesIO
import aiofiles
import websockets
import base64
import numpy as np

from src.api.routes.image_routes import settings

PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message Type:
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_REQUEST = 0b0010
FULL_SERVER_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

# Message Type Specific Flags
NO_SEQUENCE = 0b0000  # no check sequence
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_WITH_SEQUENCE = 0b0011
NEG_SEQUENCE_1 = 0b0011

# Message Serialization
NO_SERIALIZATION = 0b0000
JSON = 0b0001

# Message Compression
NO_COMPRESSION = 0b0000
GZIP = 0b0001


def generate_header(
        message_type=FULL_CLIENT_REQUEST,
        message_type_specific_flags=NO_SEQUENCE,
        serial_method=JSON,
        compression_type=GZIP,
        reserved_data=0x00
):
    """
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits)
    serialization_method(4 bits) message_compression(4 bits)
    reserved （8bits) 保留字段
    """
    header = bytearray()
    header_size = 1
    header.append((PROTOCOL_VERSION << 4) | header_size)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serial_method << 4) | compression_type)
    header.append(reserved_data)
    return header


def generate_before_payload(sequence: int):
    before_payload = bytearray()
    before_payload.extend(sequence.to_bytes(4, 'big', signed=True))  # sequence
    return before_payload


def parse_response(res):
    """
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits)
    serialization_method(4 bits) message_compression(4 bits)
    reserved （8bits) 保留字段
    header_extensions 扩展头(大小等于 8 * 4 * (header_size - 1) )
    payload 类似与http 请求体
    """
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    header_extensions = res[4:header_size * 4]
    payload = res[header_size * 4:]
    result = {
        'is_last_package': False,
    }
    payload_msg = None
    payload_size = 0
    if message_type_specific_flags & 0x01:
        # receive frame with sequence
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['payload_sequence'] = seq
        payload = payload[4:]

    if message_type_specific_flags & 0x02:
        # receive last package
        result['is_last_package'] = True

    if message_type == FULL_SERVER_RESPONSE:
        payload_size = int.from_bytes(payload[:4], "big", signed=True)
        payload_msg = payload[4:]
    elif message_type == SERVER_ACK:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['seq'] = seq
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
    elif message_type == SERVER_ERROR_RESPONSE:
        code = int.from_bytes(payload[:4], "big", signed=False)
        result['code'] = code
        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
        payload_msg = payload[8:]
    if payload_msg is None:
        return result
    if message_compression == GZIP:
        payload_msg = gzip.decompress(payload_msg)
    if serialization_method == JSON:
        payload_msg = json.loads(str(payload_msg, "utf-8"))
    elif serialization_method != NO_SERIALIZATION:
        payload_msg = str(payload_msg, "utf-8")
    result['payload_msg'] = payload_msg
    result['payload_size'] = payload_size
    return result


def read_wav_info(data: bytes = None) -> (int, int, int, int, bytes):
    with BytesIO(data) as _f:
        wave_fp = wave.open(_f, 'rb')
        nchannels, sampwidth, framerate, nframes = wave_fp.getparams()[:4]
        wave_bytes = wave_fp.readframes(nframes)
    return nchannels, sampwidth, framerate, nframes, wave_bytes


def judge_wav(ori_date):
    if len(ori_date) < 44:
        return False
    if ori_date[0:4] == b"RIFF" and ori_date[8:12] == b"WAVE":
        return True
    return False


class AsrWsClient:
    def __init__(self, audio_path, **kwargs):
        """
        :param config: config
        """
        self.audio_path = audio_path
        self.success_code = 1000  # success code, default is 1000
        self.seg_duration = int(kwargs.get("seg_duration", 100))
        self.ws_url = kwargs.get("ws_url", settings.doubao_stream_base_url)
        self.uid = kwargs.get("uid", "test")
        self.format = kwargs.get("format", "pcm")
        self.rate = kwargs.get("rate", 16000)
        self.bits = kwargs.get("bits", 16)
        self.channel = kwargs.get("channel", 1)
        self.codec = kwargs.get("codec", "raw")
        self.auth_method = kwargs.get("auth_method", "none")
        self.hot_words = kwargs.get("hot_words", None)
        self.streaming = kwargs.get("streaming", True)
        self.mp3_seg_size = kwargs.get("mp3_seg_size", 1000)
        self.req_event = 1
        self._last_text = ""  # 存储上一次的文本
        self._last_sequence = 0  # 跟踪序列号
        self._accumulated_text = ""  # 存储累积的文本
        self._last_words = []  # 存储上一次的词语列表

    def construct_request(self, reqid, data=None):
        req = {
            "user": {
                "uid": self.uid,
            },
            "audio": {
                'format': self.format,
                "sample_rate": self.rate,
                "bits": self.bits,
                "channel": self.channel,
                "codec": self.codec,
            },
            "request": {
                "model_name": "bigmodel",
                "enable_punc": True,
                "enable_itn": True,  # 启用数字和标点转换
                "enable_timestamp": True,  # 启用时间戳
                "enable_vad": True,  # 启用语音活动检测
                "vad_pause_time": 500,  # VAD暂停时间(毫秒)
                "vad_max_duration": 60000,  # 最大语音段时长(毫秒)
                "vad_max_sentence_silence": 800,  # 句子间最大静音时长(毫秒)
            }
        }
        return req

    @staticmethod
    def slice_data(data: bytes, chunk_size: int) -> (list, bool):
        data_len = len(data)
        offset = 0
        while offset + chunk_size < data_len:
            yield data[offset: offset + chunk_size], False
            offset += chunk_size
        else:
            yield data[offset: data_len], True

    async def segment_data_processor(self, wav_data: bytes, segment_size: int):
        reqid = str(uuid.uuid4())
        seq = 1
        request_params = self.construct_request(reqid)
        payload_bytes = str.encode(json.dumps(request_params))
        payload_bytes = gzip.compress(payload_bytes)
        full_client_request = bytearray(generate_header(message_type_specific_flags=POS_SEQUENCE))
        full_client_request.extend(generate_before_payload(sequence=seq))
        full_client_request.extend((len(payload_bytes)).to_bytes(
            4, 'big'))  # payload size(4 bytes)
        req_str = ' '.join(format(byte, '02x') for byte in full_client_request)
        # print(f"{time.time()}, seq", seq, "req", req_str)
        full_client_request.extend(payload_bytes)  # payload
        header = {}
        # print("reqid", reqid)
        # header["X-Tt-Logid"] = reqid
        header["X-Api-Resource-Id"] = "volc.bigasr.sauc.duration"
        header["X-Api-Access-Key"] = settings.doubao_token,
        header["X-Api-App-Key"] = settings.doubao_app_id,
        header["X-Api-Request-Id"] = reqid
        header["X-Api-Connect-Id"] = reqid
        try:
            # 修改连接方式，使用兼容参数
            # 使用Basic Auth兼容websockets 15.0.1
            auth_str = f"{self.uid}:{reqid}"
            auth_b64 = base64.b64encode(auth_str.encode()).decode()
            async with websockets.connect(
                    self.ws_url,
                    max_size=1000000000,
                    extra_headers={
                        "Authorization": f"Basic {auth_b64}",
                        "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
                        "X-Api-Access-Key": settings.doubao_token,
                        "X-Api-App-Key": settings.doubao_app_id,
                        "X-Api-Connect-Id": reqid
                    }
            ) as ws:
                await ws.send(full_client_request)
                res = await ws.recv()
                # print(res)
                print(ws.response_headers)
                # res_str = ' '.join(format(byte, '02x') for byte in res)
                # print(res_str)
                result = parse_response(res)
                print("******************")
                print("sauc result", result)
                print("******************")
                # if 'payload_msg' in result and result['payload_msg']['code'] != self.success_code:
                #     return result
                for _, (chunk, last) in enumerate(AsrWsClient.slice_data(wav_data, segment_size), 1):
                    # if no compression, comment this line
                    seq += 1
                    if last:
                        seq = -seq
                    start = time.time()
                    payload_bytes = gzip.compress(chunk)
                    audio_only_request = bytearray(
                        generate_header(message_type=AUDIO_ONLY_REQUEST, message_type_specific_flags=POS_SEQUENCE))
                    if last:
                        audio_only_request = bytearray(generate_header(message_type=AUDIO_ONLY_REQUEST,
                                                                       message_type_specific_flags=NEG_WITH_SEQUENCE))
                    audio_only_request.extend(generate_before_payload(sequence=seq))
                    audio_only_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
                    req_str = ' '.join(format(byte, '02x') for byte in audio_only_request)
                    # print("seq", seq, "req", req_str)
                    audio_only_request.extend(payload_bytes)  # payload
                    await ws.send(audio_only_request)
                    res = await ws.recv()
                    # print(res)
                    # res_str = ' '.join(format(byte, '02x') for byte in res)
                    # print(res_str)
                    result = parse_response(res)
                    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}, seq", seq, "res", result)
                    # if 'payload_msg' in result and result['payload_msg']['code'] != self.success_code:
                    #     return result
                    if self.streaming:
                        sleep_time = max(0, (self.seg_duration / 1000.0 - (time.time() - start)))
                        await asyncio.sleep(sleep_time)
            return result
        except Exception as e:
            print(f"WebSocket error: {str(e)}")
            return {
                'error': str(e),
                'code': 500
            }
        except Exception as e:
            print(f"Unexpected error: {e}")

    async def execute(self):
        if self.audio_path:
            async with aiofiles.open(self.audio_path, mode="rb") as _f:
                data = await _f.read()
            audio_data = bytes(data)
            if self.format == "mp3":
                segment_size = self.mp3_seg_size
                return await self.segment_data_processor(audio_data, segment_size)
            if self.format == "wav":
                nchannels, sampwidth, framerate, nframes, wav_len = read_wav_info(audio_data)
                size_per_sec = nchannels * sampwidth * framerate
                segment_size = int(size_per_sec * self.seg_duration / 1000)
                return await self.segment_data_processor(audio_data, segment_size)
            if self.format == "pcm":
                segment_size = int(self.rate * 2 * self.channel * self.seg_duration / 500)
                return await self.segment_data_processor(audio_data, segment_size)
            else:
                raise Exception("Unsupported format")
        else:
            # For streaming mode without file path
            return None

    async def process_chunk(self, audio_bytes):
        """处理单个音频数据块并返回识别结果"""
        try:
            # 如果是首次调用，初始化连接
            if not hasattr(self, '_sequence') or not hasattr(self, '_ws'):
                self._sequence = 1
                self._is_first_chunk = True

                # 创建请求ID
                self._reqid = str(uuid.uuid4())

                # 准备连接参数
                header = {
                    "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
                    "X-Api-Access-Key": settings.doubao_token,
                    "X-Api-App-Key": settings.doubao_app_id,
                    "X-Api-Request-Id": self._reqid,
                    "X-Api-Connect-Id": self._reqid
                }

                # 使用Basic Auth兼容websockets
                auth_str = f"{self.uid}:{self._reqid}"
                auth_b64 = base64.b64encode(auth_str.encode()).decode()
                header["Authorization"] = f"Basic {auth_b64}"

                try:
                    print(f"连接到WebSocket: {self.ws_url}")
                    print(f"请求头: {header}")

                    # 创建WebSocket连接
                    self._ws = await websockets.connect(
                        self.ws_url,
                        extra_headers=header,
                        ping_interval=None,  # 禁用ping以避免干扰
                        ping_timeout=None,
                        close_timeout=10,
                        max_size=None,  # 不限制消息大小
                    )

                    print("WebSocket连接已建立")

                    # 发送初始请求
                    request_params = self.construct_request(self._reqid)
                    print(f"初始请求参数: {request_params}")

                    payload_bytes = str.encode(json.dumps(request_params))
                    payload_bytes = gzip.compress(payload_bytes)

                    full_client_request = bytearray(generate_header(message_type_specific_flags=POS_SEQUENCE))
                    full_client_request.extend(generate_before_payload(sequence=self._sequence))
                    full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
                    full_client_request.extend(payload_bytes)

                    print(f"发送初始请求，长度: {len(full_client_request)} 字节")
                    await self._ws.send(full_client_request)

                    # 接收初始响应
                    print("等待初始响应...")
                    res = await self._ws.recv()
                    print(f"收到初始响应，长度: {len(res)} 字节")

                    result = parse_response(res)
                    print(f"解析后的初始响应: {result}")

                    # 检查初始响应是否成功
                    if 'payload_msg' in result and result['payload_msg'].get('code') != self.success_code:
                        error_msg = result['payload_msg'].get('message', '未知错误')
                        print(f"ASR初始化失败: {error_msg}")
                        raise Exception(f"ASR初始化失败: {error_msg}")

                    print("ASR初始化成功")

                except Exception as e:
                    print(f"建立ASR连接失败: {str(e)}")
                    raise Exception(f"建立ASR连接失败: {str(e)}")

            # 处理音频数据
            self._sequence += 1
            is_last = False  # 这里可以根据需要设置为True表示最后一块

            # 检查音频数据格式并转换
            # 如果是PCM格式，需要确保是16位整数格式
            if self.format == 'pcm':
                # 检查是否需要转换为Int16格式
                if isinstance(audio_bytes, bytes) and len(audio_bytes) % 2 == 0:
                    # 如果是浮点数PCM数据(通常是-1.0到1.0范围)，需要转换为Int16
                    try:
                        # 尝试将字节转换为Int16数组
                        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                        # 确保数据在有效范围内
                        audio_bytes = audio_int16.tobytes()
                    except Exception as e:
                        print(f"音频数据转换错误: {str(e)}")

            # 压缩音频数据
            payload_bytes = gzip.compress(audio_bytes)

            # 构建请求头
            audio_only_request = bytearray(generate_header(
                message_type=AUDIO_ONLY_REQUEST,
                message_type_specific_flags=NEG_WITH_SEQUENCE if is_last else POS_SEQUENCE
            ))

            # 如果是最后一块，使用负序列号
            seq = -self._sequence if is_last else self._sequence

            audio_only_request.extend(generate_before_payload(sequence=seq))
            audio_only_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
            audio_only_request.extend(payload_bytes)

            # 发送音频数据
            print(f"发送音频数据，序列号: {seq}, 长度: {len(audio_only_request)} 字节")
            await self._ws.send(audio_only_request)

            # 接收响应
            print("等待音频处理响应...")
            res = await self._ws.recv()
            print(f"收到音频处理响应，长度: {len(res)} 字节")

            result = parse_response(res)
            print(f"解析后的音频处理响应: {result}")

            # 提取识别结果
            partial_text = ""
            is_final = False

            if 'payload_msg' in result:
                msg = result['payload_msg']
                if 'result' in msg:
                    current_text = msg['result'].get('text', '')
                    is_final = msg.get('is_final', False)
                    current_sequence = result.get('payload_sequence', 0)

                    # 获取当前词语列表
                    current_words = []
                    if 'utterances' in msg['result']:
                        for utterance in msg['result']['utterances']:
                            if 'words' in utterance:
                                current_words.extend([word['text'] for word in utterance['words']])

                    # 检查是否有新的文本内容，并且序列号大于上一次的序列号
                    if current_text and current_sequence > self._last_sequence:
                        # 比较词语列表，找出新增的词语
                        new_words = []
                        for word in current_words:
                            if word not in self._last_words:
                                new_words.append(word)

                        if new_words:
                            # 构建新的文本
                            new_text = ''.join(new_words)
                            # 更新累积文本
                            self._accumulated_text = current_text
                            partial_text = new_text

                            # 更新上一次的词语列表
                            self._last_words = current_words.copy()

                        # 更新上一次的文本和序列号
                        self._last_text = current_text
                        self._last_sequence = current_sequence

                    # 调试输出
                    print(f"当前序列号: {current_sequence}")
                    print(f"当前文本: {current_text}")
                    print(f"当前词语: {current_words}")
                    print(f"累积文本: {self._accumulated_text}")
                    print(f"增量文本: {partial_text}")
                    print(f"是否最终: {is_final}")

            return {
                'partial_text': partial_text,
                'is_final': is_final,
                'full_text': self._accumulated_text,  # 返回累积的完整文本
                'sequence': self._last_sequence
            }

        except Exception as e:
            print(f"处理音频块时出错: {str(e)}")
            return {
                'error': str(e),
                'partial_text': '',
                'is_final': False,
                'full_text': self._accumulated_text,
                'sequence': self._last_sequence
            }


def execute_one(audio_item, **kwargs):
    assert 'id' in audio_item
    assert 'path' in audio_item
    audio_id = audio_item['id']
    audio_path = audio_item['path']
    asr_http_client = AsrWsClient(
        audio_path=audio_path,
        **kwargs
    )
    result = asyncio.run(asr_http_client.execute())
    return {"id": audio_id, "path": audio_path, "result": result}
