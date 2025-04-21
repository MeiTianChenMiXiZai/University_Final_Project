# 1. **deepseek-r1:7b**：作为对话模型（Chat Model），用于生成政策咨询的回答。
#
# 2. **smartcreation/bge-large-zh-v1.5**：作为嵌入模型（Embedding Model），用于将文本转换为向量，支持语义检索。
#
# 3. **llava**：作为视觉模型（CV Model），用于解析政策文件中的图像内容。

OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "models": {
        "chat": "deepseek-r1:7b",
        "embedding": "quentinz/bge-large-zh-v1.5",
        "cv": "llava"
    }
}