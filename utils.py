import os
import json
import base64
import io
import re
import time
import copy
import asyncio
import requests
import numpy as np
import random
import streamlit as st
import pandas as pd
import importlib.util
import warnings
import cv2
import logging
import functools
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Any, Union, Optional, Tuple

# 检查是否安装了必要的库
MOVIEPY_AVAILABLE = importlib.util.find_spec("moviepy") is not None
DOCX_AVAILABLE = importlib.util.find_spec("docx") is not None
FITZ_AVAILABLE = importlib.util.find_spec("fitz") is not None

if MOVIEPY_AVAILABLE:
    from moviepy.editor import VideoFileClip

if DOCX_AVAILABLE:
    from docx import Document

if FITZ_AVAILABLE:
    import fitz

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# API密钥名称常量
SILICONFLOW_API_KEY = "siliconflow_api_key"

# 确保环境变量中没有代理设置
if 'http_proxy' in os.environ:
    del os.environ['http_proxy']
if 'https_proxy' in os.environ:
    del os.environ['https_proxy']
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY'] 
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']

# 定义重试装饰器
def retry_with_backoff(max_retries=3, initial_backoff=1, backoff_factor=2):
    """
    重试装饰器，支持指数退避
    
    参数:
        max_retries: 最大重试次数
        initial_backoff: 初始等待时间（秒）
        backoff_factor: 退避因子
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            backoff = initial_backoff
            retries = 0
            last_exception = None
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    retries += 1
                    logging.warning(f"函数 {func.__name__} 调用失败 (尝试 {retries}/{max_retries}): {str(e)}")
                    
                    if retries < max_retries:
                        sleep_time = backoff * (backoff_factor ** (retries - 1))
                        logging.info(f"等待 {sleep_time} 秒后重试...")
                        time.sleep(sleep_time)
                    else:
                        logging.error(f"函数 {func.__name__} 在 {max_retries} 次尝试后仍然失败")
            
            # 所有重试都失败，抛出最后一个异常
            raise last_exception
        
        return wrapper
    
    return decorator

# 尝试导入 moviepy，如果失败则提供一个占位符
try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    # 创建一个占位符类
    class VideoFileClip:
        def __init__(self, *args, **kwargs):
            raise ImportError("MoviePy 未安装，视频功能不可用。请安装 moviepy 库。")

# 设置日志
import logging
logging.basicConfig(
    filename='error_log.txt',
    level=logging.INFO,  # 改为INFO级别，记录更多信息
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加控制台处理器，同时输出到控制台
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger('').addHandler(console_handler)

# 记录启动信息
logging.info("内容分析工具启动")

# 项目路径管理
def get_project_dir():
    """获取项目目录"""
    if 'project_dir' not in st.session_state:
        st.session_state.project_dir = os.path.join(os.getcwd(), 'projects')
        os.makedirs(st.session_state.project_dir, exist_ok=True)
    return st.session_state.project_dir

def get_current_project_path():
    """获取当前项目路径"""
    if 'current_project' not in st.session_state or not st.session_state.current_project:
        return None
    
    return os.path.join(get_project_dir(), st.session_state.current_project)

def load_variables():
    """从当前项目配置中加载变量列表
    
    返回:
        变量列表，如果没有找到则返回空列表
    """
    project_path = get_current_project_path()
    if not project_path:
        return []
    
    config_path = os.path.join(project_path, "config.json")
    if not os.path.exists(config_path):
        return []
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
        return project_config.get('variables', [])
    except Exception as e:
        logging.error(f"加载变量失败: {str(e)}")
        return []

def save_project_data(data, filename):
    """保存项目数据"""
    project_path = get_current_project_path()
    if not project_path:
        return False
    
    try:
        with open(os.path.join(project_path, filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"保存项目数据失败: {str(e)}")
        return False

def load_project_data(filename):
    """加载项目数据"""
    project_path = get_current_project_path()
    if not project_path:
        return None
    
    file_path = os.path.join(project_path, filename)
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载项目数据失败: {str(e)}")
        return None

# 文件处理函数
def get_file_content(file_path):
    """获取文件内容"""
    try:
        if not os.path.exists(file_path):
            return f"文件不存在: {file_path}"
            
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return extract_pdf_text(file_path)
        elif ext in ['.docx', '.doc']:
            return extract_word_text(file_path)
        elif ext in ['.txt', '.md', '.json', '.csv', '.py', '.js', '.html', '.css']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        return f.read()
                except:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        return f.read()
        else:
            # 尝试作为文本文件读取
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                return f"无法读取文件: {file_path} (可能是二进制文件)"
            except Exception as e:
                return f"读取文件失败: {str(e)}"
    except Exception as e:
        logging.error(f"获取文件内容失败: {str(e)}")
        return f"获取文件内容失败: {str(e)}"

def extract_pdf_text(file_path):
    """提取PDF文本"""
    if not FITZ_AVAILABLE:
        return "无法提取PDF文本: 请安装PyMuPDF库 (pip install PyMuPDF)"
    
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        logging.error(f"提取PDF文本失败: {str(e)}")
        return f"提取PDF文本失败: {str(e)}"

def extract_word_text(file_path):
    """提取Word文本"""
    if not DOCX_AVAILABLE:
        return "无法提取Word文本: 请安装python-docx库 (pip install python-docx)"
    
    try:
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        logging.error(f"提取Word文本失败: {str(e)}")
        return f"提取Word文本失败: {str(e)}"

# 视频处理函数
def extract_video_frames(video_path, interval=30):
    """从视频中提取关键帧
    
    参数:
        video_path: 视频文件路径
        interval: 提取帧的时间间隔（秒）
    
    返回:
        frames_with_timestamps: 包含(帧,时间戳)的元组列表
    """
    if not MOVIEPY_AVAILABLE:
        logging.error("未安装MoviePy库，无法提取视频帧")
        return []
    
    try:
        # 确保interval是整数
        if not isinstance(interval, int):
            try:
                interval = int(interval)
            except (ValueError, TypeError):
                logging.error(f"无效的帧间隔值: {interval}，使用默认值30")
                interval = 30
        
        clip = VideoFileClip(video_path)
        # 获取视频总时长（秒）
        duration = clip.duration
        
        # 计算需要提取的时间点
        timestamps = list(range(0, int(duration), interval))
        if not timestamps:
            timestamps = [0]  # 至少提取一帧
        
        # 提取每个时间点的帧
        frames_with_timestamps = []
        for t in timestamps:
            try:
                # 获取指定时间点的帧
                frame = clip.get_frame(t)
                # 转换为BGR格式（OpenCV格式）
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frames_with_timestamps.append((frame_bgr, t))
            except Exception as e:
                logging.error(f"无法提取时间点 {t}秒 的帧: {str(e)}")
        
        # 关闭视频clip
        clip.close()
        
        return frames_with_timestamps
    except Exception as e:
        logging.error(f"视频帧提取失败: {str(e)}")
        return []

def get_video_info(video_path):
    """获取视频信息"""
    if not MOVIEPY_AVAILABLE:
        logging.error("MoviePy 未安装，视频功能不可用")
        st.error("MoviePy 未安装，视频功能不可用。请安装 moviepy 库。")
        return None
        
    try:
        # 处理文件路径
        logging.info(f"尝试获取视频信息，原始路径: {video_path}")
        
        # 检查视频路径是否为None或空
        if not video_path:
            logging.error("视频路径为空")
            st.error("视频路径为空，无法获取视频信息")
            return None
            
        # 记录路径信息用于调试
        logging.info(f"文件类型: {type(video_path)}")
        logging.info(f"视频文件是否存在: {os.path.exists(video_path)}")
        
        # 处理路径
        fixed_path = sanitize_file_path(video_path)
        logging.info(f"处理后的路径: {fixed_path}")
        
        # 检查文件是否存在
        if not os.path.exists(fixed_path):
            logging.error(f"文件不存在: {fixed_path}")
            st.error(f"无法找到视频文件: {os.path.basename(fixed_path)}")
            return None
            
        # 记录文件大小和目录内容
        try:
            file_size = os.path.getsize(fixed_path) / (1024 * 1024)  # 以MB为单位
            logging.info(f"文件大小: {file_size:.2f} MB")
            
            # 记录同目录下的其他文件
            dir_path = os.path.dirname(fixed_path)
            if os.path.exists(dir_path):
                files = os.listdir(dir_path)
                logging.info(f"同目录下的文件: {files[:10] if len(files) > 10 else files}")
        except Exception as e:
            logging.warning(f"获取文件信息失败: {str(e)}")
        
        # 打开视频文件
        logging.info(f"开始使用MoviePy加载: {fixed_path}")
        video = VideoFileClip(fixed_path)
        info = {
            "duration": video.duration,
            "fps": video.fps,
            "size": video.size,
            "filename": os.path.basename(fixed_path)
        }
        video.close()
        logging.info(f"成功获取视频信息: {info}")
        return info
    except Exception as e:
        logging.error(f"获取视频信息失败: {str(e)}")
        st.error(f"无法读取视频文件: {os.path.basename(video_path)} ({str(e)})")
        import traceback
        logging.error(traceback.format_exc())
        return None

# 图像处理函数
def convert_image_to_base64(image):
    """将图像数据转换为base64编码字符串
    
    参数:
        image: 图像数据，OpenCV格式(BGR)
        
    返回:
        base64编码的字符串
    """
    try:
        # 将图像编码为JPEG格式
        _, buffer = cv2.imencode(".jpg", image)
        # 将编码后的数据转换为base64字符串
        base64_encoded = base64.b64encode(buffer).decode("utf-8")
        return base64_encoded
    except Exception as e:
        logging.error(f"图像转base64失败: {str(e)}")
        return ""

# AI辅助函数
@retry_with_backoff(max_retries=3, initial_backoff=2, backoff_factor=2)
def get_openai_client():
    """获取OpenAI客户端"""
    api_key = st.session_state.get('openai_api_key', '')
    
    # 详细记录API密钥状态（不记录密钥本身）
    if not api_key:
        logging.warning("OpenAI API密钥未设置")
        return None
    
    if api_key.strip() == '':
        logging.warning("OpenAI API密钥为空字符串")
        return None
    
    try:
        # 避免传递任何可能导致问题的参数，仅使用api_key
        client = OpenAI(api_key=api_key)
        logging.info("OpenAI客户端创建成功")
        return client
    except Exception as e:
        logging.error(f"创建OpenAI客户端失败: {str(e)}")
        raise  # 重新抛出异常，让重试装饰器捕获

class SiliconFlowClient:
    """自定义硅基流动客户端，完全按照官方文档实现"""
    
    class CompletionsObject:
        def __init__(self, client):
            self.client = client
            
        def create(self, model, messages, temperature=0.7, max_tokens=500, **kwargs):
            """硅基流动chat.completions.create方法
            
            按照硅基流动官方文档实现，支持视觉语言模型的调用
            """
            import urllib.request
            import json
            import ssl
            import time
            
            # 创建请求正文
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # 添加其他关键字参数
            for key, value in kwargs.items():
                data[key] = value
            
            # 打印请求数据用于调试
            logging.info(f"硅基流动API请求数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
                    
            # 创建请求
            req = urllib.request.Request(
                f"{self.client.base_url}/chat/completions",
                data=json.dumps(data).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.client.api_key}'
                },
                method='POST'
            )
            
            # 创建一个上下文，忽略SSL证书验证(仅用于调试)
            context = ssl._create_unverified_context()
            
            try:
                # 重试逻辑
                max_retries = 3
                retry_delay = 1
                last_exception = None
                
                for retry in range(max_retries):
                    try:
                        # 发送请求
                        with urllib.request.urlopen(req, context=context) as response:
                            if kwargs.get("stream", False):
                                # 处理流式响应 - 使用生成器
                                return self._handle_streaming_response(response)
                            else:
                                # 处理非流式响应
                                result = json.loads(response.read().decode('utf-8'))
                                return self._create_response_object(result)
                    except urllib.error.HTTPError as e:
                        last_exception = e
                        response_body = e.read().decode('utf-8')
                        logging.error(f"HTTP错误 {e.code}: {response_body}")
                        if retry < max_retries - 1:
                            logging.warning(f"API请求失败，将在{retry_delay}秒后重试: HTTP Error {e.code}: {e.reason}")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 指数退避
                        else:
                            raise Exception(f"HTTP Error {e.code}: {e.reason} - {response_body}")
                    except Exception as e:
                        last_exception = e
                        if retry < max_retries - 1:
                            logging.warning(f"API请求失败，将在{retry_delay}秒后重试: {str(e)}")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 指数退避
                        else:
                            raise last_exception
            except Exception as e:
                logging.error(f"硅基流动API请求失败: {str(e)}")
                raise
                
        def _handle_streaming_response(self, response):
            """处理流式响应"""
            import json
            
            buffer = b""
            for chunk in response:
                buffer += chunk
                if b'\n' in buffer:
                    lines = buffer.split(b'\n')
                    for i in range(len(lines) - 1):
                        line = lines[i].strip()
                        if line:
                            if line.startswith(b'data: '):
                                json_str = line[6:].decode('utf-8')
                                if json_str.strip() == '[DONE]':
                                    continue
                                try:
                                    data = json.loads(json_str)
                                    yield self._create_response_object(data)
                                except json.JSONDecodeError:
                                    logging.error(f"JSON解析错误: {json_str}")
                    buffer = lines[-1]
            
            if buffer:
                line = buffer.strip()
                if line and line.startswith(b'data: '):
                    json_str = line[6:].decode('utf-8')
                    if json_str.strip() != '[DONE]':
                        try:
                            data = json.loads(json_str)
                            yield self._create_response_object(data)
                        except json.JSONDecodeError:
                            logging.error(f"JSON解析错误: {json_str}")
        
        def _create_response_object(self, data):
            """创建一个响应对象"""
            class Response:
                def __init__(self, data):
                    self.data = data
                    self.choices = [Choice(data["choices"][0])] if "choices" in data and data["choices"] else []
                    self.id = data.get("id", "")
                    self.object = data.get("object", "")
                    self.created = data.get("created", 0)
                    self.model = data.get("model", "")
                    
            class Choice:
                def __init__(self, choice_data):
                    self.index = choice_data.get("index", 0)
                    self.message = Message(choice_data["message"]) if "message" in choice_data else None
                    self.delta = Delta(choice_data["delta"]) if "delta" in choice_data else None
                    self.finish_reason = choice_data.get("finish_reason", None)
                    
            class Message:
                def __init__(self, message_data):
                    self.role = message_data.get("role", "")
                    self.content = message_data.get("content", "")
            
            class Delta:
                def __init__(self, delta_data):
                    self.role = delta_data.get("role", "")
                    self.content = delta_data.get("content", "")
                    
            return Response(data)
    
    class ChatObject:
        def __init__(self, client):
            self.client = client
            self.completions = SiliconFlowClient.CompletionsObject(client)
    
    def __init__(self, api_key, base_url="https://api.siliconflow.cn/v1"):
        """初始化硅基流动客户端
        
        参数:
            api_key: 硅基流动API密钥
            base_url: API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.chat = self.ChatObject(self)

