import streamlit as st
import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from utils import get_current_project_path, get_file_content, create_wordcloud
from bertopic_utils import BERTopicAnalyzer

# 设置页面配置
st.set_page_config(
    page_title="主题分析",
    page_icon="📊",
    layout="wide"
)

# 检查是否有活动项目
if 'current_project' not in st.session_state or not st.session_state.current_project:
    st.warning("请先在首页选择或创建一个项目")
    st.stop()

# 页面标题
st.title("主题分析 (BERTopic) 仅有基础功能，如需要更多功能请使用下载界面的bertopic专用工具")
st.write(f"当前项目: {st.session_state.current_project}")

# 获取项目路径
project_path = get_current_project_path()
files_dir = os.path.join(project_path, "files")
bertopic_results_path = os.path.join(project_path, "bertopic_results.json")

# 检查文件目录是否存在
if not os.path.exists(files_dir):
    st.error("文件目录不存在")
    st.stop()

# 获取文件列表
files = [f for f in os.listdir(files_dir) if os.path.isfile(os.path.join(files_dir, f))]

if not files:
    st.error("项目中没有文件，请先上传文件")
    st.stop()

# 初始化BERTopic分析器
@st.cache_resource
def get_bertopic_analyzer():
    return BERTopicAnalyzer()

analyzer = get_bertopic_analyzer()

# 创建选项卡
tab1, tab2, tab3 = st.tabs(["主题建模", "主题可视化", "主题评估"])

