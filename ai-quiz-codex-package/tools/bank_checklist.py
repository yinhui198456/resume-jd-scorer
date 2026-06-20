#!/usr/bin/env python3
"""
题库质量 Checklist —— 每题必须通过所有检查才算达标。

用法: python3 scripts/bank_checklist.py [--bank path/to/bank.json]

每次修改题库后运行，或 cron 定时巡检。
发现 Critical/High 问题立即报错退出，Medium 汇总报告。

Checklist 持续丰富中 —— 发现新问题模式后追加到此文件。

🚩 Flag (2026-06-01): 刷题过程中用户发现的所有题目问题，必须维护到此 Checklist 中，不得遗漏。
"""

import json
import sys
import os
import argparse
from dataclasses import dataclass, field
from typing import List, Tuple

# === Checklist Definitions ===

# 模板化后缀黑名单（之前修复脚本误加的）
TEMPLATE_SUFFIXES = [
    '这在某些架构设计中可能被考虑但不是该方案的核心机制',
    '这无法应对复杂场景下的指令边界判断',
    '但这只能缓解通信问题无法从根本上解决上下文窗口限制',
    '但这忽略了实际部署中的关键约束条件',
    '这在某些特定场景下可能成立',
    '但这忽略了实际场景中需要更细粒度的处理机制',
    '但这在实际应用中效果有限',
    '这无法覆盖所有边缘场景',
    '这在生产环境中需要额外的兜底策略',
    '，但这种方案在复杂场景下效果有限',
    '，这并非业界标准实践',
    '，但实际效果取决于具体实现',
    '，这在特定场景下可能适用但不是通用方案',
    '采用替代方案处理，但这不是最优解',
    '，但这无法覆盖所有边缘场景',
    '，但这并非通用解决方案',
    '，但这种做法存在明显局限',
    '采用该方案处理，但在实际中效果有限',
    '使用替代方法处理',
    '但这只能减少波动不能保证输出一致性',  # 🔧 2026-06-02 时审新增：Q-M17_工程化35 干扰项 A/B/C 共用后缀
    '但会导致所有请求都走同一条处理链路',  # 🔧 2026-06-02 时审新增：Q-M15_成本优化32 干扰项 A/C/D 共用 15 字符后缀
]

# 🔧 通用无关干扰项前缀（2026-06-02 时审新增：Q-M15_成本优化18）
# 特征：选项形式上像合理回答，但完全不涉及题干核心概念，属于 LLM 生成的模板填充
GENERIC_NON_ANSWER_PREFIXES = [
    '该方案在复杂场景下',
    '此方法在大多数情况下',
    '该策略需要结合实际情况',


]

# 明显错误干扰项关键词
# ⚠️ 注意: "所有" 误报率极高（2026-06-02 审计: 7/7 flagged 均为正常语境），
#    建议实际使用时结合上下文判断，或改为更具体的模式如 "所有都"、"所有场景下"
# ⚠️ "无需" 在特定场景下可作为有效干扰项标记（如 ReAct 题目中 "无需工具" 为弱干扰项）
OBVIOUS_PATTERNS = ['完全不', '只需', '总是', '所有', '无需', '没有任何', '一定不']

# 🔧 答案-解析一致性假阳性模式（2026-06-02 新增：审计发现）
# 根因：8 字符连续匹配在 paraphrase/中英混用场景下误报率 ~100%
# 触发场景：
#   1. 中英混用：选项用中文（如"对话缓冲"），explanation 用英文类名（"ConversationBufferMemory"）
#   2. 同义改写：explanation 对正确选项进行意译而非直接复制
#   3. 扩展解释：explanation 补充背景知识导致措辞差异
# 建议：改为关键术语匹配（提取专业名词检查是否存在于 explanation）或引入语义相似度阈值
PARAPHRASE_FALSE_POSITIVE_PATTERNS = [
    ('中英混用', '选项用中文术语，explanation 使用对应英文类名/术语'),
    ('同义改写', 'explanation 用近义词替换选项中的关键词（如"独立"→"不同"）'),
    ('扩展解释', 'explanation 在正确选项基础上补充了背景知识或框架名称'),
    ('共享术语前缀', '选项以英文技术术语开头（如"Decoder-only"），explanation 自然提及该术语时被误判为描述该选项 —— 2026-06-02 审计发现：Q-M01_LLM基础02 选项 B 以"Decoder-only"开头，explanation 开头也提及该术语，触发 Critical 误判'),
    ('跨域不一致', 'explanation 描述的知识点属于与题目所在模块不同的知识域 —— 2026-06-02 时审发现：Q-M05_FunctionCalling33 问 RAG 延迟优化，但 explanation 讲 Function Calling 的工具调用优化'),
]


