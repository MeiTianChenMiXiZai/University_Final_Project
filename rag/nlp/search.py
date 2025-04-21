import os
import json
import re
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from rag.nlp import rag_tokenizer, term_weight

# **修正政策文件路径**
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POLICY_FILE = os.path.join(BASE_DIR, "res", "processed_policies.json")


def keyword_match_score(query_tokens, text):
    """
    计算关键词匹配得分：
    - 直接匹配的关键词得分高
    - 2 字匹配 4 字的情况，也给予额外的加权
    """
    text_tokens = set(rag_tokenizer.tokenize(text).split())  # 分词后的文本
    match_count = len(query_tokens & text_tokens)  # 直接匹配词的数量

    # ✅ 额外匹配 2 字词 -> 4 字词的情况
    for query in query_tokens:
        if len(query) == 2:  # 仅处理 2 字词
            for word in text_tokens:
                if len(word) == 4 and query in word:  # 检查 2 字是否在 4 字词中
                    match_count += 1  # 额外加 1 分

    return match_count / max(len(query_tokens), 1)  # 归一化，防止除 0 错误

class SearchEngine:
    def __init__(self, dim=300, score_threshold=0.5):
        """
        初始化搜索引擎，加载 JSON 格式的政策文档，并使用 FAISS + BM25 进行检索
        """
        self.dim = dim
        self.tw = term_weight.Dealer()
        self.score_threshold = score_threshold  # 设定最低分数阈值

        # 加载 JSON 政策文档
        self.documents = self.load_policy_documents()

        if self.documents:  # ✅ 仅在 documents 非空时初始化 BM25
            tokenized_corpus = [rag_tokenizer.tokenize(self.get_clean_text(doc)).split() for doc in self.documents]
            self.bm25 = BM25Okapi(tokenized_corpus)
        else:
            self.bm25 = None  # ✅ BM25 未初始化

        # 初始化 FAISS
        if self.documents:  # ✅ 仅在 documents 非空时初始化 FAISS
            self.faiss_index = faiss.IndexFlatL2(dim)
            self.build_faiss_index()
        else:
            self.faiss_index = None  # ✅ FAISS 未初始化


    def load_policy_documents(self):
        """从 `processed_policies.json` 加载解析后的政策数据"""
        if not os.path.exists(POLICY_FILE):
            print(f"❌ 错误：政策文件 {POLICY_FILE} 不存在！")
            return []

        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = []
        for doc_name, doc_data in data.items():
            text_chunks = doc_data.get("text_chunks", [])
            if text_chunks:
                docs.append({"name": doc_name, "text_chunks": text_chunks})
        return docs

    def get_clean_text(self, doc):
        """提取 `text_chunks` 里的纯文本，去掉 `@@页码 坐标信息##`"""
        text_chunks = doc.get("text_chunks", [])
        clean_texts = []
        for chunk in text_chunks:
            match = re.search(r"^(.*?)(@@-?\d+\t.*?##)?$", chunk)  # 改进正则，避免误删数据
            clean_texts.append(match.group(1) if match else chunk)
        return "\n".join(clean_texts) if clean_texts else ""

    def extract_relevant_sentences(self, chunk, next_chunk, query, context_size=3):
        """
        1. **如果 `chunk` 结尾不是 `##`，就合并 `next_chunk` 的 `@@坐标##`**
        2. **去掉 `chunk` 开头的 `@@坐标##`**
        3. **返回匹配句子，并附带前后一句**
        """
        query_tokens = set(rag_tokenizer.tokenize(query).split())
        best_sentences = []
        sentence_list = []

        # **去掉 `chunk` 开头的 `@@坐标##`**
        chunk = re.sub(r"^(@@\d+\t[\d\.]+\t[\d\.]+\t[\d\.]+\t[\d\.]+##)\s*", "", chunk)

        # **如果 `chunk` 结尾不是 `##`，尝试合并 `next_chunk` 的 `@@坐标##`**
        if not chunk.strip().endswith("##") and next_chunk:
            match = re.match(r"^(@@\d+\t[\d\.]+\t[\d\.]+\t[\d\.]+\t[\d\.]+##)\s*", next_chunk)
            if match:
                extra_coordinates = match.group(1)
                chunk += f" {extra_coordinates}"  # **追加坐标数据**

        # **按句号/感叹号/问号分割句子**
        sentences = re.split(r"(?<=[。！？])", chunk)  # ✅ 句号后正确分割
        sentence_list.extend([s.strip() for s in sentences if s.strip()])

        # **遍历句子，匹配关键词**
        for idx, sentence in enumerate(sentence_list):
            chunk_tokens = set(rag_tokenizer.tokenize(sentence).split())

            # **计算关键词匹配比例**
            intersection = query_tokens & chunk_tokens
            score = len(intersection) / len(query_tokens)

            if score > 0:
                # **确保前后句子完整**
                start_idx = max(0, idx - context_size)
                end_idx = min(len(sentence_list), idx + context_size + 1)

                # **额外增加前后句**
                extra_start = max(0, start_idx - 1)  # ✅ 额外前一句
                extra_end = min(len(sentence_list), end_idx + 1)  # ✅ 额外后一句

                # **确保 `@@坐标##` 数据也包括在前后文中**
                context_text = " ".join(sentence_list[extra_start:extra_end])

                best_sentences.append((context_text, score))

        # **按匹配度排序**
        return sorted(best_sentences, key=lambda x: x[1], reverse=True)

    def build_faiss_index(self):
        """构建 FAISS 向量索引"""
        embeddings = []
        for doc in self.documents:
            all_text = " ".join(doc["text_chunks"])
            tokens = rag_tokenizer.tokenize(all_text).split()
            doc_vector = [weight for _, weight in self.tw.weights(tokens)]

            if len(doc_vector) < self.dim:
                doc_vector = np.pad(doc_vector, (0, self.dim - len(doc_vector)), mode='constant')
            else:
                doc_vector = np.array(doc_vector[:self.dim])

            embeddings.append(doc_vector.astype('float32'))

        if embeddings:
            self.doc_vectors = np.vstack(embeddings)
            self.faiss_index.add(self.doc_vectors)
            print(f"✅ FAISS 索引已构建，共 {len(self.documents)} 个文档")
        else:
            print("⚠️ 没有可用的文档向量，FAISS 可能无法返回结果。")
            self.doc_vectors = None

    def search(self, query_text, top_k=5):
        """
        结合 FAISS + BM25 进行检索，按“文段”打分，并返回 **最相关的句子**
        """
        query_tokens = set(rag_tokenizer.tokenize(query_text).split())

        # **改进：针对每个 text_chunk 计算 BM25 分数**
        all_chunks = []
        for doc in self.documents:
            for chunk in doc["text_chunks"]:
                all_chunks.append({"文件": doc["name"], "内容": chunk})

        bm25_corpus = [rag_tokenizer.tokenize(chunk["内容"]).split() for chunk in all_chunks]
        bm25 = BM25Okapi(bm25_corpus)
        bm25_scores = np.array(bm25.get_scores(query_tokens))

        # **针对每个 text_chunk 计算 FAISS 分数**
        chunk_vectors = []
        for chunk in all_chunks:
            tokens = rag_tokenizer.tokenize(chunk["内容"]).split()
            vector = [weight for _, weight in self.tw.weights(tokens)]

            # **确保向量长度一致**
            if len(vector) < self.dim:
                vector = np.pad(vector, (0, self.dim - len(vector)), mode='constant')
            else:
                vector = vector[:self.dim]

            chunk_vectors.append(vector)

        # **转换为 NumPy 数组，保证是二维数组**
        if chunk_vectors:
            chunk_vectors = np.array(chunk_vectors, dtype=np.float32)

            # ✅ **清空 FAISS 旧向量，避免 index 超出范围**
            if self.faiss_index.ntotal > 0:
                self.faiss_index.reset()

            self.faiss_index.add(chunk_vectors)

            query_vector = np.array([weight for _, weight in self.tw.weights(query_tokens)]).astype('float32')
            query_vector = np.pad(query_vector, (0, self.dim - len(query_vector)), mode='constant') if len(
                query_vector) < self.dim else query_vector[:self.dim]
            query_vector = query_vector.reshape(1, -1)

            _, faiss_indices = self.faiss_index.search(query_vector, top_k)
            faiss_scores = np.zeros(len(all_chunks))

            # ✅ **检查索引范围，避免 `IndexError`**
            for rank, idx in enumerate(faiss_indices[0]):
                if idx < len(all_chunks):
                    faiss_scores[idx] = 1 / (rank + 1)
        else:
            faiss_scores = np.zeros(len(all_chunks))

        # **计算关键词匹配比例**
        keyword_match_scores = np.array([
            keyword_match_score(query_tokens, chunk["内容"])  # ✅ 改进匹配逻辑
            for chunk in all_chunks
        ])

        # **最终得分 = BM25 + FAISS + 关键词匹配**
        hybrid_scores = 0.5 * bm25_scores + 0.3 * faiss_scores + 0.2 * keyword_match_scores

        # **按“文段”得分排序**
        results = []
        top_indices = np.argsort(hybrid_scores)[::-1][:top_k]

        for i in top_indices:
            file_name = all_chunks[i]["文件"]
            chunk_text = all_chunks[i]["内容"]

            # **只传 i 和 i+1**
            next_chunk = all_chunks[i + 1]["内容"] if i + 1 < len(all_chunks) else None
            relevant_sentences = self.extract_relevant_sentences(chunk_text, next_chunk, query_text, context_size=1)

            # 取匹配度最高的句子
            if relevant_sentences:
                best_match = relevant_sentences[0][0]  # 取第一个匹配句子
            else:
                best_match = chunk_text  # 如果 `extract_relevant_sentences` 没有找到合适句子，直接返回 chunk_text

            results.append({
                "文件": file_name,
                "相关内容": [(best_match, hybrid_scores[i])],  # ✅ **存成列表，确保正确格式**
                "搜索分数": round(hybrid_scores[i], 3)
            })

        if not results:
            print("❌ 没有找到匹配内容，可能是 `score_threshold` 过高或数据问题。")

        return results



