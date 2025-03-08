import streamlit as st
import os
import json
import pandas as pd
import numpy as np
import tempfile
import cv2
import base64
import logging
import io
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import timedelta, datetime
from io import BytesIO
from utils import (
    get_current_project_path, 
    get_video_info, 
    extract_video_frames, 
    auto_code_video, 
    analyze_video_with_siliconflow, 
    get_siliconflow_client,
    convert_image_to_base64,
    load_variables,
    create_bar_chart,
    create_pie_chart
)

# 设置matplotlib中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'Microsoft YaHei', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

# 辅助函数：将李克特量表值转换为数值
def convert_likert_to_numeric(value):
    if pd.isna(value) or value == "":
        return np.nan
    try:
        return float(value)
    except (ValueError, TypeError):
        return value

# 辅助函数：确保DataFrame中的李克特量表列为数值类型
def ensure_likert_columns_numeric(df, variables_dict):
    for col in df.columns:
        if col in variables_dict and variables_dict[col].get('type') == "李克特量表":
            df[col] = df[col].apply(convert_likert_to_numeric)
    return df

# 设置页面配置
st.set_page_config(
    page_title="视频分析",
    page_icon="🎬",
    layout="wide"
)

# 检查是否有活动项目
if 'current_project' not in st.session_state or not st.session_state.current_project:
    st.warning("请先在首页选择或创建一个项目")
    st.stop()

# 页面标题
st.title("视频分析")
st.write(f"当前项目: {st.session_state.current_project}")

# 添加功能说明
st.markdown("""
## 功能介绍

本页面采用整合的视频分析方法，支持以下功能：

1. **视频预览**：查看项目中的视频文件和链接
2. **关键帧分析**：提取视频关键帧并分析内容
3. **自动编码**：根据视频内容自动生成变量编码建议
4. **高级分析**：对视频主题、情感、内容等进行深度分析

视频分析使用硅基流动视觉语言模型提供支持。
""")

# 检查API密钥
siliconflow_client = get_siliconflow_client()

if not siliconflow_client:
    st.warning("请在侧边栏设置硅基流动API密钥以启用视频分析功能")
    st.markdown("""
    视频分析需要使用硅基流动API。请在侧边栏的API设置中配置API密钥。
    """)
    st.stop()

# 显示API状态
with st.expander("API状态", expanded=False):
    if siliconflow_client:
        st.success("✅ 硅基流动API已连接")
        # 添加API连接测试功能
        if st.button("测试API连接"):
            with st.spinner("正在测试API连接..."):
                try:
                    # 创建一个简单的测试请求
                    test_response = siliconflow_client.chat.completions.create(
                        model="deepseek-ai/DeepSeek-V2.5",
                        messages=[{"role": "user", "content": "测试API连接"}],
                        max_tokens=5
                    )
                    st.success("API连接测试成功！")
                except Exception as e:
                    st.error(f"API连接测试失败: {str(e)}")
    else:
        st.warning("⚠️ 硅基流动API未连接")

# 获取项目路径
project_path = get_current_project_path()
config_path = os.path.join(project_path, "config.json")
files_dir = os.path.join(project_path, "files")
coding_results_path = os.path.join(project_path, "coding_results.json")
video_analysis_path = os.path.join(project_path, "video_analysis.json")
video_links_path = os.path.join(project_path, "video_links.json")

# 加载项目配置
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        project_config = json.load(f)
else:
    st.error("项目配置文件不存在")
    st.stop()

# 初始化变量列表
variables = project_config.get('variables', [])
coding_guide = project_config.get('coding_guide', {})

# 加载编码结果
coding_results = {}
if os.path.exists(coding_results_path):
    with open(coding_results_path, 'r', encoding='utf-8') as f:
        coding_results = json.load(f)

# 加载视频分析结果
video_analysis = {}
if os.path.exists(video_analysis_path):
    with open(video_analysis_path, 'r', encoding='utf-8') as f:
        video_analysis = json.load(f)

# 获取视频文件列表
video_files = []
if os.path.exists(files_dir):
    video_files = [f for f in os.listdir(files_dir) 
                  if os.path.isfile(os.path.join(files_dir, f)) and 
                  os.path.splitext(f)[1].lower() in ['.mp4', '.avi', '.mov', '.mkv']]

# 加载视频链接
video_links = {}
if os.path.exists(video_links_path):
    with open(video_links_path, 'r', encoding='utf-8') as f:
        video_links = json.load(f)

# 合并视频文件和链接
all_videos = video_files.copy()
for video_name in video_links.keys():
    if video_name not in all_videos:
        all_videos.append(f"[链接] {video_name}")