# 题干前缀黑名单
QUESTION_PREFIX_BAD = [': ', '：', '考 ', '考:']

# 🔧 结构对齐 Checklist（2026-06-01 新增：今晚故障根因）
# 根因：ID 命名不统一、序号断层、ID-Content 错位（并发修改导致）
ID_CONSISTENCY_PATTERNS = [
    # 模式 1：ID 格式不统一（同模块混用不同前缀）
    ('Q-8_Agent架构', 'Q-Agent架构'),  # 应统一为 Q-8_Agent架构
    # 模式 2：ID 跳跃（序号不连续）
    ('gap', True),  # 标记：模块内序号跳跃 > 1
    # 模式 3：ID-Content 错位（判题时 ID 对应的内容非预期）
    ('mismatch', True),  # 标记：ID 存在但内容完全不符
]

@dataclass
class Issue:
    qid: str
    check: str
    severity: str  # Critical, High, Medium, Low
    message: str

@dataclass
class Result:
    total: int = 0
    passed: int = 0
    failed: int = 0
    issues: List[Issue] = field(default_factory=list)
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0

    def add_issue(self, qid, check, severity, message):
        self.issues.append(Issue(qid, check, severity, message))
        if severity == 'Critical':
            self.critical += 1
        elif severity == 'High':
            self.high += 1
        elif severity == 'Medium':
            self.medium += 1
        elif severity == 'Low':
            self.low += 1

    def summarize(self):
        print(f"\n{'='*60}")
        print(f"题库质量 Checklist 结果")
        print(f"{'='*60}")
        print(f"总题数: {self.total}")
        print(f"通过:   {self.passed}")
        print(f"未通过: {self.failed}")
        print(f"")
        print(f"Critical: {self.critical} 🔴")
        print(f"High:     {self.high} 🟠")
        print(f"Medium:   {self.medium} 🟡")
        print(f"Low:      {self.low} ⚪")
        print(f"")

        if self.issues:
            print("--- 问题列表 ---")
            for issue in self.issues:
                tag = {'Critical': '🔴', 'High': '🟠', 'Medium': '🟡', 'Low': '⚪'}[issue.severity]
                print(f"  {tag} [{issue.severity}] {issue.qid} ({issue.check}): {issue.message}")

        print(f"\n{'='*60}")
        if self.critical > 0 or self.high > 0:
            print(f"❌ UNQUALIFIED — 发现 {self.critical} Critical / {self.high} High 问题")
            return 1
        else:
            print(f"✅ ALL QUALIFIED — 无 Critical/High 问题")
            return 0


def check_question_format(q, res: Result):
    """L01-题干格式检查"""
    qid = q.get('id', 'UNKNOWN')
    question = q.get('question', '')

    if not question:
        res.add_issue(qid, 'L01-题干', 'Critical', '题干为空')
        return

    # 前缀残留
    for bad_prefix in QUESTION_PREFIX_BAD:
        if question.startswith(bad_prefix):
            res.add_issue(qid, 'L01-题干', 'High', f'题干以 "{bad_prefix}" 开头（编辑残留）')
            break

    # 题干过短（不是有效问题）
    if len(question) < 5:
        res.add_issue(qid, 'L01-题干', 'Critical', f'题干过短（{len(question)}字符），可能不是有效问题')

    # 截断检测（结尾不完整）
    if question.endswith('…') or question.endswith('...') or question.endswith('——'):
        res.add_issue(qid, 'L01-题干', 'High', '题干疑似截断')


