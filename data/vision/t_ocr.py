import os
import sys
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)),
            '../../')))

from data.vision.seeit import draw_box
from data.vision import OCR, init_in_out
import argparse
import numpy as np

def run_ocr(args):
    """
    运行 OCR 解析，并将图片保存为 0.jpg, 1.jpg, 2.jpg ...
    """
    ocr = OCR()
    images, outputs = init_in_out(args)

    ocr_texts = []
    for i, img in enumerate(images):
        bxs = ocr(np.array(img))
        bxs = [(line[0], line[1][0]) for line in bxs]
        bxs = [{
            "text": t,
            "bbox": [b[0][0], b[0][1], b[1][0], b[-1][1]],
            "type": "ocr",
            "score": 1} for b, t in bxs if b[0][0] <= b[1][0] and b[0][1] <= b[-1][1]]

        # **重命名 OCR 生成的图片**
        img_output_path = os.path.join(os.path.dirname(outputs[i]), f"{i}.jpg")

        # 保存带标注的 OCR 图片
        img = draw_box(images[i], bxs, ["ocr"], 1.)
        img.save(img_output_path, quality=95)
'''
        # **重命名 OCR 识别文本**
        text_output_path = os.path.join(os.path.dirname(outputs[i]), f"{i}.txt")

        # 保存 OCR 识别文本
        with open(text_output_path, "w+", encoding="utf-8") as f:
            ocr_texts.append("\n".join([o["text"] for o in bxs]))
            f.write(ocr_texts[-1])

        print(f"✅ OCR 解析完成: {img_output_path} 和 {text_output_path}")

    return ocr_texts
'''