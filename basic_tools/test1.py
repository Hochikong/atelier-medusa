import os
import json
import sys
from copy import deepcopy
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import hdbscan
import umap
import matplotlib.pyplot as plt
from sklearn.metrics import pairwise_distances_argmin_min
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import normalize
import warnings

warnings.filterwarnings("ignore")

import re


def clean(text):
    text = re.sub(r'http\S+|www\.\S+', '', text)  # 去链接
    text = re.sub(r'@\w+', '', text)  # 去@用户名
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)  # 只保留中英文+数字
    return text.strip()




def tidy1(text):
    # 1. 转换为小写
    text = text.lower()
    # 2. 移除常见的版本/语言/翻译组标记 (使用正则表达式)
    # 示例模式，可能需要根据你数据的实际情况进行调整和扩展
    # 匹配 (Cx) 形式的版本号，如 (C103)
    text = re.sub(r'\(c\d+\)', '', text)
    # 匹配 [语言] 标记，如 [Chinese], [English]
    text = re.sub(r'\[\s*(chinese|english|japanese|digital)\s*\]', '', text)
    # 匹配 [翻译组名称] 或其他方括号内的辅助信息，如 [無邪気漢化組], [WataTL & head empty]
    # 注意：这个正则可能会移除一些核心内容，需要谨慎调整
    text = re.sub(r'\[.*?\]', '', text)  # 移除所有方括号及其内容，这可能有点激进
    # 更好的方式是针对性地移除已知的翻译组/发布者信息
    # text = re.sub(r'\[(無邪気漢化組|watatl & head empty|lin chengyu|decensored|digital|various).*?\]', '', text) # 更多示例，根据实际数据添加
    # 3. 移除作者/社团信息 (括号内的，如 [Ringoya (Alp)] 或 [Alp])
    # 这部分可能需要更复杂的逻辑，因为有些作者名是核心内容
    # 如果作者名在方括号内且是固定的模式，可以尝试移除
    # 示例：移除 [Ringoya (各种)] 或 [Nekochiwawa. (Alp)] 这样的模式
    # text = re.sub(r'\[.*?\(.*?\).*?\]', '', text) # 这会移除所有包含 () 的方括号，可能误伤
    # 针对性移除：
    text = re.sub(r'\[\s*ringoya\s*\(alp\)\s*\]', '', text)
    text = re.sub(r'\[\s*ringoya\s*\(various\)\s*\]', '', text)
    text = re.sub(r'\[\s*nekochiwawa\.\s*\(alp\)\s*\]', '', text)
    text = re.sub(r'\[\s*alp\s*\]', '', text)  # 移除单独的 [Alp]
    # 4. 移除多余的空格和标点符号，并进行精简
    text = re.sub(r'\s+', ' ', text)  # 将多个空格替换为一个空格
    text = re.sub(r'[^\w\s\(\)!？，。、]', '', text)  # 移除大部分标点符号，保留括号和一些常见符号
    text = text.strip()
    # 5. 特殊处理：移除标题末尾的重复或冗余信息
    # 例如："C103 Omakebon (Love Live! Nijigasaki High School Idol Club)"
    # 如果它后面跟着一样的括号内容，也移除
    # 需要更复杂的逻辑，可能需要匹配标题的特定部分

    return text

def tidy(line: str) -> str:
    # 先把两对括号统一成空格
    line = re.sub(r"[\[\]\(\)\{\}\-\–]", " ", line)
    # 连续空格→1个
    line = re.sub(r"\s{2,}", " ", line.strip())
    return line

# -------------------------------------------------
# 1. 准备文本（可换成你的列表 / 文件）
# -------------------------------------------------
with open('test_titles.txt', 'r', encoding='utf-8') as f:
    sentences = [line.strip() for line in f.readlines()]
old_sentences = deepcopy(sentences)
sentences = [tidy1(s) for s in sentences]

# -------------------------------------------------
# 2. 向量化
# -------------------------------------------------
print("加载模型并编码句子...")
model = SentenceTransformer(r'C:\Users\ckhoi\PycharmProjects\atelier-medusa\models\sentence-transformers\paraphrase-multilingual-MiniLM-L12-v2')
embeddings = model.encode(sentences, normalize_embeddings=True, show_progress_bar=True)
cosine_distance_matrix = pairwise_distances(embeddings, metric='cosine')
cosine_distance_matrix = cosine_distance_matrix.astype(np.float64)


# -------------------------------------------------
# 3. 降维（仅用于可视化，可选）
# -------------------------------------------------
umap_reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric='cosine', random_state=42)
umap_embeddings = umap_reducer.fit_transform(embeddings)

# -------------------------------------------------
# 4. 聚类
# -------------------------------------------------
print("使用 HDBSCAN 聚类...")
clusterer = hdbscan.HDBSCAN(
    min_cluster_size=2,  # 可按数据量调大/调小
    min_samples=1,  # 建议 >=1
    metric='precomputed',
    cluster_selection_method='eom',
)
labels = clusterer.fit_predict(cosine_distance_matrix)

n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
print(f"自动聚成了 {n_clusters} 个簇")


# -------------------------------------------------
# 5. 输出结果
# -------------------------------------------------
df = pd.DataFrame({
    "sentence": sentences,
    "old_sentence": old_sentences,
    "cluster": labels,
})
df.sort_values(by=['cluster'], inplace=True)
df.to_excel('a1.xlsx', index=False)

# 保存
os.makedirs("output", exist_ok=True)
df.to_csv("output/cluster_result.csv", index=False, encoding="utf-8-sig")


