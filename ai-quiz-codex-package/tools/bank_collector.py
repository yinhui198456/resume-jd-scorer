#!/usr/bin/env python3
"""
bank_collector.py — 题库搜集 Loop 控制器

设计理念：不是每次 prompt LLM「帮我搜集题目」，而是设计一个循环，
让系统自动迭代：搜集→验证→入库→反馈→自适应

用法：
    python3 bank_collector.py --loop --target 35    # 每模块至少 35 题
    python3 bank_collector.py --loop --target 35 --max-iter 20
    python3 bank_collector.py --status              # 查看当前各模块题数
    python3 bank_collector.py --dry-run             # 模拟运行，不写入
"""

import json
import sys
import os
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# === 路径配置 ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
BANK_PATH = os.path.join(ROOT_DIR, 'data', 'question-bank', 'bank.json')
PROGRESS_PATH = os.path.join(ROOT_DIR, 'data', 'tracking', 'progress.json')
CHANGELOG_PATH = os.path.join(ROOT_DIR, 'data', 'question-bank', 'changelog.md')
COLLECTOR_STATE_PATH = os.path.join(ROOT_DIR, 'data', 'tracking', 'collector_state.json')


# === 数据源配置 ===
SOURCES = [
    # === Y44 共享数据源（优先，已采集结构化数据） ===
    {
        "id": "y44_github",
        "name": "Y44: GitHub 面试仓库",
        "type": "y44_local",
        "path": "/root/.hermes/shared/y44/github/repos.json",
        "scraper_skill": "scraper-github-repos",
        "priority": 0.95,
        "enabled": True,
    },
    {
        "id": "y44_nowcoder",
        "name": "Y44: 牛客面经",
        "type": "y44_local",
        "path": "/root/.hermes/shared/y44/nowcoder/sample_experiences.json",
        "scraper_skill": "scraper-nowcoder",
        "priority": 0.9,
        "enabled": True,
    },
    {
        "id": "y44_cnblogs",
        "name": "Y44: 博客园技术文章",
        "type": "y44_local",
        "path": "/root/.hermes/shared/y44/cnblogs/latest_posts.json",
        "scraper_skill": "scraper-cnblogs",
        "priority": 0.7,
        "enabled": True,
    },
    # === 在线源（补充，需 LLM web_search） ===
    {
        "id": "github_llm_interview",
        "name": "GitHub: llm_interview",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/imClumsyPanda/llm_interview/main/README.md",
        "scraper_skill": "scraper-github-repos",
        "priority": 0.8,
        "enabled": True,
    },
    {
        "id": "github_ai_eng",
        "name": "GitHub: ai-engineering-interview",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/amitshekhariitbhu/ai-engineering-interview-questions/main/README.md",
        "scraper_skill": "scraper-github-repos",
        "priority": 0.7,
        "enabled": True,
    },
    {
        "id": "github_llm_genai",
        "name": "GitHub: LLMInterviewQuestions",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/llmgenai/LLMInterviewQuestions/main/README.md",
        "scraper_skill": "scraper-github-repos",
        "priority": 0.7,
        "enabled": True,
    },
    {
        "id": "github_devinterview",
        "name": "GitHub: llms-interview-questions",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/Devinterview-io/llms-interview-questions/main/README.md",
        "scraper_skill": "scraper-github-repos",
        "priority": 0.6,
        "enabled": True,
    },
    {
        "id": "nowcoder",
        "name": "牛客网面经",
        "type": "search",
        "query": 'site:nowcoder.com "大模型面试" OR "LLM面试" OR "AI算法工程师面试" 面经 2026',
        "scraper_skill": "scraper-nowcoder",
        "priority": 0.9,
        "enabled": True,
    },
    {
        "id": "juejin",
        "name": "掘金技术文章",
        "type": "search",
        "query": 'site:juejin.cn "大模型面试题" OR "LLM面试" OR "Agentic面试"',
        "scraper_skill": "scraper-search-engines",
        "priority": 0.8,
        "enabled": True,
    },
    {
        "id": "zhihu",
        "name": "知乎问答",
        "type": "search",
        "query": 'site:zhihu.com "大模型面试" OR "LLM面试题" OR "AI算法工程师面试经验"',
        "scraper_skill": "scraper-search-engines",
        "priority": 0.7,
        "enabled": True,
    },
    {
        "id": "csdn",
        "name": "CSDN博客",
        "type": "search",
        "query": 'site:blog.csdn.net "大模型面试题" OR "LLM面试"',
        "scraper_skill": "scraper-search-engines",
        "priority": 0.5,
        "enabled": True,
    },
]

