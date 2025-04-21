from fastapi import APIRouter, WebSocket
import json
import re
from rag.inference import search_engine, engine, extract_keywords, filter_top_results, format_search_results
from rag.match import process_pdf_highlight

router = APIRouter()


@router.websocket("/ws/answer")
async def websocket_answer(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_text()
            question = data.strip()

            # 🔹 左侧显示用户原始提问
            await websocket.send_text(json.dumps({"type": "user_question", "message": question}))

            # 🔍 提取关键词
            keywords, synonyms = extract_keywords(question, use_llm=True)
            if not keywords:
                await websocket.send_text(json.dumps({"type": "error", "message": "❌ 无法解析问题，请尝试更具体的提问。"}))
                continue

            expanded_query = set(keywords)
            for key, syns in synonyms.items():
                expanded_query.update(syns)
            search_query = " ".join(expanded_query)

            # 🔍 推送优化搜索关键词
            await websocket.send_text(json.dumps({"type": "query_keywords", "message": search_query}))

            # 🔎 搜索排序
            results = search_engine.search(search_query, top_k=5)
            if not results:
                await websocket.send_text(json.dumps({"type": "error", "message": "❌ 没有找到相关政策"}))
                continue

            # 💡 清洗前端展示内容（删除坐标等，仅限展示用）
            cleaned_results = []
            for r in results:
                clean_r = {"文件": r["文件"], "搜索分数": r["搜索分数"], "相关内容": []}
                for c in r["相关内容"]:
                    text = re.sub(r"@@.*?##", "", c[0]).strip()
                    clean_r["相关内容"].append((text, c[1], c[2] if len(c) > 2 else ""))
                cleaned_results.append(clean_r)

            await websocket.send_text(json.dumps({"type": "search_results", "results": cleaned_results}))

            # ✨ 选定文段用于回答
            filtered = filter_top_results(results)
            formatted = format_search_results(filtered)
            await websocket.send_text(json.dumps({"type": "thinking", "message": "📄 已选定相关文段用于回答..."}))

            # 🧠 LLM 思考生成回答
            raw_answer = engine.answer_question(question, filtered)
            await websocket.send_text(json.dumps({"type": "thinking", "message": raw_answer}))

            # ✅ 清理标签后的最终回答
            cleaned = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.DOTALL).strip()

            # 🖼️ 高亮截图路径（先处理图片）
            matched_images = process_pdf_highlight(
                "data/policy", cleaned.split("\n"), filtered,
                output_dir="C:/Users/ROG/PycharmProjects/final/ocr_results"
            )

            # 🖼️ 插入引用标注（根据 matched_images 文件名提取页码插入）
            def insert_image_refs_by_filename(text, matched_images):
                from pathlib import Path
                image_ids = []
                for path in matched_images:
                    filename = Path(path).name
                    match = re.match(r"(\d+)_highlighted\.jpg", filename)
                    if match:
                        image_ids.append(int(match.group(1)))

                pattern = r"《(.*?)》"
                matches = list(re.finditer(pattern, text))
                for idx, match in enumerate(matches):
                    if idx < len(image_ids):
                        ref = f"《{match.group(1)}》[🖼️{image_ids[idx]}]"
                        text = text.replace(match.group(0), ref, 1)
                return text

            # 插入引用标注并发送回答
            cleaned_with_refs = insert_image_refs_by_filename(cleaned, matched_images)
            await websocket.send_text(json.dumps({"type": "answer", "message": cleaned_with_refs}))

            # 推送图片路径列表（前端可预览）
            await websocket.send_text(json.dumps({"type": "highlight", "images": matched_images}))


        except Exception as e:
            await websocket.send_text(json.dumps({"type": "error", "message": f"❌ 出现错误: {str(e)}"}))
            break
