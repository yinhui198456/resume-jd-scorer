#!/usr/bin/env python3
"""
quality_gate.py — 质量门控模块

职责：
- 读取 quality_audit_results.json，构建 QID → 质量状态的索引
- 提供 is_passing(qid) 快速查询（O(1)）
- 提供 get_failed_reasons(qid) 获取失败维度详情
- 提供统计信息供 quiz_bot.py 汇报

设计原则：
- 零 LLM 调用，纯本地 JSON 读取
- 加载一次，缓存内存中（quiz_bot.py 进程生命周期短）
- 审计文件不存在时降级为全部放行（fail-open）
"""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_RESULTS_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'question-bank', 'quality_audit_results.json')

DIMENSION_LABELS = {
    "length_bias": "长度偏见",
    "semantic_diversity": "干扰项多样性",
    "answer_exp_consistency": "答案-解析一致性",
    "option_uniqueness": "选项唯一性",
    "filler_density": "填充语密度",
}

DIMENSION_THRESHOLD = 50  # 单维度失败阈值（与 quality_audit.py 一致）


class QualityGate:
    """质量门控器。加载审计结果，提供快速查询。"""

    def __init__(self, audit_path=None):
        self.audit_path = audit_path or AUDIT_RESULTS_PATH
        self._passing_qids = set()
        self._failing_qids = set()
        self._fail_reasons = {}  # qid -> [(dim_name, score), ...]
        self._total_known = 0
        self._loaded = False
        self._load()

    def _load(self):
        """加载审计结果文件。"""
        if not os.path.exists(self.audit_path):
            # 审计文件不存在 → 放行所有题目（降级模式）
            self._loaded = True
            return

        with open(self.audit_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        all_questions = data.get('all_questions', [])
        if not all_questions:
            # 没有逐题数据 → 降级放行
            self._loaded = True
            return

        for q in all_questions:
            qid = q['id']
            self._total_known += 1
            if q.get('passes', True):
                self._passing_qids.add(qid)
            else:
                self._failing_qids.add(qid)
                reasons = []
                for dim_name, score in q.get('dimensions', {}).items():
                    if score > DIMENSION_THRESHOLD:
                        reasons.append((dim_name, score))
                self._fail_reasons[qid] = reasons

        self._loaded = True

    def is_passing(self, qid: str) -> bool:
        """检查题目是否通过质量门控。
        
        返回 True：
        - 审计结果显示通过
        - 审计结果中未包含该题（未评分的题目默认放行）
        - 审计文件不存在或未加载（降级模式）
        
        返回 False：
        - 审计结果显示未通过
        """
        if not self._loaded:
            return True  # 未加载 → 降级放行
        return qid not in self._failing_qids

    def get_failed_reasons(self, qid: str) -> list:
        """获取题目失败的维度详情。
        
        返回 [(中文标签, 分数), ...]
        """
        raw = self._fail_reasons.get(qid, [])
        return [(DIMENSION_LABELS.get(d, d), s) for d, s in raw]

    def stats(self) -> dict:
        """返回质量门控统计信息。"""
        return {
            'passing': len(self._passing_qids),
            'failing': len(self._failing_qids),
            'total_known': self._total_known,
            'mode': 'full' if self._total_known > 0 else 'degraded',
        }

    @property
    def has_data(self) -> bool:
        """是否有审计数据可用。"""
        return self._total_known > 0
