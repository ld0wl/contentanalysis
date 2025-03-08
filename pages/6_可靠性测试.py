import streamlit as st
import os
import json
import pandas as pd
import numpy as np
import tempfile
from utils import get_current_project_path, calculate_percentage_agreement, calculate_krippendorff_alpha

# 设置页面配置
st.set_page_config(
    page_title="可靠性测试",
    page_icon="🔍",
    layout="wide"
)

# 检查是否有活动项目
if 'current_project' not in st.session_state or not st.session_state.current_project:
    st.warning("请先在首页选择或创建一个项目")
    st.stop()

# 页面标题
st.title("可靠性测试")
st.write(f"当前项目: {st.session_state.current_project}")

# 获取项目路径
project_path = get_current_project_path()
config_path = os.path.join(project_path, "config.json")
reliability_path = os.path.join(project_path, "reliability_results.json")

# 加载项目配置
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        project_config = json.load(f)
else:
    st.error("项目配置文件不存在")
    st.stop()

# 初始化变量列表
variables = project_config.get('variables', [])

# 检查是否有变量
if not variables:
    st.error("请先在编码管理页面添加变量")
    st.stop()

# 创建选项卡
tab1, tab2, tab3 = st.tabs(["数据导入", "可靠性计算", "结果导出"])

# 数据导入选项卡
with tab1:
    st.header("数据导入")
    
    st.write("""
    ### 数据格式说明
    
    可靠性测试需要多个编码员对相同内容进行编码的数据。您可以上传以下格式的数据：
    
    1. **Excel文件**：包含以下列：
       - `content_id`：内容ID
       - `coder_id`：编码员ID
       - 变量列：每个变量一列
       
    2. **CSV文件**：与Excel格式相同
    
    3. **JSON文件**：包含以下结构：
    ```json
    [
        {
            "content_id": "内容1",
            "coder_id": "编码员1",
            "variables": {
                "变量1": "值1",
                "变量2": "值2"
            }
        },
        ...
    ]
    ```
    """)
    
    # 上传文件
    uploaded_file = st.file_uploader("上传编码数据", type=["xlsx", "csv", "json"])
    
    if uploaded_file:
        try:
            # 根据文件类型读取数据
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            
            if file_ext == '.xlsx':
                df = pd.read_excel(uploaded_file)
                st.success("Excel文件上传成功")
            elif file_ext == '.csv':
                df = pd.read_csv(uploaded_file)
                st.success("CSV文件上传成功")
            elif file_ext == '.json':
                # 读取JSON数据
                json_data = json.load(uploaded_file)
                
                # 转换为DataFrame
                rows = []
                for item in json_data:
                    row = {
                        'content_id': item['content_id'],
                        'coder_id': item['coder_id']
                    }
                    
                    # 添加变量值
                    for var_name, value in item['variables'].items():
                        row[var_name] = value
                    
                    rows.append(row)
                
                df = pd.DataFrame(rows)
                st.success("JSON文件上传成功")
            
            # 显示数据预览
            st.subheader("数据预览")
            st.dataframe(df.head())
            
            # 检查必要的列
            required_cols = ['content_id', 'coder_id']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"缺少必要的列: {', '.join(missing_cols)}")
            else:
                # 检查变量列
                var_cols = [col for col in df.columns if col not in required_cols]
                
                if not var_cols:
                    st.error("没有找到变量列")
                else:
                    st.write(f"找到 {len(var_cols)} 个变量列: {', '.join(var_cols)}")
                    
                    # 保存数据
                    reliability_data = {
                        "data": df.to_dict(orient='records'),
                        "variables": var_cols
                    }
                    
                    with open(reliability_path, 'w', encoding='utf-8') as f:
                        json.dump(reliability_data, f, ensure_ascii=False, indent=2)
                    
                    st.session_state.reliability_data = reliability_data
                    st.success("数据已保存，可以进行可靠性计算")
        
        except Exception as e:
            st.error(f"数据导入失败: {str(e)}")
    
    # 导出样本文件
    st.subheader("导出样本文件")
    
    sample_format = st.radio("选择样本格式", ["Excel", "CSV", "JSON"])
    
    if st.button("导出样本文件"):
        # 创建样本数据
        sample_data = []
        
        # 使用项目中的变量
        var_names = [var['name'] for var in variables]
        
        # 创建样本记录
        for content_id in range(1, 4):
            for coder_id in range(1, 3):
                if sample_format == "JSON":
                    record = {
                        "content_id": f"content_{content_id}",
                        "coder_id": f"coder_{coder_id}",
                        "variables": {}
                    }
                    
                    for var_name in var_names:
                        record["variables"][var_name] = f"值_{content_id}_{coder_id}"
                    
                    sample_data.append(record)
                else:
                    record = {
                        "content_id": f"content_{content_id}",
                        "coder_id": f"coder_{coder_id}"
                    }
                    
                    for var_name in var_names:
                        record[var_name] = f"值_{content_id}_{coder_id}"
                    
                    sample_data.append(record)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{sample_format.lower()}") as tmp:
            if sample_format == "Excel":
                pd.DataFrame(sample_data).to_excel(tmp.name, index=False)
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                file_name = "reliability_sample.xlsx"
            elif sample_format == "CSV":
                pd.DataFrame(sample_data).to_csv(tmp.name, index=False)
                mime = "text/csv"
                file_name = "reliability_sample.csv"
            else:  # JSON
                with open(tmp.name, 'w', encoding='utf-8') as f:
                    json.dump(sample_data, f, ensure_ascii=False, indent=2)
                mime = "application/json"
                file_name = "reliability_sample.json"
            
            # 读取临时文件
            with open(tmp.name, "rb") as f:
                data = f.read()
            
            # 提供下载
            st.download_button(
                label=f"下载{sample_format}样本文件",
                data=data,
                file_name=file_name,
                mime=mime
            )

