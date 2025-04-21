# -*- coding: utf-8 -*-
import math
import json
import re
import os
import numpy as np
from rag.nlp import rag_tokenizer


class Dealer:
    def __init__(self):
        # 获取 `rag/` 目录的基础路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # `rag/nlp/` -> `rag/`
        res_dir = os.path.join(base_dir, "res")  # 资源文件目录

        # 停用词列表（优化）
        self.stop_words = set([
            "请问", "您", "你", "我", "他", "的", "是", "有", "在", "为", "将",
            "本办法", "本条例", "相关规定", "特此通知", "自发布之日起施行",
            "相关部门", "各院系", "有关单位", "全体师生"
        ])

        # 加载 NER 词典
        self.ne = self.load_json(os.path.join(res_dir, "ner.json"))

        # 加载 term 词频数据
        self.df = self.load_term_freq(os.path.join(res_dir, "term.freq"))

    def load_json(self, path):
        """加载 JSON 文件"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Load {path} FAIL: {e}")
            return {}

    def load_term_freq(self, path):
        """加载 term.freq 词频文件"""
        term_freq = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) == 2:
                        term_freq[parts[0]] = int(parts[1])
                    else:
                        term_freq[parts[0]] = 0
        except Exception as e:
            print(f"[WARNING] Load {path} FAIL: {e}")
        return term_freq

    def pretoken(self, txt, num=False, stpwd=True):
        """预处理文本（分词 + 去除无效字符）"""
        patt = [r"[~—\t @#%!<>,\.\?\":;'\{\}\[\]_=\(\)\|，。？》•●○↓《；‘’：“”【¥ 】…￥！、·（）×`&\\/「」\\]"]
        for p in patt:
            txt = re.sub(p, " ", txt)

        res = []
        for t in rag_tokenizer.tokenize(txt).split():
            if (stpwd and t in self.stop_words) or (re.match(r"[0-9]$", t) and not num):
                continue
            res.append(t)
        return res

    def tokenMerge(self, tks):
        """合并短词"""
        res, i = [], 0
        while i < len(tks):
            if len(tks[i]) == 1:
                if i + 1 < len(tks) and len(tks[i + 1]) > 1:
                    res.append(tks[i] + tks[i + 1])
                    i += 2
                    continue
            res.append(tks[i])
            i += 1
        return res

    def ner(self, t):
        """获取命名实体识别（NER）标签"""
        return self.ne.get(t, "")

    def weights(self, tks):
        """计算权重（TF-IDF + NER）"""

        def idf(s, N): return math.log10(10 + ((N - s + 0.5) / (s + 0.5)))

        def term_freq(t):
            return self.df.get(t, 3)  # 默认权重 3

        tw = []
        for tk in tks:
            tt = self.tokenMerge(self.pretoken(tk, True))
            idf_values = np.array([idf(term_freq(t), 1000000) for t in tt])
            weights = idf_values * np.array([1.5 if self.ner(t) else 1 for t in tt])
            tw.extend(zip(tt, weights))

        S = np.sum([s for _, s in tw])
        return [(t, s / S) for t, s in tw] if S else tw


# ========== 测试代码 ==========
if __name__ == "__main__":
    weighter = Dealer()

    policy_text = """
    根据《XX大学本科生学分制管理办法》第十条，学生GPA达到3.0方可申请奖学金。
    教务处负责审核材料，未达到学分要求者不予受理。
    """

    # 查看预处理结果
    tokens = weighter.pretoken(policy_text)
    print("\n预处理分词结果:", tokens)

    # 查看权重计算结果
    weighted_terms = weighter.weights(tokens)
    print("\n关键词权重排序:", sorted(weighted_terms, key=lambda x: x[1], reverse=True))