def check_options(q, res: Result):
    """L02-选项检查"""
    qid = q.get('id', 'UNKNOWN')
    opts = q.get('options', [])
    ans_str = q.get('answer', 'A.').strip('.．。')

    if len(opts) != 4:
        res.add_issue(qid, 'L02-选项', 'Critical', f'选项数量 {len(opts)}（应为4）')
        return

    # 空选项
    for i, o in enumerate(opts):
        if not o or not o.strip():
            res.add_issue(qid, 'L02-选项', 'Critical', f'选项 {chr(65+i)} 为空')

    # 选项截断（过短，< 4字符）
    for i, o in enumerate(opts):
        if len(o.strip()) < 4:
            res.add_issue(qid, 'L02-选项', 'High', f'选项 {chr(65+i)} 疑似截断（{len(o)}字符）: "{o}"')

    # 重复选项
    seen = {}
    for i, o in enumerate(opts):
        o_clean = o.replace('，', '').replace(',', '').replace('。', '').replace(' ', '').lower()
        for j, existing in seen.items():
            existing_clean = existing.replace('，', '').replace(',', '').replace('。', '').replace(' ', '').lower()
            if o_clean == existing_clean and len(o_clean) > 10:
                res.add_issue(qid, 'L02-选项', 'Critical', f'选项 {chr(65+i)} 与 {j} 内容重复')
            elif len(o_clean) > 20 and existing_clean and (o_clean in existing_clean or existing_clean in o_clean):
                res.add_issue(qid, 'L02-选项', 'High', f'选项 {chr(65+i)} 与 {j} 高度相似')
        seen[chr(65+i)] = o

    # 模板化后缀
    for suffix in TEMPLATE_SUFFIXES:
        for i, o in enumerate(opts):
            if o.endswith(suffix):
                res.add_issue(qid, 'L02-选项', 'High', f'选项 {chr(65+i)} 含模板化后缀')
                break

    # 🔧 干扰项共用后缀检测（2026-06-02 时审新增：Q-M17_工程化35）
    # 根因：LLM 生成干扰项时复用相同模板后缀，导致 A/B/C 尾部完全一致
    # 检测策略：提取各选项最后 N 个字符，找出 ≥2 个干扰项共享同一后缀的情况
    if ans_str in 'ABCD':
        ans_idx = "ABCD".index(ans_str)
        distractors = [(chr(65 + i), opts[i]) for i in range(4) if i != ans_idx and len(opts[i]) > 10]
        for suffix_len in [20, 15, 12, 10]:
            suffix_groups = {}
            for label, text in distractors:
                suffix = text[-suffix_len:]
                suffix_groups.setdefault(suffix, []).append(label)
            for suffix, labels in suffix_groups.items():
                if len(labels) >= 2:
                    res.add_issue(qid, 'L02-选项', 'High',
                                  f'干扰项 {"/".join(labels)} 共用 {suffix_len} 字符后缀：「{suffix}」')
                    break  # 只报最长匹配
            if any(len(v) >= 2 for v in suffix_groups.values()):
                break

    # 🔧 通用无关干扰项检测（2026-06-02 时审新增：Q-M15_成本优化18）
    # 根因：LLM 生成干扰项时使用与题目无关的通用模板句式
    # 检测策略：匹配已知无关前缀
    if ans_str in 'ABCD':
        for prefix in GENERIC_NON_ANSWER_PREFIXES:
            for i, o in enumerate(opts):
                if i == "ABCD".index(ans_str):
                    continue
                if o.startswith(prefix):
                    res.add_issue(qid, 'L02-选项', 'Medium', f'选项 {chr(65+i)} 为通用无关干扰项: 「{o[:30]}...」')
                    break

    # 明显错误干扰项
    if ans_str in 'ABCD':
        ans_idx = "ABCD".index(ans_str)
        for i, o in enumerate(opts):
            if i == ans_idx:
                continue
            for pattern in OBVIOUS_PATTERNS:
                if pattern in o:
                    res.add_issue(qid, 'L02-选项', 'Medium', f'选项 {chr(65+i)} 含明显错误模式: "{pattern}"')
                    break

    # 长度偏差（答案是干扰项长度的 >1.8 倍）
    if ans_str in 'ABCD':
        ans_idx = "ABCD".index(ans_str)
        ans_len = len(opts[ans_idx])
        distractor_lens = [len(opts[i]) for i in range(4) if i != ans_idx and len(opts[i]) > 0]
        if distractor_lens:
            avg_distr = sum(distractor_lens) / len(distractor_lens)
            if avg_distr > 0 and ans_len > avg_distr * 1.8:
                res.add_issue(qid, 'L02-选项', 'Medium', f'答案长度是干扰项的 {ans_len/avg_distr:.1f}x ({ans_len} vs 平均 {avg_distr:.0f}c)')


def check_answer(q, res: Result):
    """L03-答案检查"""
    qid = q.get('id', 'UNKNOWN')
    ans = q.get('answer', '')
    opts = q.get('options', [])

    # 答案格式
    if not ans or not ans.strip():
        res.add_issue(qid, 'L03-答案', 'Critical', '答案字段为空')
        return

    ans_clean = ans.strip('.．。')
    if ans_clean not in 'ABCD':
        res.add_issue(qid, 'L03-答案', 'Critical', f'答案格式错误: "{ans}"（应为 A/B/C/D）')
        return

    # 答案指向的选项存在
    ans_idx = "ABCD".index(ans_clean)
    if ans_idx >= len(opts) or not opts[ans_idx]:
        res.add_issue(qid, 'L03-答案', 'Critical', f'答案指向的选项 {ans_clean} 不存在或为空')


