#!/usr/bin/env python3
"""Check distractor quality in bank.json - identify length bias issues."""
import json, re, sys, os

def check_quality(bank_path, threshold=1.8):
    with open(bank_path, 'r', encoding='utf-8') as f:
        bank = json.load(f)
    
    issues = []
    total = 0
    for mod_name, mod_data in bank['modules'].items():
        for q in mod_data.get('questions', []):
            total += 1
            opts = q.get('options', [])
            ans = q.get('answer', '')
            if not opts or not ans:
                continue
            # Handle answer format: "A" or "A."
            ans_clean = ans.strip().rstrip('.')
            ans_idx = ord(ans_clean) - ord('A')
            if ans_idx < 0 or ans_idx >= len(opts):
                continue
            clean_opts = [re.sub(r'^[A-D][、.．]\s*', '', opt) for opt in opts]
            ans_len = len(clean_opts[ans_idx])
            distractor_lens = [len(clean_opts[i]) for i in range(len(clean_opts)) if i != ans_idx]
            if not distractor_lens:
                continue
            avg_d = sum(distractor_lens) / len(distractor_lens)
            ratio = ans_len / max(avg_d, 1)
            if ratio > threshold:
                issues.append({
                    'id': q['id'],
                    'module': mod_name,
                    'question': q['question'][:50],
                    'answer_len': ans_len,
                    'avg_distractor': round(avg_d, 0),
                    'ratio': round(ratio, 1)
                })
    
    issues.sort(key=lambda x: x['ratio'], reverse=True)
    print(f"Total questions: {total}")
    print(f"Issues (ratio > {threshold}x): {len(issues)}")
    for i, issue in enumerate(issues[:20]):
        print(f"  {i+1}. {issue['id']} ({issue['module'][:10]}): ratio={issue['ratio']}x, ans={issue['answer_len']}c, avg={issue['avg_distractor']}c")
    return issues

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(script_dir, '..', 'data', 'question-bank', 'bank.json')
    check_quality(path)
