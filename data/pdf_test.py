import os
import json

import pdfplumber

from parser.pdf_parser import PdfParser
import logging

# 你的 PDF 文件路径
pdf_path = "C:\\Users\\ROG\\PycharmProjects\\final\\data\\policy\\西南大学计算机与信息科学学院 软件学院推荐优秀本科毕业生免试攻读硕士学位研究生工作实施细则（202.pdf"
output_dir = "C:\\Users\\ROG\\PycharmProjects\\final\\data\\parsed_output"  # 输出目录
os.makedirs(output_dir, exist_ok=True)

# 初始化 PDF 解析器
parser = PdfParser()

# 1️⃣ **测试 `pdfplumber` 提取表格**
print("\n🔍 **步骤 1：使用 `pdfplumber` 提取表格**")
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        if tables:
            print(f"✅ `pdfplumber` 在第 {i + 1} 页检测到 {len(tables)} 个表格")
            logging.info(f"`pdfplumber` 第 {i + 1} 页解析到表格: {tables[:1]}")  # 只显示一个表格，防止输出过多
        else:
            print(f"⚠️ `pdfplumber` 在第 {i + 1} 页没有找到表格")

# 2️⃣ **测试 `pdf_parser.py` 提取表格**
print("\n🔍 **步骤 2：使用 `pdf_parser.py` 提取表格**")
parsed_text, extracted_data = parser(pdf_path, need_image=True, zoomin=3, return_html=True)

# 3️⃣ **检查 `TableStructureRecognizer` 解析表格**
print("\n🔍 **步骤 3：检查 `TableStructureRecognizer` 是否工作**")
if extracted_data:
    print("✅ `pdf_parser.py` 成功提取表格数据！")
    tables_output_path = os.path.join(output_dir, "parsed_tables.json")
    with open(tables_output_path, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=4, ensure_ascii=False)
    print(f"✅ 表格数据已保存到: {tables_output_path}")
    logging.info(f"`pdf_parser.py` 提取表格成功: {extracted_data[:1]}")
else:
    print("⚠️ `pdf_parser.py` **没有找到表格**，可能 `TableStructureRecognizer` 解析失败！")
    logging.error("`pdf_parser.py` 没有检测到表格！")

# 4️⃣ **测试 `OCR` 是否影响表格提取**
print("\n🔍 **步骤 4：测试 OCR 对表格的影响**")
for img in parser.page_images:
    ocr_result = parser.ocr.detect(img)
    if ocr_result:
        print("✅ OCR 识别到了文字，可能影响表格解析")
        logging.info(f"OCR 识别内容: {ocr_result[:1]}")
    else:
        print("⚠️ OCR **没有识别到文字**，表格可能是文本格式")