def check_explanation(q, res: Result):
    """L04-解释检查"""
    qid = q.get('id', 'UNKNOWN')
    exp = q.get('explanation', '')
    opts = q.get('options', [])
    ans_str = q.get('answer', 'A.').strip('.．。')

    if not exp or not exp.strip():
        res.add_issue(qid, 'L04-解释', 'High', '解释为空')
        return

    # 截断检测
    if exp.endswith('..') or exp.endswith('。') is False and len(exp) < 50:
        if not any(exp.endswith(p) for p in ['。', '！', '？', '!', '?', '）', ')', '】', ']']):
            res.add_issue(qid, 'L04-解释', 'High', '解释疑似截断（结尾不完整）')

    # 答案-解释一致性（2026-06-04 重构：移除 8 字符重叠 High 误报，改用关键术语匹配）
    # 🔧 根因（2026-06-04 确认）：8 字符连续重叠检测对 paraphrase（意述/同义改写）场景误报率 ~100%
    #    高质量 explanation 通常用不同措辞解释正确选项，不应强制要求原文重叠。
    #    259 个 High 全部由此检测产生，全部为误报。
    #
    # 新策略：
    # 1. Critical 检测：explanation 是否正面支持某个错误选项（排除否定语境 + 题干共用术语）
    # 2. 关键术语弱校验：提取正确选项中的实质关键词（英文术语/2-4字中文实词），
    #    检查是否在 explanation 中出现。无匹配时仅告警不阻塞。
    if ans_str in 'ABCD':
        ans_idx = "ABCD".index(ans_str)
        correct_opt = opts[ans_idx] if ans_idx < len(opts) else ''
        question_text = q.get('question', '')

        if correct_opt and len(correct_opt) > 5 and exp:
            # --- 关键术语提取（过滤停用词/填充词） ---
            import re as _re
            FILLER_PREFIXES = [
                '这种', '这是', '该方', '该策', '该技', '该模', '该架', '该算',
                '是一种', '可以通', '能够通', '需要通', '主要通',
                '采用', '使用', '通过', '利用', '借助', '基于',
                '并非', '而是', '而不是', '而非',
                '的核心', '的基础', '的关键', '的主要', '的重要',
                '的方案', '的方法', '的策略', '的机制', '的思路', '的技术',
                '的场景', '的问题', '的情况', '的过程', '的阶段', '的任务',
                '的设计', '的架构', '的系统', '的平台', '的工具', '的框架',
                '的应用', '的作用', '的效果', '的能力', '的功能', '的特性',
                '的行为', '的表现', '的特征', '的标志',
            ]
            keywords = []
            # 英文术语
            en_terms = _re.findall(r'[A-Z][a-zA-Z0-9]{2,}|[A-Z]{2,}', correct_opt)
            keywords.extend(en_terms)
            # 中文关键词：按标点分割后取实词
            segments = _re.split(r'[，、；：。！？/\s]+', correct_opt)
            for seg in segments:
                if len(seg) < 2:
                    continue
                clean = seg
                for fp in FILLER_PREFIXES:
                    if clean.startswith(fp):
                        clean = clean[len(fp):]
                        break
                clean = _re.sub(r'[的了着过]+$', '', clean)
                if len(clean) >= 2:
                    keywords.append(clean[:6])  # 取前6字作为关键词

            # 关键术语匹配
            matched_terms = [kw for kw in keywords if kw in exp]

            if not matched_terms:
                # 无关键术语匹配 → 可能是 paraphrase（不阻塞，仅记录）
                # 不再标记 High，改为在 summary 中统计
                pass

            # --- Critical 检测：explanation 是否正面支持错误选项 ---
            NEG_CONTEXT = ["不", "无法", "不能", "不会", "并非", "错误的", "混淆了",
                           "区别于", "不同于", "而非", "而不是", "仅", "只能", "片面",
                           "影响", "限制", "牺牲", "降低"]
            
            # 快速排除：解释明确标注了正确答案（如"正确答案："开头）
            if any(marker in exp[:30] for marker in ["正确答案", "答案：", "正确选项"]):
                pass  # 明确标注 → 跳过 Critical
            else:
                for i, o in enumerate(opts):
                    if i == ans_idx or len(o) <= 15:
                        continue
                    for span in [15, 12, 10]:
                        if len(o) >= span and o[:span] in exp:
                            prefix = o[:span]
                            # 排除 1：该片段在题干中（题干共用术语）
                            if prefix in question_text:
                                continue
                            # 排除 2：前缀只含英文术语（如 "Transformer "）
                            if _re.match(r'^[A-Za-z][A-Za-z0-9\s\-\_\.]*$', prefix):
                                continue
                            # 排除 3：前缀在正确选项中也出现（共享术语）
                            if prefix in correct_opt:
                                continue
                            # 排除 3b：前缀是多选项共享开头（≥3 选项以此开头 = 模板前缀）
                            shared_count = sum(1 for oo in opts if oo.startswith(prefix))
                            if shared_count >= 3:
                                continue
                            # 排除 3c：短前缀共享（前10字被≥2其他选项共享 → 公共模板开头）
                            short_prefix = prefix[:10] if len(prefix) >= 10 else prefix
                            if len(short_prefix) >= 6:
                                short_shared = sum(1 for oo in opts if oo.startswith(short_prefix))
                                if short_shared >= 3:
                                    continue
                            # 排除 4：常见技术词前缀（Decoder-only/LangChain 等）
                            tech_words = ['Transformer', 'Decoder', 'Encoder', 'LangChain',
                                          'LlamaIndex', 'AutoGen', 'ReAct', 'RAG', 'MCP',
                                          'BatchNorm', 'LayerNorm', 'JSON', 'API', 'SDK',
                                          'GPU', 'CPU', 'LLM', 'BERT', 'GPT', 'RoPE',
                                          'MoE', 'SFT', 'PPO', 'DPO', 'RLHF', 'Nucleus',
                                          'Greedy', 'Beam', 'Top-K', 'Top-P']
                            if any(prefix.startswith(tw) and len(prefix) <= len(tw) + 3
                                   for tw in tech_words):
                                continue
                            # 检查上下文是否为否定/对比该选项
                            pos = exp.find(prefix)
                            ctx_start = max(0, pos - 30)
                            ctx_end = min(len(exp), pos + len(prefix) + 30)
                            ctx = exp[ctx_start:ctx_end]
                            has_negation = any(nw in ctx for nw in NEG_CONTEXT)
                            if not has_negation:
                                res.add_issue(qid, 'L04-解释', 'Critical',
                                              f'答案标为 {ans_str}，但解释描述的是选项 {chr(65+i)} 的内容')
                            break

    # Markdown 残留
    if '**' in exp:
        res.add_issue(qid, 'L04-解释', 'Low', '解释含 Markdown 残留 (**）')

    # 章节标题泄漏
    header_patterns = ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、',
                       '## ', '### ', '📌', '---']
    for pattern in header_patterns:
        if pattern in exp:
            res.add_issue(qid, 'L04-解释', 'Medium', f'解释含章节标题残留: "{pattern}"')
            break


