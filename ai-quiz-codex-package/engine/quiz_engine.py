#!/usr/bin/env python3
"""AI Quiz Engine - Core logic for question selection, tracking, and progress management.

This module addresses the following issues identified in code review:
1. Question deduplication (tracks presented-but-not-submitted questions)
2. Standardized output templates
3. Instant write-back after each answer
4. Smart question selection strategy
5. Fixed module progress update logic
"""

import json
import sys
import os
import fcntl
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
from typing import Optional


# ============================================================
# Configuration
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
BANK_PATH = ROOT_DIR / "data" / "question-bank" / "bank.json"
PROGRESS_PATH = ROOT_DIR / "data" / "tracking" / "progress.json"
LOCK_PATH = Path("/opt/personal-agent-workspace/.locks/ai-quiz.lock")

REVIEW_INTERVALS = [1, 3, 7, 14, 30, 90]

# Output templates (Issue #2: standardized format)
CORRECT_TEMPLATE = "✅ **正确！** 答案是 {answer}。"
WRONG_TEMPLATE = "❌ **错误！** 正确答案是 **{answer}**。\n\n**解析**：{explanation}"
UNKNOWN_TEMPLATE = "正确答案是 **{answer}**。\n\n**解析**：{explanation}"

# Wrong option analysis template (Issue #3: enhanced explanation)
WRONG_OPTION_TEMPLATE = "**错误选项分析**：{wrong_analysis}"


# ============================================================
# Data Loading
# ============================================================