# 可靠性计算选项卡
with tab2:
    st.header("可靠性计算")
    
    # 检查是否有数据
    if 'reliability_data' not in st.session_state and os.path.exists(reliability_path):
        with open(reliability_path, 'r', encoding='utf-8') as f:
            st.session_state.reliability_data = json.load(f)
    
    if 'reliability_data' not in st.session_state:
        st.info("请先在数据导入选项卡中上传数据")
    else:
        # 获取数据
        reliability_data = st.session_state.reliability_data
        data_records = reliability_data["data"]
        var_cols = reliability_data["variables"]
        
        # 选择要计算的变量
        selected_vars = st.multiselect("选择要计算的变量", var_cols, default=var_cols)
        
        if not selected_vars:
            st.warning("请至少选择一个变量")
        else:
            # 选择计算方法
            methods = st.multiselect(
                "选择计算方法",
                ["百分比一致性", "Holsti系数", "Scott's Pi", "Cohen's Kappa", "Krippendorff's Alpha"],
                default=["百分比一致性", "Krippendorff's Alpha"]
            )
            
            if not methods:
                st.warning("请至少选择一种计算方法")
            elif st.button("计算可靠性"):
                # 准备数据
                df = pd.DataFrame(data_records)
                
                # 按内容ID和编码员ID分组
                observations = []
                content_ids = df['content_id'].unique()
                
                for content_id in content_ids:
                    content_df = df[df['content_id'] == content_id]
                    coders = content_df['coder_id'].unique()
                    
                    if len(coders) < 2:
                        st.warning(f"内容 '{content_id}' 只有一个编码员，跳过")
                        continue
                    
                    # 获取每个编码员的编码
                    for coder_id in coders:
                        coder_df = content_df[content_df['coder_id'] == coder_id]
                        
                        if len(coder_df) > 0:
                            # 获取变量值
                            obs = {}
                            for var in selected_vars:
                                if var in coder_df.columns:
                                    obs[var] = coder_df[var].iloc[0]
                            
                            if obs:
                                observations.append(obs)
                
                if len(observations) < 2:
                    st.error("没有足够的观察值进行计算")
                else:
                    # 计算可靠性
                    results = {}
                    
                    # 获取每个变量的类别
                    categories = {}
                    for var in selected_vars:
                        values = set()
                        for obs in observations:
                            if var in obs:
                                values.add(obs[var])
                        categories[var] = list(values)
                    
                    # 计算各种系数
                    if "百分比一致性" in methods:
                        agreement = calculate_percentage_agreement(observations)
                        results["百分比一致性"] = agreement
                    
                    if "Holsti系数" in methods:
                        # 简化实现，与百分比一致性相同
                        agreement = calculate_percentage_agreement(observations)
                        results["Holsti系数"] = agreement
                    
                    if "Scott's Pi" in methods:
                        # 需要更复杂的实现
                        results["Scott's Pi"] = "未实现"
                    
                    if "Cohen's Kappa" in methods:
                        # 需要更复杂的实现
                        results["Cohen's Kappa"] = "未实现"
                    
                    if "Krippendorff's Alpha" in methods:
                        alpha = calculate_krippendorff_alpha(observations, categories)
                        results["Krippendorff's Alpha"] = alpha
                    
                    # 显示结果
                    st.subheader("计算结果")
                    
                    result_df = pd.DataFrame({
                        "方法": list(results.keys()),
                        "系数值": list(results.values())
                    })
                    
                    st.dataframe(result_df)
                    
                    # 解释结果
                    st.subheader("结果解释")
                    
                    st.write("""
                    ### 可靠性系数解释
                    
                    - **百分比一致性**：简单计算编码员之间的一致百分比。范围：0-1，越高越好。
                    - **Holsti系数**：类似于百分比一致性，但考虑了所有可能的编码员对。范围：0-1，越高越好。
                    - **Scott's Pi**：考虑了偶然一致的可能性。范围：-1到1，通常大于0.7被认为是可接受的。
                    - **Cohen's Kappa**：考虑了偶然一致的可能性，适用于两个编码员。范围：-1到1，通常大于0.7被认为是可接受的。
                    - **Krippendorff's Alpha**：更通用的可靠性系数，适用于多个编码员和不同类型的数据。范围：0-1，通常大于0.8被认为是可靠的，大于0.667被认为是可接受的。
                    """)
                    
                    # 保存结果
                    reliability_data["results"] = results
                    
                    with open(reliability_path, 'w', encoding='utf-8') as f:
                        json.dump(reliability_data, f, ensure_ascii=False, indent=2)
                    
                    st.success("计算结果已保存")

