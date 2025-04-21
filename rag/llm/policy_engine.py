import numpy as np
from typing import List


class PolicyQAEngine:
    def __init__(self, ollama_client):
        self.client = ollama_client
        self.document_vectors = None
        self.documents = []

    def answer_question(self, question: str, search_results: List[dict], stream: bool = False):
        """
        直接使用 RAG 搜索结果进行问答
        :param question: 用户问题
        :param search_results: RAG 搜索返回的政策文本
        :param stream: 是否流式输出
        """
        if not search_results:
            return "❌ 无法找到相关政策，请尝试更具体的问题。"

        # 格式化检索结果
        formatted_docs = "\n\n".join([
            f"📄 文件: {res['文件']} (相关性: {res['搜索分数']})\n" +
            "\n".join([f"({round(sent[1], 2)}) {sent[0]}" for sent in res["相关内容"]])
            for res in search_results
        ])

        # 组织 LLM 输入
        combined_question = (
            "### 背景信息：\n"
            f"{formatted_docs}\n\n"
            "### 用户问题：\n"
            f"{question}\n\n"
            "请基于提供的政策文件回答问题，并确保答案准确。"
        )

        # 让 DeepSeek 处理最终回答
        answer = self.client.generate_response(
            context=combined_question,
            question=question,
            stream=stream
        )

        return answer