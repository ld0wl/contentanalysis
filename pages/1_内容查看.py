import streamlit as st
import os
import base64
import tempfile
import sys  # 添加sys模块导入
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
import cv2
from moviepy.editor import VideoFileClip
import pandas as pd
import json
from utils import get_current_project_path, get_file_content, get_video_info, sanitize_file_path

# 设置页面配置
st.set_page_config(
    page_title="内容查看",
    page_icon="👁️",
    layout="wide"
)

# 检查是否有活动项目
if 'current_project' not in st.session_state or not st.session_state.current_project:
    st.warning("请先在首页选择或创建一个项目")
    st.stop()

# 页面标题
st.title("内容查看")
st.write(f"当前项目: {st.session_state.current_project}")

# 获取项目路径
project_path = get_current_project_path()
files_dir = os.path.join(project_path, "files")

# 检查文件目录是否存在
if not os.path.exists(files_dir):
    st.error("文件目录不存在")
    st.stop()

# 获取文件列表
files = [f for f in os.listdir(files_dir) if os.path.isfile(os.path.join(files_dir, f))]

if not files:
    st.info("项目中没有文件，请先上传文件")
    st.stop()

# 创建文件选择器
selected_file = st.selectbox("选择文件", files)
file_path = os.path.join(files_dir, selected_file)
file_ext = os.path.splitext(selected_file)[1].lower()

# 显示文件信息
st.subheader("文件信息")
file_size = os.path.getsize(file_path) / 1024  # KB
st.write(f"文件名: {selected_file}")
st.write(f"文件类型: {file_ext}")
st.write(f"文件大小: {round(file_size, 2)} KB")

# 根据文件类型显示内容
st.subheader("文件内容")

# PDF文件
if file_ext == '.pdf':
    # 显示PDF内容
    try:
        doc = fitz.open(file_path)
        
        # 创建PDF预览
        with st.expander("PDF预览", expanded=True):
            for page_num in range(min(5, len(doc))):  # 只显示前5页
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
                img_bytes = pix.tobytes("png")
                
                st.image(img_bytes, caption=f"第 {page_num+1} 页", use_column_width=True)
                
                if page_num < min(5, len(doc)) - 1:
                    st.markdown("---")
        
        # 显示PDF文本
        with st.expander("PDF文本内容"):
            text = ""
            for page in doc:
                text += page.get_text()
            st.text_area("文本内容", text, height=400)
        
        # 下载PDF
        with open(file_path, "rb") as file:
            btn = st.download_button(
                label="下载PDF文件",
                data=file,
                file_name=selected_file,
                mime="application/pdf"
            )
    except Exception as e:
        st.error(f"无法加载PDF文件: {str(e)}")