# 添加批量视频分析功能
if all_videos:
    with st.expander("批量视频分析", expanded=False):
        st.write("您可以使用批量分析功能一次性对多个视频进行分析和编码。")
        
        # 添加全选功能
        select_col1, select_col2 = st.columns([3, 1])
        
        with select_col1:
            st.write("选择要批量分析的视频:")
        
        with select_col2:
            if st.button("全选", key="select_all_videos"):
                st.session_state['selected_all_videos'] = True
            
            if st.button("清除", key="clear_all_videos"):
                st.session_state['selected_all_videos'] = False
        
        # 选择要批量分析的视频
        if 'selected_all_videos' not in st.session_state:
            st.session_state['selected_all_videos'] = False
        
        # 根据全选状态设置默认值
        default_selection = all_videos if st.session_state['selected_all_videos'] else []
        
        # 选择要批量分析的视频
        videos_to_batch_analyze = st.multiselect(
            "视频列表", 
            all_videos,
            default=default_selection
        )
        
        # 批量分析选项
        batch_analyze_col1, batch_analyze_col2 = st.columns(2)
        
        with batch_analyze_col1:
            batch_frame_interval = st.slider(
                "帧提取间隔（秒）", 
                min_value=10, 
                max_value=120, 
                value=30, 
                step=10
            )
        
        with batch_analyze_col2:
            batch_auto_code = st.checkbox("自动编码", value=True)
        
        # 添加模型选择
        if batch_auto_code:
            batch_model_col1, batch_model_col2 = st.columns(2)
            
            with batch_model_col1:
                # 视觉模型选择
                vision_models = {
                    "通义千问2-VL-72B": "Qwen/Qwen2-VL-72B-Instruct",
                    "通义千问-VL": "Qwen/Qwen-VL-Chat",
                    "DeepSeek-VL2": "deepseek-ai/deepseek-vl2",
                    "InternVL2": "OpenGVLab/InternVL2-8B",
                    "InternVL2-26B": "OpenGVLab/InternVL2-26B",
                    "Qwen-QVQ-72B": "Qwen/QVQ-72B-Preview"
                }
                
                batch_vision_model = st.selectbox(
                    "视觉语言模型", 
                    list(vision_models.keys()),
                    index=0,
                    help="用于分析视频帧的视觉语言模型",
                    key="batch_vision_model"
                )
            
            with batch_model_col2:
                # 文本模型选择
                text_models = {
                    "DeepSeek-V2.5": "deepseek-ai/DeepSeek-V2.5",
                    "DeepSeek-Coder": "deepseek-ai/deepseek-coder-v2",
                    "通义千问2-7B": "Qwen/Qwen2-7B-Instruct"
                }
                
                batch_text_model = st.selectbox(
                    "文本模型", 
                    list(text_models.keys()),
                    index=0,
                    help="用于整体分析的文本模型",
                    key="batch_text_model"
                )
        
        # 批量分析按钮
        if st.button("开始批量分析", type="primary", use_container_width=True):
            if not videos_to_batch_analyze:
                st.error("请选择至少一个视频进行批量分析")
            else:
                # 创建进度条
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 批量分析处理
                for i, video_name in enumerate(videos_to_batch_analyze):
                    progress = (i) / len(videos_to_batch_analyze)
                    progress_bar.progress(progress, text=f"正在分析 {video_name}...")
                    status_text.info(f"正在分析 {i+1}/{len(videos_to_batch_analyze)}: {video_name}")
                    
                    # 处理视频链接
                    if video_name.startswith("[链接] "):
                        original_name = video_name[7:]  # 去掉 "[链接] " 前缀
                        video_url = video_links.get(original_name, "")
                        
                        if not video_url:
                            status_text.warning(f"找不到视频链接: {original_name}")
                            continue
                        
                        # 分析视频链接
                        status_text.info(f"正在分析视频链接: {original_name}")
                        
                        # 目前无法直接分析视频链接，提示用户
                        status_text.warning(f"暂不支持直接分析视频链接: {original_name}")
                        continue
                    
                    # 处理本地视频文件
                    video_path = os.path.join(files_dir, video_name)
                    if not os.path.exists(video_path):
                        status_text.warning(f"找不到视频文件: {video_name}")
                        continue
                    
                    try:
                        # 分析视频
                        status_text.info(f"正在提取视频帧: {video_name}")
                        
                        # 提取视频帧
                        frames_with_timestamps = extract_video_frames(video_path, int(batch_frame_interval))
                        if not frames_with_timestamps:
                            status_text.warning(f"无法提取视频帧: {video_name}")
                            continue
                        
                        # 分析视频帧
                        status_text.info(f"正在分析视频帧: {video_name}")
                        
                        # 保存分析结果
                        if video_name not in video_analysis:
                            video_analysis[video_name] = {}
                        
                        # 保存帧信息
                        video_analysis[video_name]['frames'] = []
                        for j, (frame, timestamp) in enumerate(frames_with_timestamps):
                            # 转换帧为base64
                            frame_base64 = convert_image_to_base64(frame)
                            
                            # 保存帧信息
                            video_analysis[video_name]['frames'].append({
                                'timestamp': timestamp,
                                'frame_base64': frame_base64
                            })
                        
                        # 保存视频分析结果
                        with open(video_analysis_path, 'w', encoding='utf-8') as f:
                            json.dump(video_analysis, f, ensure_ascii=False, indent=2)
                        
                        # 自动编码
                        if batch_auto_code:
                            status_text.info(f"正在自动编码: {video_name}")
                            
                            # 自动编码
                            coding_result = auto_code_video(
                                video_path, 
                                frames_with_timestamps, 
                                variables,
                                batch_frame_interval,
                                vision_model=vision_models.get(batch_vision_model, "Qwen/Qwen2-VL-72B-Instruct"),
                                text_model=text_models.get(batch_text_model, "deepseek-ai/DeepSeek-V2.5")
                            )
                            
                            if coding_result:
                                # 更新编码结果
                                if video_name not in coding_results:
                                    coding_results[video_name] = {}
                                
                                for var_name, value in coding_result.items():
                                    coding_results[video_name][var_name] = value
                                
                                # 保存编码结果
                                with open(coding_results_path, 'w', encoding='utf-8') as f:
                                    json.dump(coding_results, f, ensure_ascii=False, indent=2)
                                
                                status_text.success(f"视频 {video_name} 自动编码成功")
                            else:
                                status_text.warning(f"视频 {video_name} 自动编码失败")
                        
                    except Exception as e:
                        status_text.error(f"处理视频 {video_name} 时出错: {str(e)}")
                
                # 完成进度
                progress_bar.progress(1.0, text="批量分析完成！")
                status_text.success(f"已完成 {len(videos_to_batch_analyze)} 个视频的批量分析")

