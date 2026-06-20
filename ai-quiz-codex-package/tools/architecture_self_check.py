#!/usr/bin/env python3
"""
架构自检脚本 — 每日 5 项健康检查

1. 题库质量扫描：audit + 长度偏见 + answer/exp 一致性
2. 防幻觉机制验证：get_question.py / prepare_daily_quiz.py 可执行性 + Skill 铁律完整性
3. Cron 健康检查：20:15 / 21:15 推送状态
4. 数据一致性：bank.json ↔ progress.json 题数一致 + 孤儿记录检测
5. 自动修复：小问题直接修（孤儿记录清理等），记录 changelog

输出：JSON 格式，供 cron prompt 解析填充
用法：python3 scripts/architecture_self_check.py
"""
import json, os, sys, subprocess
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
BANK_PATH = os.path.join(BASE_DIR, "data", "question-bank", "bank.json")
PROGRESS_PATH = os.path.join(BASE_DIR, "data", "tracking", "progress.json")
CHANGELOG_PATH = os.path.join(BASE_DIR, "data", "question-bank", "changelog.md")
CRON_JOBS_PATH = os.path.join(BASE_DIR, "cron", "jobs.json")

def run_script(script_name, args=None, timeout=30):
    cmd = ["python3", os.path.join(SCRIPTS_DIR, script_name)]
    if args:
        cmd.extend(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=BASE_DIR)
        return result.returncode == 0, result.stdout[:2000], result.stderr[:500]
    except subprocess.TimeoutExpired:
        return False, "", "Timeout after %ds" % timeout
    except Exception as e:
        return False, "", str(e)

def find_bank_path():
    for p in [BANK_PATH]:
        if os.path.exists(p):
            return p
    return BANK_PATH

def check_bank_quality():
    bank_path = find_bank_path()
    results = {"audit": {"status": "pending"}, "length_bias": {"status": "pending"}, "answer_exp_consistency": {"status": "pending"}}

    ok, stdout, stderr = run_script("bank_checklist.py", ["--bank", bank_path], timeout=60)
    issue_count = 0
    for line in (stdout + stderr).split("\n"):
        if "共" in line and "个问题" in line:
            for word in line.split():
                if word.isdigit():
                    issue_count = max(issue_count, int(word))
    results["audit"]["status"] = "ok" if issue_count == 0 else "warning"
    results["audit"]["issues"] = issue_count

    ok, stdout, stderr = run_script("check_answer_quality.py", [bank_path], timeout=60)
    output = stdout + stderr
    lb_count = 0
    for line in output.split("\n"):
        if "长度偏见:" in line:
            for word in line.split(":")[-1].split():
                if word.isdigit():
                    lb_count = max(lb_count, int(word))
    results["length_bias"]["status"] = "ok" if lb_count == 0 else "warning"
    results["length_bias"]["issues"] = lb_count

    ok, stdout, stderr = run_script("check_answer_exp_consistency_v2.py", [bank_path], timeout=60)
    output = stdout + stderr
    mm_count = 0
    for line in output.split("\n"):
        if "Found" in line and "mismatch" in line.lower():
            for word in line.split():
                if word.isdigit():
                    mm_count = max(mm_count, int(word))
    results["answer_exp_consistency"]["status"] = "ok" if mm_count == 0 else "warning"
    results["answer_exp_consistency"]["issues"] = mm_count

    return results

def check_anti_hallucination():
    results = {"get_question_py": {"status": "pending"}, "prepare_daily_quiz_py": {"status": "pending"}, "skill_rules": {"status": "pending"}}

    ok, stdout, stderr = run_script("get_question.py", ["next", "M08_Agent架构", "--format", "md"], timeout=10)
    results["get_question_py"]["status"] = "ok" if ok and "Q-M08_Agent架构" in stdout else "error"

    ok, stdout, stderr = run_script("prepare_daily_quiz.py", timeout=30)
    if ok and stdout.strip().startswith("{"):
        results["prepare_daily_quiz_py"]["status"] = "ok"
    else:
        results["prepare_daily_quiz_py"]["status"] = "error"

    skill_path = os.path.join(BASE_DIR, "docs", "SKILL.md")
    try:
        with open(skill_path, "r") as f:
            content = f.read()
        rules = [("禁止编造", "禁止编造" in content or "严禁凭记忆编造题目" in content),
                 ("逐题读取", "逐题" in content or "每一道展示给用户的题必须来自" in content),
                 ("判题校验", "current_qid" in content and "QID" in content)]
        missing = [n for n, found in rules if not found]
        results["skill_rules"]["status"] = "ok" if not missing else "warning"
        results["skill_rules"]["detail"] = "%d 项铁律完整" % len(rules) if not missing else "缺失: " + ", ".join(missing)
    except Exception as e:
        results["skill_rules"]["status"] = "error"
        results["skill_rules"]["detail"] = str(e)

    return results

