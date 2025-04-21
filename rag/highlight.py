import cv2
import numpy as np

# 你的图片路径
image_path = r"C:\Users\ROG\PycharmProjects\final\rag\ocr_results\5.jpg"

# 读取图片
image = cv2.imread(image_path)

if image is None:
    print(f"⚠️ 无法读取图片: {image_path}")
    exit()

# **PDF 页面尺寸**（你提供的）
pdf_width = 595.3
pdf_height = 841.9  # 假设 PDF 页面高度一致

# **获取图片尺寸**
img_height, img_width = image.shape[:2]

# **计算缩放比例**
scale_x = img_width / pdf_width
scale_y = img_height / pdf_height

# **OCR 解析出的多个坐标（包含页数）**
ocr_bboxes = [
    {"page": 1, "bbox": [246.0, 90.7, 347.7,	117.7], "text": "西南大学"},
    {"page": 2, "bbox": [106.3, 1360.3,	252.3,	1375.3], "text": "推免生"},
    {"page": 3, "bbox": [71.7,	2145.3,	106.3,	2158.7], "text": ""},
    {"page": 5, "bbox": [340.3,	3691.7,	352.7,	3704.7], "text": "期刊"},

]

# **复制图片用于绘制**
overlay = image.copy()

# **遍历所有坐标，绘制高亮**
for entry in ocr_bboxes:
    page_num = entry["page"]
    x0, y0, x1, y1 = entry["bbox"]

    # **修正 y 坐标（减去前面页的高度）**
    corrected_y0 = y0 - (page_num - 1) * pdf_height
    corrected_y1 = y1 - (page_num - 1) * pdf_height

    # **转换 PDF 坐标到图像坐标**
    x0 = int(x0 * scale_x)
    y0 = int(corrected_y0 * scale_y)  # 翻转 y 轴
    x1 = int(x1 * scale_x)
    y1 = int(corrected_y1 * scale_y)  # 翻转 y 轴

    print(f"🔍 [第{page_num}页] 调整后坐标: x0={x0}, y0={y0}, x1={x1}, y1={y1}")

    # 画黄色高亮框
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 255, 255), thickness=-1)

# **添加透明度（50%）**
alpha = 0.5
cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

# **保存新图片**
output_path = image_path.replace(".jpg", "_multi_page_highlighted.jpg")
cv2.imwrite(output_path, image)

print(f"✅ 多页高亮完成！已保存: {output_path}")
