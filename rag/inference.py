# -*- coding: utf-8 -*-
import os
import re

from rag.llm.config import OLLAMA_CONFIG
from rag.llm.ollama_client import OllamaClient
from rag.llm.policy_engine import PolicyQAEngine
from rag.nlp.search import SearchEngine
from rag.nlp import rag_tokenizer
from rag.match import process_pdf_highlight

# 初始化 RAG 组件
search_engine = SearchEngine(score_threshold=0.5)  # 设定最小相关性
client = OllamaClient(OLLAMA_CONFIG)
engine = PolicyQAEngine(client)


# **OCR 相关路径**
pdf_base_path = "C:/Users/ROG/PycharmProjects/final/data/policy"  # 存放政策文件的 PDF 目录
# output_dir = "C:/Users/ROG/PycharmProjects/final/rag/ocr_results"  # OCR 解析后的图片存放目录
output_dir = "C:/Users/ROG/PycharmProjects/final/ocr_results"  # OCR 解析后的图片存放目录

def filter_top_results(search_results):
    """
    选择最相关的文段：
    - 选取得分 >= 最高分的 50%（动态调整）
    - 避免选太少导致信息不全
    - 避免选太多导致 LLM 误解
    """
    if not search_results:
        return []

    max_score = max(result["搜索分数"] for result in search_results)
    threshold = max_score * 0.5 # 设定 50% 阈值

    filtered_results = [res for res in search_results if res["搜索分数"] >= threshold]

    print(f"🔎 **选取 {len(filtered_results)} 个相关文段 (阈值: {threshold:.3f})**")
    return filtered_results



def format_search_results(search_results):
    """
    格式化搜索结果，生成清晰的 LLM 输入
    """
    formatted_texts = []
    for result in search_results:
        doc_name = result["文件"]
        score = result["搜索分数"]
        sentences = "\n".join([f"({round(sent[1], 2)}) {sent[0]}" for sent in result["相关内容"]])

        formatted_text = f"📄 文件: {doc_name} (相关性: {score})\n{sentences}"
        formatted_texts.append(formatted_text)

    return "\n\n".join(formatted_texts)


def extract_keywords_nlp(question: str) -> tuple[list[str], dict[str, list[str]]]:
    """
    使用 NLP 规则提取关键词，并返回空的近义词字典
    - 关键词：使用 `rag_tokenizer` 进行分词
    - 近义词：为空字典 {}
    """
    text_tokens = set(rag_tokenizer.tokenize(question).split())  # 使用 rag_tokenizer 进行分词
    return list(text_tokens), {}  # NLP 版不提供近义词扩展

def extract_keywords(question: str, use_llm=True, retries=2) -> tuple[list[str], dict[str, list[str]]]:
    """
    提取搜索关键词，并进行近义词扩展：
    - `use_llm=True`：优先使用 LLM 提取关键词 + 近义词
    - `use_llm=False`：使用 NLP 规则分词
    - LLM 失败两次后，自动回退到 NLP
    """
    if use_llm:
        for attempt in range(retries):
            try:
                result = client.extract_keywords(question)  # LLM 提取关键词 + 近义词
                if isinstance(result, tuple) and len(result) == 2:
                    keywords, synonyms = result  # 确保返回格式正确
                    if isinstance(keywords, list) and isinstance(synonyms, dict):
                        return keywords, synonyms  # LLM 结果有效，返回

            except Exception as e:
                print(f"⚠️ LLM 第 {attempt + 1} 次关键词提取失败，错误: {e}，重新请求...")

        print("⚠️ LLM 连续失败，回退到 NLP 分词...")

    return extract_keywords_nlp(question)  # NLP 规则分词（回退方案）




def answer_policy_question(question, top_k=5):
    """
    1. 解析问题，提取关键词
    2. 使用 RAG 进行搜索
    3. 结合 LLM 生成答案
    4. 高亮匹配的政策内容
    """
    print(f"\n🔍 **原始查询:** {question}")

    # 获取关键词和近义词
    keywords, synonyms = extract_keywords(question, use_llm=True)

    # 关键词为空时，返回提示
    if not keywords:
        return {
            "raw_question": question,
            "error": "❌ 无法解析问题，请尝试更具体的提问。"
        }

    # 构造最终搜索 Query（包含近义词）
    expanded_query = set(keywords)
    for key, syns in synonyms.items():
        expanded_query.update(syns)

    search_query = " ".join(expanded_query)
    print(f"🔎 **优化后的搜索 Query:** {search_query}")

    search_results = search_engine.search(search_query, top_k)

    if not search_results:
        return {
            "raw_question": question,
            "optimized_query": search_query,
            "error": "❌ 未能找到相关政策，请尝试更具体的问题。"
        }

    print("\n📄 **搜索到政策内容:**")
    print(search_results)

    # 选取得分最高的 80% 以内的文段
    filtered_results = filter_top_results(search_results)

    # 格式化检索内容
    formatted_docs = format_search_results(filtered_results)
    print("\n📄 **最终用于回答的政策内容:**")
    print(formatted_docs)

    # 调用 LLM 生成回答
    raw_answer = engine.answer_question(question, filtered_results)

    print("\n📝 **思考回答:**")
    print(raw_answer)

    # 清理 LLM 输出，去掉 <think> 标签
    cleaned_answer = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.DOTALL).strip()
    print("\n📝 **最终回答:**")
    print(cleaned_answer)

    # 高亮匹配的政策内容
    referenced_texts = cleaned_answer.split("\n")
    matched_passages = process_pdf_highlight(pdf_base_path, referenced_texts, filtered_results, output_dir)

    return {
        "raw_question": question,
        "optimized_query": search_query,
        "sorted_results": search_results,
        "filtered_results": filtered_results,
        "llm_thinking": raw_answer,
        "final_answer": cleaned_answer,
        "reference_images": matched_passages
    }

'''
# **测试代码**
if __name__ == "__main__":
    test_questions = [
        "选修课程可以补考吗"
    ]

    for question in test_questions:
        answer, highlighted_info = answer_policy_question(question)
        print("\n🔍 **匹配到的政策内容:**")
        print(highlighted_info)

'''