# 质量检查黑名单
TEMPLATE_SUFFIXES = [
    '这在某些架构设计中可能被考虑但不是该方案的核心机制',
    '这无法应对复杂场景下的指令边界判断',
    '但这只能缓解通信问题无法从根本上解决上下文窗口限制',
    '但这忽略了实际部署中的关键约束条件',
    '这在某些特定场景下可能成立',
    '在实际部署中往往难以达到预期效果',
    '这种理解来源于对底层机制的简化',
    '不过现代架构已采用不同方案',
    '但这仅适用于特定场景',
    '该方案在早期系统中常见',
]

OBVIOUS_PATTERNS = ['完全不', '只需', '总是', '所有', '无需', '没有任何', '一定不']


# === 核心类 ===

class QualityGateInterceptionLogger:
    """质量门控拦截日志 — 记录每次拦截的原因和上下文，用于反馈闭环"""
    
    def __init__(self, state_path: str):
        self.state_path = state_path
        self.interceptions = self._load()
    
    def _load(self) -> list:
        log_path = self.state_path.replace('.json', '_interceptions.json')
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                return json.load(f)
        return []
    
    def _save(self):
        log_path = self.state_path.replace('.json', '_interceptions.json')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'w') as f:
            json.dump(self.interceptions, f, ensure_ascii=False, indent=2)
    
    def log(self, reason: str, question: dict, source_id: str, module: str):
        self.interceptions.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'reason': reason,
            'source': source_id,
            'module': module,
            'question_preview': question.get('question', '')[:50],
        })
        self._save()
    
    def get_trend(self, last_n: int = 50) -> dict:
        """分析最近 N 次拦截的原因分布"""
        recent = self.interceptions[-last_n:]
        reason_counts = {}
        for entry in recent:
            r = entry['reason']
            # 归类到主类别
            category = self._categorize_reason(r)
            reason_counts[category] = reason_counts.get(category, 0) + 1
        return reason_counts
    
    @staticmethod
    def _categorize_reason(reason: str) -> str:
        if '模板' in reason or 'filler' in reason.lower():
            return 'filler_patterns'
        if '绝对化' in reason or '所有' in reason or '无需' in reason:
            return 'absolute_words'
        if '长度' in reason or '偏见' in reason:
            return 'length_bias'
        if '重复' in reason:
            return 'duplicate_options'
        if '空' in reason or '短' in reason:
            return 'empty_too_short'
        if '越界' in reason or '格式' in reason:
            return 'format_error'
        return 'other'
    
    def generate_adaptive_prompt_suffix(self, last_n: int = 50) -> str:
        """根据拦截趋势生成自适应 prompt 后缀，注入到下一轮搜集指令中"""
        trend = self.get_trend(last_n)
        if not trend:
            return ""
        
        suffixes = []
        sorted_reasons = sorted(trend.items(), key=lambda x: x[1], reverse=True)
        
        for category, count in sorted_reasons[:3]:  # 只处理 Top 3 拦截原因
            if category == 'length_bias':
                suffixes.append(
                    f"⚠️ 最近 {count} 道题因「答案比干扰项长太多」被拦截。"
                    f"请确保干扰项与正确答案长度差 ≤ 30%，可通过追加技术细节加长干扰项。"
                )
            elif category == 'filler_patterns':
                suffixes.append(
                    f"⚠️ 最近 {count} 道题因「含模板填充词」被拦截。"
                    f"严禁使用「这在某些架构设计中」「这仅适用于特定场景」等空洞后缀，"
                    f"干扰项必须是独立、专业的技术描述。"
                )
            elif category == 'absolute_words':
                suffixes.append(
                    f"⚠️ 最近 {count} 道题因「含绝对化词（所有/无需/完全不）」被拦截。"
                    f"干扰项中禁止使用绝对化措辞，改用「通常需要」「多数情况下」等温和表述。"
                )
            elif category == 'duplicate_options':
                suffixes.append(
                    f"⚠️ 最近 {count} 道题因「选项重复」被拦截。"
                    f"四个选项必须在语义上完全独立，不能是同一概念的不同说法。"
                )
            elif category == 'empty_too_short':
                suffixes.append(
                    f"⚠️ 最近 {count} 道题因「题干过短/选项为空」被拦截。"
                    f"题干至少 10 字，四个选项都必须有实质性内容。"
                )
        
        if suffixes:
            return "\n\n📊 **自适应反馈（基于历史拦截数据）**\n" + "\n".join(suffixes)
        return ""


