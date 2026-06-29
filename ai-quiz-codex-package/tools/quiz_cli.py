#!/usr/bin/env python3
"""Quiz CLI - Command-line interface for AI quiz operations.

This tool provides commands for:
- Starting a quiz session
- Getting questions
- Submitting answers
- Viewing progress

Usage:
    python quiz_cli.py start [options]
    python quiz_cli.py get <mode> [limit] [modules...]
    python quiz_cli.py submit <qid> <answer>
    python quiz_cli.py stats
    python quiz_cli.py session-info
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add engine directory to path for imports
engine_dir = Path(__file__).parent.parent / "engine"
sys.path.insert(0, str(engine_dir))
from quiz_engine import QuizSession, format_correct, format_wrong, format_unknown


def cmd_start(mode="mixed"):
    """Start a new quiz session.

    Args:
        mode: "review" (due questions), "new" (new questions),
              "wrong" (wrong questions), "mixed" (all types)
    """
    session = QuizSession(restore_session=False)
    session.reset_session(mode=mode)
    today = datetime.now().strftime("%Y-%m-%d")

    # Check if questions were already answered today
    today_new = {qid for qid, q in session.q_tracking.items()
                 if q.get("first_learned") == today}
    today_reviewed = {qid for qid, q in session.q_tracking.items()
                      if q.get("last_reviewed") == today}
    # A question learned and reviewed today should only count as new
    today_review_only = today_reviewed - today_new

    print(f"=== AI 刷题会话 — {today} ===\n")
    print(f"总体进度: {sum(m.get('topics_done', 0) for m in session.modules.values())}/"
          f"{sum(m.get('total_topics', 0) for m in session.modules.values())}")
    print(f"今日已刷: 新学 {len(today_new)} 题, 复习 {len(today_review_only)} 题\n")

    # Get questions based on mode
    if mode == "wrong":
        qids = session.get_wrong_questions(5)
        print(f" 错题复习 ({len(qids)} 题)\n")
    elif mode == "new":
        pairs = session.get_new_questions(limit=5)
        qids = [p[0] for p in pairs]
        print(f"🆕 新学题目 ({len(qids)} 题)\n")
    elif mode == "review":
        qids = session.get_due_questions(5)
        print(f"📅 到期复习 ({len(qids)} 题)\n")
    else:  # mixed
        # Get wrong questions first
        wrong_qids = session.get_wrong_questions(3)
        # Then due questions
        due_qids = [q for q in session.get_due_questions(5) if q not in wrong_qids]
        qids = wrong_qids + due_qids[:2]  # 3 wrong + 2 due
        print(f"📋 混合模式: 错题 {len(wrong_qids)} 题 + 到期 {len(due_qids[:2])} 题\n")

    if not qids:
        print("✅ 今日暂无题目需要作答！")
        return

    # Print questions
    for i, qid in enumerate(qids, 1):
        session.mark_presented(qid)
        q = session.get_question(qid)
        if q:
            mod = q.get("_module", "")
            conf = session.q_tracking.get(qid, {}).get("confidence", "N/A")
            print(f"### Q{i}（共 {len(qids)} 题）\n")
            print(f"**{qid}** [{mod}] (置信度={conf})")
            print(f"\n{q['question']}\n")
            labels = ['A', 'B', 'C', 'D']
            for j, opt in enumerate(q["options"]):
                print(f"{labels[j]}) {opt}")
            print()

    print("---\n")
    print("请逐题回复答案（A/B/C/D），输入 '不会' 表示不知道")
    print("输入 'stats' 查看统计，输入 'exit' 结束会话")


def cmd_get(mode="review", limit=5, modules=None):
    """Get questions without starting a full session."""
    session = QuizSession()
    if not session.session_id:
        session.reset_session(mode=mode)

    if mode == "wrong":
        qids = session.get_wrong_questions(limit)
    elif mode == "new":
        pairs = session.get_new_questions(modules, limit)
        qids = [p[0] for p in pairs]
    elif mode == "due":
        qids = session.get_due_questions(limit)
    else:
        qids = session.get_due_questions(limit)

    for i, qid in enumerate(qids, 1):
        session.mark_presented(qid)
        q = session.get_question(qid)
        if q:
            print(f"--- Q{i}: {qid} [{q.get('_module', '')}] ---")
            print(f"题目: {q['question']}")
            labels = ['A', 'B', 'C', 'D']
            for j, opt in enumerate(q["options"]):
                print(f"{labels[j]}) {opt}")
            print()


def cmd_submit(qid, user_answer):
    """Submit an answer and get immediate feedback."""
    session = QuizSession()
    q = session.get_question(qid)

    if not q:
        print(f" 错误：题目 {qid} 不存在")
        return

    # Normalize answer
    correct_answer = q["answer"].strip().rstrip('.').upper()
    user_answer = user_answer.strip().upper()

    # Handle "不会" (don't know)
    if user_answer in ["不会", "不知道", "PASS"]:
        is_new = qid not in session.q_tracking or not session.q_tracking[qid].get("first_learned")
        session.record_answer(qid, False, is_new=is_new)
        explanation = q.get("explanation", "暂无解析")
        print(format_unknown(correct_answer, explanation))
        return

    # Validate answer format
    if user_answer not in ["A", "B", "C", "D"]:
        print(" 无效答案，请输入 A/B/C/D 或 '不会'")
        return

    is_correct = user_answer == correct_answer
    is_new = qid not in session.q_tracking or not session.q_tracking[qid].get("first_learned")

    # Record answer (includes instant save)
    session.record_answer(qid, is_correct, is_new=is_new)

    # Output feedback
    if is_correct:
        print(format_correct(correct_answer))
    else:
        explanation = q.get("explanation", "暂无解析")
        print(format_wrong(correct_answer, explanation))


def cmd_stats():
    """Show detailed statistics."""
    session = QuizSession()

    total_done = sum(m.get("topics_done", 0) for m in session.modules.values())
    total_all = sum(m.get("total_topics", 0) for m in session.modules.values())
    pct = total_done / total_all * 100 if total_all > 0 else 0

    print(f"=== 学习统计 ===\n")
    print(f"总体进度: {total_done}/{total_all} ({pct:.1f}%)")
    print(f"累计跟踪: {len(session.q_tracking)} 题\n")

    # Confidence distribution
    from collections import Counter
    conf_dist = Counter(q.get("confidence", 0) for q in session.q_tracking.values() if q.get("confidence"))
    print("置信度分布:")
    for c in sorted(conf_dist.keys(), reverse=True):
        bar = "█" * conf_dist[c]
        print(f"  {c}分: {conf_dist[c]} 题 {bar}")

    # Weak modules
    print("\n薄弱模块 (<30%):")
    weak = []
    for name, m in sorted(session.modules.items()):
        done = m.get("topics_done", 0)
        total = m.get("total_topics", 0)
        p = done / total * 100 if total > 0 else 0
        if p < 30:
            weak.append((name, done, total, p))

    for name, done, total, p in sorted(weak, key=lambda x: x[3]):
        print(f"  {name}: {done}/{total} ({p:.0f}%)")

    # Session stats
    stats = session.get_stats()
    if stats["total"] > 0:
        print(f"\n=== 本次会话 ===")
        print(f"已答: {stats['total']} 题, 正确: {stats['correct']} 题 ({stats['accuracy']:.0f}%)")


def cmd_session_info():
    """Show current session information."""
    session = QuizSession()
    stats = session.get_stats()

    print(f"=== 会话信息 ===")
    print(f"已展示题目: {len(session.presented_questions)} 题")
    print(f"已答题目: {stats['total']} 题")
    if stats['total'] > 0:
        print(f"正确率: {stats['accuracy']:.0f}%")

    if session.answered_questions:
        print("\n答题记录:")
        for a in session.answered_questions:
            status = "✅" if a["correct"] else ""
            new_tag = " [新学]" if a["is_new"] else ""
            print(f"  {status} {a['qid']}{new_tag}")


def cmd_help():
    """Show detailed help message."""
    print("""AI 刷题命令行工具