def load_bank():
    """Load question bank from JSON file."""
    with open(BANK_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_progress():
    """Load progress tracking data from JSON file."""
    with open(PROGRESS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_progress(progress):
    """Save progress tracking data to JSON file."""
    with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def save_progress_locked(progress):
    """Save progress with file lock for concurrency safety."""
    os.makedirs(LOCK_PATH.parent, exist_ok=True)
    with open(LOCK_PATH, 'w') as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            save_progress(progress)
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


# ============================================================
# Question Selection Engine (Issue #1 & #5)
# ============================================================

class QuizSession:
    """Manages a quiz session with proper deduplication and tracking."""

    def __init__(self):
        self.bank = load_bank()
        self.progress = load_progress()
        self.q_tracking = self.progress.get("question_tracking", {})
        self.modules = self.progress.get("modules_progress", {})

        # Issue #1: Track questions presented but not yet submitted
        self.presented_questions = set()

        # Track answered questions in this session
        self.answered_questions = []

        # Build question lookup
        self._build_question_map()

    def _build_question_map(self):
        """Build a flat map of all questions by ID."""
        self.q_map = {}
        for mod_key, mod_data in self.bank["modules"].items():
            for q in mod_data["questions"]:
                self.q_map[q["id"]] = {
                    **q,
                    "_module": mod_key,
                    "_module_name": mod_data.get("name", mod_key)
                }

    def get_due_questions(self, limit=10):
        """Get questions due for review, sorted by priority.

        Priority order (Issue #5: smart selection):
        1. Low confidence (1-2) first
        2. Due date (earlier first)
        3. Module weakness (lower % first)
        """
        today = datetime.now().strftime("%Y-%m-%d")

        due = []
        for qid, q in self.q_tracking.items():
            if (q.get("next_review") and q.get("next_review") <= today
                and q.get("status") == "reviewing"
                and qid not in self.presented_questions
                and qid not in [a["qid"] for a in self.answered_questions]):

                conf = q.get("confidence", 5)
                module = q.get("module", "")
                mod_info = self.modules.get(module, {})
                mod_progress = mod_info.get("topics_done", 0) / max(mod_info.get("total_topics", 1), 1)

                due.append({
                    "qid": qid,
                    "confidence": conf,
                    "module": module,
                    "module_progress": mod_progress,
                    "next_review": q.get("next_review", ""),
                    "priority_score": conf * 10 + mod_progress * 5  # Lower score = higher priority
                })

        # Sort by priority
        due.sort(key=lambda x: x["priority_score"])

        return [d["qid"] for d in due[:limit]]

    def get_new_questions(self, modules=None, limit=5):
        """Get new (never learned) questions from specified modules.

        Issue #7: Prioritize weak modules (progress < 10%)
        """
        if modules is None:
            # Default: prioritize weakest modules
            modules = self._get_weakest_modules()

        selected = []
        for mod_name in modules:
            if mod_name not in self.bank["modules"]:
                continue

            mod_qs = self.bank["modules"][mod_name]["questions"]
            for q in mod_qs:
                if (q["id"] not in self.q_tracking
                    and q["id"] not in self.presented_questions
                    and q["id"] not in [a["qid"] for a in self.answered_questions]):
                    selected.append((q["id"], mod_name))
                    if len(selected) >= limit:
                        return selected

        return selected

    def get_wrong_questions(self, limit=5):
        """Get questions that were answered incorrectly recently."""
        wrong = []
        for qid, q in self.q_tracking.items():
            conf = q.get("confidence", 5)
            last_reviewed = q.get("last_reviewed", "")

            # Confidence <= 2 indicates wrong answer
            if (conf <= 2
                and qid not in self.presented_questions
                and qid not in [a["qid"] for a in self.answered_questions]):
                wrong.append((qid, conf, q.get("module", "")))

        # Sort by confidence (lowest first)
        wrong.sort(key=lambda x: x[1])
        return [w[0] for w in wrong[:limit]]

    def _get_weakest_modules(self, top=5):
        """Get the weakest modules by progress percentage."""
        weak = []
        for name, m in self.modules.items():
            done = m.get("topics_done", 0)
            total = m.get("total_topics", 1)
            pct = done / total
            weak.append((name, pct))

        weak.sort(key=lambda x: x[1])
        return [w[0] for w in weak[:top]]

    def mark_presented(self, qid):
        """Mark a question as presented to user (for deduplication)."""
        self.presented_questions.add(qid)

    def get_question(self, qid):
        """Get question data by ID."""
        return self.q_map.get(qid)

    def format_question(self, qid):
        """Format a question for display."""
        q = self.q_map.get(qid)
        if not q:
            return None

        mod = q.get("_module", "")
        conf = self.q_tracking.get(qid, {}).get("confidence", "N/A")

        lines = []
        lines.append(f"**{qid}** [{mod}] (置信度={conf})")
        lines.append(f"{q['question']}")
        lines.append("")

        labels = ['A', 'B', 'C', 'D']
        for i, opt in enumerate(q["options"]):
            lines.append(f"{labels[i]}) {opt}")

        return "\n".join(lines)

    def record_answer(self, qid, is_correct, is_new=False):
        """Record an answer and update progress (Issue #4: instant write-back).

        Args:
            qid: Question ID
            is_correct: Whether the answer was correct
            is_new: Whether this is a new question (first learn)
        """
        q = self.q_tracking.get(qid)
        if not q:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        module = q.get("module", "")

        if is_new:
            # First time learning
            q["first_learned"] = today
            q["last_reviewed"] = today
            q["review_count"] = 1
            q["confidence"] = 5 if is_correct else 2
            q["status"] = "reviewing"
            q["next_review"] = self._calc_next_review(today, 1)
            q["review_history"] = [{
                "date": today,
                "confidence": q["confidence"],
                "result": "pass" if is_correct else "fail"
            }]

            # Issue #7: Only increment topics_done for new questions
            if module in self.modules:
                self.modules[module]["topics_done"] = self.modules[module].get("topics_done", 0) + 1
        else:
            # Review
            q["last_reviewed"] = today
            q["review_count"] = q.get("review_count", 0) + 1
            rc = q["review_count"]

            old_conf = q.get("confidence", 3)
            if is_correct:
                new_conf = min(5, old_conf + 1)
            else:
                new_conf = max(1, old_conf - 1)

            q["confidence"] = new_conf
            q["next_review"] = self._calc_next_review(today, rc)

            if "review_history" not in q:
                q["review_history"] = []
            q["review_history"].append({
                "date": today,
                "confidence": new_conf,
                "result": "pass" if is_correct else "fail"
            })

        # Always update last_studied for the module
        if module in self.modules:
            self.modules[module]["started"] = True
            self.modules[module]["last_studied"] = today

        # Issue #4: Save immediately after each answer
        self._save()

        # Track answered
        self.answered_questions.append({
            "qid": qid,
            "correct": is_correct,
            "is_new": is_new
        })

    def _calc_next_review(self, date_str, review_count):
        """Calculate next review date based on spaced repetition intervals."""
        if review_count < len(REVIEW_INTERVALS):
            days = REVIEW_INTERVALS[review_count]
        else:
            days = REVIEW_INTERVALS[-1]
        d = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=days)
        return d.strftime("%Y-%m-%d")

    def _save(self):
        """Save progress with lock."""
        save_progress_locked(self.progress)

    def get_stats(self):
        """Get current session statistics."""
        total = len(self.answered_questions)
        correct = sum(1 for a in self.answered_questions if a["correct"])
        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total * 100 if total > 0 else 0,
            "answered": self.answered_questions
        }


