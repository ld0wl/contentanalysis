import numpy as np
import pandas as pd
import jieba
import logging
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import base64

# 设置日志
logging.basicConfig(
    filename='error_log.txt',
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class BERTopicAnalyzer:
    def __init__(self, language="chinese"):
        self.language = language
        self.model = None
        self.topics = None
        self.topic_info = None
        self.stopwords = set()
        self.embedding_model = None
        
    def load_stopwords(self, stopwords_file=None):
        """加载停用词"""
        self.stopwords = set()
        
        # 加载默认停用词
        default_stopwords = [
            "的", "了", "和", "是", "在", "我", "有", "这", "个", "们",
            "中", "也", "为", "以", "到", "说", "着", "对", "那", "你",
            "就", "与", "而", "使", "向", "它", "等", "但", "被", "所",
            "如", "于", "由", "上", "下", "之", "或", "时", "都", "要"
        ]
        self.stopwords.update(default_stopwords)
        
        # 加载用户提供的停用词
        if stopwords_file:
            try:
                with open(stopwords_file, 'r', encoding='utf-8') as f:
                    user_stopwords = [line.strip() for line in f if line.strip()]
                    self.stopwords.update(user_stopwords)
            except Exception as e:
                logging.error(f"加载停用词文件失败: {str(e)}")
        
        return self.stopwords
    
    def preprocess_texts(self, texts):
        """预处理文本"""
        processed_texts = []
        
        for text in texts:
            if not text:
                processed_texts.append("")
                continue
                
            # 分词
            words = jieba.lcut(text)
            
            # 去除停用词
            filtered_words = [word for word in words if word not in self.stopwords and len(word) > 1]
            
            # 重新组合
            processed_text = " ".join(filtered_words)
            processed_texts.append(processed_text)
        
        return processed_texts
    
    def fit_transform(self, texts, n_topics=10, min_topic_size=5, embedding_model_name="paraphrase-multilingual-MiniLM-L12-v2"):
        """训练BERTopic模型"""
        try:
            # 预处理文本
            processed_texts = self.preprocess_texts(texts)
            
            # 加载嵌入模型
            self.embedding_model = SentenceTransformer(embedding_model_name)
            
            # 创建UMAP降维模型
            umap_model = UMAP(
                n_neighbors=15,
                n_components=5,
                min_dist=0.0,
                metric='cosine',
                random_state=42
            )
            
            # 创建聚类模型
            hdbscan_model = HDBSCAN(
                min_cluster_size=min_topic_size,
                metric='euclidean',
                cluster_selection_method='eom',
                prediction_data=True
            )
            
            # 创建向量化模型
            vectorizer_model = CountVectorizer(
                stop_words=list(self.stopwords) if self.language == "chinese" else None
            )
            
            # 创建BERTopic模型
            self.model = BERTopic(
                embedding_model=self.embedding_model,
                umap_model=umap_model,
                hdbscan_model=hdbscan_model,
                vectorizer_model=vectorizer_model,
                nr_topics=n_topics,
                verbose=True
            )
            
            # 训练模型
            self.topics, self.topic_info = self.model.fit_transform(processed_texts)
            
            return self.topics, self.topic_info
            
        except Exception as e:
            logging.error(f"训练BERTopic模型失败: {str(e)}")
            raise e
    
    def get_topic_info(self):
        """获取主题信息"""
        if not self.model or self.topic_info is None:
            return None
        
        return self.topic_info
    
    def get_topic_words(self, n_words=10):
        """获取每个主题的关键词"""
        if not self.model:
            return None
        
        topic_words = {}
        for topic_id in set(self.topics):
            if topic_id == -1:  # 噪声主题
                continue
                
            words = self.model.get_topic(topic_id)
            topic_words[topic_id] = [(word, round(weight, 4)) for word, weight in words[:n_words]]
        
        return topic_words
    
    def get_document_topics(self):
        """获取每个文档的主题分布"""
        if not self.model or self.topics is None:
            return None
        
        doc_topics = []
        for i, topic_id in enumerate(self.topics):
            doc_topics.append({
                "document_id": i,
                "topic_id": topic_id
            })
        
        return doc_topics
    
    def visualize_topics(self):
        """可视化主题"""
        if not self.model:
            return None
        
        try:
            # 使用BERTopic内置的可视化
            fig = self.model.visualize_topics()
            return fig
        except Exception as e:
            logging.error(f"可视化主题失败: {str(e)}")
            return None
    
    def visualize_barchart(self):
        """可视化主题分布条形图"""
        if not self.model or self.topics is None:
            return None
        
        try:
            # 计算每个主题的文档数量
            topic_counts = {}
            for topic in self.topics:
                if topic == -1:  # 噪声主题
                    topic_label = "噪声"
                else:
                    topic_label = f"主题 {topic}"
                    
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
            
            return fig
        except Exception as e:
            logging.error(f"可视化主题分布条形图失败: {str(e)}")
            return None
    
    def visualize_wordcloud(self, topic_id=None):
        """为特定主题创建词云"""
        if not self.model:
            return None
        
        try:
            if topic_id is not None:
                # 获取特定主题的词
                words = self.model.get_topic(topic_id)
                if not words:
                    return None
                    
                # 创建词频字典
                word_freq = {word: weight for word, weight in words}
                
                # 创建词云
                wc = WordCloud(
                    font_path="simhei.ttf",  # 需要有中文字体
                    width=800,
                    height=400,
                    background_color="white",
                    max_words=100
                )
                
                wc.generate_from_frequencies(word_freq)
                
                # 转换为图像
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wc, interpolation='bilinear')
                ax.axis("off")
                ax.set_title(f"主题 {topic_id} 词云")
                
                # 转换为base64
                buf = BytesIO()
                fig.savefig(buf, format="png")
                plt.close(fig)
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode()
                
                return img_str
            else:
                # 获取所有主题的词云
                topic_clouds = {}
                for topic_id in set(self.topics):
                    if topic_id == -1:  # 噪声主题
                        continue
                        
                    topic_cloud = self.visualize_wordcloud(topic_id)
                    if topic_cloud:
                        topic_clouds[topic_id] = topic_cloud
                
                return topic_clouds
                
        except Exception as e:
            logging.error(f"创建词云失败: {str(e)}")
            return None
    
    def evaluate_topics(self, texts, topic_range=(2, 20, 2)):
        """评估不同主题数量的效果"""
        try:
            # 预处理文本
            processed_texts = self.preprocess_texts(texts)
            
            # 创建临时模型
            temp_model = BERTopic(embedding_model=self.embedding_model)
            
            # 计算不同主题数量的一致性得分
            coherences = []
            topic_nums = list(range(topic_range[0], topic_range[1] + 1, topic_range[2]))
            
            for num_topics in topic_nums:
                temp_model.update_topics(processed_texts, topics=None, nr_topics=num_topics)
                coherence = temp_model.get_topic_coherence()
                coherences.append(coherence)
            
            # 创建评估图表
            df = pd.DataFrame({
                "主题数量": topic_nums,
                "一致性得分": coherences
            })
            
            fig = px.line(
                df, 
                x="主题数量", 
                y="一致性得分", 
                title="主题数量评估",
                markers=True
            )
            
            return fig, df
            
        except Exception as e:
            logging.error(f"评估主题数量失败: {str(e)}")
            return None, None
    
    def find_similar_topics(self, threshold=0.7):
        """查找相似的主题"""
        if not self.model:
            return None
        
        try:
            # 获取主题嵌入
            topic_embeddings = self.model.topic_embeddings_
            
            # 计算主题间的相似度
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(topic_embeddings)
            
            # 查找相似主题对
            similar_topics = []
            for i in range(similarities.shape[0]):
                for j in range(i+1, similarities.shape[1]):
                    if similarities[i, j] > threshold:
                        similar_topics.append((i, j, similarities[i, j]))
            
            # 按相似度排序
            similar_topics.sort(key=lambda x: x[2], reverse=True)
            
            return similar_topics
            
        except Exception as e:
            logging.error(f"查找相似主题失败: {str(e)}")
            return None 