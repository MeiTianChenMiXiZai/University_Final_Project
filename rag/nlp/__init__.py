# 文档解析
# 识别章节结构（BULLET_PATTERN）
# 分块处理（hierarchical_merge）

import re

def find_codec(blob):
    global all_codecs
    for c in all_codecs:
        try:
            blob[:1024].decode(c)
            return c
        except Exception as e:
            pass
        try:
            blob.decode(c)
            return c
        except Exception as e:
            pass

    return "utf-8"

class PolicyStructureParser:
    SECTION_PATTERNS = [
        r"第[一二三四五六七八九十]+章",  # 章
        r"第[零一二三四五六七八九十百]+条"  # 条款
    ]

    def extract_sections(self, text: str) -> dict:
        """提取政策文件章节结构"""
        sections = {}
        current_chapter = ""

        for line in text.split("\n"):
            line = line.strip()
            # 识别章节标题
            for pattern in self.SECTION_PATTERNS:
                if re.match(pattern, line):
                    current_chapter = line
                    sections[current_chapter] = []
                    break
            # 收集条款内容
            if current_chapter and line:
                sections[current_chapter].append(line)

        return sections