class QuestionDedupCache:
    """题干去重缓存"""
    
    def __init__(self, bank: dict):
        self._hashes = set()
        for mod_key, mod_data in bank.get('modules', {}).items():
            for q in mod_data.get('questions', []):
                q_text = q.get('question', '').strip()
                if q_text:
                    self._hashes.add(self._hash_text(q_text))
    
    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def is_duplicate(self, question_text: str) -> bool:
        return self._hash_text(question_text.strip()) in self._hashes
    
    def add(self, question_text: str):
        self._hashes.add(self._hash_text(question_text.strip()))


class QualityGate:
    """入库前质量预检（轻量版，不依赖 bank_checklist.py 全量扫描）"""
    
    def check(self, question: dict) -> Tuple[bool, str]:
        """返回 (通过, 原因)"""
        q_text = question.get('question', '').strip()
        options = question.get('options', [])
        answer = question.get('answer', '').strip().rstrip('.')
        explanation = question.get('explanation', '')
        
        # 1. 题干不能为空
        if not q_text:
            return False, "题干为空"
        
        # 2. 题干至少 10 字
        if len(q_text) < 10:
            return False, f"题干过短 ({len(q_text)} 字)"
        
        # 3. 选项数量
        if len(options) != 4:
            return False, f"选项数量不为 4 ({len(options)})"
        
        # 4. 选项不能为空
        for i, opt in enumerate(options):
            if not opt.strip():
                return False, f"选项 {chr(65+i)} 为空"
        
        # 5. 选项不能重复
        opt_set = set()
        for opt in options:
            clean = opt.strip()
            if clean in opt_set:
                return False, f"选项重复: {clean[:20]}..."
            opt_set.add(clean)
        
        # 6. 答案必须在 A-D 范围内
        if answer not in ('A', 'B', 'C', 'D'):
            return False, f"答案格式错误: {answer}"
        
        # 7. 答案索引不能越界
        answer_idx = ord(answer) - ord('A')
        if answer_idx >= len(options):
            return False, f"答案越界: {answer} 但只有 {len(options)} 个选项"
        
        # 8. 检查模板填充词
        for suffix in TEMPLATE_SUFFIXES:
            for opt in options:
                if suffix in opt:
                    return False, f"选项含模板后缀: {suffix[:15]}..."
        
        # 9. 检查明显错误词
        for i, opt in enumerate(options):
            label = chr(65 + i)
            if label != answer:  # 只检查干扰项
                for pattern in OBVIOUS_PATTERNS:
                    if pattern in opt and len(opt) < 30:  # 短选项+绝对化词
                        return False, f"干扰项 {label} 含绝对化词: {pattern}"
        
        # 10. 长度偏见检查（答案不应比干扰项长太多）
        answer_len = len(options[answer_idx])
        distractor_lens = [len(options[i]) for i in range(4) if i != answer_idx]
        avg_distractor_len = sum(distractor_lens) / len(distractor_lens) if distractor_lens else 0
        if avg_distractor_len > 0 and answer_len > avg_distractor_len * 1.8:
            return False, f"长度偏见: 答案 {answer_len} 字 vs 干扰项平均 {avg_distractor_len:.0f} 字"
        
        # 11. 解析不能为空
        if not explanation.strip():
            return False, "解析为空"
        
        # 全部通过
        return True, ""


class ModuleGapAnalyzer:
    """分析各模块题数缺口 — 流动模式：不设上限，持续补充高质量题目"""
    
    def __init__(self, bank: dict, target_per_module: int = 50):
        self.target = target_per_module  # 软目标，不设硬性上限
        self.module_counts = {}
        self.gaps = {}
        for mod_key, mod_data in bank.get('modules', {}).items():
            count = len(mod_data.get('questions', []))
            self.module_counts[mod_key] = count
            if count < target_per_module:
                self.gaps[mod_key] = {
                    'current': count,
                    'target': target_per_module,
                    'need': target_per_module - count,
                }
    
    def has_gaps(self) -> bool:
        """即使全部达标，也继续搜集（流动模式）"""
        return True  # 永远返回 True，持续搜集
    
    def get_priority_modules(self, max_count: int = 3) -> List[str]:
        """按题数从少到多排序，优先补充薄弱模块"""
        sorted_modules = sorted(self.module_counts.items(), key=lambda x: x[1])
        return [mod_key for mod_key, _ in sorted_modules[:max_count]]
    
    def summary(self) -> str:
        lines = []
        for mod_key in sorted(self.module_counts.keys()):
            count = self.module_counts[mod_key]
            status = "⚠️ 薄弱" if count < 35 else ("✅ 达标" if count < 50 else "📈 丰富")
            lines.append(f"  {mod_key}: {count} 题 {status}")
        return '\n'.join(lines)