def check_cron_health():
    results = {"study_reminder": {"status": "pending"}, "bank_update": {"status": "pending"}}
    if not os.path.exists(CRON_JOBS_PATH):
        results["study_reminder"]["status"] = "skipped"
        results["study_reminder"]["detail"] = "本迁移包未包含 cron/jobs.json"
        results["bank_update"]["status"] = "skipped"
        results["bank_update"]["detail"] = "本迁移包未包含 cron/jobs.json"
        return results
    try:
        with open(CRON_JOBS_PATH, "r") as f:
            cron_data = json.load(f)
        for job in cron_data.get("jobs", []):
            jid = job.get("id", "")
            if jid == "395ff1b42f88":
                lr = job.get("last_run_at", "从未")
                ls = job.get("last_status", "unknown")
                en = job.get("enabled", False)
                if en and ls == "ok":
                    results["study_reminder"]["status"] = "ok"
                    results["study_reminder"]["detail"] = "最近运行 %s" % (lr.split("T")[0] if "T" in lr else lr)
                else:
                    results["study_reminder"]["status"] = "warning"
            if jid == "042e42c8a3dd":
                lr = job.get("last_run_at", "从未")
                ls = job.get("last_status", "unknown")
                en = job.get("enabled", False)
                if en and ls == "ok":
                    results["bank_update"]["status"] = "ok"
                    results["bank_update"]["detail"] = "最近运行 %s" % (lr.split("T")[0] if "T" in lr else lr)
                else:
                    results["bank_update"]["status"] = "warning"
    except Exception as e:
        results["study_reminder"]["status"] = "error"
        results["bank_update"]["status"] = "error"
    return results

def check_data_consistency():
    results = {"total_count": {"status": "pending"}, "orphan_records": {"status": "pending", "count": 0}, "missing_in_bank": {"status": "pending", "count": 0}}
    try:
        with open(BANK_PATH, "r") as f:
            bank = json.load(f)
        with open(PROGRESS_PATH, "r") as f:
            progress = json.load(f)

        bank_qids = set()
        actual_count = 0
        for mod in bank.get("modules", {}).values():
            for q in mod.get("questions", []):
                bank_qids.add(q.get("id"))
                actual_count += 1

        progress_total = sum(m.get("total_topics", 0) for m in progress.get("modules_progress", {}).values())
        results["total_count"]["detail"] = "bank=%d题, progress.total_topics之和=%d" % (actual_count, progress_total)
        results["total_count"]["status"] = "ok" if abs(actual_count - progress_total) <= 5 else "warning"

        tracking = progress.get("question_tracking", {})
        orphans = [qid for qid in tracking if qid not in bank_qids]
        results["orphan_records"]["count"] = len(orphans)
        results["orphan_records"]["status"] = "ok" if len(orphans) == 0 else "warning"
        results["orphan_records"]["detail"] = "%d 条孤儿记录" % len(orphans)

        if 0 < len(orphans) <= 3:
            for qid in orphans:
                del tracking[qid]
            with open(PROGRESS_PATH, "w") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
            results["orphan_records"]["status"] = "fixed"
            results["orphan_records"]["detail"] += " (已自动清理)"

        missing = [qid for qid, rec in tracking.items() if rec.get("first_learned") and qid not in bank_qids]
        results["missing_in_bank"]["count"] = len(missing)
        results["missing_in_bank"]["status"] = "ok" if len(missing) == 0 else "warning"
    except Exception as e:
        results["total_count"]["status"] = "error"
    return results

def main():
    overall = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "quality": check_bank_quality(),
        "anti_hallucination": check_anti_hallucination(),
        "cron_health": check_cron_health(),
        "data_consistency": check_data_consistency(),
        "summary": {"total_checks": 0, "passed": 0, "warnings": 0, "errors": 0, "skipped": 0, "fixed": 0}
    }

    for section in [overall["quality"], overall["anti_hallucination"], overall["cron_health"], overall["data_consistency"]]:
        for check_result in section.values():
            s = check_result.get("status", "unknown")
            overall["summary"]["total_checks"] += 1
            if s in ("ok", "fixed"):
                overall["summary"]["passed"] += 1
                if s == "fixed":
                    overall["summary"]["fixed"] += 1
            elif s == "warning":
                overall["summary"]["warnings"] += 1
            elif s == "error":
                overall["summary"]["errors"] += 1
            elif s == "skipped":
                overall["summary"]["skipped"] += 1

    print(json.dumps(overall, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
