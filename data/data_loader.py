# -*- coding: utf-8 -*-
import os
import json
from tqdm import tqdm
from data.parser import PdfParser, DocxParser, ExcelParser, PptParser, HtmlParser

# 原始政策文件目录
POLICY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "policy")
# 解析后的数据存储路径
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "rag", "res", "processed_policies.json")

# 确保存储目录存在
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# 解析器映射
PARSERS = {
    ".pdf": PdfParser(),
    ".docx": DocxParser(),
    ".xlsx": ExcelParser(),
    ".pptx": PptParser(),
    ".html": HtmlParser(),
}


def load_existing_data():
    """加载已解析的 JSON 数据，避免重复处理"""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_json(data):
    """存储 JSON 数据"""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def process_policy_file(file_path):
    """根据文件类型选择合适的解析器"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in PARSERS:
        print(f"❌ 跳过不支持的文件: {file_path}")
        return None

    parser = PARSERS[ext]

    try:
        # 处理 PDF、DOCX、PPTX、HTML 文件（解析结果为 `tuple`）
        if ext in [".pdf", ".docx", ".pptx", ".html"]:
            text_content, tables = parser(file_path)
            return {
                "file_name": os.path.basename(file_path),
                "text": text_content,
                "tables": tables
            }

        # 处理 Excel 文件（解析结果为 `list`）
        elif ext == ".xlsx":
            parsed_result = parser(file_path)

            # 处理 Excel 数据：区分文本数据和表格数据
            if isinstance(parsed_result, list):
                # 如果 `parsed_result` 只有一张表，直接存储
                if len(parsed_result) == 1:
                    text_content = ""
                    tables = parsed_result  # Excel 解析结果直接存入 `tables`
                else:
                    text_content = "\n".join([" ".join(row) for row in parsed_result if isinstance(row, list)])
                    tables = parsed_result  # 存储完整表格数据

                return {
                    "file_name": os.path.basename(file_path),
                    "text": text_content,
                    "tables": tables
                }

            else:
                print(f"⚠️ Excel 解析返回未知格式: {type(parsed_result)}，请检查 `ExcelParser` 的实现。")
                return None

    except Exception as e:
        print(f"⚠️ 解析失败: {file_path}, 错误: {e}")
        return None


def process_policy_files():
    """批量处理 `data/policy/` 目录下的政策文件"""
    print("📂 正在加载政策文件...")

    existing_data = load_existing_data()
    new_data = {}

    for root, _, files in os.walk(POLICY_DIR):
        for file in tqdm(files, desc="解析政策文件"):
            file_path = os.path.join(root, file)
            if file in existing_data:  # 避免重复解析
                continue

            parsed_data = process_policy_file(file_path)
            if parsed_data:
                new_data[file] = parsed_data

    if new_data:
        existing_data.update(new_data)
        save_json(existing_data)
        print(f"✅ 解析完成！共新增 {len(new_data)} 条政策数据。")
    else:
        print("✅ 没有新文件需要解析，所有政策数据已是最新！")


if __name__ == "__main__":
    process_policy_files()
