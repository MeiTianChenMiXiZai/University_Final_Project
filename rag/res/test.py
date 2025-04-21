import json
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POLICY_FILE = os.path.join(BASE_DIR, "res", "processed_policies.json")

if os.path.exists(POLICY_FILE):
    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"✅ 解析的政策文件总数: {len(data)}")

    for idx, (filename, content) in enumerate(data.items()):
        text = content.get("text_chunks", "❌ 无内容")
        print(f"\n📄 文件: {filename}")
        print(f"📜 文本内容: {text[:300]}...")  # 仅打印前300字符
        if idx >= 3:
            break  # 只查看前4条数据，避免过多输出
else:
    print(f"❌ {POLICY_FILE} 文件不存在！请先运行 `data_devide.py` 解析政策文件。")
