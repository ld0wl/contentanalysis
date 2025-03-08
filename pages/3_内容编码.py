import streamlit as st
import os
import json
import pandas as pd
import requests
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
from io import BytesIO
from utils import get_current_project_path, get_file_content, get_ai_suggestion, auto_code_content, load_variables, get_video_info, sanitize_file_path
import re
import base64

# 设置页面配置
st.set_page_config(
    page_title="内容编码",
    page_icon="✏️",
    layout="wide"
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

# 检查是否有活动项目
if 'current_project' not in st.session_state or not st.session_state.current_project:
    st.warning("请先在首页选择或创建一个项目")
    st.stop()

# 检查API密钥
if 'siliconflow_api_key' not in st.session_state or not st.session_state.siliconflow_api_key:
    st.warning("请在首页设置硅基流动API密钥以启用AI辅助功能")

# 页面标题
st.title("内容编码")
st.write(f"当前项目: {st.session_state.current_project}")

# 获取项目路径
project_path = get_current_project_path()
config_path = os.path.join(project_path, "config.json")
files_dir = os.path.join(project_path, "files")
coding_results_path = os.path.join(project_path, "coding_results.json")
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

# 检查是否有变量
if not variables:
    st.error("请先在编码管理页面添加变量")
    st.stop()

# 加载编码结果
coding_results = {}
if os.path.exists(coding_results_path):
    with open(coding_results_path, 'r', encoding='utf-8') as f:
        coding_results = json.load(f)

# 获取文件列表
files = []
if os.path.exists(files_dir):
    files = [f for f in os.listdir(files_dir) if os.path.isfile(os.path.join(files_dir, f))]

# 加载视频链接
video_links = {}
if os.path.exists(video_links_path):
    with open(video_links_path, 'r', encoding='utf-8') as f:
        video_links = json.load(f)

# 合并文件列表和视频链接
all_files = files + list(video_links.keys())

# 检查URL参数中是否有文件名
params = st.query_params
url_file = params.get("file", None)

# 创建选项卡
tab1, tab2, tab3 = st.tabs(["单个编码", "批量编码", "编码结果"])

# 单个编码选项卡
with tab1:
    # 检查是否有可编码的文件
    if not all_files:
        st.warning("没有可编码的文件。请先在内容管理页面上传文件或添加视频链接。")
        st.info("您可以点击左侧导航栏中的\"内容管理\"来添加文件。")
    else:
        # 确定默认选择的文件
        try:
            if url_file and url_file in all_files:
                default_index = all_files.index(url_file)
            else:
                # 查找未编码的文件
                uncoded_files = [f for f in all_files if f not in coding_results]
                if uncoded_files:
                    default_index = all_files.index(uncoded_files[0])
                else:
                    default_index = 0
            
            # 创建文件选择器
            selected_file = st.selectbox(
                "选择文件",
                all_files,
                index=default_index
            )
            
            # 如果选择了不同的文件，更新URL参数
            if url_file != selected_file:
                st.query_params["file"] = selected_file
        except Exception as e:
            st.error(f"加载文件列表时出错: {str(e)}")
            st.info("请尝试刷新页面或重新选择项目。")
            selected_file = None
        
        # 只有在成功选择文件时继续显示内容
        if selected_file:
            # 创建两列布局
            col1, col2 = st.columns([3, 2])
            
            # 内容显示区域
            with col1:
                st.subheader("文件内容")
                
                # 显示文件内容
                if selected_file in video_links:
                    # 视频链接
                    video_url = video_links[selected_file]
                    st.write(f"视频链接: {selected_file}")
                    
                    # 检查视频链接类型
                    if "bilibili.com" in video_url.lower():
                        # 哔哩哔哩视频
                        # 提取视频ID
                        bvid = ""
                        if "BV" in video_url:
                            bvid_match = re.search(r'BV\w+', video_url)
                            if bvid_match:
                                bvid = bvid_match.group(0)
                        
                        if bvid:
                            # 使用iframe嵌入B站播放器
                            bili_embed = f"""
                            <iframe src="//player.bilibili.com/player.html?bvid={bvid}&page=1" 
                                    width="100%" height="500" scrolling="no" border="0" 
                                    frameborder="no" framespacing="0" allowfullscreen="true"> 
                            </iframe>
                            """
                            st.markdown(bili_embed, unsafe_allow_html=True)
                        else:
                            # 如果无法提取视频ID，提供链接
                            st.warning("无法嵌入哔哩哔哩视频，请直接访问链接查看")
                            st.markdown(f"[在新窗口打开视频]({video_url})")
                    
                    elif "douyin.com" in video_url.lower() or "tiktok.com" in video_url.lower():
                        # 抖音/TikTok视频
                        st.warning("抖音/TikTok视频无法直接嵌入，请使用内置浏览器查看")
                        
                        # 使用iframe嵌入网页
                        iframe_html = f"""
                        <iframe src="{video_url}" width="100%" height="600" 
                                style="border:none;overflow:hidden" scrolling="yes" 
                                frameborder="0" allowTransparency="true" allowFullScreen="true">
                        </iframe>
                        """
                        st.markdown(iframe_html, unsafe_allow_html=True)
                        st.markdown(f"[在新窗口打开视频]({video_url})")
                    
                    else:
                        # 其他视频链接，尝试使用st.video
                        try:
                            st.video(video_url)
                        except Exception as e:
                            # 如果st.video失败，使用iframe嵌入
                            st.warning(f"无法使用Streamlit视频播放器: {str(e)}")
                            st.warning("尝试使用内置浏览器播放")
                            iframe_html = f"""
                            <iframe src="{video_url}" width="100%" height="500" 
                                    style="border:none;overflow:hidden" scrolling="no" 
                                    frameborder="0" allowTransparency="true" allowFullScreen="true">
                            </iframe>
                            """
                            st.markdown(iframe_html, unsafe_allow_html=True)
                            st.markdown(f"[在新窗口打开视频]({video_url})")
                else:
                    # 本地文件
                    file_path = os.path.join(files_dir, selected_file)
                    
                    # 检查是否是视频文件
                    _, file_ext = os.path.splitext(selected_file)
                    if file_ext.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                        try:
                            # 获取视频信息
                            try:
                                # 路径处理
                                file_path = sanitize_file_path(file_path)
                                video_info = get_video_info(file_path)
                                
                                if video_info:
                                    st.write(f"视频时长: {round(video_info['duration'], 2)} 秒")
                                    st.write(f"帧率: {video_info['fps']} FPS")
                                    st.write(f"分辨率: {video_info['size'][0]} x {video_info['size'][1]}")
                            except Exception as e:
                                st.warning(f"无法获取视频信息: {str(e)}")
                            
                            # 尝试使用多种方式打开视频
                            st.subheader("视频播放")
                            
                            # 方法1: 使用st.video尝试打开
                            try:
                                # 确保文件路径有效
                                video_file = open(file_path, 'rb')
                                video_bytes = video_file.read()
                                video_file.close()
                                st.video(video_bytes)
                            except Exception as e:
                                st.warning(f"使用Streamlit视频播放器失败: {str(e)}")
                                
                                # 方法2: 使用HTML5视频标签
                                try:
                                    # 获取文件的相对路径
                                    rel_path = os.path.join('projects', st.session_state.current_project, 'files', selected_file)
                                    rel_path = rel_path.replace('\\', '/')  # 确保使用正斜杠
                                    
                                    # 使用HTML5视频标签
                                    st.warning("尝试使用HTML5视频播放器")
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
                                    st.write(f"视频路径: {file_path}")
                        except Exception as e:
                            st.error(f"视频处理失败: {str(e)}")
                            st.write(f"视频路径: {file_path}")
                            st.write("请使用外部视频播放器查看此文件")
                    else:
                        # 非视频文件，显示文本内容
                        try:
                            content = get_file_content(file_path)
                            st.text_area("文件内容", value=content, height=500, disabled=True)
                        except Exception as e:
                            st.error(f"无法读取文件内容: {str(e)}")
            
            # AI辅助功能
            with st.expander("AI辅助功能"):
                ai_tabs = st.tabs(["编码建议", "自动编码", "自定义提示词"])
                
                # 编码建议选项卡
                with ai_tabs[0]:
                    # 编码建议
                    if st.button("获取编码建议", key="get_suggestion"):
                        if not st.session_state.siliconflow_api_key:
                            st.error("请先在首页设置硅基流动API密钥")
                        else:
                            with st.spinner("正在生成编码建议..."):
                                # 创建提示词
                                prompt = "请分析以下内容，并给出编码建议。考虑以下变量：\n\n"
                                
                                for var in variables:
                                    prompt += f"变量：{var['name']} ({var['type']})\n"
                                    if var['type'] == "分类变量" and var['options']:
                                        options = [opt.strip() for opt in var['options'].split(',') if opt.strip()]
                                        prompt += f"可选值：{', '.join(options)}\n"
                                    elif var['type'] == "李克特量表":
                                        likert_scale = var.get('likert_scale', 5)
                                        likert_labels = var.get('likert_labels', '')
                                        if likert_labels:
                                            labels = [label.strip() for label in likert_labels.split(',')]
                                            prompt += f"量表：{', '.join(labels)}\n"
                                        else:
                                            prompt += f"量表：1-{likert_scale}\n"
                                    
                                    if var['name'] in coding_guide and coding_guide[var['name']]:
                                        prompt += f"编码指南：{coding_guide[var['name']]}\n"
                                    prompt += "\n"
                                
                                # 获取AI建议
                                suggestion = get_ai_suggestion(content, prompt)
                                st.text_area("编码建议", suggestion, height=200)
                
                # 自动编码选项卡
                with ai_tabs[1]:
                    # 一键编码
                    if st.button("一键编码", key="auto_code"):
                        if not st.session_state.siliconflow_api_key:
                            st.error("请先在首页设置硅基流动API密钥")
                        else:
                            with st.spinner("正在进行自动编码..."):
                                # 准备变量信息
                                variables_info = []
                                for var in variables:
                                    var_info = {
                                        "name": var['name'],
                                        "type": var['type'],
                                        "options": var.get('options', ''),
                                        "description": var.get('description', '')
                                    }
                                    
                                    # 添加李克特量表信息
                                    if var['type'] == "李克特量表":
                                        var_info["likert_scale"] = var.get('likert_scale', 5)
                                        var_info["likert_labels"] = var.get('likert_labels', '')
                                    
                                    if var['name'] in coding_guide:
                                        var_info["guide"] = coding_guide[var['name']]
                                    
                                    variables_info.append(var_info)
                                
                                # 自动编码
                                auto_results = auto_code_content(content, variables_info)
                                
                                if auto_results:
                                    # 更新编码结果
                                    if selected_file not in coding_results:
                                        coding_results[selected_file] = {}
                                    
                                    # 直接覆盖现有编码结果
                                    coding_results[selected_file] = auto_results
                                    
                                    # 保存编码结果
                                    with open(coding_results_path, 'w', encoding='utf-8') as f:
                                        json.dump(coding_results, f, ensure_ascii=False, indent=2)
                                    
                                    st.success("自动编码完成")
                                    
                                    # 查找下一个未编码文件
                                    uncoded_files = [f for f in all_files if f not in coding_results]
                                    if uncoded_files:
                                        # 自动跳转到下一个未编码文件
                                        st.query_params["file"] = uncoded_files[0]
                                    
                                    st.rerun()
                                else:
                                    st.error("自动编码失败")
                
                # 自定义提示词选项卡
                with ai_tabs[2]:
                    st.write("您可以自定义提示词来获得更精确的编码结果。使用 {content} 表示内容，{variables} 表示变量信息。")
                    
                    # 初始化自定义提示词
                    if 'custom_prompt' not in st.session_state:
                        st.session_state.custom_prompt = """请根据以下内容，为指定的变量进行编码。

内容:
{content}

需要编码的变量:
{variables}

请以JSON格式返回编码结果，格式为：
{
    "变量名1": "编码值1",
    "变量名2": "编码值2",
    ...
}

重要说明：
1. 对于分类变量，你必须且只能从提供的选项中选择一个，不要创建新的选项。
2. 对于李克特量表，请返回1到5之间的数值。
3. 请严格按照每个变量的编码指南进行编码。
4. 请确保编码结果符合变量的要求和内容特点。
"""
                    
                    # 自定义提示词编辑器
                    custom_prompt = st.text_area(
                        "自定义提示词", 
                        value=st.session_state.custom_prompt, 
                        height=300
                    )
                    
                    # 保存自定义提示词
                    if st.button("保存提示词", key="save_prompt"):
                        st.session_state.custom_prompt = custom_prompt
                        st.success("提示词已保存")
                    
                    # 使用自定义提示词进行编码
                    if st.button("使用自定义提示词编码", key="custom_code"):
                        if not st.session_state.siliconflow_api_key:
                            st.error("请先在首页设置硅基流动API密钥")
                        else:
                            with st.spinner("正在使用自定义提示词进行编码..."):
                                # 准备变量信息
                                variables_info = []
                                for var in variables:
                                    var_info = {
                                        "name": var['name'],
                                        "type": var['type'],
                                        "options": var.get('options', ''),
                                        "description": var.get('description', '')
                                    }
                                    
                                    # 添加李克特量表信息
                                    if var['type'] == "李克特量表":
                                        var_info["likert_scale"] = var.get('likert_scale', 5)
                                        var_info["likert_labels"] = var.get('likert_labels', '')
                                    
                                    if var['name'] in coding_guide:
                                        var_info["guide"] = coding_guide[var['name']]
                                    
                                    variables_info.append(var_info)
                                
                                # 自动编码
                                auto_results = auto_code_content(content, variables_info, custom_prompt)
                                
                                if auto_results:
                                    # 更新编码结果
                                    if selected_file not in coding_results:
                                        coding_results[selected_file] = {}
                                    
                                    for var_name, value in auto_results.items():
                                        coding_results[selected_file][var_name] = value
                                    
                                    # 保存编码结果
                                    with open(coding_results_path, 'w', encoding='utf-8') as f:
                                        json.dump(coding_results, f, ensure_ascii=False, indent=2)
                                    
                                    st.success("使用自定义提示词编码完成")
                                    st.rerun()
                                else:
                                    st.error("使用自定义提示词编码失败")

# 编码表单
with col2:
    st.subheader("编码表单")
    
    # 初始化当前文件的编码结果
    current_coding = coding_results.get(selected_file, {})
    
    # 创建编码表单
    with st.form("coding_form", clear_on_submit=False):
        # 使用容器来创建列表样式
        coding_container = st.container()
        
        # 为每个变量创建输入字段
        for i, var in enumerate(variables):
            var_name = var['name']
            var_type = var['type']
            var_options = var['options']
            
            # 创建列表项样式
            with coding_container:
                st.markdown(f"### {i+1}. {var_name}")
                
                # 显示编码指南
                if var_name in coding_guide and coding_guide[var_name]:
                    with st.expander(f"查看 {var_name} 编码指南"):
                        st.write(coding_guide[var_name])
                
                # 根据变量类型创建不同的输入字段
                if var_type == "分类变量":
                    options = [opt.strip() for opt in var_options.split(',') if opt.strip()]
                    if options:
                        current_value = current_coding.get(var_name, options[0])
                        
                        # 使用单选按钮组
                        current_coding[var_name] = st.radio(
                            label=f"选择{var_name}的值",
                            options=options,
                            index=options.index(current_value) if current_value in options else 0,
                            horizontal=True
                        )
                    else:
                        current_coding[var_name] = st.text_input(f"{var_name}的值", value=current_coding.get(var_name, ""))
                elif var_type == "李克特量表":
                    # 获取李克特量表级别和标签
                    likert_scale = var.get('likert_scale', 5)
                    likert_labels = var.get('likert_labels', '')
                    
                    # 创建标签列表
                    if likert_labels:
                        labels = [label.strip() for label in likert_labels.split(',') if label.strip()]
                        # 如果标签数量不足，使用数字补充
                        if len(labels) < likert_scale:
                            labels.extend([str(i+1) for i in range(len(labels), likert_scale)])
                    else:
                        # 默认使用数字作为标签
                        labels = [str(i+1) for i in range(likert_scale)]
                    
                    # 使用单选按钮组显示李克特量表
                    current_value = current_coding.get(var_name, labels[0])
                    current_coding[var_name] = st.radio(
                        label=f"选择{var_name}的值",
                        options=labels,
                        index=labels.index(current_value) if current_value in labels else 0,
                        horizontal=True
                    )
                elif var_type == "数值变量":
                    current_coding[var_name] = st.number_input(
                        f"{var_name}的值", 
                        value=float(current_coding.get(var_name, 0)) if current_coding.get(var_name) else 0.0
                    )
                else:  # 文本变量
                    current_coding[var_name] = st.text_area(
                        f"{var_name}的值", 
                        value=current_coding.get(var_name, ""),
                        height=100
                    )
                
                # 添加分隔线
                if i < len(variables) - 1:
                    st.markdown("---")
        
        # 添加笔记
        st.markdown("### 编码笔记")
        notes = st.text_area("添加任何相关笔记", value=current_coding.get("__notes__", ""), height=100)
        if notes:
            current_coding["__notes__"] = notes
        
        # 提交按钮
        col1, col2 = st.columns([1, 1])
        with col1:
            submit_coding = st.form_submit_button("保存编码", use_container_width=True)
        with col2:
            submit_and_next = st.form_submit_button("保存并跳转到下一个", use_container_width=True)
        
        if submit_coding or submit_and_next:
            # 更新编码结果
            coding_results[selected_file] = current_coding
            
            # 保存编码结果
            with open(coding_results_path, 'w', encoding='utf-8') as f:
                json.dump(coding_results, f, ensure_ascii=False, indent=2)
            
            st.success("编码已保存")
            
            # 如果是"保存并跳转"或者自动跳转设置为True
            if submit_and_next:
                # 查找下一个未编码文件
                uncoded_files = [f for f in all_files if f not in coding_results]
                if uncoded_files:
                    # 自动跳转到下一个未编码文件
                    next_file = uncoded_files[0]
                    st.session_state.next_file = next_file
                    st.rerun()
    
    # 显示编码进度
    st.subheader("编码进度")
    
    # 计算进度
    total_files = len(all_files)
    coded_files = len(coding_results)
    progress = coded_files / total_files if total_files > 0 else 0
    
    # 显示进度条
    st.progress(progress)
    st.write(f"已编码 {coded_files} 个文件，共 {total_files} 个文件 ({int(progress * 100)}%)")
    
    # 显示下一个未编码文件
    uncoded_files = [f for f in all_files if f not in coding_results]
    if uncoded_files:
        next_file = uncoded_files[0]
        st.write(f"下一个未编码文件: {next_file}")
        
        if st.button("跳转到下一个未编码文件", key="manual_jump"):
            # 重定向到下一个未编码文件
            st.session_state.next_file = next_file
            st.rerun()

# 检查是否需要跳转到下一个文件
if 'next_file' in st.session_state:
    next_file = st.session_state.next_file
    # 清除状态，避免循环跳转
    del st.session_state.next_file
    # 设置URL参数
    st.query_params["file"] = next_file

# 页脚
st.markdown("---")
st.markdown("内容分析工具 © 2023")

# 添加批量编码功能
with st.expander("批量编码功能"):
    st.write("您可以使用批量编码功能一次性对多个文件进行编码。")
    
    # 添加全选功能
    select_col1, select_col2 = st.columns([3, 1])
    
    with select_col1:
        st.write("选择要批量编码的文件:")
    
    with select_col2:
        if st.button("全选", key="select_all_files"):
            st.session_state['selected_all_files'] = True
        
        if st.button("清除", key="clear_all_files"):
            st.session_state['selected_all_files'] = False
    
    # 选择要批量编码的文件
    if 'selected_all_files' not in st.session_state:
        st.session_state['selected_all_files'] = False
    
    # 根据全选状态设置默认值
    default_selection = all_files if st.session_state['selected_all_files'] else (uncoded_files[:5] if uncoded_files else [])
    
    files_to_batch_code = st.multiselect(
        "文件列表", 
        all_files,
        default=default_selection
    )
    
    # 批量编码选项
    batch_code_col1, batch_code_col2 = st.columns(2)
    
    with batch_code_col1:
        batch_code_method = st.radio(
            "选择批量编码方法",
            ["自动编码", "复制当前编码", "使用自定义提示词"],
            index=0
        )
    
    with batch_code_col2:
        if batch_code_method == "复制当前编码":
            source_file = st.selectbox(
                "选择源文件（复制其编码结果）",
                [f for f in all_files if f in coding_results],
                index=0 if [f for f in all_files if f in coding_results] else None
            )
        elif batch_code_method == "使用自定义提示词":
            # 检查是否已有自定义提示词
            if 'custom_prompt' not in st.session_state:
                st.session_state.custom_prompt = """请根据以下内容，为指定的变量进行编码。

内容:
{content}

需要编码的变量:
{variables}

请以JSON格式返回编码结果，格式为：
{
    "变量名1": "编码值1",
    "变量名2": "编码值2",
    ...
}

重要说明：
1. 对于分类变量，你必须且只能从提供的选项中选择一个，不要创建新的选项。
2. 对于李克特量表，请返回1到5之间的数值。
3. 请严格按照每个变量的编码指南进行编码。
4. 请确保编码结果符合变量的要求和内容特点。
"""
            
            st.info("将使用自定义提示词进行批量编码。您可以在AI辅助功能中编辑自定义提示词。")
    
    # 批量编码按钮
    if st.button("开始批量编码", type="primary", use_container_width=True):
        if not files_to_batch_code:
            st.error("请选择至少一个文件进行批量编码")
        else:
            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 批量编码处理
            for i, file in enumerate(files_to_batch_code):
                progress = (i) / len(files_to_batch_code)
                progress_bar.progress(progress, text=f"正在处理 {file}...")
                status_text.info(f"正在处理 {i+1}/{len(files_to_batch_code)}: {file}")
                
                if batch_code_method == "自动编码":
                    # 获取文件内容
                    if file in video_links:
                        # 视频链接
                        video_description_key = f"{file}_description"
                        if video_description_key in coding_results:
                            content = coding_results[video_description_key]
                        else:
                            content = f"视频链接: {video_links[file]}"
                    else:
                        # 本地文件
                        file_path = os.path.join(files_dir, file)
                        content = get_file_content(file_path)
                    
                    # 准备变量信息
                    variables_info = []
                    for var in variables:
                        var_info = {
                            "name": var['name'],
                            "type": var['type'],
                            "options": var.get('options', ''),
                            "description": var.get('description', '')
                        }
                        
                        # 添加李克特量表信息
                        if var['type'] == "李克特量表":
                            var_info["likert_scale"] = var.get('likert_scale', 5)
                            var_info["likert_labels"] = var.get('likert_labels', '')
                        
                        # 添加编码指南
                        if var['name'] in coding_guide:
                            var_info["guide"] = coding_guide[var['name']]
                        
                        variables_info.append(var_info)
                    
                    # 自动编码
                    auto_results = auto_code_content(content, variables_info)
                    
                    if auto_results:
                        # 更新编码结果
                        if file not in coding_results:
                            coding_results[file] = {}
                        
                        for var_name, value in auto_results.items():
                            coding_results[file][var_name] = value
                    else:
                        status_text.warning(f"文件 {file} 自动编码失败")
                
                elif batch_code_method == "复制当前编码" and source_file in coding_results:
                    # 复制编码结果
                    if file not in coding_results:
                        coding_results[file] = {}
                    
                    # 复制源文件的编码结果
                    coding_results[file] = coding_results[source_file].copy()
                
                elif batch_code_method == "使用自定义提示词":
                    # 获取文件内容
                    if file in video_links:
                        # 视频链接
                        video_description_key = f"{file}_description"
                        if video_description_key in coding_results:
                            content = coding_results[video_description_key]
                        else:
                            content = f"视频链接: {video_links[file]}"
                    else:
                        # 本地文件
                        file_path = os.path.join(files_dir, file)
                        content = get_file_content(file_path)
                    
                    # 准备变量信息
                    variables_info = []
                    for var in variables:
                        var_info = {
                            "name": var['name'],
                            "type": var['type'],
                            "options": var.get('options', ''),
                            "description": var.get('description', '')
                        }
                        
                        # 添加李克特量表信息
                        if var['type'] == "李克特量表":
                            var_info["likert_scale"] = var.get('likert_scale', 5)
                            var_info["likert_labels"] = var.get('likert_labels', '')
                        
                        # 添加编码指南
                        if var['name'] in coding_guide:
                            var_info["guide"] = coding_guide[var['name']]
                        
                        variables_info.append(var_info)
                    
                    # 使用自定义提示词进行编码
                    auto_results = auto_code_content(content, variables_info, st.session_state.custom_prompt)
                    
                    if auto_results:
                        # 更新编码结果
                        if file not in coding_results:
                            coding_results[file] = {}
                        
                        for var_name, value in auto_results.items():
                            coding_results[file][var_name] = value
                    else:
                        status_text.warning(f"文件 {file} 使用自定义提示词编码失败")
            
            # 保存编码结果
            with open(coding_results_path, 'w', encoding='utf-8') as f:
                json.dump(coding_results, f, ensure_ascii=False, indent=2)
            
            # 完成进度
            progress_bar.progress(1.0, text="批量编码完成！")
            status_text.success(f"已完成 {len(files_to_batch_code)} 个文件的批量编码")

# 更新URL参数
if selected_file != st.query_params.get("file"):
    st.query_params["file"] = selected_file

# 编码结果选项卡
with tab3:
    st.header("编码结果呈现与导出")
    
    # 加载编码结果
    if os.path.exists(coding_results_path):
        with open(coding_results_path, 'r', encoding='utf-8') as f:
            all_coding_results = json.load(f)
    else:
        all_coding_results = {}
    
    # 加载变量信息
    variables_dict = {var['name']: var for var in variables}
    
    if not all_coding_results:
        st.warning("暂无编码结果，请先进行内容编码")
    else:
        # 创建子选项卡
        results_tab1, results_tab2, results_tab3 = st.tabs(["结果概览", "详细分析", "导出结果"])
        
        # 结果概览选项卡
        with results_tab1:
            st.subheader("编码结果概览")
            
            # 显示已编码内容数量
            st.info(f"已编码内容数量: {len(all_coding_results)}")
            
            # 创建编码结果数据框
            results_data = []
            
            for content_name, var_results in all_coding_results.items():
                # 跳过视频描述等非编码结果
                if content_name.endswith("_description"):
                    continue
                    
                row = {"内容名称": content_name}
                
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
                    coded_count = sum(1 for results in all_coding_results.values() 
                                     if not str(results).endswith("_description") and var_name in results)
                    completion_data.append({
                        "变量名": var_name,
                        "已编码内容数": coded_count,
                        "编码完成率": round(coded_count / len(results_data) * 100, 2)
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
                key="text_analysis_var_select"
            )
            
            if analysis_var:
                selected_var = variables_dict.get(analysis_var)
                
                if selected_var:
                    var_type = selected_var.get('type', '')
                    st.write(f"变量类型: {var_type}")
                    
                    # 收集该变量的所有值
                    var_values = []
                    content_names = []
                    for content_name, var_results in all_coding_results.items():
                        # 跳过视频描述等非编码结果
                        if content_name.endswith("_description"):
                            continue
                            
                        if analysis_var in var_results:
                            var_values.append(var_results[analysis_var])
                            content_names.append(content_name)
                    
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
                                "内容": content_names,
                                f"{analysis_var}": var_values
                            })
                            st.dataframe(text_df, use_container_width=True)
                    else:
                        st.warning(f"没有找到变量 '{analysis_var}' 的编码值")
                else:
                    st.error(f"找不到变量 '{analysis_var}' 的信息")
            
            # 添加AI分析报告生成功能
            st.subheader("AI分析报告")
            
            if st.button("生成AI分析报告", key="text_generate_ai_report"):
                # 检查是否有硅基流动API客户端
                from utils import get_siliconflow_client
                client = get_siliconflow_client()
                if not client:
                    st.error("生成AI分析报告需要硅基流动API支持，请在设置中配置API密钥")
                else:
                    with st.spinner("正在生成分析报告..."):
                        try:
                            # 准备数据
                            report_data = {
                                "编码结果": {k: v for k, v in all_coding_results.items() if not k.endswith("_description")},
                                "变量信息": {var['name']: var for var in variables}
                            }
                            
                            # 构建提示词
                            prompt = f"""
请根据以下内容编码结果数据，生成一份详细的分析报告。

编码数据:
{json.dumps(report_data, ensure_ascii=False, indent=2)}

请在报告中包含以下内容:
1. 总体概述：已编码内容数量、变量数量等基本信息
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
                                    report_path = os.path.join(project_path, "content_coding_report.md")
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
                horizontal=True,
                key="text_export_format"
            )
            
            # 选择要导出的变量
            export_vars = st.multiselect(
                "选择要导出的变量",
                [var['name'] for var in variables],
                default=[var['name'] for var in variables],
                key="text_export_vars"
            )
            
            # 导出按钮
            if st.button("导出编码结果", key="text_export_results_btn"):
                if not export_vars:
                    st.error("请至少选择一个变量进行导出")
                else:
                    # 准备导出数据
                    export_data = []
                    
                    for content_name, var_results in all_coding_results.items():
                        # 跳过视频描述等非编码结果
                        if content_name.endswith("_description"):
                            continue
                            
                        row = {"内容名称": content_name}
                        
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
                            href = f'<a href="data:file/csv;base64,{b64}" download="content_coding_results.csv">下载CSV文件</a>'
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
                                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="content_coding_results.xlsx">下载Excel文件</a>'
                                st.markdown(href, unsafe_allow_html=True)
                            except ImportError:
                                st.error("导出Excel需要安装xlsxwriter模块。请运行 `pip install xlsxwriter` 安装该模块。")
                                # 提供CSV作为备选
                                st.info("您可以选择CSV格式作为替代。")
                        
                        else:  # JSON
                            # 创建JSON格式的数据
                            json_data = {}
                            for content_name, var_results in all_coding_results.items():
                                # 跳过视频描述等非编码结果
                                if content_name.endswith("_description"):
                                    continue
                                    
                                json_data[content_name] = {}
                                for var_name in export_vars:
                                    if var_name in var_results:
                                        # 处理李克特量表数据，将其转换为数值
                                        if var_name in variables_dict and variables_dict[var_name].get('type') == "李克特量表":
                                            value = var_results[var_name]
                                            converted_value = convert_likert_to_numeric(value)
                                            if not pd.isna(converted_value) and isinstance(converted_value, (int, float)):
                                                json_data[content_name][var_name] = converted_value
                                            else:
                                                json_data[content_name][var_name] = value
                                        else:
                                            json_data[content_name][var_name] = var_results[var_name]
                                    else:
                                        json_data[content_name][var_name] = ""
                            
                            json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
                            b64 = base64.b64encode(json_str.encode('utf-8')).decode()
                            href = f'<a href="data:file/json;base64,{b64}" download="content_coding_results.json">下载JSON文件</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    else:
                        st.warning("没有可导出的数据")

# 更新URL参数
if selected_file != st.query_params.get("file"):
    st.query_params["file"] = selected_file

# 视频描述编辑
st.subheader("内容描述")
video_description_key = f"{selected_file}_description"
video_description = coding_results.get(video_description_key, "")

new_description = st.text_area(
    "编辑内容描述",
    value=video_description,
    height=200
)

if st.button("保存内容描述"):
    coding_results[video_description_key] = new_description
    with open(coding_results_path, 'w', encoding='utf-8') as f:
        json.dump(coding_results, f, ensure_ascii=False, indent=2)
    st.success("内容描述已保存") 