class SourceScorer:
    """数据源评分器（自适应优先 + 连续 streak 追踪）"""
    
    def __init__(self, state_path: str):
        self.state_path = state_path
        self.scores = self._load()
    
    def _load(self) -> dict:
        if os.path.exists(self.state_path):
            with open(self.state_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save(self):
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, 'w') as f:
            json.dump(self.scores, f, ensure_ascii=False, indent=2)
    
    def record(self, source_id: str, collected: int, passed: int, injected: int):
        if source_id not in self.scores:
            self.scores[source_id] = {
                'total_runs': 0,
                'total_collected': 0,
                'total_passed': 0,
                'total_injected': 0,
                'streak': 0,       # 连续成功轮次（>0）或连续失败轮次（<0）
                'streak_best': 0,  # 历史最佳连续成功
                'streak_worst': 0, # 历史最差连续失败
            }
        s = self.scores[source_id]
        s['total_runs'] += 1
        s['total_collected'] += collected
        s['total_passed'] += passed
        s['total_injected'] += injected
        s['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 兼容旧数据：缺少新字段时初始化
        s.setdefault('streak', 0)
        s.setdefault('streak_best', 0)
        s.setdefault('streak_worst', 0)
        s.setdefault('temporary_demotion', False)
        
        # 更新 streak：有入库 = 成功，0 入库 = 失败
        if injected > 0:
            s['streak'] = max(1, s['streak'] + 1)
            s['streak_best'] = max(s['streak_best'], s['streak'])
        else:
            s['streak'] = min(-1, s['streak'] - 1)
            s['streak_worst'] = min(s['streak_worst'], s['streak'])
        
        # 连续 5 次失败 → 临时降权标记
        if s['streak'] <= -5:
            s['temporary_demotion'] = True
        elif s['streak'] >= 3:
            s['temporary_demotion'] = False
        
        self._save()
    
    def get_sorted_sources(self, sources: list) -> list:
        """按通过率 + streak 综合排序，连续失败降权"""
        def score(source):
            sid = source['id']
            if sid not in self.scores:
                return source.get('priority', 0.5)
            s = self.scores[sid]
            if s['total_collected'] == 0:
                return source.get('priority', 0.5)
            pass_rate = s['total_passed'] / s['total_collected']
            base_score = pass_rate * 0.6 + source.get('priority', 0.5) * 0.3
            
            # Streak 微调：连续成功加分，连续失败扣分
            streak = s.get('streak', 0)
            streak_bonus = streak * 0.02  # 每连续成功+2%，连续失败-2%
            base_score += streak_bonus
            
            # 临时降权：连续 5+ 次失败，权重减半
            if s.get('temporary_demotion', False):
                base_score *= 0.5
            
            return base_score
        return sorted(sources, key=score, reverse=True)
    
    def summary(self) -> str:
        if not self.scores:
            return "  （无历史数据）"
        lines = []
        # 过滤掉非 dict 的顶层键（如 last_collection/last_added）
        source_items = {k: v for k, v in self.scores.items() if isinstance(v, dict)}
        for sid, s in sorted(source_items.items(), key=lambda x: x[1].get('total_injected', 0), reverse=True):
            collected = s.get('total_collected', 0)
            passed = s.get('total_passed', 0)
            injected = s.get('total_injected', 0)
            pass_rate = (passed / collected * 100) if collected > 0 else 0
            streak = s.get('streak', 0)
            streak_str = f"🔥连续{streak}轮成功" if streak > 0 else (f"❄️连续{-streak}轮失败" if streak < 0 else "中性")
            demotion = "⚠️降权" if s.get('temporary_demotion', False) else ""
            lines.append(f"  {sid}: 搜集 {collected} → 通过 {passed} ({pass_rate:.0f}%) → 入库 {injected} | {streak_str} {demotion}")
        return '\n'.join(lines)


class BankCollectorLoop:
    """题库搜集循环控制器"""
    
    def __init__(self, target_per_module: int = 35, max_iterations: int = 20, dry_run: bool = False):
        self.target = target_per_module
        self.max_iter = max_iterations
        self.dry_run = dry_run
        self.session_log = []
        self.total_collected = 0
        self.total_passed = 0
        self.total_injected = 0
        self.total_failed = 0
        self.total_duplicates = 0
        
        # 加载数据
        self.bank = self._load_bank()
        self.gap_analyzer = ModuleGapAnalyzer(self.bank, target_per_module)
        self.dedup_cache = QuestionDedupCache(self.bank)
        self.quality_gate = QualityGate()
        self.source_scorer = SourceScorer(COLLECTOR_STATE_PATH)
        self.interception_logger = QualityGateInterceptionLogger(COLLECTOR_STATE_PATH)
    
    def _load_bank(self) -> dict:
        with open(BANK_PATH, 'r') as f:
            return json.load(f)
    
    def _save_bank(self):
        if self.dry_run:
            print("[DRY RUN] 跳过写入 bank.json")
            return
        tmp_path = BANK_PATH + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(self.bank, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, BANK_PATH)
    
    def _append_changelog(self, entry: str):
        if self.dry_run:
            return
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        with open(CHANGELOG_PATH, 'a') as f:
            f.write(f"\n### {timestamp}\n{entry}\n")
    
    def run(self, interactive=False):
        """主循环
        
        Args:
            interactive: 交互式模式，每轮暂停等待 LLM 提取题目后继续
        """
        start_time = time.time()
        print(f"=== 题库搜集 Loop 启动 ===")
        print(f"目标: 每模块至少 {self.target} 题")
        print(f"最大迭代: {self.max_iter}")
        print(f"{'[DRY RUN] ' if self.dry_run else ''}")
        if interactive:
            print("模式: 交互式（每轮等待 LLM 提取）")
        print()
        
        # 初始缺口
        print("📊 初始模块缺口:")
        print(self.gap_analyzer.summary())
        print()
        
        iteration = 0
        while iteration < self.max_iter:
            # 检查是否还有缺口
            if not self.gap_analyzer.has_gaps():
                print("✅ 所有模块已达标，循环结束")
                break
            
            iteration += 1
            print(f"\n--- 第 {iteration} 轮 ---")
            
            # 1. 选源（自适应排序）— 本轮遍历所有启用的源
            enabled_sources = [s for s in SOURCES if s.get('enabled', True)]
            sorted_sources = self.source_scorer.get_sorted_sources(enabled_sources)
            print(f"📡 本轮将遍历 {len(sorted_sources)} 个源（按优先级排序）")
            print()
            
            for source_idx, current_source in enumerate(sorted_sources):
                print(f"  [{source_idx+1}/{len(sorted_sources)}] {current_source['name']}")
            
            # 2. 对每个源执行一轮提取
            for source_idx, current_source in enumerate(sorted_sources):
                # 2a. 确定目标模块（每轮动态选择最薄弱的）
                priority_modules = self.gap_analyzer.get_priority_modules(max_count=3)
                target_module = priority_modules[0] if priority_modules else None
                
                if not target_module:
                    print(f"\n  ⏭️ 无目标模块，跳过剩余源")
                    break
                
                print(f"\n  ── 源 {source_idx+1}: {current_source['name']} → {target_module} ──")
                
                # 2b. 生成 LLM 提取指令
                llm_prompt = self._generate_llm_prompt(current_source, target_module)
                
                if interactive:
                    # 交互式：输出完整 prompt，等待 LLM 提取
                    print(f"  📝 LLM 提取指令:")
                    print(llm_prompt)
                    print(f"  ⏸️ 等待 LLM 提取后注入...")
                    break  # 交互模式每源 break，等注入后继续下一个
                else:
                    # 非交互（纯展示模式）：输出所有源的 prompt 摘要，不 break
                    print(f"  🔍 prompt 已生成")
                    print(f"  📝 指令摘要: {llm_prompt[:200]}...")
                    # 继续下一个源，不 break
            
            print()
        
        elapsed = time.time() - start_time
        print(f"\n=== 循环结束 (耗时 {elapsed:.1f}s) ===")
        self._print_report()
    
    def _generate_llm_prompt(self, source: dict, target_module: str) -> str:
        """生成给 LLM 的提取指令"""
        source_type = source.get('type', '')
        scraper_skill = source.get('scraper_skill', '')
        
        skill_instruction = f"""
📚 **步骤 0：加载抓取 Skill**
请先加载对应的抓取 Skill 获取详细规范：
- 技能名：`{scraper_skill}`
- 执行命令：`skill_view(name='{scraper_skill}')`
- 严格按照 Skill 中的「抓取方法」、「提取规则」和「铁律」执行。
"""

        if source_type == 'y44_local':
            path = source.get('path', '')
            adaptive_suffix = self.interception_logger.generate_adaptive_prompt_suffix()
            return f"""{skill_instruction}
请从 Y44 共享数据源中**提取**与「{target_module}」相关的面试题：

数据源: {source['name']}
文件路径: {path}

⛔ 铁律（违反视为严重事故）：
- **绝对禁止**凭自己的知识编写/创作/编造题目
- **绝对禁止**用"专业知识"补充内容
- **只能**从实际文件内容中提取已有信息
- 如果文件内容中没有相关题目，直接返回空数组 []

📋 **重要：从问答题生成 MCQ 的策略**
中文互联网的 AI 面试题 90% 是问答题格式（Q&A），不是现成的选择题。
你可以从真实问答题中生成 MCQ，但必须遵循以下规则：

1. **提取题干和正确答案**：从问答题中提取原始题干和标准答案（作为正确选项）
2. **生成干扰项策略（真实技术混淆）**：
   - **竞品概念张冠李戴**：把正确技术的特点安到另一个真实技术上
   - **常见误区**：开发者容易混淆的相似概念
   - **边界条件混淆**：适用场景、性能特征、限制条件的错误陈述
3. **干扰项要求**：
   - 必须使用真实存在的技术名词
   - 必须与正确答案长度相当（字数差 ≤ 30%）
   - 必须结构平行
   - 禁止使用空洞模板后缀

操作步骤:
1. 读取索引文件: `cat {path}`
2. 如果内容是仓库列表（如 repos.json）:
   a. 选择与 {target_module} 最相关的仓库
   b. 按照 `scraper-github-repos` Skill 的方法 curl 仓库内容
   c. **仅从 curl 返回的真实内容中**提取题目
3. 如果内容是面经索引:
   a. 找有具体问题的面经
   b. 按照对应 Skill 的方法抓取具体内容
   c. **仅从面经内容中**提取题目
4. 如果是问答题，提取题干+标准答案，按上述策略生成 3 个干扰项
5. 提取 2-4 道高质量题目（宁缺毋滥）
6. 输出 JSON 格式...{adaptive_suffix}
"""
        elif source_type == 'github_raw':
            url = source.get('url', '')
            adaptive_suffix = self.interception_logger.generate_adaptive_prompt_suffix()
            return f"""{skill_instruction}
请从以下数据源中**提取**与「{target_module}」相关的面试题：

源: {source['name']}
类型: github_raw
URL: {url}

⛔ 铁律（违反视为严重事故）：
- **绝对禁止**凭自己的知识编写/创作/编造题目
- **只能**从 curl 下载的真实内容中提取
- 如果 curl 内容为空或 404，直接返回空数组 []

📋 **重要：从问答题生成 MCQ 的策略**
中文互联网的 AI 面试题 90% 是问答题格式（Q&A），不是现成的选择题。
你可以从真实问答题中生成 MCQ，但必须遵循以下规则：

1. **提取题干和正确答案**：从问答题中提取原始题干和标准答案（作为正确选项）
2. **生成干扰项策略（真实技术混淆）**：
   - **竞品概念张冠李戴**：把正确技术的特点安到另一个真实技术上
   - **常见误区**：开发者容易混淆的相似概念
   - **边界条件混淆**：适用场景、性能特征、限制条件的错误陈述
3. **干扰项要求**：
   - 必须使用真实存在的技术名词
   - 必须与正确答案长度相当（字数差 ≤ 30%）
   - 必须结构平行
   - 禁止使用空洞模板后缀

操作步骤:
1. 按照 `scraper-github-repos` Skill 的方法 curl 下载内容
2. **仅从返回的真实内容中**提取与 {target_module} 相关的题目
3. 如果是问答题，提取题干+标准答案，按上述策略生成 3 个干扰项
4. 提取 2-4 道高质量题目（宁缺毋滥）
5. 输出 JSON 格式...{adaptive_suffix}
"""
        else:
            # search 类型
            query = source.get('query', '')
            adaptive_suffix = self.interception_logger.generate_adaptive_prompt_suffix()
            return f"""{skill_instruction}
请从以下数据源中**提取**与「{target_module}」相关的面试题：

源: {source['name']}
类型: search
搜索: {query}

⛔ 铁律（违反视为严重事故）：
- **绝对禁止**凭自己的知识编写/创作/编造题目
- **只能**从 web_search 返回的真实搜索结果中提取
- **题干和标准答案**必须来自真实内容，禁止编造
- 如果搜索结果为空或不相关，直接返回空数组 []

📋 **重要：从问答题生成 MCQ 的策略**
中文互联网的 AI 面试题 90% 是问答题格式（Q&A），不是现成的选择题。
你可以从真实问答题中生成 MCQ，但必须遵循以下规则：

1. **提取题干和正确答案**：从问答题中提取原始题干和标准答案（作为正确选项）
2. **生成干扰项策略（真实技术混淆）**：
   - **竞品概念张冠李戴**：把正确技术的特点安到另一个真实技术上
   - **常见误区**：开发者容易混淆的相似概念
   - **边界条件混淆**：适用场景、性能特征、限制条件的错误陈述
3. **干扰项要求**：
   - 必须使用真实存在的技术名词（如 ViT、Swin、MAE、DINO 等）
   - 必须与正确答案长度相当（字数差 ≤ 30%）
   - 必须结构平行（如果正确答案是「X 通过 Y 实现 Z」，干扰项也必须是「A 通过 B 实现 C」）
   - 禁止使用「这仅适用于特定场景」「在实际部署中往往难以达到预期效果」等空洞模板

操作步骤:
1. 按照对应 Scraper Skill 的方法执行搜索和抓取
2. **仅从搜索结果页面的真实内容中**提取题目
3. 如果是问答题，提取题干+标准答案，按上述策略生成 3 个干扰项
4. 提取 2-4 道高质量题目（宁缺毋滥）
5. 输出 JSON 格式...{adaptive_suffix}
"""
    
    def process_extracted_questions(self, questions: list, source_id: str, target_module: str):
        """处理 LLM 提取的题目（在实际 cron 场景中调用）"""
        collected = len(questions)
        passed_questions = []
        
        for q in questions:
            # 质量检查
            ok, reason = self.quality_gate.check(q)
            if not ok:
                self.total_failed += 1
                # 🔁 Loop 关键：记录拦截原因，供下一轮自适应
                self.interception_logger.log(reason, q, source_id, target_module)
                print(f"  ❌ 质量不合格: {reason}")
                continue
            
            # 去重
            if self.dedup_cache.is_duplicate(q['question']):
                self.total_duplicates += 1
                print(f"  ⏭️ 重复题目: {q['question'][:30]}...")
                continue
            
            passed_questions.append(q)
            self.dedup_cache.add(q['question'])
        
        passed = len(passed_questions)
        
        # 入库
        injected = 0
        for q in passed_questions:
            self._inject_question(q, target_module)
            injected += 1
        
        self.total_collected += collected
        self.total_passed += passed
        self.total_injected += injected
        
        # 更新源评分
        self.source_scorer.record(source_id, collected, passed, injected)
        
        # 刷新缺口分析
        self.gap_analyzer = ModuleGapAnalyzer(self.bank, self.target)
    
    def _inject_question(self, question: dict, module_key: str):
        """写入一道题到 bank.json"""
        if module_key not in self.bank['modules']:
            print(f"  ⚠️ 模块 {module_key} 不存在，跳过")
            return
        
        # 分配 Q-ID
        existing_questions = self.bank['modules'][module_key].get('questions', [])
        max_seq = 0
        for q in existing_questions:
            qid = q.get('id', '')
            # 提取序号: Q-M08_Agent架构36 → 36
            seq_str = ''.join(filter(str.isdigit, qid.split('_')[-1]))
            if seq_str:
                max_seq = max(max_seq, int(seq_str))
        
        new_id = f"Q-{module_key}{max_seq + 1}"
        
        new_question = {
            'id': new_id,
            'question': question['question'],
            'options': question['options'],
            'answer': question['answer'].rstrip('.'),
            'explanation': question.get('explanation', ''),
            'difficulty': question.get('difficulty', 3),
            'tags': question.get('tags', []),
            'key_concepts': question.get('key_concepts', ''),
        }
        
        self.bank['modules'][module_key]['questions'].append(new_question)
        print(f"  ✅ 入库: {new_id} ({question['question'][:40]}...)")
    
    def _print_report(self):
        print("\n" + "=" * 50)
        print("📊 搜集报告")
        print("=" * 50)
        print(f"总计搜集: {self.total_collected} 题")
        print(f"质量通过: {self.total_passed} 题")
        print(f"入库: {self.total_injected} 题")
        print(f"质量不合格: {self.total_failed} 题")
        print(f"重复跳过: {self.total_duplicates} 题")
        print()
        print("📈 源评分:")
        print(self.source_scorer.summary())
        print()
        print("📊 当前模块缺口:")
        print(self.gap_analyzer.summary())
        print()
        # 🔁 Loop 反馈闭环报告
        trend = self.interception_logger.get_trend(last_n=50)
        if trend:
            print("🔁 拦截趋势（最近 50 次）:")
            for reason, count in sorted(trend.items(), key=lambda x: x[1], reverse=True):
                print(f"  {reason}: {count} 次")
            print()
            adaptive = self.interception_logger.generate_adaptive_prompt_suffix()
            if adaptive:
                print("📝 自适应反馈已注入下一轮 prompt:")
                print(adaptive[:200] + "..." if len(adaptive) > 200 else adaptive)


# === CLI 入口 ===

def cmd_status():
    """查看当前各模块题数"""
    with open(BANK_PATH, 'r') as f:
        bank = json.load(f)
    
    print("📊 题库状态")
    print(f"总模块数: {len(bank['modules'])}")
    total = sum(len(m['questions']) for m in bank['modules'].values())
    print(f"总题数: {total}")
    print()
    
    for mod_key in sorted(bank['modules'].keys()):
        count = len(bank['modules'][mod_key]['questions'])
        bar = '█' * (count // 2)
        print(f"  {mod_key:25s} {count:3d} 题 {bar}")


def cmd_loop(target=35, max_iter=20, dry_run=False):
    loop = BankCollectorLoop(target_per_module=target, max_iterations=max_iter, dry_run=dry_run)
    loop.run()


def cmd_loop_info():
    """查看 Loop 反馈闭环状态"""
    if not os.path.exists(COLLECTOR_STATE_PATH):
        print("（无 Loop 状态数据）")
        return
    
    with open(COLLECTOR_STATE_PATH, 'r') as f:
        state = json.load(f)
    
    interception_path = COLLECTOR_STATE_PATH.replace('.json', '_interceptions.json')
    if os.path.exists(interception_path):
        with open(interception_path, 'r') as f:
            interceptions = json.load(f)
    else:
        interceptions = []
    
    print("=== 🔁 Loop 反馈闭环状态 ===")
    print()
    print(f"总拦截次数: {len(interceptions)}")
    print()
    
    if interceptions:
        # 分类统计
        from collections import Counter
        reasons = Counter()
        sources = Counter()
        for entry in interceptions:
            r = QualityGateInterceptionLogger._categorize_reason(entry['reason'])
            reasons[r] += 1
            sources[entry.get('source', 'unknown')] += 1
        
        print("📊 拦截原因分布（全部）:")
        for reason, count in reasons.most_common():
            bar = '█' * (count // 2)
            print(f"  {reason}: {count} 次 {bar}")
        print()
        
        print("📡 源拦截分布:")
        for source, count in sources.most_common():
            print(f"  {source}: {count} 次")
        print()
        
        # 最近趋势
        recent = interceptions[-20:]
        recent_reasons = Counter()
        for entry in recent:
            r = QualityGateInterceptionLogger._categorize_reason(entry['reason'])
            recent_reasons[r] += 1
        
        print("📈 最近 20 次拦截趋势:")
        for reason, count in recent_reasons.most_common():
            print(f"  {reason}: {count} 次")
        print()
        
        # 自适应反馈预览
        logger = QualityGateInterceptionLogger(COLLECTOR_STATE_PATH)
        adaptive = logger.generate_adaptive_prompt_suffix()
        if adaptive:
            print("📝 当前自适应反馈（注入下一轮 prompt）:")
            print(adaptive)
        else:
            print("📝 无自适应反馈（暂无足够拦截数据）")
    else:
        print("（暂无拦截数据，首次运行后会自动积累）")
    
    print()
    # 源 streak 状态
    print("📡 源 Streak 状态:")
    scorer = SourceScorer(COLLECTOR_STATE_PATH)
    print(scorer.summary())


def cmd_inject(json_path, source_id, target_module):
    """从 JSON 文件导入题目并入库"""
    with open(json_path, 'r') as f:
        questions = json.load(f)
    print(f"📥 从 {json_path} 读取 {len(questions)} 道题目")
    print(f"📡 源: {source_id}")
    print(f"🎯 模块: {target_module}")
    print()
    
    loop = BankCollectorLoop()
    loop.process_extracted_questions(questions, source_id, target_module)
    loop._save_bank()
    loop._print_report()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='题库搜集 Loop 控制器')
    parser.add_argument('--status', action='store_true', help='查看当前题库状态')
    parser.add_argument('--loop', action='store_true', help='启动搜集循环')
    parser.add_argument('--loop-info', action='store_true', help='查看 Loop 反馈闭环状态')
    parser.add_argument('--inject', type=str, help='从 JSON 文件导入题目')
    parser.add_argument('--source', type=str, default='manual_test', help='源 ID (配合 --inject)')
    parser.add_argument('--module', type=str, help='目标模块 (配合 --inject)')
    parser.add_argument('--target', type=int, default=35, help='每模块目标题数 (default: 35)')
    parser.add_argument('--max-iter', type=int, default=20, help='最大迭代轮数 (default: 20)')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不写入')
    
    args = parser.parse_args()
    
    if args.status:
        cmd_status()
    elif args.loop_info:
        cmd_loop_info()
    elif args.inject:
        if not args.module:
            print("ERROR: --inject 需要 --module 参数")
            sys.exit(1)
        cmd_inject(args.inject, args.source, args.module)
    elif args.loop:
        cmd_loop(target=args.target, max_iter=args.max_iter, dry_run=args.dry_run)
    else:
        parser.print_help()