if not all_videos:
    st.warning("项目中没有视频文件或链接，请先上传视频或添加视频链接")
    
    # 提供链接添加功能
    st.subheader("添加视频链接")
    with st.form("video_link_form"):
        video_url = st.text_input("视频URL")
        video_name = st.text_input("视频名称 (可选)")
        submit_video = st.form_submit_button("添加视频链接")
        
        if submit_video and video_url:
            if not video_name:
                video_name = os.path.basename(video_url.split("?")[0])
                if not video_name or "." not in video_name:
                    video_name = f"video_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
            elif "." not in video_name:
                video_name = f"{video_name}.mp4"
                
            video_links[video_name] = video_url
            with open(video_links_path, 'w', encoding='utf-8') as f:
                json.dump(video_links, f, ensure_ascii=False, indent=2)
                
            st.success(f"视频链接 '{video_name}' 添加成功")
            st.experimental_rerun()
    
    st.stop()

# 创建选项卡
tab1, tab2, tab3, tab4, tab5 = st.tabs(["视频预览", "关键帧分析", "自动编码", "高级分析", "编码结果"])

# 视频预览选项卡
with tab1:
    st.header("视频预览")
    
    # 视频选择器
    selected_video = st.selectbox("选择视频", all_videos, key="preview_video_select")
    
    # 处理视频路径
    if selected_video.startswith("[链接] "):
        # 视频链接
        video_name = selected_video[6:]  # 去掉 "[链接] " 前缀
        video_url = video_links.get(video_name, "")
        
        if video_url:
            st.write(f"视频链接: {video_url}")
            
            # 尝试嵌入视频
            try:
                st.video(video_url)
            except:
                st.warning("无法嵌入视频，请直接访问链接查看")
                st.markdown(f"[在新窗口打开视频]({video_url})")
            
            # 硅基流动不支持直接分析视频链接的提示
            if siliconflow_client:
                st.info("硅基流动目前不支持直接分析视频链接，请下载视频后上传以获取更好的分析效果")
            
            video_path = None
        else:
            st.error(f"找不到视频链接: {video_name}")
            video_path = None
    else:
        # 本地视频文件
        video_path = os.path.join(files_dir, selected_video)
        
        # 显示视频信息
        video_info = get_video_info(video_path)
        
        if video_info:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"视频时长: {round(video_info['duration'], 2)} 秒")
            
            with col2:
                st.write(f"帧率: {video_info['fps']} FPS")
            
            with col3:
                st.write(f"分辨率: {video_info['size'][0]} x {video_info['size'][1]}")
        
        # 视频播放器
        video_file = open(video_path, 'rb')
        video_bytes = video_file.read()
        st.video(video_bytes)

