import json
import jieba
import jieba.analyse
import re
from collections import Counter

# 读取政策文件 JSON
POLICY_FILE = "processed_policies.json"


# 读取政策文本
def load_policy_texts():
    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts = []
    for doc_name, doc_data in data.items():
        texts.extend(doc_data.get("text_chunks", []))  # 读取所有文本片段
    return texts


# 清理文本，去除 @@ 页码 坐标信息##
def clean_text(text):
    return re.sub(r"@@\d+\t.*?##", "", text)


# 生成 huqie.txt 词典
def generate_huqie(texts, output_file="huqie.txt", min_freq=5):
    word_freq = Counter()
    for text in texts:
        clean_text_chunk = clean_text(text)
        words = jieba.cut(clean_text_chunk)
        word_freq.update(words)

    # 选取高频词并存储
    with open(output_file, "w", encoding="utf-8") as f:
        for word, freq in word_freq.items():
            if freq >= min_freq and len(word) > 1:
                f.write(f"{word} {freq} n\n")  # 设定所有词性为 'n'（名词）
    print(f"✅ huqie.txt 生成完成，共 {len(word_freq)} 个词")


# 生成 term.freq 文件
def generate_term_freq(texts, output_file="term.freq", min_freq=2):
    term_counter = Counter()
    for text in texts:
        clean_text_chunk = clean_text(text)
        words = jieba.lcut(clean_text_chunk)
        term_counter.update(words)

    # 选取高频词并存储
    with open(output_file, "w", encoding="utf-8") as f:
        for word, freq in term_counter.most_common():
            if freq >= min_freq and len(word) > 1:
                f.write(f"{word} {freq}\n")
    print(f"✅ term.freq 生成完成，共 {len(term_counter)} 个词")


if __name__ == "__main__":
    print("🔄 读取政策文件...")
    policy_texts = load_policy_texts()

    print("📌 生成 huqie.txt...")
    generate_huqie(policy_texts)

    print("📌 生成 term.freq...")
    generate_term_freq(policy_texts)

    print("🎉 处理完成，可以检查生成的 huqie.txt 和 term.freq 文件！")