用法:
  python tools/quiz_cli.py start [mixed|wrong|new|review]
  python tools/quiz_cli.py get <mode> [limit] [modules...]
  python tools/quiz_cli.py submit <qid> <answer>
  python tools/quiz_cli.py stats
  python tools/quiz_cli.py session-info
  python tools/quiz_cli.py --help

说明:
  start    启动新会话（默认 mixed：3 错题 + 2 到期复习）
  get      获取题目但不启动完整会话
  submit   提交答案（A/B/C/D 或 不会）
  stats    查看学习统计
  session-info  查看当前会话状态
""")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(1)

    command = sys.argv[1]

    if command in ("--help", "-h"):
        cmd_help()
        sys.exit(0)

    if command == "start":
        mode = sys.argv[2] if len(sys.argv) > 2 else "mixed"
        cmd_start(mode)

    elif command == "get":
        mode = sys.argv[2] if len(sys.argv) > 2 else "review"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        modules = sys.argv[4:] if len(sys.argv) > 4 else None
        cmd_get(mode, limit, modules)

    elif command == "submit":
        if len(sys.argv) < 4:
            print("Usage: python quiz_cli.py submit <qid> <answer>")
            sys.exit(1)
        cmd_submit(sys.argv[2], sys.argv[3])

    elif command == "stats":
        cmd_stats()

    elif command == "session-info":
        cmd_session_info()

    else:
        print(f"未知命令: {command}")
        cmd_help()
        sys.exit(1)
