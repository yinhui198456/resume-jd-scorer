#!/usr/bin/env python3
"""
quiz_bot.py — 确定性 AI 八股文刷题引擎

职责：
- 根据用户指令出题（新题 / 复习 / 指定题号）
- 判题（A/B/C/D 与答案比对）
- 更新进度（progress.json，带文件锁，与 cron 不冲突）
- 质量门控：自动跳过 quality_audit.py 判定不合格的题目
- 输出纯文本，LLM 只需原样转发

用法：
    python3 scripts/quiz_bot.py next              # 下一道未学习题
    python3 scripts/quiz_bot.py next M08_Agent架构 # 指定模块下一道
    python3 scripts/quiz_bot.py review             # 下一道到期复习题
    python3 scripts/quiz_bot.py answer Q-088 B     # 用户答 Q-088 选 B
    python3 scripts/quiz_bot.py skip Q-088         # 标记为'不会'，加入复习队列
    python3 scripts/quiz_bot.py explain Q-088      # 获取解析
    python3 scripts/quiz_bot.py status             # 当前进度
    python3 scripts/quiz_bot.py quality            # 质量门控状态
    python3 scripts/quiz_bot.py module M08_Agent架构 # 模块进度
    python3 scripts/quiz_bot.py intercepts         # 查看 Hash 拦截统计
    python3 scripts/quiz_bot.py --format md next   # 直接输出 Markdown 格式（LLM 零推理，纯转发）
"""

import json
import sys
import os
import fcntl
from datetime import datetime, date, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
TOOLS_DIR = os.path.join(ROOT_DIR, 'tools')
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

BANK_PATH = os.path.join(ROOT_DIR, 'data', 'question-bank', 'bank.json')
PROGRESS_PATH = os.path.join(ROOT_DIR, 'data', 'tracking', 'progress.json')
QUIZ_STATE_PATH = os.path.join(ROOT_DIR, 'data', 'tracking', 'quiz_bot_state.json')
QUIZ_HASH_LOG_PATH = os.path.join(ROOT_DIR, 'data', 'tracking', 'quiz_hash_log.jsonl')
QUIZ_INTERCEPT_LOG_PATH = os.path.join(ROOT_DIR, 'data', 'tracking', 'quiz_intercept_log.jsonl')

# 质量门控模块（懒加载，避免 audit 文件不存在时报错）
_quality_gate = None

def get_quality_gate():
    """懒加载质量门控器。"""
    global _quality_gate
    if _quality_gate is None:
        try:
            from quality_gate import QualityGate
            _quality_gate = QualityGate()
        except Exception:
            # 质量门控加载失败 → 降级放行所有题目
            _quality_gate = None
    return _quality_gate

REVIEW_INTERVALS = [1, 3, 7, 14, 30, 90]

# 全局输出格式：'pipe'（默认，供 LLM 解析）或 'md'（直接面向用户转发）
OUTPUT_FORMAT = 'pipe'

# 跳过的模块列表（用户可临时屏蔽某些模块）
# 修改示例：SKIPPED_MODULES = ['M01_LLM基础']
SKIPPED_MODULES = ['M01_LLM基础', 'M02_Transformer']


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def save_json(path, data):
    """带文件锁的安全写入，与 cron 的 update_daily_tracking.py 不冲突。"""
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)
    os.replace(tmp_path, path)


def load_bank():
    return load_json(BANK_PATH)


def load_progress():
    return load_json(PROGRESS_PATH)


def save_progress(progress):
    save_json(PROGRESS_PATH, progress)


def save_quiz_state(state):
    """保存 quiz_bot 会话状态（当前题号等）。"""
    save_json(QUIZ_STATE_PATH, state)


def load_quiz_state():
    if os.path.exists(QUIZ_STATE_PATH):
        return load_json(QUIZ_STATE_PATH)
    return {}


