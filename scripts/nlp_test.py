# -*- coding: utf-8 -*-
import os
from rag.nlp.query import QueryProcessor
from rag.nlp.search import SearchEngine



# ========== 2. 初始化搜索引擎 ==========
search_engine = SearchEngine()

# ========== 3. 初始化查询处理器 ==========
query_processor = QueryProcessor(search_engine)

# ========== 4. 测试查询 ==========
queries = [
    "外语要求",
    "人工智能创意赛",
    "英文标题",
    "写作规范",
    "推免生的基本条件",
    "接诉即办平台",
]

print("\n🎯 **NLP 测试开始** 🎯")
for q in queries:
    print(f"\n🔍 **查询:** {q}")
    results = query_processor.search(q, top_k=3)
    for idx, (doc, score) in enumerate(results, 1):
        print(f"  {idx}. {doc}  (相关性: {score:.4f})")

print("\n✅ **NLP 测试完成！** ✅")