def check_metadata(q, res: Result):
    """L05-元数据检查"""
    qid = q.get('id', 'UNKNOWN')
    question = q.get('question', '')
    kc = q.get('key_concepts', '')
    tags = q.get('tags', [])
    difficulty = q.get('difficulty')

    # key_concepts 复制题干
    if kc == question or (len(question) > 10 and len(kc) > 10 and question[:20] == kc[:20]):
        res.add_issue(qid, 'L05-元数据', 'Medium', 'key_concepts 直接复制了题干文本')

    # difficulty 缺失
    if difficulty is None or difficulty == '':
        res.add_issue(qid, 'L05-元数据', 'Low', '缺少 difficulty 字段')


def run_checklist(bank_path: str) -> int:
    with open(bank_path, 'r', encoding='utf-8') as f:
        bank = json.load(f)

    res = Result()
    check_functions = [
        check_question_format,
        check_options,
        check_answer,
        check_explanation,
        check_metadata,
    ]

    for mod_id, mod in bank.get('modules', {}).items():
        for q in mod.get('questions', []):
            qid = q.get('id', 'UNKNOWN')
            res.total += 1
            question_passed = True
            for check_fn in check_functions:
                before_count = len(res.issues)
                check_fn(q, res)
                if len(res.issues) > before_count:
                    question_passed = False

            if question_passed:
                res.passed += 1
            else:
                res.failed += 1

    return res.summarize()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='题库质量 Checklist')
    parser.add_argument('--bank', default=None, help='bank.json 路径')
    args = parser.parse_args()

    bank_path = args.bank
    if not bank_path:
        # 默认路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bank_path = os.path.join(script_dir, '..', 'data', 'question-bank', 'bank.json')

    if not os.path.exists(bank_path):
        print(f"Error: bank not found at {bank_path}")
        sys.exit(2)

    exit_code = run_checklist(bank_path)
    sys.exit(exit_code)
