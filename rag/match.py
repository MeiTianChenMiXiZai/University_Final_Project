import argparse
import ast
import os
import re
import shutil
from difflib import SequenceMatcher
from data.vision.t_ocr import run_ocr
import cv2
import fitz

import os

def clear_output_folder(output_dir: str):
    """
    清空 OCR 结果文件夹，防止重复命名
    - `output_dir`: 需要清理的文件夹路径
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)  # **删除整个文件夹**
        os.makedirs(output_dir)  # **重新创建空文件夹**
        print(f"🗑️ 已清空文件夹: {output_dir}")
    else:
        os.makedirs(output_dir)  # **如果文件夹不存在，则创建**
        print(f"📂 已创建文件夹: {output_dir}")
##=============OCR=================
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

def run_pdf_ocr_for_highlight(pdf_path: str, output_dir: str) -> str:
    """
    运行 OCR 解析指定 PDF 并存储 OCR 识别的图像
    - `pdf_path`: 需要 OCR 解析的 PDF 文件
    - `output_dir`: OCR 生成的图片存放目录
    """
    extracted_text = process_pdf_with_ocr(pdf_path)  # OCR 处理 PDF
    return extracted_text


##=============Matching==============================
import ast

import re


def find_best_matching_passage(referenced_texts: list[str], ocr_results: list[dict]) -> dict:
    """
    在 OCR 识别的文本中，找到与 LLM 生成的最终回答最相似的片段
    """
    best_match = None
    best_score = 0

    for ref_text in referenced_texts:
        for passage in ocr_results:
            for ocr_text, _ in passage["相关内容"]:
                match_score = SequenceMatcher(None, ref_text, ocr_text).ratio()

                if match_score > best_score:
                    coordinates = re.findall(r"@@\d+\s[\d.]+\s[\d.]+\s[\d.]+\s[\d.]+##", ocr_text)

                    best_match = {
                        "文件": passage["文件"],
                        "引用内容": ref_text,
                        "匹配 OCR 文本": ocr_text,
                        "匹配分数": match_score,
                        "坐标": list(coordinates)  # **确保返回的是列表**
                    }
                    best_score = match_score

    return best_match if best_match else {"匹配结果": "未找到匹配的 OCR 文段"}


##=======================Highlight==============================

def highlight_text_in_image(image_path: str, page_number: int, coordinates: list[dict], output_dir: str, pdf_width: int, pdf_height: int):
    """
    在 OCR 生成的图片上高亮 LLM 回答中引用的政策内容
    - `image_path`: OCR 解析生成的图片路径
    - `coordinates`: 需要高亮的坐标信息 (包含 page 和 bbox)
    - `output_dir`: 输出带高亮的图片目录
    - `pdf_width`: PDF 宽度 (默认 595.3)
    - `pdf_height`: PDF 高度 (默认 841.9)
    """

    # **读取 OCR 解析的图片**
    image = cv2.imread(image_path)
    if image is None:
        print(f"⚠️ 无法读取图片: {image_path}")
        return

    # **获取图像实际尺寸**
    img_height, img_width = image.shape[:2]

    # **计算缩放比例**
    scale_x = img_width / pdf_width
    scale_y = img_height / pdf_height

    # **复制图片用于绘制**
    overlay = image.copy()

    # **遍历所有坐标，绘制高亮**
    for coord in coordinates:
        coords = list(map(float, coord.replace("@@", "").replace("##", "").split()))


        # **修正 y 坐标（减去前面页的高度）**
        corrected_y0 = coords[2] - (page_number - 1) * pdf_height
        corrected_y1 = coords[4] - (page_number - 1) * pdf_height

        # **转换 PDF 坐标到图像坐标**
        x0 = int(coords[1] * scale_x)
        y0 = int(corrected_y0 * scale_y)
        x1 = int(coords[3] * scale_x)
        y1 = int(corrected_y1 * scale_y)

        print(f"🔍  调整后坐标: x0={x0}, y0={y0}, x1={x1}, y1={y1}")

        # **画黄色高亮框**
        cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 255, 255), thickness=-1)

    # **添加透明度（50%）**
    alpha = 0.5
    cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

    # **保存高亮后的图片**
    output_path = os.path.join(output_dir, os.path.basename(image_path).replace(".jpg", "_highlighted.jpg"))
    cv2.imwrite(output_path, image)

    print(f"✅ 高亮完成！已保存: {output_path}")


##================================================
def process_pdf_highlight(pdf_path: str, referenced_texts: list[str], extracted_text:list[dict], output_dir: str):
    """
    1. 解析 PDF 进行 OCR
    2. 找到 LLM 引用的政策内容
    3. 在 OCR 生成的图片上高亮
    """
    print(f"\n🔍 **正在处理 OCR 解析 PDF:** {pdf_path}")
    clear_output_folder(output_dir)

    # **匹配 LLM 回答**
    matched_passages = find_best_matching_passage(referenced_texts, extracted_text)
    image_paths = []

    if matched_passages:
        # **2. 确保 "坐标" 是列表**
        if isinstance(matched_passages["坐标"], str):
            matched_passages["坐标"] = ast.literal_eval(matched_passages["坐标"])  # 转换为列表

        # **3. 确定 PDF 文件路径**
        pdf_filename = matched_passages["文件"]
        pdf_path = os.path.join(pdf_path, pdf_filename)  # 改写路径

        doc = fitz.open(pdf_path)

        # **获取第一页的尺寸**
        pdf_rect = doc[0].rect
        pdf_width, pdf_height = pdf_rect.width, pdf_rect.height

        print(pdf_width, pdf_height )
        # **4. 运行 OCR 解析**
        run_pdf_ocr_for_highlight(pdf_path, output_dir)

        # **5. 解析 PDF 页码**
        page_number = int(re.search(r"@@(\d+)", matched_passages["坐标"][0]).group(1))  # 提取页码

        # **6. 计算 OCR 生成的图片路径**
        image_path = os.path.join(output_dir, f"{page_number - 1}.jpg")  # 正确拼接文件名

        print(matched_passages["坐标"])

        # **7. 在 OCR 图片上高亮**
        highlight_text_in_image(image_path, page_number, matched_passages["坐标"], output_dir, pdf_width, pdf_height)

        highlighted_image_path = image_path.replace('.jpg', '_highlighted.jpg')
        image_paths.append(highlighted_image_path)  # 将图像路径添加到列表

        print(f"✅ 高亮完成！已保存: {highlighted_image_path}")
    else:
        print("❌ 未找到匹配的 OCR 片段，无法高亮。")

    return image_paths  # 返回图像路径列表








# **测试代码**
if __name__ == "__main__":
    pdf_path = "C:/Users/ROG/PycharmProjects/final/data/policy"  # 你的 PDF 文件路径
    output_dir = "C:/Users/ROG/PycharmProjects/final/rag/ocr_results"  # OCR 生成的图片目录
    # 传入 LLM 生成的引用文本
    referenced_texts = [
        "2.学术论文需提交检索报告，",
        "以第一作者在B级期刊上发表专业相关的学术",
        "有争议的成果由学院推免工"
    ]

    # 传入 OCR 识别的政策文档片段
    ocr_results = [
        {'文件': '西南大学计算机与信息科学学院 软件学院推荐优秀本科毕业生免试攻读硕士学位研究生工作实施细则（202.pdf',
         '相关内容': [
             ('@@5\t431.3\t3781.0\t446.7\t3792.7##\n2.学术论文需提交检索报告，@@5\t429.0\t3796.0\t544.0\t3808.3##\n'
              '以第一作者在B级期刊上发表专业相关的学术@@5\t81.7\t3811.0\t261.3\t3823.3##\n'
              '有争议的成果由学院推免工@@5\t432.3\t3811.7\t538.7\t3824.0##\n'
              '2.4@@5\t51.3\t3827.7\t69.0\t3838.0##', 5.041)]
         },
        {'文件': '附件1：西南大学本科毕业论文（设计）规范.docx',
         '相关内容': [
             (
             '对于一些不宜放入正文中，但对毕业论文（设计）有参考价值的内容，或以他人阅读方便的工具性资料，如调查问卷、公式推演、编写程序、原始数据附表等，可编入附录中格式同正文',
             3.265)]
         }
    ]

    process_pdf_highlight(pdf_path, referenced_texts, ocr_results, output_dir)



    print("✅ OCR 解析完成！")