# ============================================================
# Output Formatters (Issue #2)
# ============================================================

def format_correct(answer):
    """Format correct answer response."""
    return CORRECT_TEMPLATE.format(answer=answer)


def format_wrong(answer, explanation, wrong_options=None):
    """Format wrong answer response with explanation.

    Issue #3: Enhanced explanation with wrong option analysis
    """
    result = WRONG_TEMPLATE.format(answer=answer, explanation=explanation)

    if wrong_options:
        result += "\n\n" + WRONG_OPTION_TEMPLATE.format(wrong_analysis=wrong_options)

    return result


def format_unknown(answer, explanation):
    """Format 'don't know' response."""
    return UNKNOWN_TEMPLATE.format(answer=answer, explanation=explanation)


# ============================================================
# CLI Interface
# ============================================================

def cmd_get_questions(mode="review", limit=5, modules=None):
    """Get questions for a round.

    Args:
        mode: "review", "new", "wrong", or "due"
        limit: Number of questions
        modules: Optional module filter
    """
    session = QuizSession()

    if mode == "wrong":
        qids = session.get_wrong_questions(limit)
    elif mode == "new":
        pairs = session.get_new_questions(modules, limit)
        qids = [p[0] for p in pairs]
    elif mode == "due":
        qids = session.get_due_questions(limit)
    else:
        qids = session.get_due_questions(limit)

    for qid in qids:
        session.mark_presented(qid)
        q = session.get_question(qid)
        if q:
            print(f"--- {qid} [{q.get('_module', '')}] ---")
            print(q["question"])
            labels = ['A', 'B', 'C', 'D']
            for i, opt in enumerate(q["options"]):
                print(f"{labels[i]}) {opt}")
            print()


def cmd_submit_answer(qid, user_answer):
    """Submit an answer and get feedback.

    Args:
        qid: Question ID
        user_answer: User's answer (A/B/C/D)
    """
    session = QuizSession()
    q = session.get_question(qid)

    if not q:
        print(f"Error: Question {qid} not found")
        return

    # Normalize answer
    correct_answer = q["answer"].strip().rstrip('.').upper()
    user_answer = user_answer.strip().upper()

    is_correct = user_answer == correct_answer
    is_new = qid not in session.q_tracking or not session.q_tracking[qid].get("first_learned")

    # Record answer (this also saves to file)
    session.record_answer(qid, is_correct, is_new=is_new)

    # Output feedback
    if is_correct:
        print(format_correct(correct_answer))
    else:
        explanation = q.get("explanation", "暂无解析")
        print(format_wrong(correct_answer, explanation))


def cmd_stats():
    """Show current progress statistics."""
    session = QuizSession()

    total_done = sum(m.get("topics_done", 0) for m in session.modules.values())
    total_all = sum(m.get("total_topics", 0) for m in session.modules.values())

    print(f"总体进度: {total_done}/{total_all} ({total_done/total_all*100:.1f}%)")
    print(f"累计跟踪: {len(session.q_tracking)} 题")

    # Show weak modules
    print("\n薄弱模块 (<30%):")
    for name, m in sorted(session.modules.items()):
        done = m.get("topics_done", 0)
        total = m.get("total_topics", 0)
        pct = done / total * 100 if total > 0 else 0
        if pct < 30:
            print(f"  {name}: {done}/{total} ({pct:.0f}%)")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quiz_engine.py <command> [args]")
        print("Commands:")
        print("  get-questions <mode> [limit] [modules...]")
        print("  submit-answer <qid> <answer>")
        print("  stats")
        sys.exit(1)

    command = sys.argv[1]

    if command == "get-questions":
        mode = sys.argv[2] if len(sys.argv) > 2 else "review"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        modules = sys.argv[4:] if len(sys.argv) > 4 else None
        cmd_get_questions(mode, limit, modules)

    elif command == "submit-answer":
        if len(sys.argv) < 4:
            print("Usage: python quiz_engine.py submit-answer <qid> <answer>")
            sys.exit(1)
        qid = sys.argv[2]
        answer = sys.argv[3]
        cmd_submit_answer(qid, answer)

    elif command == "stats":
        cmd_stats()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
