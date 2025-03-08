import streamlit as st
import os
import json
import pandas as pd
import shutil
from datetime import datetime
from utils import get_current_project_path, get_file_content, get_video_info

# 设置页面配置
st.set_page_config(
    page_title="内容管理",
    page_icon="📁",
    layout="wide"
)

# 检查是否有活动项目
if 'current_project' not in st.session_state or not st.session_state.current_project:
    st.warning("请先在首页选择或创建一个项目")
    st.stop()

# 页面标题
st.title("内容管理")
st.write(f"当前项目: {st.session_state.current_project}")

# 获取项目路径
project_path = get_current_project_path()
files_dir = os.path.join(project_path, "files")
coding_results_path = os.path.join(project_path, "coding_results.json")
video_links_path = os.path.join(project_path, "video_links.json")

# 确保文件目录存在
if not os.path.exists(files_dir):
    os.makedirs(files_dir)

# 加载编码结果
coding_results = {}
if os.path.exists(coding_results_path):
    with open(coding_results_path, 'r', encoding='utf-8') as f:
        coding_results = json.load(f)

# 加载视频链接
video_links = {}
if os.path.exists(video_links_path):
    with open(video_links_path, 'r', encoding='utf-8') as f:
        video_links = json.load(f)

# 创建选项卡
tab1, tab2, tab3 = st.tabs(["文件管理", "视频链接管理", "内容预览"])

