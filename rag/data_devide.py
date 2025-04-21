# -*- coding: utf-8 -*-
import os
import json
import re
from tqdm import tqdm
from timeit import default_timer as timer
from io import BytesIO
from docx import Document
import pandas as pd
from data.parser import PdfParser, ExcelParser
from docx2pdf import convert
import os
from pathlib import Path


# 原始政策文件目录
POLICY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "policy")
# 解析后的数据存储路径
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "rag", "res", "processed_policies.json")

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "policy"

# 确保存储目录存在
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)


class Pdf(PdfParser):
    def __call__(self, filename, binary=None, from_page=0, to_page=100000, zoomin=3, callback=None):
        self.pdf_path = filename
        start = timer()
        if callback:
            callback(msg="OCR is running...")

        self.__images__(filename if not binary else binary, zoomin, from_page, to_page, callback)
        if callback:
            callback(msg="OCR finished")

        self._layouts_rec(zoomin)  # 版面分析
        self._table_transformer_job(zoomin)  # 表格转换
        self._text_merge()  # 文本合并
        tbls = self._extract_table_figure(True, zoomin, True, True)  # 提取表格 & 图像

        text_with_positions = []
        for b in self.boxes:
            text = b.get("text", "").strip()

            # **📌 修正 `page` 读取方式**
            page = b.get("page", b.get("page_number", -1))

            # **📌 修正 `y0, y1` 读取方式**
            x0 = b.get("x0", 0.0)
            y0 = b.get("y0", b.get("top", 0.0))
            x1 = b.get("x1", 0.0)
            y1 = b.get("y1", b.get("bottom", 0.0))


            pos_info = f"@@{page}\t{x0:.1f}\t{y0:.1f}\t{x1:.1f}\t{y1:.1f}##"
            text_with_positions.append(text + pos_info)

        return "\n".join(text_with_positions), tbls



# ========== 📌 Excel 解析==========
class Excel(ExcelParser):
    def __call__(self, filename, binary=None):
        df = pd.read_excel(filename if not binary else BytesIO(binary), sheet_name=None)
        tables = []

        for sheet_name, sheet in df.items():
            html = f"<h3>{sheet_name}</h3><table border='1'>"
            html += sheet.to_html(index=False, escape=False)
            html += "</table>"
            tables.append(html)

        return [], tables


# ========== 📌 文本切分（提升 RAG 检索能力） ==========
def chunk_text(text, chunk_size=128):
    """将文本切分为小段，提高 RAG 检索能力"""
    delimiters = re.compile(r"[!?。；！？]")
    sections = delimiters.split(text)
    chunks = []
    buffer = ""

    for sec in sections:
        if len(buffer) + len(sec) < chunk_size:
            buffer += sec
        else:
            chunks.append(buffer)
            buffer = sec
    if buffer:
        chunks.append(buffer)

    return chunks


def process_policy_file(file_path):
    """根据文件类型选择合适的解析器"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in [".pdf", ".xlsx"]:
        print(f"❌ 跳过不支持的文件: {file_path}")
        return None

    parser = {"pdf": Pdf(), "xlsx": ExcelParser()}.get(ext[1:])

    try:
        if ext == ".xlsx":
            parsed_result = parser(file_path)

            print(f"📌 DEBUG: `ExcelParser` 解析返回 -> {type(parsed_result)}, 值: {parsed_result}")

            if isinstance(parsed_result, tuple) and len(parsed_result) == 2:
                text_content, tables = parsed_result
            elif isinstance(parsed_result, list):
                text_content = ""
                tables = parsed_result
            elif isinstance(parsed_result, pd.DataFrame):
                text_content = ""
                tables = [parsed_result.to_html(index=False, escape=False)]
            else:
                print(f"⚠️ `ExcelParser` 返回未知格式: {type(parsed_result)}，请检查 `ExcelParser` 代码。")
                return None
        else:
            text_content, tables = parser(file_path)

        print(f"🔍 DEBUG: {file_path} 解析返回：{type(text_content)}, {type(tables)}")

        if text_content is None:
            print(f"⚠️ `PdfParser` 解析失败，未返回有效文本: {file_path}")
            return None

        if isinstance(text_content, str):
            # ✅ `Pdf` 解析后应该是 `str` 格式的文本
            text_lines = text_content.strip().split("\n")
        elif isinstance(text_content, list):
            # ✅ `Docx` 解析器可能返回 `list`
            text_lines = [t[0] if isinstance(t, tuple) else str(t) for t in text_content]
        else:
            print(f"⚠️ `text_content` 解析格式未知: {type(text_content)}")
            text_lines = []

        # ✅ 确保 `tables` 不是 `None`
        if not tables:
            tables = []

        # ✅ 保持 `text_chunks` 里带有位置信息
        return {
            "file_name": os.path.basename(file_path),
            "text_chunks": chunk_text("\n".join(text_lines)),  # ✅ 这里不会丢失位置信息
            "tables": tables
        }

    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        print(f"⚠️ 解析失败: {file_path}, 错误详情:\n{error_message}")
        return None




def convert_all_docx_to_pdf():
    """将 UPLOAD_DIR 中所有 docx 文件转换为 PDF"""
    docx_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".docx")]

    if not docx_files:
        print("✅ 没有需要转换的 Word 文件。")
        return

    for docx_file in docx_files:
        docx_path = str(UPLOAD_DIR / docx_file)
        try:
            print(f"🔄 正在转换: {docx_file}")
            convert(docx_path)
            print(f"✅ 转换完成: {docx_file}")
        except Exception as e:
            print(f"❌ 转换失败: {docx_file}, 错误: {e}")




# ========== 📌 处理所有政策文件 ==========

def process_policy_files():
    """🔄 先转换 `.docx`，再遍历 `.pdf` 和 `.xlsx` 解析"""
    print("📂 正在加载政策文件...")

    convert_all_docx_to_pdf()  # ✅ **先转换 Word**

    existing_data = load_existing_data()
    new_data = {}

    # **遍历目录，解析 `.pdf` 和 `.xlsx`**
    for root, _, files in os.walk(POLICY_DIR):
        for file in tqdm(files, desc="解析政策文件"):
            file_path = os.path.join(root, file)

            # ✅ **只处理 `.pdf` 和 `.xlsx`**
            if not file.endswith((".pdf", ".xlsx")):
                continue

            if file in existing_data:  # ✅ **避免重复解析**
                print(f"⏩ 跳过已解析文件: {file}")
                continue

            print(f"🔍 解析政策文件: {file}")
            parsed_data = process_policy_file(file_path)

            if parsed_data:
                new_data[file] = parsed_data
                print(f"✅ 解析成功: {file}")
            else:
                print(f"❌ 解析失败: {file}")

    if new_data:
        existing_data.update(new_data)
        save_json(existing_data)
        print(f"✅ 解析完成！共新增 {len(new_data)} 条政策数据。")
    else:
        print("✅ 没有新文件需要解析，所有政策数据已是最新！")


# ========== 📌 加载 & 存储 JSON ==========
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


# ========== 📌 主运行入口 ==========
if __name__ == "__main__":
    process_policy_files()