# Word文件
elif file_ext in ['.docx', '.doc']:
    try:
        doc = Document(file_path)
        
        # 提取文本
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        
        # 显示文本内容
        st.text_area("文档内容", text, height=400)
        
        # 下载Word文件
        with open(file_path, "rb") as file:
            btn = st.download_button(
                label="下载Word文件",
                data=file,
                file_name=selected_file,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    except Exception as e:
        st.error(f"无法加载Word文件: {str(e)}")

# 视频文件
elif file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
    st.subheader("视频信息")
    try:
        # 先处理文件路径，解决特殊字符问题
        file_path = sanitize_file_path(file_path)
        st.info(f"视频文件: {os.path.basename(file_path)}")
        
        # 获取视频信息
        video_info = get_video_info(file_path)
        
        if video_info:
            st.write(f"视频时长: {round(video_info['duration'], 2)} 秒")
            st.write(f"帧率: {video_info['fps']} FPS")
            st.write(f"分辨率: {video_info['size'][0]} x {video_info['size'][1]}")
            
            # 视频播放器 - 方法1: 使用st.video
            try:
                st.subheader("视频播放")
                video_file = open(file_path, 'rb')
                video_bytes = video_file.read()
                video_file.close()
                st.video(video_bytes)
            except Exception as e:
                st.error(f"使用Streamlit视频播放器失败: {str(e)}")
                
                # 尝试使用HTML5视频标签
                try:
                    st.warning("尝试使用HTML5视频播放器")
                    # 获取文件的相对路径
                    rel_path = os.path.join('projects', st.session_state.current_project, 'files', os.path.basename(file_path))
                    rel_path = rel_path.replace('\\', '/')  # 确保使用正斜杠
                    
                    # 使用HTML5视频标签
                    video_html = f"""
                    <video width="100%" controls>
                        <source src="{rel_path}" type="video/mp4">
                        您的浏览器不支持视频标签。
                    </video>
                    """
                    st.markdown(video_html, unsafe_allow_html=True)
                    
                    # 添加下载链接
                    st.write(f"如果视频无法播放，请[下载视频]({rel_path})后查看")
                except Exception as e2:
                    st.error(f"HTML5视频播放器也失败: {str(e2)}")
                    st.error("请使用外部播放器查看视频")
        
            # 提取关键帧
            with st.expander("视频关键帧"):
                # 设置帧提取间隔
                interval = st.slider("帧提取间隔(秒)", 1, 60, 10)
                
                if st.button("提取关键帧"):
                    with st.spinner("正在提取关键帧..."):
                        try:
                            # 打开视频
                            video = VideoFileClip(file_path)
                            duration = video.duration
                            
                            # 创建列布局
                            cols = st.columns(3)
                            frame_index = 0
                            
                            # 提取帧
                            for t in range(0, int(duration), interval):
                                frame = video.get_frame(t)
                                
                                # 将帧转换为PIL图像
                                from PIL import Image
                                import numpy as np
                                img = Image.fromarray(np.uint8(frame))
                                
                                # 显示帧
                                with cols[frame_index % 3]:
                                    st.image(img, caption=f"时间: {t}秒")
                                    frame_index += 1
                                    
                            video.close()
                        except Exception as e:
                            st.error(f"提取关键帧失败: {str(e)}")
        else:
            st.error("无法获取视频信息，请检查文件格式是否正确")
    except Exception as e:
        st.error(f"处理视频文件时出错: {str(e)}")
        st.warning("请尝试使用外部视频播放器查看此文件")
        import traceback
        st.error(f"错误详情: {traceback.format_exc()}")

# 文本文件
elif file_ext in ['.txt', '.md', '.json', '.csv']:
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 显示文本内容
        st.text_area("文件内容", content, height=400)
        
        # 如果是JSON文件，尝试解析并显示为表格
        if file_ext == '.json':
            try:
                json_data = json.loads(content)
                st.subheader("JSON数据")
                st.json(json_data)
            except:
                st.warning("无法解析JSON数据")
        
        # 如果是CSV文件，尝试解析并显示为表格
        elif file_ext == '.csv':
            try:
                df = pd.read_csv(file_path)
                st.subheader("CSV数据")
                st.dataframe(df)
            except:
                st.warning("无法解析CSV数据")
        
        # 下载文件
        with open(file_path, "rb") as file:
            btn = st.download_button(
                label="下载文件",
                data=file,
                file_name=selected_file,
                mime="text/plain"
            )
    except Exception as e:
        st.error(f"无法加载文本文件: {str(e)}")

# 图片文件
elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
    try:
        # 显示图片
        st.image(file_path, caption=selected_file, use_column_width=True)
        
        # 下载图片
        with open(file_path, "rb") as file:
            btn = st.download_button(
                label="下载图片",
                data=file,
                file_name=selected_file,
                mime=f"image/{file_ext[1:]}"
            )
    except Exception as e:
        st.error(f"无法加载图片文件: {str(e)}")

# 其他文件类型
else:
    st.warning(f"不支持预览的文件类型: {file_ext}")
    
    # 提供下载链接
    with open(file_path, "rb") as file:
        btn = st.download_button(
            label="下载文件",
            data=file,
            file_name=selected_file
        )

# 页脚
st.markdown("---")
st.markdown("内容分析工具 © 2023") 