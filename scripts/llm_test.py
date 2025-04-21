from rag.llm.config import OLLAMA_CONFIG
from rag.llm.ollama_client import OllamaClient
from rag.llm.policy_engine import PolicyQAEngine

# 初始化客户端
client = OllamaClient(OLLAMA_CONFIG)
print(dir(OllamaClient))
engine = PolicyQAEngine(client)

# 加载政策文档
policy_docs = [
    "《高新技术企业认定管理办法》第三章第十二条：企业研发费用占比需达到...",
    "《人才引进实施细则》第五条：博士研究生可申请一次性安家费20万元...",
    # 更多政策文档...
]
engine.load_documents(policy_docs)

# 示例问答
question = "博士研究生可以申请哪些补贴？"

# 普通模式
answer = engine.answer_question(question)
print(answer)

# 流式模式
for chunk in engine.answer_question(question, stream=True):
    print(chunk, end="", flush=True)

# 图像解析示例
image_desc = engine.analyze_policy_image("policy_images/chart.png")
print(f"图像分析结果：{image_desc}")