@retry_with_backoff(max_retries=3, initial_backoff=2, backoff_factor=2)
def get_siliconflow_client():
    """获取硅基流动客户端"""
    api_key = st.session_state.get('siliconflow_api_key', '')
    
    if not api_key:
        logging.warning("硅基流动API密钥未设置")
        return None
    
    if api_key.strip() == '':
        logging.warning("硅基流动API密钥为空字符串")
        return None
    
    try:
        logging.info("创建硅基流动客户端")
        client = SiliconFlowClient(api_key)
        logging.info("硅基流动客户端创建成功")
        return client
    except Exception as e:
        logging.error(f"创建硅基流动客户端失败: {str(e)}")
        return None

def get_ai_client():
    """获取AI客户端"""
    return get_siliconflow_client()

@retry_with_backoff(max_retries=3, initial_backoff=2, backoff_factor=2)
def get_ai_suggestion(content, prompt):
    """获取AI编码建议"""
    client = get_ai_client()
    if not client:
        return "请先设置硅基流动API密钥"
    
    try:
        # 硅基流动模型
        model = "deepseek-ai/DeepSeek-V2.5"
            
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是内容分析和编码专家。"},
                {"role": "user", "content": f"{prompt}\n\n{content}"}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        if hasattr(response, 'choices') and len(response.choices) > 0:
            if hasattr(response.choices[0], 'message'):
                result = response.choices[0].message.content
            else:
                result = str(response.choices[0])
        else:
            result = str(response)
        
        return result
    except Exception as e:
        logging.error(f"获取AI建议失败: {str(e)}")
        return f"获取AI建议时出错: {str(e)}"

