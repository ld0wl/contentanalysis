# 在导入任何其他模块之前应用补丁
import os
import sys
import pathlib
import io
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("streamlit_app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("内容分析工具")

# 记录启动信息
logger.info("应用程序启动")
logger.info(f"Python版本: {sys.version}")
logger.info(f"运行环境: {'PyInstaller打包环境' if getattr(sys, 'frozen', False) else '开发环境'}")

# 创建一个假的Lorem ipsum.txt文件内容
LOREM_IPSUM_CONTENT = """Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum.
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia."""

# 保存原始的pathlib.Path.read_text方法
original_read_text = pathlib.Path.read_text

# 创建补丁方法
def patched_read_text(self, encoding=None, errors=None):
    try:
        return original_read_text(self, encoding=encoding, errors=errors)
    except FileNotFoundError as e:
        # 检查是否是Lorem ipsum.txt文件
        if 'Lorem ipsum.txt' in str(self):
            logger.info(f"使用补丁提供Lorem ipsum.txt内容: {self}")
            return LOREM_IPSUM_CONTENT
        logger.error(f"文件未找到: {self}, 错误: {e}")
        raise

# 应用补丁
pathlib.Path.read_text = patched_read_text

# 保存原始的pathlib.Path.open方法
original_open = pathlib.Path.open

# 创建补丁方法
def patched_open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
    try:
        return original_open(self, mode, buffering, encoding, errors, newline)
    except FileNotFoundError as e:
        # 检查是否是Lorem ipsum.txt文件
        if 'Lorem ipsum.txt' in str(self) and 'r' in mode:
            logger.info(f"使用补丁提供Lorem ipsum.txt文件对象: {self}")
            return io.StringIO(LOREM_IPSUM_CONTENT)
        logger.error(f"无法打开文件: {self}, 模式: {mode}, 错误: {e}")
        raise

# 应用补丁
pathlib.Path.open = patched_open

# 设置环境变量，解决Streamlit版本检测问题
os.environ["STREAMLIT_VERSION"] = "1.42.0"

# 创建一个假的streamlit.version模块
class VersionModule:
    def __init__(self):
        self.__version__ = "1.42.0"
        self.STREAMLIT_VERSION_STRING = "1.42.0"

# 检查是否在PyInstaller环境中运行
if getattr(sys, 'frozen', False):
    # 如果是打包后的环境，应用Streamlit版本补丁
    sys.modules['streamlit.version'] = VersionModule()
    logger.info("已应用Streamlit版本补丁")
    
    # 注意：移除了浏览器自动启动代码，现在由launcher.py负责

import importlib.util
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path
from datetime import datetime
import shutil
import requests
from io import BytesIO
import re
import time
import uuid
from utils import get_project_dir, get_current_project_path, save_project_data, load_project_data, get_siliconflow_client

# 设置页面配置
st.set_page_config(
    page_title="内容分析工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化会话状态
if 'current_project' not in st.session_state:
    st.session_state.current_project = None

if 'siliconflow_api_key' not in st.session_state:
    st.session_state.siliconflow_api_key = ""

# 侧边栏
with st.sidebar:
    st.title("内容分析工具")
    
    # 用户指南链接
    if os.path.exists(os.path.join(os.getcwd(), "content_analysis_streamlit", "用户指南.md")):
        with open(os.path.join(os.getcwd(), "content_analysis_streamlit", "用户指南.md"), "r", encoding="utf-8") as f:
            user_guide_content = f.read()
        
        st.markdown("[📖 查看用户指南](#user-guide)", unsafe_allow_html=True)
        
        # 创建一个展开面板，用于显示用户指南
        with st.expander("关于本工具"):
            st.markdown("""
            内容分析工具是一个基于Streamlit的应用程序，用于文本和视频内容的编码、分析和可视化。
            
            主要功能包括：
            - 内容查看：支持PDF、Word、视频等多种格式
            - 内容编码：支持手动编码和AI辅助自动编码
            - 主题分析：使用BERTopic进行主题建模
            - 视频分析：支持视频内容的自动化编码
            - 可靠性测试：支持编码员间一致性检验
            
            点击上方的"查看用户指南"链接获取详细使用说明。
            """)
    
    # API设置
    with st.expander("API设置", expanded=True):  # 默认展开API设置
        st.markdown("""
        ### 硅基流动API密钥设置
        请设置硅基流动API密钥以启用AI辅助功能。硅基流动提供文本分析和视觉分析能力。
        
        **注意**：视频分析功能需要设置硅基流动API密钥。
        """)
        
        st.markdown("""
        **硅基流动API密钥格式说明**：
        - 硅基流动API密钥通常以`sf-`开头
        - 请确保复制完整的API密钥，不包含多余的空格
        - 如果您没有硅基流动API密钥，请访问[硅基流动官网](https://docs.siliconflow.cn/)申请
        """)
        
        api_key = st.text_input("硅基流动API密钥", 
                            value=st.session_state.siliconflow_api_key,
                            type="password")
        if api_key:
            st.session_state.siliconflow_api_key = api_key
            st.success("硅基流动API密钥已设置")
            
            # 测试API连接
            try:
                client = get_siliconflow_client()
                if client:
                    test_response = client.chat.completions.create(
                        model="deepseek-ai/DeepSeek-V2.5",
                        messages=[{"role": "user", "content": "API测试"}],
                        max_tokens=5
                    )
                    st.success("✅ 硅基流动API验证成功")
                else:
                    st.warning("⚠️ 硅基流动API密钥可能无效")
            except Exception as e:
                st.error(f"API验证失败：{str(e)}")
    
    # 项目管理
    st.header("项目管理")
    
    # 创建新项目
    with st.form("new_project_form"):
        new_project_name = st.text_input("新项目名称")
        create_project = st.form_submit_button("创建项目")
        
        if create_project and new_project_name:
            project_dir = os.path.join(get_project_dir(), new_project_name)
            if os.path.exists(project_dir):
                st.error(f"项目 '{new_project_name}' 已存在")
            else:
                os.makedirs(project_dir)
                os.makedirs(os.path.join(project_dir, "files"))
                
                # 创建项目配置文件
                project_config = {
                    "name": new_project_name,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "variables": [],
                    "coding_guide": {}
                }
                
                with open(os.path.join(project_dir, "config.json"), 'w', encoding='utf-8') as f:
                    json.dump(project_config, f, ensure_ascii=False, indent=2)
                
                st.session_state.current_project = new_project_name
                st.success(f"项目 '{new_project_name}' 创建成功")
                st.rerun()
    
    # 加载项目列表
    project_dir = get_project_dir()
    projects = [d for d in os.listdir(project_dir) 
               if os.path.isdir(os.path.join(project_dir, d))]
    
    if projects:
        selected_project = st.selectbox(
            "选择项目",
            projects,
            index=projects.index(st.session_state.current_project) if st.session_state.current_project in projects else 0
        )
        
        if st.button("加载项目"):
            st.session_state.current_project = selected_project
            st.success(f"项目 '{selected_project}' 已加载")
            st.rerun()
        
        if st.session_state.current_project and st.button("删除项目", type="primary", help="此操作不可撤销"):
            project_to_delete = st.session_state.current_project
            confirm = st.text_input("输入项目名称确认删除", key="confirm_delete")
            
            if confirm == project_to_delete:
                project_path = os.path.join(project_dir, project_to_delete)
                try:
                    shutil.rmtree(project_path)
                    st.session_state.current_project = None
                    st.success(f"项目 '{project_to_delete}' 已删除")
                    st.rerun()
                except Exception as e:
                    st.error(f"删除项目失败: {str(e)}")
    else:
        st.info("没有可用的项目，请创建新项目")

# 主内容区域
st.title("内容分析工具")
st.markdown("欢迎使用内容分析工具，这是一个用于内容编码和分析的应用程序。")

# 用户指南
with st.expander("用户指南", expanded=True):
    st.markdown("""
    ## 使用指南
    
    ### 1. 项目管理
    - 在首页创建或选择一个项目
    - 每个项目独立保存所有数据和设置
    
    ### 2. 内容管理
    - 在"内容管理"页面上传文件或添加视频链接
    - 支持文本文件(.txt)、Word文档(.docx)、PDF文件(.pdf)和视频文件(.mp4, .avi等)
    - 可以预览和删除已上传的内容
    
    ### 3. 编码管理
    - 在"编码管理"页面创建和管理变量
    - 支持文本变量、分类变量、李克特量表和数值变量
    - 可以为每个变量添加编码指南，帮助编码员理解如何编码
    - 变量可以随时编辑或删除（删除操作不可恢复）
    
    ### 4. 内容编码
    - 在"内容编码"页面对内容进行编码
    - 可以手动编码或使用AI辅助功能
    - 编码结果会自动保存
    - 支持批量编码功能，可以一次性对多个文件进行编码
    - 自动编码功能会严格按照变量定义和编码指南进行编码，对于分类变量只会从选项中选择
    - 可以自定义提示词，增强AI编码的准确性
    
    ### 5. 视频分析
    - 在"视频分析"页面分析视频内容
    - 支持关键帧提取和描述
    - 可以进行自动编码
    - 批量视频分析功能允许一次性处理多个视频
    - 可以选择不同的视觉语言模型和文本模型进行分析
    
    ### 6. 结果分析
    - 在"结果分析"页面查看和分析编码结果
    - 支持导出为CSV或Excel格式
    - 提供基本的统计分析和可视化
    - 可以计算编码员间信度
    
    ### 7. API设置
    - 在"设置"页面配置API密钥和其他设置
    - 支持硅基流动API
    
    ### 注意事项
    - 所有数据都保存在本地，不会上传到云端
    - 大文件处理可能需要较长时间
    - 视频分析需要安装额外的依赖库
    """)

# 项目选择
st.header("项目选择")

# 检查当前项目
if st.session_state.current_project:
    st.header(f"当前项目: {st.session_state.current_project}")
    
    # 加载项目配置
    project_path = get_current_project_path()
    config_path = os.path.join(project_path, "config.json")
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
        
        # 显示项目信息
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("项目信息")
            st.write(f"创建时间: {project_config.get('created_at', '未知')}")
            st.write(f"变量数量: {len(project_config.get('variables', []))}")
            
            # 加载编码结果
            coding_results_path = os.path.join(project_path, "coding_results.json")
            if os.path.exists(coding_results_path):
                with open(coding_results_path, 'r', encoding='utf-8') as f:
                    coding_results = json.load(f)
                st.write(f"已编码文件: {len(coding_results)}")
        
        # 文件管理
        st.subheader("文件管理")
        
        # 创建选项卡
        upload_tab1, upload_tab2, upload_tab3, upload_tab4 = st.tabs(["单个文件上传", "批量上传", "视频链接上传", "批量文本内容上传"])
        
        # 单个文件上传
        with upload_tab1:
            uploaded_files = st.file_uploader("上传文件", accept_multiple_files=True)
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    file_path = os.path.join(project_path, "files", uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"文件 '{uploaded_file.name}' 上传成功")
        
        # 批量上传
        with upload_tab2:
            st.write("通过Excel文件批量上传文件")
            st.markdown("""
            ### 批量上传说明
            
            请上传一个Excel文件，文件应包含以下列：
            - **file_path**: 本地文件路径（绝对路径）
            - **file_url**: 文件URL（可选，如果提供则从URL下载）
            - **file_name**: 文件名称（可选，如果不提供则使用原始文件名）
            
            您可以下载[模板文件](https://example.com/template.xlsx)进行填写。
            """)
            
            # 上传Excel文件
            batch_file = st.file_uploader("上传批量导入Excel文件", type=["xlsx", "xls"])
            
            if batch_file:
                try:
                    df = pd.read_excel(batch_file)
                    st.write("Excel文件预览:")
                    st.dataframe(df.head())
                    
                    # 检查必要的列
                    if "file_path" not in df.columns and "file_url" not in df.columns:
                        st.error("Excel文件必须包含'file_path'或'file_url'列")
                    else:
                        if st.button("开始批量导入"):
                            with st.spinner("正在批量导入文件..."):
                                success_count = 0
                                error_count = 0
                                
                                for index, row in df.iterrows():
                                    try:
                                        # 确定文件名
                                        if "file_name" in df.columns and not pd.isna(row["file_name"]):
                                            file_name = row["file_name"]
                                        elif "file_path" in df.columns and not pd.isna(row["file_path"]):
                                            file_name = os.path.basename(row["file_path"])
                                        elif "file_url" in df.columns and not pd.isna(row["file_url"]):
                                            file_name = os.path.basename(row["file_url"].split("?")[0])
                                        else:
                                            file_name = f"file_{index}.bin"
                                        
                                        # 目标文件路径
                                        target_path = os.path.join(project_path, "files", file_name)
                                        
                                        # 从本地路径或URL获取文件
                                        if "file_path" in df.columns and not pd.isna(row["file_path"]):
                                            # 从本地路径复制
                                            shutil.copy2(row["file_path"], target_path)
                                            success_count += 1
                                        elif "file_url" in df.columns and not pd.isna(row["file_url"]):
                                            # 从URL下载
                                            response = requests.get(row["file_url"])
                                            if response.status_code == 200:
                                                with open(target_path, "wb") as f:
                                                    f.write(response.content)
                                                success_count += 1
                                            else:
                                                st.error(f"下载文件失败: {row['file_url']}, 状态码: {response.status_code}")
                                                error_count += 1
                                    except Exception as e:
                                        st.error(f"导入文件失败: {str(e)}")
                                        error_count += 1
                                
                                st.success(f"批量导入完成: 成功 {success_count} 个文件, 失败 {error_count} 个文件")
                                if success_count > 0:
                                    st.rerun()
                except Exception as e:
                    st.error(f"读取Excel文件失败: {str(e)}")
        
        # 视频链接上传
        with upload_tab3:
            st.write("添加视频链接")
            
            # 创建子选项卡
            link_tab1, link_tab2 = st.tabs(["单个链接", "批量链接"])
            
            # 单个链接上传
            with link_tab1:
                with st.form("video_link_form"):
                    video_url = st.text_input("视频URL")
                    video_name = st.text_input("视频名称 (可选)")
                    submit_video = st.form_submit_button("添加视频链接")
                    
                    if submit_video and video_url:
                        try:
                            # 确定视频名称
                            if not video_name:
                                video_name = os.path.basename(video_url.split("?")[0])
                                if not video_name or "." not in video_name:
                                    video_name = f"video_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
                            elif "." not in video_name:
                                video_name = f"{video_name}.mp4"
                            
                            # 保存视频链接信息
                            video_links_path = os.path.join(project_path, "video_links.json")
                            video_links = {}
                            
                            if os.path.exists(video_links_path):
                                with open(video_links_path, 'r', encoding='utf-8') as f:
                                    video_links = json.load(f)
                            
                            video_links[video_name] = video_url
                            
                            with open(video_links_path, 'w', encoding='utf-8') as f:
                                json.dump(video_links, f, ensure_ascii=False, indent=2)
                            
                            st.success(f"视频链接 '{video_name}' 添加成功")
                            st.rerun()
                        except Exception as e:
                            st.error(f"添加视频链接失败: {str(e)}")
            
            # 批量链接上传
            with link_tab2:
                st.write("通过Excel文件批量添加视频链接")
                st.markdown("""
                ### 批量添加视频链接说明
                
                请上传一个Excel文件，文件应包含以下列：
                - **video_url**: 视频URL（必填）
                - **video_name**: 视频名称（可选，如果不提供则使用URL中的文件名或生成随机名称）
                
                您可以下载[模板文件](https://example.com/video_links_template.xlsx)进行填写。
                """)
                
                # 上传Excel文件
                batch_links_file = st.file_uploader("上传批量视频链接Excel文件", type=["xlsx", "xls"], key="batch_links")
                
                if batch_links_file:
                    try:
                        df = pd.read_excel(batch_links_file)
                        st.write("Excel文件预览:")
                        st.dataframe(df.head())
                        
                        # 检查必要的列
                        if "video_url" not in df.columns:
                            st.error("Excel文件必须包含'video_url'列")
                        else:
                            if st.button("开始批量添加视频链接"):
                                with st.spinner("正在批量添加视频链接..."):
                                    success_count = 0
                                    error_count = 0
                                    
                                    # 加载现有视频链接
                                    video_links_path = os.path.join(project_path, "video_links.json")
                                    video_links = {}
                                    
                                    if os.path.exists(video_links_path):
                                        with open(video_links_path, 'r', encoding='utf-8') as f:
                                            video_links = json.load(f)
                                    
                                    # 处理每一行
                                    for index, row in df.iterrows():
                                        try:
                                            if pd.isna(row["video_url"]):
                                                continue
                                                
                                            video_url = row["video_url"]
                                            
                                            # 确定视频名称
                                            if "video_name" in df.columns and not pd.isna(row["video_name"]):
                                                video_name = row["video_name"]
                                                if "." not in video_name:
                                                    video_name = f"{video_name}.mp4"
                                            else:
                                                video_name = os.path.basename(video_url.split("?")[0])
                                                if not video_name or "." not in video_name:
                                                    video_name = f"video_{datetime.now().strftime('%Y%m%d%H%M%S')}_{index}.mp4"
                                            
                                            # 添加到视频链接字典
                                            video_links[video_name] = video_url
                                            success_count += 1
                                            
                                        except Exception as e:
                                            st.error(f"添加视频链接失败 (行 {index+2}): {str(e)}")
                                            error_count += 1
                                    
                                    # 保存视频链接
                                    with open(video_links_path, 'w', encoding='utf-8') as f:
                                        json.dump(video_links, f, ensure_ascii=False, indent=2)
                                    
                                    st.success(f"批量添加完成: 成功 {success_count} 个链接, 失败 {error_count} 个链接")
                                    if success_count > 0:
                                        st.rerun()
                    except Exception as e:
                        st.error(f"读取Excel文件失败: {str(e)}")
        
        # 添加批量文本内容上传选项卡
        with upload_tab4:
            st.write("批量上传文本内容")
            st.markdown("""
            ### 批量上传文本内容说明
            
            请上传一个Excel文件，文件应包含以下列：
            - **title**: 文章标题（必填）
            - **content**: 文章内容（必填）
            - **source**: 文章来源（可选）
            - **publish_date**: 发布日期（可选，格式：YYYY-MM-DD）
            
            每一行将作为一篇单独的文章保存到项目中。
            """)
            
            # 上传Excel文件
            batch_text_file = st.file_uploader("上传批量文本内容Excel文件", type=["xlsx", "xls"], key="batch_text")
            
            if batch_text_file:
                try:
                    df = pd.read_excel(batch_text_file)
                    st.write("Excel文件预览:")
                    st.dataframe(df.head())
                    
                    # 检查必要的列
                    if "title" not in df.columns or "content" not in df.columns:
                        st.error("Excel文件必须包含'title'和'content'列")
                    else:
                        if st.button("开始批量添加文本内容"):
                            with st.spinner("正在批量添加文本内容..."):
                                success_count = 0
                                error_count = 0
                                
                                # 确保文件目录存在
                                files_dir = os.path.join(project_path, "files")
                                os.makedirs(files_dir, exist_ok=True)
                                
                                # 处理每一行
                                for index, row in df.iterrows():
                                    try:
                                        if pd.isna(row["title"]) or pd.isna(row["content"]):
                                            continue
                                            
                                        title = row["title"]
                                        content = row["content"]
                                        
                                        # 获取可选字段
                                        source = row["source"] if "source" in df.columns and not pd.isna(row["source"]) else ""
                                        publish_date = row["publish_date"] if "publish_date" in df.columns and not pd.isna(row["publish_date"]) else ""
                                        
                                        # 创建文件名（使用标题的前20个字符，移除特殊字符）
                                        safe_title = re.sub(r'[^\w\s]', '', title)
                                        safe_title = re.sub(r'\s+', '_', safe_title)
                                        file_name = f"{safe_title[:20]}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{index}.txt"
                                        
                                        # 创建文本文件
                                        file_path = os.path.join(files_dir, file_name)
                                        
                                        # 写入文本内容
                                        with open(file_path, 'w', encoding='utf-8') as f:
                                            # 添加元数据
                                            f.write(f"标题: {title}\n")
                                            if source:
                                                f.write(f"来源: {source}\n")
                                            if publish_date:
                                                f.write(f"发布日期: {publish_date}\n")
                                            f.write("\n")  # 空行分隔元数据和内容
                                            f.write(content)
                                        
                                        success_count += 1
                                        
                                    except Exception as e:
                                        st.error(f"添加文本内容失败 (行 {index+2}): {str(e)}")
                                        error_count += 1
                                
                                st.success(f"批量添加完成: 成功 {success_count} 篇文章, 失败 {error_count} 篇文章")
                                if success_count > 0:
                                    st.rerun()
                except Exception as e:
                    st.error(f"读取Excel文件失败: {str(e)}")
        
        # 显示文件列表
        files_dir = os.path.join(project_path, "files")
        if os.path.exists(files_dir):
            files = [f for f in os.listdir(files_dir) if os.path.isfile(os.path.join(files_dir, f))]
            
            # 加载视频链接
            video_links_path = os.path.join(project_path, "video_links.json")
            video_links = {}
            if os.path.exists(video_links_path):
                with open(video_links_path, 'r', encoding='utf-8') as f:
                    video_links = json.load(f)
            
            # 合并文件列表和视频链接
            all_files = files.copy()
            for video_name in video_links.keys():
                if video_name not in all_files:
                    all_files.append(f"[链接] {video_name}")
            
            if all_files:
                st.write(f"项目中共有 {len(all_files)} 个文件")
                
                # 创建文件表格
                file_data = []
                for file in all_files:
                    if file.startswith("[链接] "):
                        # 视频链接
                        file_name = file[6:]  # 去掉 "[链接] " 前缀
                        file_data.append({
                            "文件名": file,
                            "类型": "视频链接",
                            "大小(KB)": "-",
                            "URL": video_links.get(file_name, "")
                        })
                    else:
                        # 本地文件
                        file_path = os.path.join(files_dir, file)
                        file_size = os.path.getsize(file_path) / 1024  # KB
                        file_type = os.path.splitext(file)[1]
                        file_data.append({
                            "文件名": file,
                            "类型": file_type,
                            "大小(KB)": round(file_size, 2),
                            "URL": ""
                        })
                
                file_df = pd.DataFrame(file_data)
                st.dataframe(file_df, use_container_width=True)
                
                # 删除选定文件
                files_to_delete = st.multiselect("选择要删除的文件", all_files)
                if files_to_delete and st.button("删除选定文件"):
                    for file in files_to_delete:
                        if file.startswith("[链接] "):
                            # 删除视频链接
                            file_name = file[6:]  # 去掉 "[链接] " 前缀
                            if file_name in video_links:
                                del video_links[file_name]
                                st.success(f"视频链接 '{file_name}' 已删除")
                        else:
                            # 删除本地文件
                            file_path = os.path.join(files_dir, file)
                            try:
                                os.remove(file_path)
                                st.success(f"文件 '{file}' 已删除")
                            except Exception as e:
                                st.error(f"删除文件 '{file}' 失败: {str(e)}")
                    
                    # 保存更新后的视频链接
                    if os.path.exists(video_links_path):
                        with open(video_links_path, 'w', encoding='utf-8') as f:
                            json.dump(video_links, f, ensure_ascii=False, indent=2)
                    
                    st.rerun()
            else:
                st.info("项目中没有文件，请上传文件")
    else:
        st.error("项目配置文件不存在")

# 页脚
st.markdown("---")
st.markdown("内容分析工具 © 2025 灵动未来") 