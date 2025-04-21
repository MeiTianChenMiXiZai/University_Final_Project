from data.parser.pdf_parser import PdfParser

# 测试 PDF 文件路径
pdf_path = "/data/policy/1_关于组织开展西南大学学生接诉即办平台“西小办”内部试运行的通知.pdf"

# 初始化解析器
parser = PdfParser()

# 解析 PDF
try:
    print(f"🔍 解析 PDF: {pdf_path}")

    text_content, tables = parser(pdf_path)

    # 输出解析结果
    print("\n📄 **文本内容:**")
    print(text_content[:500])  # 只打印前 500 字符，避免输出过长

    print("\n📊 **表格内容:**")
    for table in tables:
        print(table)

    print("\n✅ 解析完成！")
except Exception as e:
    print(f"❌ 解析失败，错误信息: {e}")

    # 额外调试输出
    print("\n🔎 **调试信息:**")
    print(f"- `self.boxes` 长度: {len(parser.boxes) if hasattr(parser, 'boxes') else '未定义'}")
    print(f"- `self.page_images` 长度: {len(parser.page_images) if hasattr(parser, 'page_images') else '未定义'}")