# 主题建模选项卡
with tab1:
    st.header("主题建模")
    
    # 参数设置
    with st.expander("参数设置", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            num_topics = st.slider("主题数量", 2, 20, 5)
            min_topic_size = st.slider("最小主题大小", 2, 20, 5)
        
        with col2:
            embedding_model = st.selectbox(
                "嵌入模型",
                ["paraphrase-multilingual-MiniLM-L12-v2", "distiluse-base-multilingual-cased"]
            )
            
            stopwords_file = st.file_uploader("停用词文件 (可选)", type=["txt"])
    
    # 加载停用词
    if stopwords_file:
        stopwords = []
        for line in stopwords_file:
            stopwords.append(line.decode("utf-8").strip())
        analyzer.load_stopwords(stopwords)
    else:
        analyzer.load_stopwords()
    
    # 开始分析按钮
    if st.button("开始主题分析"):
        # 加载文件内容
        texts = []
        file_names = []
        
        with st.spinner("正在加载文件内容..."):
            for file in files:
                file_path = os.path.join(files_dir, file)
                content = get_file_content(file_path)
                if content:
                    texts.append(content)
                    file_names.append(file)
        
        if not texts:
            st.error("没有可用的文本内容")
        else:
            with st.spinner("正在进行主题建模，这可能需要几分钟..."):
                try:
                    # 训练模型
                    topics, topic_info = analyzer.fit_transform(
                        texts, 
                        n_topics=num_topics,
                        min_topic_size=min_topic_size,
                        embedding_model_name=embedding_model
                    )
                    
                    # 获取主题词
                    topic_words = analyzer.get_topic_words()
                    
                    # 获取文档主题
                    doc_topics = analyzer.get_document_topics()
                    
                    # 保存结果
                    results = {
                        "topic_info": topic_info.to_dict() if topic_info is not None else None,
                        "topic_words": topic_words,
                        "doc_topics": doc_topics,
                        "file_names": file_names,
                        "params": {
                            "num_topics": num_topics,
                            "min_topic_size": min_topic_size,
                            "embedding_model": embedding_model
                        }
                    }
                    
                    with open(bertopic_results_path, 'w', encoding='utf-8') as f:
                        json.dump(results, f, ensure_ascii=False, indent=2)
                    
                    st.success("主题分析完成")
                    
                    # 显示主题词
                    st.subheader("主题关键词")
                    
                    for topic_id, words in topic_words.items():
                        st.write(f"**主题 {topic_id}**: " + ", ".join([f"{word} ({weight})" for word, weight in words]))
                    
                    # 显示文档主题分布
                    st.subheader("文档主题分布")
                    
                    doc_topic_df = pd.DataFrame(doc_topics)
                    doc_topic_df["文件名"] = [file_names[i] for i in doc_topic_df["document_id"]]
                    doc_topic_df = doc_topic_df[["文件名", "topic_id"]]
                    doc_topic_df.columns = ["文件名", "主题ID"]
                    
                    st.dataframe(doc_topic_df)
                    
                except Exception as e:
                    st.error(f"主题分析失败: {str(e)}")

# 主题可视化选项卡
with tab2:
    st.header("主题可视化")
    
    # 检查是否有分析结果
    if not os.path.exists(bertopic_results_path):
        st.info("请先在主题建模选项卡中进行主题分析")
    else:
        # 加载分析结果
        with open(bertopic_results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # 显示可视化选项
        viz_type = st.radio(
            "选择可视化类型",
            ["主题分布", "主题词云", "主题网络"]
        )
        
        if viz_type == "主题分布":
            # 创建主题分布图
            if "doc_topics" in results and results["doc_topics"]:
                doc_topics = results["doc_topics"]
                file_names = results["file_names"]
                
                # 计算每个主题的文档数量
                topic_counts = {}
                for doc in doc_topics:
                    topic_id = doc["topic_id"]
                    if topic_id == -1:
                        topic_label = "噪声"
                    else:
                        topic_label = f"主题 {topic_id}"
                        
                    topic_counts[topic_label] = topic_counts.get(topic_label, 0) + 1
                
                # 创建数据框
                df = pd.DataFrame({
                    "主题": list(topic_counts.keys()),
                    "文档数量": list(topic_counts.values())
                })
                
                # 创建条形图
                fig = px.bar(
                    df, 
                    x="主题", 
                    y="文档数量", 
                    title="主题分布",
                    color="主题"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示主题文档列表
                st.subheader("各主题文档列表")
                
                # 按主题分组显示文档
                for topic_id in set([doc["topic_id"] for doc in doc_topics]):
                    if topic_id == -1:
                        topic_label = "噪声主题"
                    else:
                        topic_label = f"主题 {topic_id}"
                    
                    st.write(f"**{topic_label}**")
                    
                    # 获取该主题的文档
                    topic_docs = [file_names[doc["document_id"]] for doc in doc_topics if doc["topic_id"] == topic_id]
                    
                    # 显示文档列表
                    for doc in topic_docs:
                        st.write(f"- {doc}")
                    
                    st.write("")
            else:
                st.warning("没有可用的主题分布数据")
        
        elif viz_type == "主题词云":
            # 显示主题词云
            if "topic_words" in results and results["topic_words"]:
                topic_words = results["topic_words"]
                
                # 选择主题
                topic_ids = [int(tid) for tid in topic_words.keys()]
                selected_topic = st.selectbox("选择主题", topic_ids)
                
                # 创建词云
                if str(selected_topic) in topic_words:
                    words = topic_words[str(selected_topic)]
                    word_dict = {word: weight for word, weight in words}
                    
                    # 使用词云可视化
                    try:
                        # 创建词频字典
                        word_freq = {word: weight for word, weight in words}
                        
                        # 创建词云
                        from wordcloud import WordCloud
                        import matplotlib.pyplot as plt
                        from io import BytesIO
                        import base64
                        
                        wc = WordCloud(
                            font_path="simhei.ttf",  # 需要有中文字体
                            width=800,
                            height=400,
                            background_color="white",
                            max_words=100
                        )
                        
                        wc.generate_from_frequencies(word_freq)
                        
                        # 显示词云
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wc, interpolation='bilinear')
                        ax.axis("off")
                        ax.set_title(f"主题 {selected_topic} 词云")
                        
                        st.pyplot(fig)
                        
                        # 显示主题词列表
                        st.subheader(f"主题 {selected_topic} 关键词")
                        
                        # 创建关键词表格
                        word_df = pd.DataFrame(words, columns=["词语", "权重"])
                        st.dataframe(word_df)
                        
                    except Exception as e:
                        st.error(f"创建词云失败: {str(e)}")
                        
                        # 显示词表
                        st.write(f"主题 {selected_topic} 关键词:")
                        for word, weight in words:
                            st.write(f"- {word}: {weight}")
                else:
                    st.warning(f"主题 {selected_topic} 没有可用的词语数据")
            else:
                st.warning("没有可用的主题词数据")
        
        elif viz_type == "主题网络":
            st.info("主题网络可视化需要使用BERTopic的内置功能，请先在主题建模选项卡中进行分析")
            
            # 如果模型已经训练，显示主题网络
            if hasattr(analyzer, 'model') and analyzer.model is not None:
                try:
                    # 使用BERTopic的可视化功能
                    fig = analyzer.visualize_topics()
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"主题网络可视化失败: {str(e)}")
            else:
                st.warning("请先在主题建模选项卡中进行分析")

# 主题评估选项卡
with tab3:
    st.header("主题评估")
    
    # 主题数量评估
    st.subheader("主题数量评估")
    
    # 参数设置
    min_topics = st.slider("最小主题数", 2, 10, 2)
    max_topics = st.slider("最大主题数", 5, 30, 20)
    step = st.slider("步长", 1, 5, 2)
    
    if st.button("评估主题数量"):
        # 加载文件内容
        texts = []
        
        with st.spinner("正在加载文件内容..."):
            for file in files:
                file_path = os.path.join(files_dir, file)
                content = get_file_content(file_path)
                if content:
                    texts.append(content)
        
        if not texts:
            st.error("没有可用的文本内容")
        else:
            with st.spinner("正在评估主题数量，这可能需要几分钟..."):
                try:
                    # 评估主题数量
                    fig, df = analyzer.evaluate_topics(
                        texts, 
                        topic_range=(min_topics, max_topics, step)
                    )
                    
                    if fig is not None:
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 显示评估结果表格
                        st.subheader("评估结果")
                        st.dataframe(df)
                        
                        # 找出最佳主题数
                        best_num_topics = df.loc[df["一致性得分"].idxmax(), "主题数量"]
                        st.success(f"根据一致性得分，建议的主题数量为: {best_num_topics}")
                    else:
                        st.error("主题数量评估失败")
                except Exception as e:
                    st.error(f"主题数量评估失败: {str(e)}")
    
    # 主题相似度分析
    st.subheader("主题相似度分析")
    
    if hasattr(analyzer, 'model') and analyzer.model is not None:
        similarity_threshold = st.slider("相似度阈值", 0.5, 0.9, 0.7, 0.05)
        
        if st.button("分析主题相似度"):
            with st.spinner("正在分析主题相似度..."):
                try:
                    # 查找相似主题
                    similar_topics = analyzer.find_similar_topics(threshold=similarity_threshold)
                    
                    if similar_topics:
                        st.subheader("相似主题对")
                        
                        # 创建相似主题表格
                        similar_df = pd.DataFrame(similar_topics, columns=["主题1", "主题2", "相似度"])
                        st.dataframe(similar_df)
                        
                        # 显示合并建议
                        st.subheader("合并建议")
                        st.write("以下主题可能需要合并:")
                        
                        for t1, t2, sim in similar_topics:
                            st.write(f"- 主题 {t1} 和主题 {t2} (相似度: {sim:.4f})")
                    else:
                        st.info(f"没有找到相似度高于 {similarity_threshold} 的主题对")
                except Exception as e:
                    st.error(f"主题相似度分析失败: {str(e)}")
    else:
        st.info("请先在主题建模选项卡中进行分析")

# 页脚
st.markdown("---")
st.markdown("内容分析工具 © 2023") 