# 结果导出选项卡
with tab3:
    st.header("结果导出")
    
    # 检查是否有结果
    if 'reliability_data' not in st.session_state and os.path.exists(reliability_path):
        with open(reliability_path, 'r', encoding='utf-8') as f:
            st.session_state.reliability_data = json.load(f)
    
    if 'reliability_data' not in st.session_state or "results" not in st.session_state.reliability_data:
        st.info("请先在可靠性计算选项卡中计算结果")
    else:
        # 获取结果
        reliability_data = st.session_state.reliability_data
        results = reliability_data["results"]
        
        # 显示结果
        st.subheader("计算结果")
        
        result_df = pd.DataFrame({
            "方法": list(results.keys()),
            "系数值": list(results.values())
        })
        
        st.dataframe(result_df)
        
        # 导出格式选择
        export_format = st.radio("选择导出格式", ["Excel", "CSV", "JSON"])
        
        if st.button("导出结果"):
            # 创建导出数据
            export_data = {
                "project": st.session_state.current_project,
                "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "variables": reliability_data["variables"],
                "results": results
            }
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{export_format.lower()}") as tmp:
                if export_format == "Excel":
                    # 创建Excel写入器
                    with pd.ExcelWriter(tmp.name) as writer:
                        # 写入结果
                        result_df.to_excel(writer, sheet_name="结果", index=False)
                        
                        # 写入原始数据
                        pd.DataFrame(reliability_data["data"]).to_excel(writer, sheet_name="原始数据", index=False)
                        
                        # 写入项目信息
                        pd.DataFrame([{
                            "项目名称": st.session_state.current_project,
                            "时间戳": export_data["timestamp"],
                            "变量数量": len(reliability_data["variables"])
                        }]).to_excel(writer, sheet_name="项目信息", index=False)
                    
                    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    file_name = "reliability_results.xlsx"
                elif export_format == "CSV":
                    # 只能导出结果
                    result_df.to_csv(tmp.name, index=False)
                    mime = "text/csv"
                    file_name = "reliability_results.csv"
                else:  # JSON
                    with open(tmp.name, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                    mime = "application/json"
                    file_name = "reliability_results.json"
                
                # 读取临时文件
                with open(tmp.name, "rb") as f:
                    data = f.read()
                
                # 提供下载
                st.download_button(
                    label=f"下载{export_format}结果文件",
                    data=data,
                    file_name=file_name,
                    mime=mime
                )

# 页脚
st.markdown("---")
st.markdown("内容分析工具 © 2023") 