def append_hash_log(qid, q_hash):
    """P4: 将 hash 追加到只增日志文件（不可篡改的第三验证源）。"""
    import time
    log_entry = json.dumps({
        'qid': qid,
        'q_hash': q_hash,
        'timestamp': time.time()
    })
    with open(QUIZ_HASH_LOG_PATH, 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(log_entry + '\n')
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)


def get_latest_hash_from_log(qid):
    """P4: 从追加日志读取指定 QID 的最新 hash。"""
    if not os.path.exists(QUIZ_HASH_LOG_PATH):
        return None
    latest_hash = None
    with open(QUIZ_HASH_LOG_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get('qid') == qid:
                    latest_hash = entry.get('q_hash')
            except json.JSONDecodeError:
                continue
    return latest_hash


def _log_intercept(qid, reason, expected_hash=None, actual_hash=None):
    """记录拦截事件到独立的拦截日志文件（P5 可观测性）。"""
    import time
    entry = json.dumps({
        'qid': qid,
        'reason': reason,
        'expected_hash': expected_hash,
        'actual_hash': actual_hash,
        'timestamp': time.time()
    })
    with open(QUIZ_INTERCEPT_LOG_PATH, 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(entry + '\n')
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)


def cmd_skip(qid):
    """P0 修复：标记题目为'不会'，写入进度并安排复习。"""
    bank = load_bank()
    progress = load_progress()
    tracking = progress.get('question_tracking', {})
    today = str(date.today())

    # 查找题目所属模块
    target_mod = None
    target_q = None
    for mod_key, mod_data in bank['modules'].items():
        for q in mod_data['questions']:
            if q['id'] == qid:
                target_mod = mod_key
                target_q = q
                break
        if target_mod:
            break

    if not target_q:
        print(f"ERROR|题目 {qid} 不存在")
        return

    if qid not in tracking:
        tracking[qid] = {
            'module': target_mod,
            'first_learned': today,
            'last_reviewed': None,
            'review_count': 0,
            'next_review': None,
            'confidence': 1,
            'status': 'new',
            'review_history': [],
            'confidence_history': [],
            'wrong_count': 0,
        }

    t = tracking[qid]
    # 修复：确保 first_learned 不为 null（否则 next 会反复返回已跳过的题）
    if not t.get('first_learned'):
        t['first_learned'] = today
    t['confidence'] = 1
    t['wrong_count'] = t.get('wrong_count', 0) + 1
    t['last_reviewed'] = today
    t['review_count'] = t.get('review_count', 0) + 1
    t['result'] = 'skipped'
    t['status'] = 'learning'

    # 计算下次复习（confidence=1 会促使尽快复习）
    try:
        first_date = datetime.strptime(t['first_learned'], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        first_date = date.today()

    if t['review_count'] < len(REVIEW_INTERVALS):
        next_rev = calc_next_review(first_date, t['review_count'])
        t['next_review'] = str(next_rev)
    else:
        t['next_review'] = None

    progress['question_tracking'] = tracking
    save_progress(progress)

    if OUTPUT_FORMAT == 'md':
        print(f"⏭️ {qid} 已标记为'不会'，已加入复习队列（信心 1/5）")
        if t['next_review']:
            print(f"📅 下次复习: {t['next_review']}")
    else:
        print(f"SKIP|{qid}")
        print(f"CONFIDENCE|1/5")
        if t['next_review']:
            print(f"NEXT_REVIEW|{t['next_review']}")
        print("END")


def find_module_id(modules, partial):
    """查找匹配的模块 ID。"""
    for key in modules:
        if partial in key:
            return key
    return None


def calc_next_review(first_learned, review_count):
    """计算下次复习日期。"""
    if review_count >= len(REVIEW_INTERVALS):
        return None
    days = REVIEW_INTERVALS[review_count]
    return first_learned + timedelta(days=days)


def cmd_next(module_partial=None):
    """出一道未学习的题（跳过质量不合格的题目）。"""
    bank = load_bank()
    progress = load_progress()
    tracking = progress.get('question_tracking', {})
    gate = get_quality_gate()
    state = load_quiz_state()

    # P1 修复：模块锁定策略 — 每个模块至少连续刷 3 题
    locked_mod = state.get('locked_module')
    locked_count = state.get('module_question_count', 0)
    MIN_QUESTIONS_PER_MODULE = 3

    # P0: 开放题检测关键词
    OPEN_QUESTION_PATTERNS = ['面试建议', '回忆题', '开放性', '说说你', '你的看法']

    def _find_q_in_module(mod_key, mod_data):
        """在单个模块中找一道未学习的合格题目。"""
        for q in mod_data['questions']:
            tid = q['id']
            t = tracking.get(tid, {})
            if t.get('first_learned') is not None:
                continue
            q_text = q.get('question', '')
            options = q.get('options', [])
            is_open = any(pat in q_text for pat in OPEN_QUESTION_PATTERNS) or \
                      any(pat in opt for opt in options for pat in OPEN_QUESTION_PATTERNS)
            if is_open:
                continue
            if gate and not gate.is_passing(tid):
                continue
            return q
        return None

    if module_partial:
        # 用户指定模块：强制锁定，并在指定模块中找题
        mod_key = find_module_id(bank['modules'], module_partial)
        if not mod_key:
            print(f"ERROR|模块 '{module_partial}' 不存在")
            return
        q = _find_q_in_module(mod_key, bank['modules'][mod_key])
        if q:
            state['locked_module'] = mod_key
            state['module_question_count'] = 1
            save_quiz_state(state)
            _output_question(q, mod_key, "NEXT")
            return
        # 指定模块无可用题，回退到遍历所有模块
        locked_mod = None
        locked_count = 0
    elif locked_mod and locked_count < MIN_QUESTIONS_PER_MODULE:
        # 锁定模块在跳过列表中 → 强制解锁
        if locked_mod in SKIPPED_MODULES:
            locked_mod = None
            locked_count = 0
        else:
            # 已有锁定模块且未达到最小深度：优先在锁定模块中找题
            if locked_mod in bank['modules']:
                q = _find_q_in_module(locked_mod, bank['modules'][locked_mod])
                if q:
                    locked_count += 1
                    state['locked_module'] = locked_mod
                    state['module_question_count'] = locked_count
                    save_quiz_state(state)
                    _output_question(q, locked_mod, "NEXT")
                    return
            # 锁定模块无可用题 → 解锁
            locked_mod = None
            locked_count = 0

    # 未锁定、锁定模块耗尽、或达到最小深度：遍历所有模块找题
    # 优先复习模块（有到期题的模块），其次按顺序遍历
    skipped_count = 0
    for mod_key, mod_data in bank['modules'].items():
        if mod_key in SKIPPED_MODULES:
            continue
        q = _find_q_in_module(mod_key, mod_data)
        if q:
            # 锁定新模块
            state['locked_module'] = mod_key
            state['module_question_count'] = 1
            save_quiz_state(state)
            if skipped_count > 0:
                if OUTPUT_FORMAT == 'md':
                    print(f"⚠️ 已跳过 {skipped_count} 道质量不合格的题目")
                else:
                    print(f"SKIPPED|{skipped_count} 道质量不合格题目已跳过")
            _output_question(q, mod_key, "NEXT")
            return

    print("COMPLETE|所有模块题目已学完！可以开始复习模式。")


def cmd_review():
    """出一道到期复习题（跳过质量不合格的题目）。"""
    progress = load_progress()
    bank = load_bank()
    today = str(date.today())
    tracking = progress.get('question_tracking', {})
    gate = get_quality_gate()

    due = []
    for qid, t in tracking.items():
        first = t.get('first_learned')
        if not first:
            continue
        try:
            first_date = datetime.strptime(first, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue
        review_count = t.get('review_count', 0)
        if review_count >= len(REVIEW_INTERVALS):
            continue
        next_rev = calc_next_review(first_date, review_count)
        if next_rev and str(next_rev) <= today:
            due.append((qid, str(next_rev)))

    if not due:
        print("NO_REVIEW|今天没有到期复习题。试试 'next' 出新题。")
        return

    # 选最早到期的一道
    due.sort(key=lambda x: x[1])

    # 跳过质量不合格的题目和被屏蔽模块的题目，选第一个通过的
    skipped_count = 0
    for target_qid, _ in due:
        # 检查题目所属模块是否在跳过列表中
        target_mod = tracking[target_qid].get('module', '')
        if target_mod in SKIPPED_MODULES:
            continue
        # 质量门控检查
        if gate and not gate.is_passing(target_qid):
            skipped_count += 1
            continue

        # 找到题目
        for mod_key, mod_data in bank['modules'].items():
            for q in mod_data['questions']:
                if q['id'] == target_qid:
                    if skipped_count > 0:
                        if OUTPUT_FORMAT == 'md':
                            print(f"⚠️ 已跳过 {skipped_count} 道质量不合格的复习题")
                        else:
                            print(f"SKIPPED|{skipped_count} 道质量不合格复习题已跳过")
                    _output_question(q, mod_key, "REVIEW")
                    return

    # 所有到期复习题都不合格
    if skipped_count > 0:
        if OUTPUT_FORMAT == 'md':
            print(f"⚠️ {skipped_count} 道到期复习题质量均不合格，已跳过。试试 'next' 出新题。")
        else:
            print(f"SKIPPED|{skipped_count} 道到期复习题质量均不合格")
    print("NO_REVIEW|今天没有可做的到期复习题（全部质量不合格或无到期题）。")


def cmd_answer(qid, user_answer):
    """判题并更新进度。"""
    user_answer = user_answer.strip().upper().rstrip('.')
    if user_answer not in ('A', 'B', 'C', 'D'):
        print(f"ERROR|无效答案 '{user_answer}'，请输入 A/B/C/D")
        return

    bank = load_bank()
    progress = load_progress()
    tracking = progress.get('question_tracking', {})

    # 2026-06-15 修复：answer 前置校验 state.current_qid 一致性（防错位判题）
    state = load_quiz_state()
    state_qid = state.get('current_qid')
    if state_qid and state_qid != qid:
        print(f"⚠️ P5 拦截：state.current_qid({state_qid}) ≠ 请求 QID({qid})")
        print(f"   这是错位判题，请先执行 `next` 获取最新题目")
        _log_intercept(qid, 'qid_mismatch', state_qid, qid)
        return

    # 找题目
    target_q = None
    target_mod = None
    for mod_key, mod_data in bank['modules'].items():
        for q in mod_data['questions']:
            if q['id'] == qid:
                target_q = q
                target_mod = mod_key
                break
        if target_q:
            break

    if not target_q:
        print(f"ERROR|题目 {qid} 不存在")
        return

    correct_answer = target_q['answer'].strip().upper().rstrip('.')
    is_correct = (user_answer == correct_answer)

    # 更新 tracking
    today = str(date.today())
    if qid not in tracking:
        tracking[qid] = {
            'module': target_mod,
            'first_learned': today,
            'last_reviewed': None,
            'review_count': 0,
            'next_review': None,
            'confidence': 3,
            'status': 'new',
            'review_history': [],
            'confidence_history': [],
            'wrong_count': 0,
        }

    t = tracking[qid]

    # P4 Triple-Source Verification: 三源校验防串题
    # 源1: quiz_hash_log.jsonl 中的追加日志（不可变，最权威）
    # 源2: quiz_bot_state.json 中的快照（可能被竞态覆盖）
    # 源3: bank.json 中的题目实时计算
    import hashlib
    bank_content = target_q['question'] + '|'.join(target_q.get('options', []))
    bank_hash = hashlib.md5(bank_content.encode()).hexdigest()[:8]

    state = load_quiz_state()
    state_hash = state.get('q_hash')
    state_question = state.get('q_question')
    state_options = state.get('q_options')
    log_hash = get_latest_hash_from_log(qid)

    # P0 修复：修复竞态条件 — log_hash 作为唯一权威源
    # snapshot_mismatch 不再作为独立拒绝条件，因为 state 是全局单例可被竞态覆盖
    
    # 步骤 1: log hash vs bank hash (log 是不可变日志，最权威)
    log_mismatch = False
    if log_hash and log_hash != bank_hash:
        log_mismatch = True  # log 是追加写入，不匹配=题库被修改=真正的串题，必须拒绝

    # 步骤 2: snapshot 校验（仅用于可观测性，不再拒绝用户答题）
    snapshot_mismatch = False
    if state_question and state_question != target_q['question']:
        snapshot_mismatch = True
    if state_options and state_options != target_q.get('options', []):
        snapshot_mismatch = True

    # P0 修复：只有 log_hash 明确不匹配才拒绝
    # snapshot_mismatch 不再拒绝用户（因为可能是竞态导致的 state 覆盖，不是用户/串题问题）
    if log_mismatch:
        reasons = [f"日志 hash({log_hash}) ≠ 题库 hash({bank_hash})"]
        print(f"⚠️ P4 拦截：题目内容不一致，拒绝判题！")
        print(f"原因: {'; '.join(reasons)}")
        print(f"请重新运行 `quiz_bot.py --format md next` 获取最新题目。")
        _log_intercept(qid, 'log_mismatch', log_hash, bank_hash)
        return

    # 降级策略：log 中无记录（时序问题）或 snapshot 不匹配 → 记录警告
    if snapshot_mismatch:
        # state 被覆盖是系统问题，不应惩罚用户
        _log_intercept(qid, 'snapshot_mismatch_warn', state_hash, bank_hash)
        # 2026-06-15 修复：snapshot 不一致时直接重新出题（防错位判题）
        if not log_mismatch:
            print(f"⚠️ snapshot 不匹配（state 被覆盖），自动重新出题...")
            # 重新调用 next 推送新题
            import sys
            saved_argv = sys.argv
            try:
                sys.argv = ['quiz_bot.py', '--format', 'md', 'next']
                cmd_next()
            finally:
                sys.argv = saved_argv
            return

    # P1 Defensive: 自动补全残缺记录（防止 quiz_session.py 等竞争脚本写入不完整 schema）
    if t.get('module') is None:
        t['module'] = target_mod
    if t.get('status') is None:
        t['status'] = 'new'
    if t.get('first_learned') is None:
        t['first_learned'] = today
    if 'confidence' not in t:
        t['confidence'] = 3
    if 'review_count' not in t:
        t['review_count'] = 0
    if 'wrong_count' not in t:
        t['wrong_count'] = 0
    if 'review_history' not in t:
        t['review_history'] = []
    if 'confidence_history' not in t:
        t['confidence_history'] = []

    if is_correct:
        t['confidence'] = min(5, t.get('confidence', 3) + 1)
        result = 'pass'
        status = 'reviewing' if t.get('review_count', 0) > 0 else 'learning'
    else:
        t['confidence'] = max(1, t.get('confidence', 3) - 1)
        t['wrong_count'] = t.get('wrong_count', 0) + 1
        result = 'fail'
        status = 'learning'

    t['last_reviewed'] = today
    t['review_count'] = t.get('review_count', 0) + 1
    t['status'] = status
    t['result'] = result  # P0 fix: 写入答题结果到顶层

    review_entry = {'date': today, 'confidence': t['confidence'], 'result': result}
    t.setdefault('review_history', []).append(review_entry)
    t.setdefault('confidence_history', []).append({
        'date': today,
        'confidence': t['confidence'],
        'result': result
    })

    # 计算下次复习
    try:
        first_date = datetime.strptime(t['first_learned'], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        first_date = date.today()

    if t['review_count'] < len(REVIEW_INTERVALS):
        next_rev = calc_next_review(first_date, t['review_count'])
        t['next_review'] = str(next_rev)
    else:
        t['next_review'] = None
        t['status'] = 'mastered'

    # 更新模块完成度
    if target_mod:
        mp = progress.setdefault('modules_progress', {}).get(target_mod, {})
        mp.setdefault('topics_done', 0)
        if is_correct:
            mp['topics_done'] = mp.get('topics_done', 0) + 1  # P1 fix: 答对才+1

    progress['question_tracking'] = tracking
    save_progress(progress)

    # 输出结果
    if OUTPUT_FORMAT == 'md':
        # P3: 输出正确选项完整文本，防止 LLM 自由解释
        correct_opt_text = target_q.get('options', [])[ord(correct_answer) - ord('A')] if ord(correct_answer) - ord('A') < len(target_q.get('options', [])) else ''
        if is_correct:
            print(f"✅ 正确！正确答案是 {correct_answer}")
        else:
            print(f"❌ 错误。正确答案是 {correct_answer}")
        if correct_opt_text:
            print(f"{correct_answer} 选项：{correct_opt_text}")
        print(f"📊 {qid} | 信心: {t['confidence']}/5 | 第 {t['review_count']} 轮复习")
        if t['next_review']:
            print(f"📅 下次复习: {t['next_review']}")
        print(f"📌 状态: {t['status']}")
    else:
        if is_correct:
            print(f"RESULT|✅ 正确！正确答案是 {correct_answer}")
        else:
            print(f"RESULT|❌ 错误。正确答案是 {correct_answer}")

        print(f"QID|{qid}")
        print(f"CONFIDENCE|{t['confidence']}/5")
        print(f"REVIEW_COUNT|第 {t['review_count']} 轮")
        if t['next_review']:
            print(f"NEXT_REVIEW|{t['next_review']}")
        print(f"STATUS|{t['status']}")
        print("END")


def cmd_explain(qid):
    """输出题目解析。"""
    bank = load_bank()
    for mod_key, mod_data in bank['modules'].items():
        for q in mod_data['questions']:
            if q['id'] == qid:
                print(f"QID|{qid}")
                print(f"MODULE|{mod_key}")
                print(f"QUESTION|{q['question']}")
                labels = ['A', 'B', 'C', 'D']
                for i, opt in enumerate(q.get('options', [])):
                    print(f"OPT|{labels[i]}|{opt}")
                print(f"ANSWER|{q['answer'].rstrip('.')}")
                print(f"EXPLANATION|{q.get('explanation', '暂无解析')}")
                kc = q.get('key_concepts', '')
                if isinstance(kc, list):
                    kc_str = ', '.join(kc)
                else:
                    kc_str = str(kc)
                print(f"KEY_CONCEPTS|{kc_str}")
                print("END")
                return
    print(f"ERROR|题目 {qid} 不存在")


def cmd_status():
    """输出当前学习进度。"""
    progress = load_progress()
    bank = load_bank()
    tracking = progress.get('question_tracking', {})
    mp = progress.get('modules_progress', {})

    total_in_bank = sum(len(m['questions']) for m in bank['modules'].values())
    learned = sum(1 for t in tracking.values() if t.get('first_learned'))
    mastered = sum(1 for t in tracking.values() if t.get('status') == 'mastered')

    today = str(date.today())
    due_count = 0
    for qid, t in tracking.items():
        first = t.get('first_learned')
        if not first:
            continue
        try:
            first_date = datetime.strptime(first, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue
        rc = t.get('review_count', 0)
        if rc >= len(REVIEW_INTERVALS):
            continue
        next_rev = calc_next_review(first_date, rc)
        if next_rev and str(next_rev) <= today:
            due_count += 1

    print(f"STATUS|学习进度")
    print(f"TOTAL|{total_in_bank} 题 / {len(bank['modules'])} 模块")
    print(f"LEARNED|{learned} 题")
    print(f"MASTERED|{mastered} 题")
    print(f"DUE_REVIEW|{due_count} 题待复习")
    print(f"TODAY|{today}")
    print("END")


def cmd_module(module_partial):
    """输出指定模块进度。"""
    bank = load_bank()
    progress = load_progress()
    tracking = progress.get('question_tracking', {})

    mod_key = find_module_id(bank['modules'], module_partial)
    if not mod_key:
        print(f"ERROR|模块 '{module_partial}' 不存在")
        return

    mod_data = bank['modules'][mod_key]
    total = len(mod_data['questions'])
    learned = 0
    mastered = 0
    confs = []

    for q in mod_data['questions']:
        t = tracking.get(q['id'], {})
        if t.get('first_learned'):
            learned += 1
            if t.get('status') == 'mastered':
                mastered += 1
            if t.get('confidence'):
                confs.append(t['confidence'])

    avg_conf = sum(confs) / len(confs) if confs else 0

    print(f"MODULE|{mod_key}")
    print(f"TOTAL|{total}")
    print(f"LEARNED|{learned}")
    print(f"MASTERED|{mastered}")
    print(f"AVG_CONFIDENCE|{avg_conf:.1f}")
    print(f"PCT|{learned/total*100:.0f}%")
    print("END")


def cmd_quality():
    """输出质量门控状态。"""
    gate = get_quality_gate()
    if not gate or not gate.has_data:
        print("QUALITY|质量门控未启用")
        print("STATUS|审计文件不存在或未加载。所有题目正常放行。")
        print("END")
        return

    stats = gate.stats()
    bank = load_bank()
    progress = load_progress()
    tracking = progress.get('question_tracking', {})

    # 计算可用题目数（未学习 + 通过质量门控）
    available_count = 0
    for mod_key, mod_data in bank['modules'].items():
        for q in mod_data['questions']:
            tid = q['id']
            t = tracking.get(tid, {})
            if t.get('first_learned') is None and gate.is_passing(tid):
                available_count += 1

    total_in_bank = sum(len(m['questions']) for m in bank['modules'].values())

    if OUTPUT_FORMAT == 'md':
        print(f"📊 质量门控状态")
        print(f"题库总量: {total_in_bank} 题")
        print(f"通过审计: {stats['passing']} 题 ({stats['passing']/stats['total_known']*100:.1f}%)")
        print(f"未通过审计: {stats['failing']} 题 ({stats['failing']/stats['total_known']*100:.1f}%)")
        print(f"当前可刷: {available_count} 题（未学习且通过审计）")
    else:
        print(f"QUALITY|质量门控状态")
        print(f"TOTAL|{total_in_bank}")
        print(f"PASSING|{stats['passing']}")
        print(f"FAILING|{stats['failing']}")
        print(f"AVAILABLE|{available_count}")
        print(f"MODE|{stats['mode']}")
        print("END")


def cmd_intercepts():
    """P1 修复：查看拦截统计（可观测性）。"""
    if not os.path.exists(QUIZ_INTERCEPT_LOG_PATH):
        if OUTPUT_FORMAT == 'md':
            print("📊 拦截统计：无记录")
        else:
            print("INTERCEPTS|无拦截记录")
        return

    from collections import Counter
    reasons = Counter()
    qid_counts = Counter()
    total = 0
    with open(QUIZ_INTERCEPT_LOG_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                reasons[entry['reason']] += 1
                qid_counts[entry['qid']] += 1
                total += 1
            except (json.JSONDecodeError, KeyError):
                continue

    if OUTPUT_FORMAT == 'md':
        print(f"📊 拦截统计：共 {total} 次")
        print(f"\n**按原因分类：**")
        for reason, count in reasons.most_common():
            print(f"- {reason}: {count}次")
        print(f"\n**最常被拦截的题目 TOP 5：**")
        for qid, count in qid_counts.most_common(5):
            print(f"- {qid}: {count}次")
    else:
        print(f"INTERCEPTS|共 {total} 次拦截")
        for reason, count in reasons.most_common():
            print(f"  {reason}: {count}次")
        print("TOP_QUESTIONS|最常被拦截的题目:")
        for qid, count in qid_counts.most_common(5):
            print(f"  {qid}: {count}次")
        print("END")


def _output_question(q, mod_key, cmd_type):
    """格式化输出题目。"""
    import hashlib
    today = str(date.today())
    output_lines = []

    # P2: 生成题目内容 hash（用于判题时一致性校验）
    q_content = q['question'] + '|'.join(q.get('options', []))
    q_hash = hashlib.md5(q_content.encode()).hexdigest()[:8]

    if OUTPUT_FORMAT == 'md':
        # Markdown 格式：不输出答案，直接可转发给用户
        labels = ['A', 'B', 'C', 'D']
        options_md = ''
        for i, opt in enumerate(q.get('options', [])):
            options_md += f'{labels[i]}. {opt}\n'
        output_lines.append(f'📝 {q["id"]} | {mod_key}')
        output_lines.append(q['question'])
        output_lines.append('')
        output_lines.append(options_md.rstrip())
        # P4: 保存完整题目快照 + hash + 写入追加日志（三源验证）
        # 合并已有 state 保留 locked_module / module_question_count 等字段
        existing_state = load_quiz_state()
        state_data = {
            'current_qid': q['id'],
            'current_mod': mod_key,
            'cmd': cmd_type,
            'timestamp': today,
            'q_hash': q_hash,
            'q_question': q['question'],
            'q_options': q.get('options', []),
        }
        existing_state.update(state_data)
        save_quiz_state(existing_state)
        append_hash_log(q['id'], q_hash)
    else:
        # 原始 pipe 格式
        output_lines.append(f"CMD|{cmd_type}")
        output_lines.append(f"QID|{q['id']}")
        output_lines.append(f"MODULE|{mod_key}")
        output_lines.append(f"QUESTION|{q['question']}")
        labels = ['A', 'B', 'C', 'D']
        for i, opt in enumerate(q.get('options', [])):
            output_lines.append(f"OPT|{labels[i]}|{opt}")
        output_lines.append(f"ANSWER|{q['answer'].rstrip('.')}")
        # P4: pipe 格式也保存完整快照 + hash + 追加日志（与 md 分支同等级保护）
        # 合并已有 state 保留 locked_module / module_question_count 等字段
        existing_state = load_quiz_state()
        state_data = {
            'current_qid': q['id'],
            'current_mod': mod_key,
            'cmd': cmd_type,
            'timestamp': today,
            'q_hash': q_hash,
            'q_question': q['question'],
            'q_options': q.get('options', []),
        }
        existing_state.update(state_data)
        save_quiz_state(existing_state)
        append_hash_log(q['id'], q_hash)
        output_lines.append("END")

    print('\n'.join(output_lines))


def main():
    global OUTPUT_FORMAT

    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    # 解析 --format 参数
    format_idx = None
    for i, arg in enumerate(args):
        if arg == '--format' and i + 1 < len(args):
            OUTPUT_FORMAT = args[i + 1]
            format_idx = i
            # 移除 --format 和它的值
            args = args[:i] + args[i+2:]
            break
        elif arg.startswith('--format='):
            OUTPUT_FORMAT = arg.split('=', 1)[1]
            format_idx = i
            args = args[:i] + args[i+1:]
            break

    if not args:
        print(__doc__)
        sys.exit(1)

    cmd = args[0]

    if cmd == 'next':
        module = args[1] if len(args) > 1 else None
        cmd_next(module)
    elif cmd == 'review':
        cmd_review()
    elif cmd == 'answer' and len(args) >= 3:
        cmd_answer(args[1], args[2])
    elif cmd == 'skip' and len(args) >= 2:
        cmd_skip(args[1])
    elif cmd == 'explain' and len(args) >= 2:
        cmd_explain(args[1])
    elif cmd == 'status':
        cmd_status()
    elif cmd == 'module' and len(args) >= 2:
        cmd_module(args[1])
    elif cmd == 'quality':
        cmd_quality()
    elif cmd == 'intercepts':
        cmd_intercepts()
    else:
        print(f"ERROR|未知命令 '{cmd}'")
        print("用法: python3 quiz_bot.py [--format md|pipe] [next|review|answer|skip|explain|status|module|quality|intercepts]")
        sys.exit(1)


if __name__ == '__main__':
    main()
