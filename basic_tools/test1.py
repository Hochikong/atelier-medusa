import os
import json
from copy import deepcopy
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import hdbscan
import umap
import matplotlib.pyplot as plt
from sklearn.metrics import pairwise_distances_argmin_min
import warnings

warnings.filterwarnings("ignore")

import re


def clean(text):
    text = re.sub(r'http\S+|www\.\S+', '', text)  # 去链接
    text = re.sub(r'@\w+', '', text)  # 去@用户名
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)  # 只保留中英文+数字
    return text.strip()


# -------------------------------------------------
# 1. 准备文本（可换成你的列表 / 文件）
# -------------------------------------------------
with open('test_titles.txt', 'r', encoding='utf-8') as f:
    sentences = [line.strip() for line in f.readlines()]
old_sentences = deepcopy(sentences)
sentences = [clean(s) for s in sentences]

# -------------------------------------------------
# 2. 向量化
# -------------------------------------------------
print("加载模型并编码句子...")
model = SentenceTransformer(r'C:\Users\ckhoi\PycharmProjects\atelier-medusa\models\sentence-transformers\paraphrase-multilingual-MiniLM-L12-v2')
embeddings = model.encode(sentences, normalize_embeddings=True, show_progress_bar=True)

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
    metric='euclidean',
    cluster_selection_method='eom'
)
labels = clusterer.fit_predict(embeddings)

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

# 保存
os.makedirs("output", exist_ok=True)
df.to_csv("output/cluster_result.csv", index=False, encoding="utf-8-sig")


# 每个簇挑一个最接近中心的句子做“代表句”
def find_representative(sent_vec, cluster_vec):
    center = cluster_vec.mean(axis=0).reshape(1, -1)
    closest, _ = pairwise_distances_argmin_min(center, cluster_vec, metric='cosine')
    return closest[0]


representatives = []
for c in sorted(df['cluster'].unique()):
    if c == -1:
        continue  # 噪声
    sub = df[df['cluster'] == c]
    idx = find_representative(
        sub['sentence'].tolist(),
        embeddings[sub.index]
    )
    representatives.append({
        "cluster_id": int(c),
        "representative": sub.iloc[idx]['sentence'],
        "size": len(sub)
    })
with open("output/cluster_representatives.json", "w", encoding="utf-8") as f:
    json.dump(representatives, f, ensure_ascii=False, indent=2)

# -------------------------------------------------
# 6. 可视化（2D）
# -------------------------------------------------
plt.figure(figsize=(10, 8))
scatter = plt.scatter(
    umap_embeddings[:, 0],
    umap_embeddings[:, 1],
    c=labels,
    s=30,
    cmap='Spectral',
    alpha=0.7
)
plt.title(f"HDBSCAN 聚类结果（向量降维后）\n共{n_clusters}簇")
plt.colorbar(scatter, ticks=sorted(set(labels)))
plt.savefig("output/cluster_plot.png", dpi=300)
plt.show()

import streamlit as st

df = pd.read_csv("output/cluster_result.csv")
coords = np.load("output/umap_coords.npy")  # 提前保存

st.title("文本聚类交互可视化")
st.scatter_chart(pd.DataFrame({"x": coords[:, 0], "y": coords[:, 1], "cluster": df["cluster"]}), x="x", y="y",
                 color="cluster")

sel_cluster = st.selectbox("选择簇", sorted(df["cluster"].unique()))
st.write(df[df["cluster"] == sel_cluster])