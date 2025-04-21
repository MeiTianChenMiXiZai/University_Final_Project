# -*- coding: utf-8 -*-
import json
import os
import logging


class SynonymDealer:
    def __init__(self):
        """
        同义词查询工具，使用本地 `synonym.json`
        """
        # 词典路径（相对路径）
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dict_path = os.path.join(base_dir, "res", "synonym.json")

        # 加载本地词典
        self.dictionary = self.load_local_dict()

    def load_local_dict(self):
        """加载本地 synonym.json"""
        try:
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                dictionary = json.load(f)
            logging.info(f"✅ SynonymDealer: 词典加载成功，共 {len(dictionary)} 条同义词")
            return dictionary
        except Exception as e:
            logging.warning(f"⚠️ SynonymDealer: 词典加载失败 ({e})")
            return {}

    def lookup(self, word):
        """查找同义词"""
        return self.dictionary.get(word.lower(), [])


# ========== 测试代码 ==========
if __name__ == "__main__":
    synonym = SynonymDealer()

    test_words = ["学生", "论文", "政策", "奖学金", "研究"]
    for word in test_words:
        print(f"{word} 的同义词: {synonym.lookup(word)}")
