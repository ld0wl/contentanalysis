import streamlit as st
import os
import json
import pandas as pd
from utils import get_current_project_path, save_project_data, load_project_data

# 设置页面配置
st.set_page_config(
    page_title="编码管理",
    page_icon="🔖",
    layout="wide"
)

# 检查是否有活动项目
if 'current_project' not in st.session_state or not st.session_state.current_project:
    st.warning("请先在首页选择或创建一个项目")
    st.stop()

# 页面标题
st.title("编码管理")
st.write(f"当前项目: {st.session_state.current_project}")

# 获取项目路径
project_path = get_current_project_path()
config_path = os.path.join(project_path, "config.json")

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

# 创建选项卡
tab1, tab2, tab3 = st.tabs(["变量管理", "编码指南", "导入/导出"])

# 变量管理选项卡
with tab1:
    st.header("变量管理")
    
    # 添加新变量
    with st.expander("添加新变量", expanded=True):
        with st.form("add_variable_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                var_name = st.text_input("变量名称")
                var_type = st.selectbox("变量类型", ["分类变量", "李克特量表", "数值变量", "文本变量"])
            
            with col2:
                var_options = st.text_area("变量选项 (分类变量用逗号分隔)", height=100)
                if var_type == "李克特量表":
                    likert_scale = st.slider("李克特量表级别", min_value=3, max_value=10, value=5, step=1)
                    likert_labels = st.text_input("量表标签 (可选，用逗号分隔，例如：非常不同意,不同意,中立,同意,非常同意)")
                var_desc = st.text_input("变量描述 (可选)")
            
            # 添加编码指南字段
            var_guide = st.text_area("编码指南", height=150, 
                                   help="为该变量提供详细的编码指南，帮助编码员和AI理解如何编码")
            
            submit_var = st.form_submit_button("添加变量")
            
            if submit_var and var_name:
                # 检查变量名是否已存在
                existing_names = [v['name'] for v in variables]
                if var_name in existing_names:
                    st.error(f"变量 '{var_name}' 已存在")
                else:
                    # 添加新变量
                    new_var = {
                        "name": var_name,
                        "type": var_type,
                        "options": var_options,
                        "description": var_desc,
                        "guide": var_guide
                    }
                    
                    # 如果是李克特量表，添加额外信息
                    if var_type == "李克特量表":
                        new_var["likert_scale"] = likert_scale
                        new_var["likert_labels"] = likert_labels
                    
                    variables.append(new_var)
                    
                    # 更新项目配置
                    project_config['variables'] = variables
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(project_config, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"变量 '{var_name}' 添加成功")
                    st.rerun()
    
    # 显示现有变量
    if variables:
        st.subheader("现有变量")
        
        # 创建变量表格
        var_data = []
        for i, var in enumerate(variables):
            var_data.append({
                "ID": str(i + 1),
                "变量名": var['name'],
                "类型": var['type'],
                "选项": var['options'],
                "描述": var.get('description', ''),
                "编码指南": var.get('guide', '')[:50] + ('...' if var.get('guide', '') and len(var.get('guide', '')) > 50 else '')
            })
        
        var_df = pd.DataFrame(var_data)
        st.dataframe(var_df, use_container_width=True)
        
        # 删除变量
        with st.expander("删除变量"):
            delete_col1, delete_col2 = st.columns([3, 1])
            
            with delete_col1:
                var_to_delete = st.selectbox("选择要删除的变量", [v['name'] for v in variables])
            
            with delete_col2:
                delete_button = st.button("删除选定变量", type="primary", use_container_width=True)
            
            if delete_button:
                # 设置删除确认状态
                st.session_state['confirm_var_delete'] = True
                st.session_state['var_to_delete'] = var_to_delete
            
            # 检查是否需要显示确认对话框
            if st.session_state.get('confirm_var_delete', False):
                st.warning(f"确定要删除变量 '{st.session_state['var_to_delete']}' 吗？此操作不可撤销。")
                col1, col2 = st.columns(2)
                with col1:
                    confirm_delete = st.button("确认删除", key="confirm_delete_var", type="primary")
                with col2:
                    cancel_delete = st.button("取消", key="cancel_delete_var")
                
                if confirm_delete:
                    # 删除变量
                    variables = [v for v in variables if v['name'] != st.session_state['var_to_delete']]
                    
                    # 更新项目配置
                    project_config['variables'] = variables
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(project_config, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"变量 '{st.session_state['var_to_delete']}' 已删除")
                    # 清除删除状态
                    st.session_state.pop('confirm_var_delete', None)
                    st.session_state.pop('var_to_delete', None)
                    st.rerun()
                
                if cancel_delete:
                    # 清除删除状态
                    st.session_state.pop('confirm_var_delete', None)
                    st.session_state.pop('var_to_delete', None)
                    st.rerun()
    else:
        st.info("项目中没有变量，请添加变量")

# 编码指南选项卡
with tab2:
    st.header("编码指南")
    
    if not variables:
        st.info("请先添加变量")
    else:
        # 选择变量
        selected_var_name = st.selectbox("选择变量", [v['name'] for v in variables])
        
        # 获取选中的变量
        selected_var = next((v for v in variables if v['name'] == selected_var_name), None)
        
        if selected_var:
            # 获取当前编码指南
            current_guide = selected_var.get('guide', '')
            
            # 编辑编码指南
            new_guide = st.text_area("编码指南", value=current_guide, height=300,
                                   help="为该变量提供详细的编码指南，帮助编码员和AI理解如何编码")
            
            if st.button("保存编码指南"):
                # 更新变量的编码指南
                for i, var in enumerate(variables):
                    if var['name'] == selected_var_name:
                        variables[i]['guide'] = new_guide
                        break
                
                # 更新项目配置
                project_config['variables'] = variables
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(project_config, f, ensure_ascii=False, indent=2)
                
                st.success(f"变量 '{selected_var_name}' 的编码指南已更新")

# 导入/导出选项卡
with tab3:
    st.header("导入/导出")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("导出变量模板")
        
        if variables:
            # 创建导出数据
            export_data = {
                "variables": variables,
                "coding_guide": coding_guide
            }
            
            # 转换为JSON
            export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
            
            # 提供下载
            st.download_button(
                label="导出变量模板",
                data=export_json,
                file_name="variables_template.json",
                mime="application/json"
            )
        else:
            st.info("没有变量可导出")
    
    with col2:
        st.subheader("导入变量模板")
        
        uploaded_file = st.file_uploader("上传变量模板", type=["json"])
        
        if uploaded_file:
            try:
                # 读取上传的文件
                import_data = json.load(uploaded_file)
                
                # 验证数据格式
                if "variables" not in import_data:
                    st.error("无效的变量模板：缺少 'variables' 字段")
                else:
                    # 确认导入
                    if st.button("确认导入"):
                        # 更新变量和编码指南
                        project_config['variables'] = import_data.get('variables', [])
                        project_config['coding_guide'] = import_data.get('coding_guide', {})
                        
                        # 保存项目配置
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(project_config, f, ensure_ascii=False, indent=2)
                        
                        st.success("变量模板导入成功")
                        st.rerun()
            except Exception as e:
                st.error(f"导入失败: {str(e)}")

# 页脚
st.markdown("---")
st.markdown("内容分析工具 © 2023") 