# 关键帧分析选项卡
with tab2:
    st.header("视觉分析")
    
    if not siliconflow_client:
        st.warning("请先在侧边栏设置硅基流动API密钥")
    else:
        # 视频选择器
        selected_video = st.selectbox("选择视频", video_files, key="frames_video_select")
        if not selected_video:
            st.warning("请先上传视频文件")
            st.stop()
            
        video_path = os.path.join(files_dir, selected_video)
        
        # 参数设置
        frame_interval = st.slider("帧提取间隔(秒)", 1, 60, 30)
        
        # 视觉模型选择
        vision_models = {
            "通义千问2-VL-72B": "Qwen/Qwen2-VL-72B-Instruct",
            "通义千问-VL": "Qwen/Qwen-VL-Chat",
            "DeepSeek-VL2": "deepseek-ai/deepseek-vl2",
            "InternVL2": "OpenGVLab/InternVL2-8B",
            "InternVL2-26B": "OpenGVLab/InternVL2-26B",
            "Qwen-QVQ-72B": "Qwen/QVQ-72B-Preview"
        }
        
        vision_model = st.selectbox(
            "视觉语言模型", 
            list(vision_models.keys()),
            index=0,
            help="用于分析视频帧的视觉语言模型"
        )
        vision_model_id = vision_models[vision_model]
    
        # 提取并分析帧
        if st.button("提取并分析关键帧"):
            with st.spinner("正在提取视频帧..."):
                frames_with_timestamps = extract_video_frames(video_path, frame_interval)
                
                if not frames_with_timestamps:
                    st.error("无法提取视频帧")
                else:
                    st.success(f"成功提取 {len(frames_with_timestamps)} 个关键帧")
                    
                    # 显示帧
                    st.subheader("关键帧")
                    cols = st.columns(3)
                    frame_data = []
                    
                    for i, (frame, timestamp) in enumerate(frames_with_timestamps):
                        # 格式化时间戳
                        seconds = int(timestamp)
                        minutes = seconds // 60
                        remaining_seconds = seconds % 60
                        time_str = f"{minutes:02d}:{remaining_seconds:02d}"
                        
                        # 保存帧信息
                        frame_data.append({
                            "index": i,
                            "timestamp": timestamp,
                            "time_str": time_str,
                            "frame": frame
                        })
                        
                        # 显示在列中
                        with cols[i % 3]:
                            # 转换BGR到RGB
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            st.image(frame_rgb, caption=f"帧 {i+1} - 时间: {time_str}")
                    
                    # 分析帧内容
                    st.subheader("帧内容分析")
                    
                    analyze_frames = st.checkbox("分析帧内容", value=True)
                    
                    if analyze_frames:
                        frame_prompt = st.text_area(
                            "分析提示词", 
                            value="请详细描述这个视频帧中的内容，包括场景、人物、动作和可能的主题。",
                            help="用于指导模型分析视频帧内容的提示词"
                        )
                        
                        if st.button("开始分析"):
                            with st.spinner("正在分析帧内容..."):
                                for i, frame_info in enumerate(frame_data):
                                    st.subheader(f"帧 {i+1} - 时间: {frame_info['time_str']}")
                                    col1, col2 = st.columns([1, 2])
                                    
                                    with col1:
                                        frame_rgb = cv2.cvtColor(frame_info["frame"], cv2.COLOR_BGR2RGB)
                                        st.image(frame_rgb)
                                    
                                    with col2:
                                        # 转换帧为base64
                                        base64_image = convert_image_to_base64(frame_info["frame"])
                                        
                                        # 分析帧
                                        with st.spinner(f"分析帧 {i+1}..."):
                                            try:
                                                # 使用视觉语言模型分析
                                                response = siliconflow_client.chat.completions.create(
                                                    model=vision_model_id,
                                                    messages=[
                                                        {
                                                            "role": "user", 
                                                            "content": [
                                                                {
                                                                    "type": "image_url",
                                                                    "image_url": {
                                                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                                                        "detail": "high"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "text",
                                                                    "text": frame_prompt
                                                                }
                                                            ]
                                                        }
                                                    ],
                                                    max_tokens=500
                                                )
                                                
                                                if hasattr(response, 'choices') and len(response.choices) > 0 and hasattr(response.choices[0], 'message'):
                                                    description = response.choices[0].message.content
                                                    st.write(description)
                                                else:
                                                    st.warning("无法获取分析结果")
                                            except Exception as e:
                                                error_msg = str(e)
                                                st.error(f"分析失败: {error_msg}")
                                                logging.error(f"帧分析失败: {error_msg}")

# 自动编码选项卡
with tab3:
    st.header("视频自动编码")
    
    # 检查是否有变量
    if not variables:
        st.error("请先在编码管理页面添加变量")
        st.stop()
    
    # 视频选择器
    selected_video = st.selectbox("选择视频", video_files, key="coding_video_select")
    video_path = os.path.join(files_dir, selected_video)
    
    # 显示视频信息
    video_info = get_video_info(video_path)
    if video_info:
        st.write(f"视频时长: {round(video_info['duration'], 2)} 秒")
    
    # 参数设置
    col1, col2 = st.columns(2)
    
    with col1:
        frame_interval = st.slider("帧提取间隔(秒)", 1, 60, 10, key="coding_interval")
    
    with col2:
        # 添加模型选择
        vision_models = {
            "通义千问2-VL-72B": "Qwen/Qwen2-VL-72B-Instruct",
            "通义千问-VL": "Qwen/Qwen-VL-Chat",
            "DeepSeek-VL2": "deepseek-ai/deepseek-vl2",
            "InternVL2": "OpenGVLab/InternVL2-8B",
            "InternVL2-26B": "OpenGVLab/InternVL2-26B",
            "Qwen-QVQ-72B": "Qwen/QVQ-72B-Preview"
        }
        
        text_models = {
            "DeepSeek-V2.5": "deepseek-ai/DeepSeek-V2.5",
            "DeepSeek-Coder": "deepseek-ai/deepseek-coder-v2",
            "通义千问2-7B": "Qwen/Qwen2-7B-Instruct"
        }
        
        vision_model = st.selectbox(
            "视觉语言模型", 
            list(vision_models.keys()),
            index=0,
            help="用于分析视频帧的视觉语言模型",
            key="coding_vision_model"
        )
        vision_model_id = vision_models[vision_model]
        
        text_model = st.selectbox(
            "文本模型", 
            list(text_models.keys()),
            index=0,
            help="用于整体分析的文本模型",
            key="coding_text_model"
        )
        text_model_id = text_models[text_model]
    
    # 显示变量
    st.subheader("待编码变量")
    
    with st.expander("查看变量列表", expanded=True):
        variables_df = pd.DataFrame([
            {
                "变量ID": var.get('id', ''),
                "变量名称": var.get('name', ''),
                "描述": var.get('description', ''),
                "类型": var.get('type', 'text')
            }
            for var in variables
        ])
        
        st.table(variables_df)
    
    # 自动编码部分
    with st.expander("自动编码", expanded=False):
        st.write("使用AI自动为视频内容编码")
        
        # 加载变量
        variables = load_variables()
        if not variables:
            st.warning("请先在编码管理页面创建变量")
        else:
            # 显示变量列表
            st.subheader("选择要编码的变量")
            
            # 使用多选框选择变量
            variable_options = {var['name']: var for var in variables}
            selected_var_names = st.multiselect(
                "选择变量",
                options=list(variable_options.keys()),
                default=list(variable_options.keys())[:min(5, len(variable_options))]
            )
            
            selected_variables = [variable_options[name] for name in selected_var_names]
            
            # 自定义提示词
            st.subheader("自定义提示词（可选）")
            
            # 初始化自定义提示词
            if "custom_video_prompt" not in st.session_state:
                st.session_state.custom_video_prompt = """请根据以下视频描述，为指定的变量进行编码。

视频描述:
{content}

需要编码的变量:
{variables}

请以JSON格式返回编码结果，格式为：
{
    "变量名1": "编码值1",
    "变量名2": "编码值2",
    ...
}

对于分类变量，请只返回选项中的一个值。
对于李克特量表，请返回对应的数值或标签。
请确保编码结果符合变量的要求和视频内容。"""
            
            custom_prompt = st.text_area(
                "自定义提示词",
                value=st.session_state.custom_video_prompt,
                height=300,
                help="使用 {content} 表示视频内容，{variables} 表示变量信息"
            )
            
            # 保存自定义提示词
            if st.button("保存提示词"):
                st.session_state.custom_video_prompt = custom_prompt
                st.success("提示词已保存！")
            
            # 使用自定义提示词
            use_custom_prompt = st.checkbox("使用自定义提示词", value=True)
            
            # 开始自动编码按钮
            if st.button("开始自动编码", key="auto_code_btn"):
                if not selected_variables:
                    st.error("请至少选择一个变量")
                elif not video_path:
                    st.error("请先上传或选择视频")
                else:
                    # 创建进度条
                    st.session_state.analysis_progress = st.progress(0, text="准备分析...")
                    
                    try:
                        # 提取视频帧
                        frames_with_timestamps = extract_video_frames(video_path, frame_interval=30)
                        
                        if not frames_with_timestamps:
                            st.error("无法提取视频帧，请检查视频文件")
                        else:
                            # 自动编码
                            final_prompt = custom_prompt if use_custom_prompt else None
                            coding_results = auto_code_video(
                                video_path, 
                                frames_with_timestamps=frames_with_timestamps,
                                variables=selected_variables,
                                custom_prompt=final_prompt
                            )
                            
                            if coding_results:
                                st.success("自动编码完成！")
                                
                                # 显示编码结果
                                st.subheader("编码结果")
                                
                                # 创建结果表格
                                result_data = []
                                for var_name, value in coding_results.items():
                                    var_info = next((v for v in variables if v['name'] == var_name), None)
                                    if var_info:
                                        var_type = var_info.get('type', '')
                                        result_data.append({
                                            "变量名": var_name,
                                            "变量类型": var_type,
                                            "编码值": value
                                        })
                                
                                if result_data:
                                    st.table(result_data)
                                    
                                    # 保存编码结果
                                    if st.button("保存编码结果"):
                                        # 获取视频文件名（不含扩展名）
                                        video_filename = os.path.splitext(os.path.basename(video_path))[0]
                                        
                                        # 加载现有编码结果
                                        coding_results_file = os.path.join(project_dir, "coding_results.json")
                                        existing_results = {}
                                        if os.path.exists(coding_results_file):
                                            try:
                                                with open(coding_results_file, "r", encoding="utf-8") as f:
                                                    existing_results = json.load(f)
                                            except Exception as e:
                                                st.error(f"加载现有编码结果失败: {str(e)}")
                                        
                                        # 更新编码结果
                                        if video_filename not in existing_results:
                                            existing_results[video_filename] = {}
                                        
                                        # 更新变量值
                                        for var_name, value in coding_results.items():
                                            existing_results[video_filename][var_name] = value
                                        
                                        # 保存更新后的结果
                                        try:
                                            with open(coding_results_file, "w", encoding="utf-8") as f:
                                                json.dump(existing_results, f, ensure_ascii=False, indent=2)
                                            st.success(f"编码结果已保存到 {video_filename}")
                                        except Exception as e:
                                            st.error(f"保存编码结果失败: {str(e)}")
                            else:
                                st.error("自动编码失败，请查看日志了解详情")
                    
                    except Exception as e:
                        st.error(f"自动编码过程中发生错误: {str(e)}")
                    finally:
                        # 清除进度条
                        if 'analysis_progress' in st.session_state:
                            del st.session_state.analysis_progress

# 高级分析选项卡
with tab4:
    st.header("视频高级分析")
    
    # 视频选择器
    selected_video = st.selectbox("选择视频", video_files, key="advanced_video_select")
    video_path = os.path.join(files_dir, selected_video)
    
    # 分析参数设置
    col1, col2 = st.columns(2)
    
    with col1:
        frame_interval = st.slider("帧提取间隔(秒)", 1, 60, 30, key="advanced_interval")
    
    with col2:
        # 添加模型选择
        vision_models = {
            "通义千问2-VL-72B": "Qwen/Qwen2-VL-72B-Instruct",
            "通义千问-VL": "Qwen/Qwen-VL-Chat",
            "DeepSeek-VL2": "deepseek-ai/deepseek-vl2",
            "InternVL2": "OpenGVLab/InternVL2-8B",
            "InternVL2-26B": "OpenGVLab/InternVL2-26B",
            "Qwen-QVQ-72B": "Qwen/QVQ-72B-Preview"
        }
        
        text_models = {
            "DeepSeek-V2.5": "deepseek-ai/DeepSeek-V2.5",
            "DeepSeek-Coder": "deepseek-ai/deepseek-coder-v2",
            "通义千问2-7B": "Qwen/Qwen2-7B-Instruct"
        }
        
        vision_model = st.selectbox(
            "视觉语言模型", 
            list(vision_models.keys()),
            index=0,
            help="用于分析视频帧的视觉语言模型",
            key="advanced_vision_model"
        )
        vision_model_id = vision_models[vision_model]
        
        text_model = st.selectbox(
            "文本模型", 
            list(text_models.keys()),
            index=0,
            help="用于整体分析的文本模型",
            key="advanced_text_model"
        )
        text_model_id = text_models[text_model]
    
    # 分析提示词设置
    analysis_prompt = st.text_area(
        "分析提示词", 
        value="请分析这个视频的主要内容、主题、情感基调和可能的受众。分析应包括视频的叙事结构、视觉元素和关键信息点。",
        height=100,
        help="用于指导模型分析视频整体内容的提示词"
    )
    
    # 开始分析
    if st.button("开始高级分析"):
        if not siliconflow_client:
            st.error("高级分析需要硅基流动API支持")
            st.stop()
        
        with st.spinner("正在进行高级分析..."):
            try:
                analysis_result = analyze_video_with_siliconflow(
                    video_path, 
                    frame_interval=frame_interval,
                    prompt=analysis_prompt,
                    vision_model=vision_model_id,
                    text_model=text_model_id
                )
                
                if analysis_result:
                    # 成功分析
                    st.success("视频分析完成")
                    
                    # 显示分析结果
                    st.subheader("视频整体分析")
                    st.markdown(analysis_result)
                    
                    # 保存分析结果
                    video_basename = os.path.basename(video_path)
                    
                    if video_basename not in video_analysis:
                        video_analysis[video_basename] = {}
                    
                    video_analysis[video_basename] = analysis_result
                    
                    # 写入分析结果到文件
                    with open(video_analysis_path, 'w', encoding='utf-8') as f:
                        json.dump(video_analysis, f, ensure_ascii=False, indent=2)
                    
                    st.success("分析结果已保存")
                else:
                    st.error("分析失败")
            except Exception as e:
                st.error(f"分析过程中发生错误: {str(e)}")
                logging.error(f"视频高级分析错误: {str(e)}")

# 编码结果选项卡
with tab5:
    st.header("编码结果呈现与导出")
    
    # 加载编码结果
    if os.path.exists(coding_results_path):
        with open(coding_results_path, 'r', encoding='utf-8') as f:
            all_coding_results = json.load(f)
    else:
        all_coding_results = {}
    
    # 加载变量信息
    variables = load_variables()
    variables_dict = {var['name']: var for var in variables}
    
    if not all_coding_results:
        st.warning("暂无编码结果，请先进行视频编码")
    else:
        # 创建子选项卡
        results_tab1, results_tab2, results_tab3 = st.tabs(["结果概览", "详细分析", "导出结果"])
        
        # 结果概览选项卡
        with results_tab1:
            st.subheader("编码结果概览")
            
            # 显示已编码视频数量
            st.info(f"已编码视频数量: {len(all_coding_results)}")
            
            # 创建编码结果数据框
            results_data = []
            
            for video_name, var_results in all_coding_results.items():
                row = {"视频名称": video_name}
                
                for var_name, value in var_results.items():
                    if var_name in variables_dict:
                        var_type = variables_dict[var_name].get('type', '')
                        row[f"{var_name} ({var_type})"] = value
                
                results_data.append(row)
            
            if results_data:
                results_df = pd.DataFrame(results_data)
                st.dataframe(results_df, use_container_width=True)
                
                # 显示变量编码完成率
                st.subheader("变量编码完成率")
                
                completion_data = []
                for var in variables:
                    var_name = var['name']
                    coded_count = sum(1 for results in all_coding_results.values() if var_name in results)
                    completion_data.append({
                        "变量名": var_name,
                        "已编码视频数": coded_count,
                        "编码完成率": round(coded_count / len(all_coding_results) * 100, 2)
                    })
                
                completion_df = pd.DataFrame(completion_data)
                st.dataframe(completion_df, use_container_width=True)
                
                # 绘制编码完成率图表
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.barplot(x="变量名", y="编码完成率", data=completion_df, ax=ax)
                ax.set_title("变量编码完成率")
                ax.set_xlabel("变量")
                ax.set_ylabel("完成率 (%)")
                ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
                plt.tight_layout()
                st.pyplot(fig)
        
        # 详细分析选项卡
        with results_tab2:
            st.subheader("编码结果详细分析")
            
            # 选择要分析的变量
            analysis_var = st.selectbox(
                "选择要分析的变量", 
                [var['name'] for var in variables],
                key="analysis_var_select"
            )
            
            if analysis_var:
                selected_var = variables_dict.get(analysis_var)
                
                if selected_var:
                    var_type = selected_var.get('type', '')
                    st.write(f"变量类型: {var_type}")
                    
                    # 收集该变量的所有值
                    var_values = []
                    for video_name, var_results in all_coding_results.items():
                        if analysis_var in var_results:
                            var_values.append(var_results[analysis_var])
                    
                    if var_values:
                        # 根据变量类型进行不同的分析
                        if var_type == "分类变量":
                            # 计算每个类别的频率
                            value_counts = pd.Series(var_values).value_counts()
                            
                            # 显示频率表
                            st.write("类别频率分布:")
                            freq_df = pd.DataFrame({
                                "类别": value_counts.index,
                                "频次": value_counts.values,
                                "百分比": [f"{round(x/len(var_values)*100, 2)}%" for x in value_counts.values]
                            })
                            st.dataframe(freq_df, use_container_width=True)
                            
                            # 绘制饼图
                            fig, ax = plt.subplots(figsize=(10, 6))
                            ax.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%')
                            ax.set_title(f"{analysis_var} 类别分布")
                            st.pyplot(fig)
                            
                        elif var_type == "李克特量表":
                            # 尝试将值转换为数值
                            try:
                                numeric_values = [float(v) if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace('.', '', 1).isdigit()) else np.nan for v in var_values]
                                numeric_values = [v for v in numeric_values if not np.isnan(v)]
                                
                                if numeric_values:
                                    # 计算基本统计量
                                    mean_val = np.mean(numeric_values)
                                    median_val = np.median(numeric_values)
                                    std_val = np.std(numeric_values)
                                    
                                    st.write(f"平均值: {mean_val:.2f}")
                                    st.write(f"中位数: {median_val:.2f}")
                                    st.write(f"标准差: {std_val:.2f}")
                                    
                                    # 绘制直方图
                                    fig, ax = plt.subplots(figsize=(10, 6))
                                    sns.histplot(numeric_values, kde=True, ax=ax)
                                    ax.set_title(f"{analysis_var} 分布")
                                    ax.set_xlabel("值")
                                    ax.set_ylabel("频次")
                                    st.pyplot(fig)
                                else:
                                    st.warning("无法将李克特量表值转换为数值进行分析")
                            except Exception as e:
                                st.error(f"分析李克特量表数据时出错: {str(e)}")
                        
                        else:  # 文本变量
                            # 显示所有文本值
                            st.write("文本值列表:")
                            text_df = pd.DataFrame({
                                "视频": all_coding_results.keys(),
                                f"{analysis_var}": [results.get(analysis_var, "") for results in all_coding_results.values()]
                            })
                            st.dataframe(text_df, use_container_width=True)
                    else:
                        st.warning(f"没有找到变量 '{analysis_var}' 的编码值")
                else:
                    st.error(f"找不到变量 '{analysis_var}' 的信息")
            
            # 添加AI分析报告生成功能
            st.subheader("AI分析报告")
            
            if st.button("生成AI分析报告", key="generate_ai_report"):
                # 检查是否有硅基流动API客户端
                client = get_siliconflow_client()
                if not client:
                    st.error("生成AI分析报告需要硅基流动API支持，请在设置中配置API密钥")
                else:
                    with st.spinner("正在生成分析报告..."):
                        try:
                            # 准备数据
                            report_data = {
                                "编码结果": all_coding_results,
                                "变量信息": {var['name']: var for var in variables}
                            }
                            
                            # 构建提示词
                            prompt = f"""
请根据以下视频编码结果数据，生成一份详细的分析报告。

编码数据:
{json.dumps(report_data, ensure_ascii=False, indent=2)}

请在报告中包含以下内容:
1. 总体概述：已编码视频数量、变量数量等基本信息
2. 各变量的分布情况分析
3. 变量之间可能存在的关联性
4. 主要发现和洞察
5. 建议和下一步分析方向

请以结构化的方式呈现报告，使用标题、小标题和要点列表等格式。
"""
                            
                            # 调用API生成报告
                            response = client.chat.completions.create(
                                model="deepseek-ai/DeepSeek-V2.5",
                                messages=[
                                    {"role": "system", "content": "你是一位专业的内容分析专家，擅长分析编码数据并生成见解深刻的报告。"},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0.7,
                                max_tokens=2000
                            )
                            
                            # 获取报告内容
                            if hasattr(response, 'choices') and len(response.choices) > 0:
                                if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'content'):
                                    report_content = response.choices[0].message.content
                                    
                                    # 显示报告
                                    st.subheader("AI生成的分析报告")
                                    st.markdown(report_content)
                                    
                                    # 保存报告
                                    report_path = os.path.join(project_dir, "video_coding_report.md")
                                    with open(report_path, 'w', encoding='utf-8') as f:
                                        f.write(report_content)
                                    
                                    st.success(f"分析报告已保存到 {report_path}")
                                else:
                                    st.error("无法获取API响应内容")
                            else:
                                st.error("API响应格式不正确")
                        except Exception as e:
                            st.error(f"生成分析报告时出错: {str(e)}")
                            logging.error(f"生成分析报告错误: {str(e)}")
        
        # 导出结果选项卡
        with results_tab3:
            st.subheader("导出编码结果")
            
            # 创建导出选项
            export_format = st.radio(
                "选择导出格式",
                ["CSV", "Excel", "JSON"],
                horizontal=True
            )
            
            # 选择要导出的变量
            export_vars = st.multiselect(
                "选择要导出的变量",
                [var['name'] for var in variables],
                default=[var['name'] for var in variables]
            )
            
            # 导出按钮
            if st.button("导出编码结果", key="export_results_btn"):
                if not export_vars:
                    st.error("请至少选择一个变量进行导出")
                else:
                    # 准备导出数据
                    export_data = []
                    
                    for video_name, var_results in all_coding_results.items():
                        row = {"视频名称": video_name}
                        
                        for var_name in export_vars:
                            if var_name in var_results:
                                row[var_name] = var_results[var_name]
                            else:
                                row[var_name] = ""
                        
                        export_data.append(row)
                    
                    if export_data:
                        # 创建DataFrame
                        export_df = pd.DataFrame(export_data)
                        
                        # 根据选择的格式导出
                        if export_format == "CSV":
                            # 处理李克特量表数据，将其转换为数值
                            for var_name in export_vars:
                                if var_name in variables_dict and variables_dict[var_name].get('type') == "李克特量表":
                                    export_df[var_name] = export_df[var_name].apply(convert_likert_to_numeric)
                                    
                            # 确保所有李克特量表列为数值类型
                            export_df = ensure_likert_columns_numeric(export_df, variables_dict)
                                    
                            # 使用utf-8-sig编码解决中文乱码问题
                            csv = export_df.to_csv(index=False, encoding='utf-8-sig')
                            b64 = base64.b64encode(csv.encode('utf-8-sig')).decode()
                            href = f'<a href="data:file/csv;base64,{b64}" download="video_coding_results.csv">下载CSV文件</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        
                        elif export_format == "Excel":
                            # 处理李克特量表数据，将其转换为数值
                            for var_name in export_vars:
                                if var_name in variables_dict and variables_dict[var_name].get('type') == "李克特量表":
                                    export_df[var_name] = export_df[var_name].apply(convert_likert_to_numeric)
                                    
                            # 确保所有李克特量表列为数值类型
                            export_df = ensure_likert_columns_numeric(export_df, variables_dict)
                                    
                            try:
                                output = BytesIO()
                                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                    export_df.to_excel(writer, index=False, sheet_name='编码结果')
                                
                                b64 = base64.b64encode(output.getvalue()).decode()
                                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="video_coding_results.xlsx">下载Excel文件</a>'
                                st.markdown(href, unsafe_allow_html=True)
                            except ImportError:
                                st.error("导出Excel需要安装xlsxwriter模块。请运行 `pip install xlsxwriter` 安装该模块。")
                                # 提供CSV作为备选
                                st.info("您可以选择CSV格式作为替代。")
                        
                        elif export_format == "JSON":
                            # 创建JSON格式的数据
                            json_data = {}
                            for video_name, var_results in all_coding_results.items():
                                json_data[video_name] = {}
                                for var_name in export_vars:
                                    if var_name in var_results:
                                        # 处理李克特量表数据，将其转换为数值
                                        if var_name in variables_dict and variables_dict[var_name].get('type') == "李克特量表":
                                            value = var_results[var_name]
                                            converted_value = convert_likert_to_numeric(value)
                                            if not pd.isna(converted_value) and isinstance(converted_value, (int, float)):
                                                json_data[video_name][var_name] = converted_value
                                            else:
                                                json_data[video_name][var_name] = value
                                        else:
                                            json_data[video_name][var_name] = var_results[var_name]
                                    else:
                                        json_data[video_name][var_name] = ""
                            
                            json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
                            b64 = base64.b64encode(json_str.encode('utf-8')).decode()
                            href = f'<a href="data:file/json;base64,{b64}" download="video_coding_results.json">下载JSON文件</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        else:
                            st.warning("没有可导出的数据")

# 页脚
st.markdown("---")
st.markdown("内容分析工具 © 2023")