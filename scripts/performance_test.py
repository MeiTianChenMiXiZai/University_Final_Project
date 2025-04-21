import time
from rag.inference import extract_keywords, search_engine, engine, process_pdf_highlight

# 多个问题用于批量测试
test_questions = [
    "学生因病申请保留学籍的流程是什么？",
    "推免资格具体要求有哪些？",
    "国家奖学金评选标准是什么？",
    "什么时候可以申请转专业？需要满足什么条件？",
    "想要参与交换项目需满足哪些条件？",
    "平时成绩在课程总评成绩中占比是多少？",
    "一个学生可以同时获得多项奖学金吗？",
    "留学交换期间学分如何转换？"
]

def measure_time(func, *args, desc=""):
    start = time.time()
    result = func(*args)
    duration = time.time() - start
    return result, duration

def run_batch_performance_test():
    print("\n📊 批量测试开始，共{}个问题\n".format(len(test_questions)))
    for idx, question in enumerate(test_questions):
        print(f"=== 测试 {idx + 1}: {question} ===")

        # 🔹 关键词提取 + 同义词
        (keywords, synonyms), t1 = measure_time(extract_keywords, question, True)
        search_query = " ".join(set(keywords).union(*synonyms.values()))
        status_kw = "✅" if keywords else "❌"

        # 🔹 检索
        search_results, t2 = measure_time(search_engine.search, search_query, 5)
        status_search = "✅" if len(search_results) >= 1 else "❌"

        # 🔹 LLM生成
        answer, t3 = measure_time(engine.answer_question, question, search_results, False)
        status_llm = "✅" if answer else "❌"

        # 🔹 截图标注
        images, t4 = measure_time(
            process_pdf_highlight,
            "C:/Users/ROG/PycharmProjects/final/data/policy",
            answer.split("\n"),
            search_results,
            "C:/Users/ROG/PycharmProjects/final/ocr_results"
        )
        status_ocr = "✅" if images else "⚠️"

        total = t1 + t2 + t3 + t4

        print(f"关键词: {status_kw} ({t1:.2f}s) | 检索: {status_search} ({t2:.2f}s) | LLM: {status_llm} ({t3:.2f}s) | 截图: {status_ocr} ({t4:.2f}s) | 总计: {total:.2f}s\n")

if __name__ == "__main__":
    run_batch_performance_test()