@retry_with_backoff(max_retries=2, initial_backoff=5, backoff_factor=2)
def auto_code_content(content, variables, custom_prompt=None):
    """使用AI自动编码内容
    
    参数:
        content: 要编码的内容
        variables: 变量列表
        custom_prompt: 自定义提示词
    
    返回:
        编码结果字典
    """
    try:
        # 获取硅基流动客户端
        client = get_siliconflow_client()
        if not client:
            logging.error("未设置硅基流动API密钥，无法进行自动编码")
            return None
        
        # 构建变量文本和选项映射
        variables_text = ""
        options_map = {}  # 用于存储每个变量的有效选项
        
        for var in variables:
            var_name = var.get('name', '')
            var_type = var.get('type', '')
            var_id = var.get('id', var_name)
            
            variables_text += f"{var_name} ({var_type})"
            
            # 处理选项
            if var_type == "分类变量" or var_type == "select":
                options = []
                
                # 处理不同格式的选项
                if 'options' in var and isinstance(var['options'], str):
                    # 字符串格式的选项，用逗号分隔
                    options = [opt.strip() for opt in var['options'].split(',') if opt.strip()]
                    options_map[var_name] = options
                    if options:
                        option_text = ", ".join(options)
                        variables_text += f" [选项: {option_text}]"
                
                elif 'options' in var and isinstance(var['options'], list):
                    # 列表格式的选项
                    if all(isinstance(opt, dict) for opt in var['options']):
                        # 选项是字典列表，包含value和label
                        option_labels = [opt.get('label', '') for opt in var['options'] if 'label' in opt]
                        option_values = [opt.get('value', '') for opt in var['options'] if 'value' in opt]
                        
                        if option_labels:
                            option_text = ", ".join(option_labels)
                            variables_text += f" [选项: {option_text}]"
                            options_map[var_name] = option_labels
                            # 同时保存值和标签的映射关系
                            options_map[f"{var_name}_values"] = option_values
                            options_map[f"{var_name}_labels"] = option_labels
                    else:
                        # 选项是简单列表
                        option_text = ", ".join(var['options'])
                        variables_text += f" [选项: {option_text}]"
                        options_map[var_name] = var['options']
            
            elif var_type == "李克特量表":
                likert_scale = var.get('likert_scale', 5)
                likert_labels = var.get('likert_labels', '')
                
                if likert_labels:
                    labels = [label.strip() for label in likert_labels.split(',') if label.strip()]
                    if labels:
                        variables_text += f" [量表: {', '.join(labels)}]"
                    else:
                        variables_text += f" [量表: 1-{likert_scale}]"
                else:
                    variables_text += f" [量表: 1-{likert_scale}]"
            
            # 添加编码指南
            if 'guide' in var and var['guide']:
                variables_text += f"\n编码指南: {var['guide']}"
            
            variables_text += "\n\n"
        
        # 使用自定义提示词或默认提示词
        if custom_prompt:
            user_prompt = custom_prompt.replace("{content}", content).replace("{variables}", variables_text)
        else:
            user_prompt = f"""请根据以下内容，为指定的变量进行编码。

内容:
{content}

需要编码的变量:
{variables_text}

请以JSON格式返回编码结果，格式为：
{{
    "变量名1": "编码值1",
    "变量名2": "编码值2",
    ...
}}

重要说明：
1. 对于分类变量，你必须且只能从提供的选项中选择一个，不要创建新的选项。
2. 对于李克特量表，请返回1到5之间的数值。
3. 请严格按照每个变量的编码指南进行编码。
4. 请确保编码结果符合变量的要求和内容特点。
"""
        
        # 构建请求
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V2.5",
            messages=[
                {"role": "system", "content": "你是一位内容分析和编码专家，精通各种内容编码规则和方法。请严格按照变量定义和编码指南进行编码，对于分类变量，只能从提供的选项中选择一个值。"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        # 获取编码结果
        # 处理不同类型的响应格式
        if hasattr(response, 'choices') and len(response.choices) > 0:
            if hasattr(response.choices[0], 'message'):
                if hasattr(response.choices[0].message, 'content'):
                    coding_result = response.choices[0].message.content
                else:
                    # 处理message是字符串的情况
                    coding_result = response.choices[0].message
            else:
                # 处理choices[0]直接包含text的情况
                coding_result = response.choices[0].text if hasattr(response.choices[0], 'text') else str(response.choices[0])
        else:
            # 如果响应格式完全不同，尝试直接转换为字符串
            coding_result = str(response)
        
        # 解析编码结果
        coding_results = {}
        
        # 尝试解析JSON格式
        try:
            # 尝试直接解析
            coding_json = json.loads(coding_result)
            
            # 验证编码结果并确保分类变量的值在选项中
            valid_coding = {}
            for var in variables:
                var_name = var.get('name', '')
                var_type = var.get('type', '')
                
                # 检查变量是否在编码结果中
                if var_name in coding_json:
                    value = coding_json[var_name]
                    
                    # 处理分类变量
                    if (var_type == "分类变量" or var_type == "select") and var_name in options_map:
                        # 获取该变量的有效选项
                        valid_options = options_map[var_name]
                        
                        # 检查值是否在有效选项中
                        if value in valid_options:
                            # 值直接匹配选项
                            valid_coding[var_name] = value
                        else:
                            # 尝试模糊匹配
                            best_match = None
                            best_score = 0
                            
                            for option in valid_options:
                                # 简单的包含关系检查
                                if option.lower() in value.lower() or value.lower() in option.lower():
                                    score = len(set(option.lower()) & set(value.lower())) / max(len(option), len(value))
                                    if score > best_score:
                                        best_score = score
                                        best_match = option
                            
                            if best_match and best_score > 0.5:  # 设置一个阈值
                                valid_coding[var_name] = best_match
                            else:
                                # 如果没有匹配，使用第一个选项作为默认值
                                logging.warning(f"变量 {var_name} 的值 '{value}' 不在有效选项中，使用默认值")
                                valid_coding[var_name] = valid_options[0] if valid_options else ""
                    else:
                        # 非分类变量，直接使用值
                        valid_coding[var_name] = value
            
            return valid_coding
            
        except json.JSONDecodeError:
            # 如果JSON解析失败，尝试从文本中提取JSON部分
            try:
                json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', coding_result)
                if json_match:
                    coding_json = json.loads(json_match.group(1))
                    # 处理JSON结果...
                    # 验证编码结果并确保分类变量的值在选项中
                    valid_coding = {}
                    for var in variables:
                        var_name = var.get('name', '')
                        var_type = var.get('type', '')
                        
                        # 检查变量是否在编码结果中
                        if var_name in coding_json:
                            value = coding_json[var_name]
                            
                            # 处理分类变量
                            if (var_type == "分类变量" or var_type == "select") and var_name in options_map:
                                # 获取该变量的有效选项
                                valid_options = options_map[var_name]
                                
                                # 检查值是否在有效选项中
                                if value in valid_options:
                                    # 值直接匹配选项
                                    valid_coding[var_name] = value
                                else:
                                    # 尝试模糊匹配
                                    best_match = None
                                    best_score = 0
                                    
                                    for option in valid_options:
                                        # 简单的包含关系检查
                                        if option.lower() in value.lower() or value.lower() in option.lower():
                                            score = len(set(option.lower()) & set(value.lower())) / max(len(option), len(value))
                                            if score > best_score:
                                                best_score = score
                                                best_match = option
                                        
                                        if best_match and best_score > 0.5:  # 设置一个阈值
                                            valid_coding[var_name] = best_match
                                        else:
                                            # 如果没有匹配，使用第一个选项作为默认值
                                            logging.warning(f"变量 {var_name} 的值 '{value}' 不在有效选项中，使用默认值")
                                            valid_coding[var_name] = valid_options[0] if valid_options else ""
                            else:
                                # 非分类变量，直接使用值
                                valid_coding[var_name] = value
                    
                    return valid_coding
                else:
                    # 尝试找到第一个 { 和最后一个 } 之间的内容
                    start_idx = coding_result.find('{')
                    end_idx = coding_result.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        coding_json = json.loads(coding_result[start_idx:end_idx+1])
                        # 处理JSON结果...
                        # 验证编码结果并确保分类变量的值在选项中
                        valid_coding = {}
                        for var in variables:
                            var_name = var.get('name', '')
                            var_type = var.get('type', '')
                            
                            # 检查变量是否在编码结果中
                            if var_name in coding_json:
                                value = coding_json[var_name]
                                
                                # 处理分类变量
                                if (var_type == "分类变量" or var_type == "select") and var_name in options_map:
                                    # 获取该变量的有效选项
                                    valid_options = options_map[var_name]
                                    
                                    # 检查值是否在有效选项中
                                    if value in valid_options:
                                        # 值直接匹配选项
                                        valid_coding[var_name] = value
                                    else:
                                        # 尝试模糊匹配
                                        best_match = None
                                        best_score = 0
                                        
                                        for option in valid_options:
                                            # 简单的包含关系检查
                                            if option.lower() in value.lower() or value.lower() in option.lower():
                                                score = len(set(option.lower()) & set(value.lower())) / max(len(option), len(value))
                                                if score > best_score:
                                                    best_score = score
                                                    best_match = option
                                        
                                        if best_match and best_score > 0.5:  # 设置一个阈值
                                            valid_coding[var_name] = best_match
                                        else:
                                            # 如果没有匹配，使用第一个选项作为默认值
                                            logging.warning(f"变量 {var_name} 的值 '{value}' 不在有效选项中，使用默认值")
                                            valid_coding[var_name] = valid_options[0] if valid_options else ""
                                else:
                                    # 非分类变量，直接使用值
                                    valid_coding[var_name] = value
                        
                        return valid_coding
                    else:
                        # 如果无法提取JSON，尝试按行解析
                        for line in coding_result.strip().split('\n'):
                            if '=' in line:
                                var_name, value = line.split('=', 1)
                                coding_results[var_name.strip()] = value.strip()
                        
                        # 验证编码结果并确保分类变量的值在选项中
                        valid_coding = {}
                        for var in variables:
                            var_name = var.get('name', '')
                            var_type = var.get('type', '')
                            
                            # 检查变量是否在编码结果中
                            if var_name in coding_results:
                                value = coding_results[var_name]
                                
                                # 处理分类变量
                                if (var_type == "分类变量" or var_type == "select") and var_name in options_map:
                                    # 获取该变量的有效选项
                                    valid_options = options_map[var_name]
                                    
                                    # 检查值是否在有效选项中
                                    if value in valid_options:
                                        # 值直接匹配选项
                                        valid_coding[var_name] = value
                                    else:
                                        # 尝试模糊匹配
                                        best_match = None
                                        best_score = 0
                                        
                                        for option in valid_options:
                                            # 简单的包含关系检查
                                            if option.lower() in value.lower() or value.lower() in option.lower():
                                                score = len(set(option.lower()) & set(value.lower())) / max(len(option), len(value))
                                                if score > best_score:
                                                    best_score = score
                                                    best_match = option
                                        
                                        if best_match and best_score > 0.5:  # 设置一个阈值
                                            valid_coding[var_name] = best_match
                                        else:
                                            # 如果没有匹配，使用第一个选项作为默认值
                                            logging.warning(f"变量 {var_name} 的值 '{value}' 不在有效选项中，使用默认值")
                                            valid_coding[var_name] = valid_options[0] if valid_options else ""
                                else:
                                    # 非分类变量，直接使用值
                                    valid_coding[var_name] = value
                        
                        return valid_coding
            except Exception as e:
                logging.error(f"解析编码结果失败: {str(e)}")
                # 如果JSON解析失败，尝试按行解析
                for line in coding_result.strip().split('\n'):
                    if '=' in line:
                        var_name, value = line.split('=', 1)
                        coding_results[var_name.strip()] = value.strip()
        
        return coding_results
    except Exception as e:
        logging.error(f"自动编码失败: {str(e)}")
        return None

@retry_with_backoff(max_retries=2, initial_backoff=5, backoff_factor=2)
def auto_code_video(video_path, frames_with_timestamps=None, variables=None, frame_interval=30, custom_prompt=None, 
                   vision_model="Qwen/Qwen2-VL-72B-Instruct", text_model="deepseek-ai/DeepSeek-V2.5"):
    """使用AI分析视频内容并为变量自动编码
    
    参数:
        video_path: 视频文件路径
        frames_with_timestamps: 预先提取的帧和时间戳，如果为None则自动提取
        variables: 变量列表
        frame_interval: 帧提取间隔（秒），仅在frames_with_timestamps为None时使用
        custom_prompt: 自定义提示词
        vision_model: 视觉语言模型ID
        text_model: 文本分析模型ID
    
    返回:
        变量编码结果字典
    """
    try:
        # 获取硅基流动客户端
        client = get_siliconflow_client()
        if not client:
            logging.error("未设置硅基流动API密钥，无法进行自动编码")
            return None
        
        # 提取视频帧
        if frames_with_timestamps is None:
            frames_with_timestamps = extract_video_frames(video_path, frame_interval)
        
        if not frames_with_timestamps:
            logging.error("视频帧提取失败")
            return None
        
        # 使用视觉语言模型分析每个帧
        frame_descriptions = []
        
        if 'analysis_progress' in st.session_state:
            st.session_state.analysis_progress.progress(0.1, text="分析视频帧...")
        
        # 限制帧数量，避免请求过大
        max_frames = min(len(frames_with_timestamps), 4)
        selected_frames = frames_with_timestamps[:max_frames]
        
        for i, (frame, timestamp) in enumerate(selected_frames):
            if 'analysis_progress' in st.session_state:
                progress = 0.1 + (i / max_frames) * 0.4
                st.session_state.analysis_progress.progress(progress, text=f"分析第 {i+1}/{max_frames} 帧...")
            
            # 转换帧为base64
            frame_base64 = convert_image_to_base64(frame)
            
            # 使用视觉语言模型分析帧
            try:
                response = client.chat.completions.create(
                    model=vision_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{frame_base64}"}
                                },
                                {
                                    "type": "text",
                                    "text": "请详细描述这个视频帧中的内容，包括场景、人物、活动和可能的主题。"
                                }
                            ]
                        }
                    ],
                    temperature=0.2,
                    max_tokens=500
                )
                
                if hasattr(response, 'choices') and len(response.choices) > 0 and hasattr(response.choices[0], 'message'):
                    description = response.choices[0].message.content
                    time_str = str(timedelta(seconds=int(timestamp)))
                    frame_descriptions.append(f"时间点: {time_str} (第{int(timestamp)}秒)\n描述: {description}")
            except Exception as e:
                logging.error(f"分析视频帧失败: {str(e)}")
                # 继续处理下一帧
        
        # 合并所有帧描述
        combined_description = "\n\n".join(frame_descriptions)
        
        if 'analysis_progress' in st.session_state:
            st.session_state.analysis_progress.progress(0.6, text="生成编码建议...")
        
        # 构建变量文本和选项映射
        variables_text = ""
        options_map = {}  # 用于存储每个变量的有效选项
        
        for var in variables:
            var_name = var.get('name', '')
            var_type = var.get('type', '')
            var_id = var.get('id', var_name)
            
            variables_text += f"{var_name} ({var_type})"
            
            # 处理选项
            if var_type == "分类变量" or var_type == "select":
                options = []
                
                # 处理不同格式的选项
                if 'options' in var and isinstance(var['options'], str):
                    # 字符串格式的选项，用逗号分隔
                    options = [opt.strip() for opt in var['options'].split(',') if opt.strip()]
                    options_map[var_name] = options
                    if options:
                        option_text = ", ".join(options)
                        variables_text += f" [选项: {option_text}]"
                
                elif 'options' in var and isinstance(var['options'], list):
                    # 列表格式的选项
                    if all(isinstance(opt, dict) for opt in var['options']):
                        # 选项是字典列表，包含value和label
                        option_labels = [opt.get('label', '') for opt in var['options'] if 'label' in opt]
                        option_values = [opt.get('value', '') for opt in var['options'] if 'value' in opt]
                        
                        if option_labels:
                            option_text = ", ".join(option_labels)
                            variables_text += f" [选项: {option_text}]"
                            options_map[var_name] = option_labels
                            # 同时保存值和标签的映射关系
                            options_map[f"{var_name}_values"] = option_values
                            options_map[f"{var_name}_labels"] = option_labels
                    else:
                        # 选项是简单列表
                        option_text = ", ".join(var['options'])
                        variables_text += f" [选项: {option_text}]"
                        options_map[var_name] = var['options']
            
            elif var_type == "李克特量表":
                likert_scale = var.get('likert_scale', 5)
                likert_labels = var.get('likert_labels', '')
                
                if likert_labels:
                    labels = [label.strip() for label in likert_labels.split(',') if label.strip()]
                    if labels:
                        variables_text += f" [量表: {', '.join(labels)}]"
                    else:
                        variables_text += f" [量表: 1-{likert_scale}]"
                else:
                    variables_text += f" [量表: 1-{likert_scale}]"
            
            # 添加编码指南
            if 'guide' in var and var['guide']:
                variables_text += f"\n编码指南: {var['guide']}"
            
            variables_text += "\n\n"
        
        # 使用自定义提示词或默认提示词
        if custom_prompt:
            user_prompt = custom_prompt.replace("{content}", combined_description).replace("{variables}", variables_text)
        else:
            user_prompt = f"""请根据以下视频描述，为指定的变量进行编码。

视频描述:
{combined_description}

需要编码的变量:
{variables_text}

请以JSON格式返回编码结果，格式为：
{{
    "变量名1": "编码值1",
    "变量名2": "编码值2",
    ...
}}

重要说明：
1. 对于分类变量，你必须且只能从提供的选项中选择一个，不要创建新的选项。
2. 对于李克特量表，请返回1到5之间的数值。
3. 请确保编码结果符合变量的要求和视频内容。
"""
        
        # 生成编码建议
        try:
            if 'analysis_progress' in st.session_state:
                st.session_state.analysis_progress.progress(0.7, text="生成编码结果...")
            
            response = client.chat.completions.create(
                model=text_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一位内容分析专家，擅长根据视频内容为变量赋值。请根据视频帧描述，为每个变量提供合适的编码值。对于分类变量，你必须且只能从提供的选项中选择一个，不要创建新的选项。"
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            if 'analysis_progress' in st.session_state:
                st.session_state.analysis_progress.progress(0.9, text="处理编码结果...")
            
            # 获取编码结果
            if hasattr(response, 'choices') and len(response.choices) > 0 and hasattr(response.choices[0], 'message'):
                coding_result = response.choices[0].message.content
                
                # 从响应文本中提取JSON
                try:
                    # 尝试直接解析
                    coding_json = json.loads(coding_result)
                except json.JSONDecodeError:
                    # 如果直接解析失败，尝试从文本中提取JSON部分
                    try:
                        json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', coding_result)
                        if json_match:
                            coding_json = json.loads(json_match.group(1))
                        else:
                            # 尝试找到第一个 { 和最后一个 } 之间的内容
                            start_idx = coding_result.find('{')
                            end_idx = coding_result.rfind('}')
                            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                                coding_json = json.loads(coding_result[start_idx:end_idx+1])
                            else:
                                raise ValueError("无法从响应中提取JSON")
                    except Exception as e:
                        logging.error(f"从响应提取JSON失败: {str(e)}")
                        return None
                
                # 验证编码结果并确保分类变量的值在选项中
                valid_coding = {}
                for var in variables:
                    var_name = var.get('name', '')
                    var_type = var.get('type', '')
                    var_id = var.get('id', var_name)
                    
                    # 检查变量是否在编码结果中
                    if var_name in coding_json:
                        value = coding_json[var_name]
                        
                        # 处理分类变量
                        if (var_type == "分类变量" or var_type == "select") and var_name in options_map:
                            # 获取该变量的有效选项
                            valid_options = options_map[var_name]
                            
                            # 检查值是否在有效选项中
                            if value in valid_options:
                                # 值直接匹配选项
                                valid_coding[var_name] = value
                            else:
                                # 尝试模糊匹配
                                best_match = None
                                best_score = 0
                                
                                for option in valid_options:
                                    # 简单的包含关系检查
                                    if option.lower() in value.lower() or value.lower() in option.lower():
                                        score = len(set(option.lower()) & set(value.lower())) / max(len(option), len(value))
                                        if score > best_score:
                                            best_score = score
                                            best_match = option
                                
                                if best_match and best_score > 0.5:  # 设置一个阈值
                                    valid_coding[var_name] = best_match
                                else:
                                    # 如果没有匹配，使用第一个选项作为默认值
                                    logging.warning(f"变量 {var_name} 的值 '{value}' 不在有效选项中，使用默认值")
                                    valid_coding[var_name] = valid_options[0] if valid_options else ""
                        else:
                            # 非分类变量，直接使用值
                            valid_coding[var_name] = value
                
                if 'analysis_progress' in st.session_state:
                    st.session_state.analysis_progress.progress(1.0, text="编码完成！")
                
                return valid_coding
            else:
                logging.error("无法获取编码结果")
                return None
        
        except Exception as e:
            logging.error(f"生成编码建议失败: {str(e)}")
            return None
    
    except Exception as e:
        logging.error(f"自动编码视频失败: {str(e)}")
        return None

# 硅基流动视频分析增强功能
@retry_with_backoff(max_retries=2, initial_backoff=5, backoff_factor=2)
def analyze_video_with_siliconflow(video_path, frame_interval=30, prompt="请分析这个视频的内容和主题", 
                          vision_model="Qwen/Qwen2-VL-72B-Instruct", 
                          text_model="deepseek-ai/DeepSeek-V2.5"):
    """使用硅基流动的视觉语言模型分析视频
    
    参数:
        video_path: 视频文件路径
        frame_interval: 帧提取间隔（秒）
        prompt: 分析提示
        vision_model: 视觉语言模型名称
        text_model: 文本分析模型名称
    
    返回:
        分析结果文本
    """
    try:
        # 获取硅基流动客户端
        client = get_siliconflow_client()
        if not client:
            return "请先设置硅基流动API密钥"
        
        # 提取视频帧
        frames_with_timestamps = extract_video_frames(video_path, frame_interval)
        if not frames_with_timestamps:
            return "视频帧提取失败"
        
        # 使用视觉语言模型分析每个帧
        frame_descriptions = []
        
        for i, (frame, timestamp) in enumerate(frames_with_timestamps):
            # 转换帧为base64
            frame_base64 = convert_image_to_base64(frame)
            
            try:
                # 使用视觉语言模型分析
                response = client.chat.completions.create(
                    model=vision_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{frame_base64}",
                                        "detail": "high"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": "请详细描述这个视频帧中的内容，包括场景、人物、动作和可能的主题。"
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
                
                if hasattr(response, 'choices') and len(response.choices) > 0 and hasattr(response.choices[0], 'message'):
                    frame_desc = response.choices[0].message.content
                    seconds = int(timestamp)
                    minutes = seconds // 60
                    remaining_seconds = seconds % 60
                    time_str = f"{minutes:02d}:{remaining_seconds:02d}"
                    frame_descriptions.append(f"时间点: {time_str} (第{seconds}秒)\n描述: {frame_desc}")
                else:
                    frame_descriptions.append(f"时间点: {timestamp}秒\n描述: 无法获取描述")
            except Exception as e:
                logging.error(f"分析帧失败: {str(e)}")
                frame_descriptions.append(f"时间点: {timestamp}秒\n描述: 分析失败 ({str(e)})")
        
        # 合并所有帧的描述
        combined_descriptions = "\n\n".join(frame_descriptions)
        
        # 使用文本模型进行整体分析
        final_response = client.chat.completions.create(
            model=text_model,
            messages=[
                {
                    "role": "system", 
                    "content": "你是一位专业的视频内容分析专家，擅长从视频内容中提取主题、情感和关键信息。"
                },
                {
                    "role": "user", 
                    "content": f"""
根据以下视频帧描述，{prompt}

视频帧描述：
{combined_descriptions}

请提供详细的分析，包括但不限于：
1. 视频的主要内容和主题
2. 关键场景和重要时刻
3. 人物及其行为、表情和互动
4. 视频风格和情感基调
5. 其他值得注意的关键元素

请以结构化的方式组织你的分析。
"""
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        if hasattr(final_response, 'choices') and len(final_response.choices) > 0 and hasattr(final_response.choices[0], 'message'):
            analysis_result = final_response.choices[0].message.content
        else:
            analysis_result = "无法获取分析结果"
        
        return analysis_result
    except Exception as e:
        logging.error(f"视频分析失败: {str(e)}")
        return f"视频分析失败: {str(e)}"

# 可靠性测试函数
def calculate_percentage_agreement(observations):
    """计算百分比一致性"""
    if not observations or len(observations) < 2:
        return 0
    
    total_agreements = 0
    total_comparisons = 0
    
    for i in range(len(observations)):
        for j in range(i+1, len(observations)):
            for var in observations[i].keys():
                if var in observations[j]:
                    total_comparisons += 1
                    if observations[i][var] == observations[j][var]:
                        total_agreements += 1
    
    if total_comparisons == 0:
        return 0
    
    return total_agreements / total_comparisons

def calculate_krippendorff_alpha(observations, categories):
    """计算Krippendorff's Alpha系数"""
    # 简化版实现
    if not observations or len(observations) < 2:
        return 0
    
    # 转换为矩阵格式
    variables = list(categories.keys())
    coders = len(observations)
    
    # 计算观察到的不一致
    observed_disagreement = 0
    total_pairs = 0
    
    for var in variables:
        values = [obs.get(var) for obs in observations if var in obs]
        if len(values) < 2:
            continue
            
        for i in range(len(values)):
            for j in range(i+1, len(values)):
                if values[i] != values[j]:
                    observed_disagreement += 1
                total_pairs += 1
    
    if total_pairs == 0:
        return 0
    
    observed_disagreement /= total_pairs
    
    # 计算期望的不一致
    expected_disagreement = 0
    
    for var in variables:
        if var not in categories:
            continue
            
        cat_values = categories[var]
        if not cat_values:
            continue
            
        # 计算每个类别的概率
        value_counts = {}
        total_values = 0
        
        for obs in observations:
            if var in obs:
                value = obs[var]
                value_counts[value] = value_counts.get(value, 0) + 1
                total_values += 1
        
        if total_values < 2:
            continue
            
        # 计算期望不一致
        var_expected_disagreement = 0
        for val1 in value_counts:
            for val2 in value_counts:
                if val1 != val2:
                    var_expected_disagreement += (value_counts[val1] / total_values) * (value_counts[val2] / total_values)
        
        expected_disagreement += var_expected_disagreement
    
    expected_disagreement /= len(variables)
    
    if expected_disagreement == 0:
        return 1
    
    # 计算alpha
    alpha = 1 - (observed_disagreement / expected_disagreement)
    return alpha

# 数据可视化函数
def create_wordcloud(text, stopwords=None):
    """创建词云"""
    if not text:
        return None
    
    # 分词
    words = jieba.lcut(text)
    word_text = " ".join(words)
    
    # 创建词云
    wc = WordCloud(
        font_path="simhei.ttf",  # 需要有中文字体
        width=800,
        height=400,
        background_color="white",
        max_words=200,
        stopwords=stopwords
    )
    
    wc.generate(word_text)
    
    # 转换为图像
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis("off")
    
    # 转换为base64
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    
    return img_str

def create_bar_chart(data, x, y, title, color=None):
    """创建条形图"""
    fig = px.bar(data, x=x, y=y, title=title, color=color)
    return fig

def create_pie_chart(data, names, values, title):
    """创建饼图"""
    fig = px.pie(data, names=names, values=values, title=title)
    return fig

def create_line_chart(data, x, y, title):
    """创建线图"""
    fig = px.line(data, x=x, y=y, title=title)
    return fig

def sanitize_file_path(file_path):
    """
    处理和修复文件路径，特别是处理包含特殊字符的路径
    和PyInstaller打包后的路径问题
    
    参数:
        file_path: 原始文件路径
        
    返回:
        修复后的文件路径
    """
    if not file_path:
        return file_path
        
    logging.info(f"处理文件路径: {file_path}")
    
    # 导入sys模块（如果尚未导入）
    try:
        import sys as _sys
        have_sys = True
    except ImportError:
        have_sys = False
        logging.warning("无法导入sys模块，部分路径处理功能将不可用")
    
    # 尝试多种方法修复路径
    fixed_path = file_path
    
    # 规范化路径，处理正反斜杠问题
    fixed_path = os.path.normpath(fixed_path)
    
    # 检查是否在PyInstaller环境
    if have_sys:
        try:
            # 检查是否在PyInstaller环境
            if getattr(_sys, 'frozen', False):
                # 尝试找到临时目录中的文件
                if not os.path.isabs(fixed_path):
                    temp_path = os.path.join(_sys._MEIPASS, fixed_path)
                    if os.path.exists(temp_path):
                        return temp_path
        except Exception as e:
            logging.warning(f"PyInstaller环境检查失败: {str(e)}")
    
    # 检查文件是否存在
    if not os.path.exists(fixed_path):
        # 尝试URL解码
        try:
            from urllib.parse import unquote
            decoded_path = unquote(fixed_path)
            if os.path.exists(decoded_path):
                return decoded_path
        except Exception:
            pass
            
        # 尝试绝对路径
        abs_path = os.path.abspath(fixed_path)
        if os.path.exists(abs_path):
            return abs_path
            
        # 尝试转义特殊字符
        special_chars = ['#', '?', '&', '%', ' ']
        path_parts = os.path.split(fixed_path)
        dir_path, filename = path_parts
        
        if any(char in filename for char in special_chars):
            logging.info(f"文件名包含特殊字符: {filename}")
            
            # 尝试在目录中寻找可能匹配的文件
            if os.path.exists(dir_path):
                # 获取文件名的基本部分（去除特殊字符前的部分）
                base_name = filename
                for char in special_chars:
                    if char in base_name:
                        base_name = base_name.split(char)[0]
                
                if base_name:
                    potential_files = [f for f in os.listdir(dir_path) 
                                    if f.startswith(base_name)]
                    
                    if potential_files:
                        logging.info(f"找到潜在匹配文件: {potential_files[0]}")
                        return os.path.join(dir_path, potential_files[0])
    
    return fixed_path 