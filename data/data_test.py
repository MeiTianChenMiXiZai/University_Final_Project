from data.parser.pdf_parser import PdfParser
from data.vision.t_ocr import run_ocr
import argparse
# 你的 PDF 文件路径
pdf_file = "C:\\Users\\ROG\\PycharmProjects\\final\\data\\policy\\西南大学计算机与信息科学学院 软件学院推荐优秀本科毕业生免试攻读硕士学位研究生工作实施细则（202.pdf"


def process_pdf_with_ocr(file_path):
    """对扫描版 PDF 进行 OCR 处理"""
    print(f"🖼️  处理扫描版 PDF: {file_path}")

    try:
        # 手动构造 `args`
        args = argparse.Namespace(
            inputs=file_path,  # 输入文件路径
            output_dir="./ocr_results"  # 固定输出目录
        )

        # 运行 OCR 识别
        ocr_results = run_ocr(args)
        extracted_text = "\n".join(ocr_results) if ocr_results else ""

        return extracted_text

    except Exception as e:
        print(f"❌ OCR 解析失败: {e}")
        return ""




try:
    ocr_results = process_pdf_with_ocr(pdf_file)
    print(f"🖼️ OCR 识别文本: {' '.join(ocr_results)}")
except Exception as ocr_error:
    print(f"❌ OCR 解析失败: {ocr_error}")
