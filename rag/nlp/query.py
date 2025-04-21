from rag.nlp.search import SearchEngine

class QueryProcessor:
    def __init__(self, search_engine):
        """ 初始化查询处理器 """
        self.search_engine = search_engine

    def search(self, query_text, top_k=3):
        """
        解析查询，并调用搜索引擎
        """
        search_results = self.search_engine.search(query_text, top_k)
        formatted_results = []

        if not search_results:
            print(f"❌ `{query_text}` 查询结果为空！")
            return []

        for res in search_results:
            if not isinstance(res["相关内容"], list):
                print(f"⚠️ `相关内容` 不是列表，修正格式: {res}")
                res["相关内容"] = [(res["相关内容"], res["搜索分数"])]  # ✅ **修正为元组列表**

            relevant_sentences = "\n - ".join([
                f"({round(sent[1], 2)}) {sent[0]}" if isinstance(sent, tuple) else f"(未知) {sent}"
                for sent in res["相关内容"]
            ])

            formatted_results.append({
                "文件": res["文件"],
                "搜索分数": res["搜索分数"],
                "相关内容": relevant_sentences
            })

        if not formatted_results:
            print(f"❌ 查询 `{query_text}` 没有找到任何相关内容！（但 `search_results` 不为空）")

        return formatted_results




if __name__ == "__main__":
    search_engine = SearchEngine(score_threshold=0.5)  # 只返回相关性大于 0.5 的
    query_processor = QueryProcessor(search_engine)

    queries = [
        "毕业论文"
    ]

    for q in queries:
        print(f"\n🔍 查询: {q}")
        results = query_processor.search(q, top_k=3)

        if not results:
            print(f"❌ 查询 `{q}` 没有找到任何相关内容！（但 `search_results` 不为空）")
            continue

        for idx, res in enumerate(results, 1):
            print(f"{idx}. 文件: {res['文件']} (分数: {res['搜索分数']})")
            print(f"   相关内容:\n - {res['相关内容']}\n")


