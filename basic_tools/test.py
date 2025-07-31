from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
import numpy as np

texts = [
    "我喜欢吃苹果",
    "苹果很好吃",
    "我今天去了超市买水果",
    "我喜欢吃香蕉",
    "我爱看电影",
    "昨晚看了一部恐怖片",
    "电影真不错"
]

# 1. 文本向量化
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')  # 中文可用 `paraphrase-multilingual-MiniLM-L12-v2`
embeddings = model.encode(texts)

# 2. 聚类（假设你知道有多少类），也可以自动估计
n_clusters = 3  # 可根据需要改
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
labels = kmeans.fit_predict(embeddings)

# 3. 输出结果
from collections import defaultdict

clusters = defaultdict(list)
for text, label in zip(texts, labels):
    clusters[label].append(text)

for cluster_id, cluster_texts in clusters.items():
    print(f"Cluster {cluster_id}:")
    for text in cluster_texts:
        print(f" - {text}")