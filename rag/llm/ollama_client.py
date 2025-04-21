import re

import requests
import base64
from typing import Generator
from PIL import Image
from io import BytesIO
import json

class OllamaClient:
    def __init__(self, config):
        self.base_url = config["base_url"]
        self.models = config["models"]

    def _send_request(self, endpoint: str, payload: dict) -> dict:
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama API请求失败: {str(e)}")

    def _image_to_base64(self, image_path: str) -> str:
        with Image.open(image_path) as img:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")

    # 嵌入模型接口
    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """获取批量文本嵌入向量"""
        payload = {
            "model": self.models["embedding"],
            "prompt": texts[0],  # 新模型要求单条输入
            "options": {"embedding_only": True}
        }
        # 批量处理逻辑需要改为循环
        embeddings = []
        for text in texts:
            payload["prompt"] = text
            result = self._send_request("/api/embeddings", payload)
            if "embedding" in result:
                embeddings.append(result["embedding"])
        return embeddings

    # 视觉模型接口
    def describe_image(self, image_path: str, lang: str = "zh") -> str:
        """解析图像内容"""
        base64_image = self._image_to_base64(image_path)
        prompt = "请用中文详细描述图片中的内容，包括文字、图表、数据等所有可见信息" if lang == "zh" else \
            "Describe the image content in detail including text, charts, data, etc."

        payload = {
            "model": self.models["cv"],
            "prompt": prompt,
            "images": [base64_image],
            "stream": False
        }
        result = self._send_request("/api/generate", payload)
        return result.get("response", "")

    # 对话模型接口
    def generate_response(
            self,
            context: str,
            question: str,
            stream: bool = False
    ) -> Generator[str, None, None] | str:
        """生成政策咨询回答"""
        system_prompt = f"""你是一个专业的学校政策咨询助手，请严格根据提供的上下文信息回答问题。

        上下文内容：
        {context}

        回答要求：
        1. 使用中文回答
        2. 用简洁，专业，确切的语句回答问题。
        3. 一定要用《》给出引用的政策文件名
        4. 并用【】给出引用的具体政策原文
        5. 如没有政策符合提问，则输出“并未查询到相关政策，无法作答”
"""

        payload = {
            "model": self.models["chat"],
            "system": system_prompt,
            "prompt": question,
            "stream": stream,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 1024
            }
        }

        if stream:
            return self._stream_generation(payload)
        else:
            result = self._send_request("/api/generate", payload)
            return result.get("response", "")

    def _stream_generation(self, payload: dict) -> Generator[str, None, None]:
        """处理流式响应"""
        try:
            with requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=60
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf-8"))  # <-- 需要json模块
                        yield chunk.get("response", "")
        except Exception as e:
            yield f"流式生成错误: {str(e)}"

    import re

    def extract_keywords(self, question: str) -> tuple[list[str], dict[str, list[str]]]:
        prompt = f"""用户正在进行学校政策文件提问，请从以下问题中提取最重要的关键词（2-3字，只有专有名词可为4字以上），用于后续文档检索。
同时，为了提高搜索效果，请参考 `jieba` 词库，为每个关键词提供 1-2 个近义词。
关键词应避免单字，常见词汇无需提取。近义词若没有，可以不提供。
  
**示例 1：**
- 输入："推免的年级排名应为多少？"
- 关键词提取："推免 年级 排名"
- 近义词扩展："推免|保研 年级|年段 排名|排名要求"

**示例 2：**
- 输入："保研的英语要求是什么？雅思 5 分可以吗？"
- 关键词提取："保研 英语 雅思"
- 近义词扩展："保研|推免 英语|外语 雅思|雅思考试"

请严格按照以下格式返回：
---
关键词：关键词1 关键词2 关键词3
近义词：关键词1|近义词A 关键词2|近义词B 关键词3|近义词C
---
  
请处理以下用户问题：
问题：{question}
"""
        response = self.generate_response(context="", question=prompt, stream=False)

        # 处理 LLM 可能的 <think> 结构
        cleaned_response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()

        # 提取关键词
        keywords_match = re.search(r"关键词：(.*?)\n", cleaned_response)
        keywords = keywords_match.group(1).split() if keywords_match else []

        # 提取近义词
        synonyms_match = re.search(r"近义词：(.*?)\n", cleaned_response)
        synonyms_list = synonyms_match.group(1).split() if synonyms_match else []

        # 构建近义词字典
        synonyms = {}
        for pair in synonyms_list:
            parts = pair.split("|")
            if len(parts) == 2:
                keyword, synonym = parts
                if keyword in synonyms:
                    synonyms[keyword].append(synonym)
                else:
                    synonyms[keyword] = [synonym]

        return keywords, synonyms