# 文件管理选项卡
with tab1:
    st.header("文件管理")
    
    # 上传文件
    uploaded_files = st.file_uploader("上传文件", accept_multiple_files=True)
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # 保存文件
            file_path = os.path.join(files_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"文件 '{uploaded_file.name}' 上传成功")
    
    # 显示现有文件
    if os.path.exists(files_dir):
        files = [f for f in os.listdir(files_dir) if os.path.isfile(os.path.join(files_dir, f))]
        
        if files:
            st.subheader("现有文件")
            
            # 创建文件表格
            file_data = []
            for i, file_name in enumerate(files):
                file_path = os.path.join(files_dir, file_name)
                file_size = os.path.getsize(file_path) / 1024  # KB
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                
                # 检查是否已编码
                is_coded = file_name in coding_results
                
                file_data.append({
                    "ID": str(i + 1),
                    "文件名": file_name,
                    "大小(KB)": str(round(file_size, 2)),
                    "修改时间": file_time,
                    "已编码": "是" if is_coded else "否"
                })
            
            file_df = pd.DataFrame(file_data)
            st.dataframe(file_df, use_container_width=True)
            
            # 删除文件
            with st.expander("删除文件"):
                delete_col1, delete_col2 = st.columns([3, 1])
                
                with delete_col1:
                    file_to_delete = st.selectbox("选择要删除的文件", files)
                
                with delete_col2:
                    delete_button = st.button("删除选定文件", type="primary", use_container_width=True)
                
                if delete_button:
                    # 设置删除确认状态
                    st.session_state['confirm_file_delete'] = True
                    st.session_state['file_to_delete'] = file_to_delete
                
                # 检查是否需要显示确认对话框
                if st.session_state.get('confirm_file_delete', False):
                    st.warning(f"确定要删除文件 '{st.session_state['file_to_delete']}' 吗？此操作不可撤销。")
                    col1, col2 = st.columns(2)
                    with col1:
                        confirm_delete = st.button("确认删除", key="confirm_delete_file", type="primary")
                    with col2:
                        cancel_delete = st.button("取消", key="cancel_delete_file")
                    
                    if confirm_delete:
                        # 删除文件
                        file_path = os.path.join(files_dir, st.session_state['file_to_delete'])
                        try:
                            os.remove(file_path)
                            
                            # 如果有编码结果，也删除
                            if st.session_state['file_to_delete'] in coding_results:
                                del coding_results[st.session_state['file_to_delete']]
                                with open(coding_results_path, 'w', encoding='utf-8') as f:
                                    json.dump(coding_results, f, ensure_ascii=False, indent=2)
                            
                            st.success(f"文件 '{st.session_state['file_to_delete']}' 已删除")
                            # 清除删除状态
                            st.session_state.pop('confirm_file_delete', None)
                            st.session_state.pop('file_to_delete', None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除文件失败: {str(e)}")
                            # 清除删除状态
                            st.session_state.pop('confirm_file_delete', None)
                            st.session_state.pop('file_to_delete', None)
                    
                    if cancel_delete:
                        # 清除删除状态
                        st.session_state.pop('confirm_file_delete', None)
                        st.session_state.pop('file_to_delete', None)
                        st.rerun()
        else:
            st.info("项目中没有文件，请上传文件")

# 视频链接管理选项卡
with tab2:
    st.header("视频链接管理")
    
    # 添加视频链接
    with st.form("add_video_link_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            video_name = st.text_input("视频名称")
        
        with col2:
            video_url = st.text_input("视频链接 (URL)")
        
        submit_link = st.form_submit_button("添加视频链接")
        
        if submit_link and video_name and video_url:
            # 添加视频链接
            video_links[video_name] = video_url
            
            # 保存视频链接
            with open(video_links_path, 'w', encoding='utf-8') as f:
                json.dump(video_links, f, ensure_ascii=False, indent=2)
            
            st.success(f"视频链接 '{video_name}' 添加成功")
            st.rerun()
    
    # 显示现有视频链接
    if video_links:
        st.subheader("现有视频链接")
        
        # 创建视频链接表格
        link_data = []
        for i, (name, url) in enumerate(video_links.items()):
            # 检查是否已编码
            is_coded = name in coding_results
            
            link_data.append({
                "ID": str(i + 1),
                "视频名称": name,
                "视频链接": url,
                "已编码": "是" if is_coded else "否"
            })
        
        link_df = pd.DataFrame(link_data)
        st.dataframe(link_df, use_container_width=True)
        
        # 删除视频链接
        with st.expander("删除视频链接"):
            delete_col1, delete_col2 = st.columns([3, 1])
            
            with delete_col1:
                link_to_delete = st.selectbox("选择要删除的视频链接", list(video_links.keys()))
            
            with delete_col2:
                delete_button = st.button("删除选定链接", type="primary", use_container_width=True, key="delete_link_button")
            
            if delete_button:
                # 设置删除确认状态
                st.session_state['confirm_link_delete'] = True
                st.session_state['link_to_delete'] = link_to_delete
            
            # 检查是否需要显示确认对话框
            if st.session_state.get('confirm_link_delete', False):
                st.warning(f"确定要删除视频链接 '{st.session_state['link_to_delete']}' 吗？此操作不可撤销。")
                col1, col2 = st.columns(2)
                with col1:
                    confirm_delete = st.button("确认删除", key="confirm_delete_link", type="primary")
                with col2:
                    cancel_delete = st.button("取消", key="cancel_delete_link")
                
                if confirm_delete:
                    # 删除视频链接
                    del video_links[st.session_state['link_to_delete']]
                    
                    # 保存视频链接
                    with open(video_links_path, 'w', encoding='utf-8') as f:
                        json.dump(video_links, f, ensure_ascii=False, indent=2)
                    
                    # 如果有编码结果，也删除
                    if st.session_state['link_to_delete'] in coding_results:
                        del coding_results[st.session_state['link_to_delete']]
                        with open(coding_results_path, 'w', encoding='utf-8') as f:
                            json.dump(coding_results, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"视频链接 '{st.session_state['link_to_delete']}' 已删除")
                    # 清除删除状态
                    st.session_state.pop('confirm_link_delete', None)
                    st.session_state.pop('link_to_delete', None)
                    st.rerun()
                
                if cancel_delete:
                    # 清除删除状态
                    st.session_state.pop('confirm_link_delete', None)
                    st.session_state.pop('link_to_delete', None)
                    st.rerun()
    else:
        st.info("项目中没有视频链接，请添加视频链接")

# 内容预览选项卡
with tab3:
    st.header("内容预览")
    
    # 合并文件和视频链接
    all_contents = []
    
    # 添加文件
    if os.path.exists(files_dir):
        files = [f for f in os.listdir(files_dir) if os.path.isfile(os.path.join(files_dir, f))]
        for file_name in files:
            all_contents.append({"name": file_name, "type": "file"})
    
    # 添加视频链接
    for video_name in video_links.keys():
        all_contents.append({"name": video_name, "type": "video"})
    
    if all_contents:
        # 选择内容
        content_names = [c["name"] for c in all_contents]
        selected_content = st.selectbox("选择内容", content_names)
        
        # 查找选中内容的类型
        content_type = next((c["type"] for c in all_contents if c["name"] == selected_content), None)
        
        if content_type == "file":
            # 显示文件内容
            file_path = os.path.join(files_dir, selected_content)
            content = get_file_content(file_path)
            st.text_area("文件内容", content, height=400)
        elif content_type == "video":
            # 显示视频
            video_url = video_links[selected_content]
            st.write(f"视频链接: {video_url}")
            
            try:
                st.video(video_url)
            except:
                st.warning("无法嵌入视频，请直接访问链接查看")
                st.markdown(f"[在新窗口打开视频]({video_url})")
    else:
        st.info("项目中没有内容，请上传文件或添加视频链接")

# 页脚
st.markdown("---")
st.markdown("内容分析工具 © 2023") 