#!/usr/bin/env python3
"""Scan bank.json for answer-explanation mismatches.

Fixed version: uses positional indices (A=0, B=1, C=2, D=3) instead of
first-character matching, which broke when options lost their A/B/C/D prefixes.
"""
import json
import sys
import os

def find_mismatches(bank_path):
    with open(bank_path, encoding="utf-8") as f:
        bank = json.load(f)

    modules = bank.get('modules', {})
    mismatches = []

    for mname, mdata in modules.items():
        qs = mdata.get('questions', [])
        for q in qs:
            ans_letter = q.get('answer', '').strip().rstrip('.')
            opts = q.get('options', [])
            exp = q.get('explanation', '')

            if not ans_letter or len(opts) != 4 or not exp:
                continue

            ans_idx = ord(ans_letter) - ord('A')
            if ans_idx < 0 or ans_idx >= 4:
                continue

            ans_text = opts[ans_idx]

            # Check: does the explanation contain a NON-answer option's text verbatim?
            # Only flag if the option text appears near the START of explanation
            # (explanations often mention correct answer first)
            exp_start = exp[:200]  # Check first 200 chars
            for i, opt in enumerate(opts):
                if i == ans_idx:
                    continue
                if len(opt) < 15:
                    continue
                # Check if the non-answer option appears at the very start of explanation
                # (indicating it's the real answer being explained)
                opt_prefix = opt[:min(30, len(opt))]
                if exp_start.startswith(opt_prefix):
                    mismatches.append({
                        'id': q.get('id', '?'),
                        'module': mname,
                        'question': q.get('question', '')[:80],
                        'answer': ans_letter,
                        'answer_text': ans_text[:60],
                        'matching_option': chr(65 + i),
                        'matching_text': opt[:60],
                        'explanation': exp[:120],
                    })
                    break
                # Also check if explanation starts with the concept name that matches this option
                # but NOT the answer
                opt_key = opt[:15]
                ans_key = ans_text[:15]
                if opt_key in exp_start and ans_key not in exp_start[:50]:
                    # Non-answer option key found early, answer key not found early
                    # This might be a real mismatch
                    # But be careful - many explanations start with the concept name
                    # which might appear in multiple options
                    pass

    return mismatches

if __name__ == '__main__':
    bank_path = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'question-bank', 'bank.json')

    mismatches = find_mismatches(bank_path)

    if not mismatches:
        print('All answer-explanation pairs consistent. ✅')
        sys.exit(0)

    print(f'Found {len(mismatches)} answer-explanation mismatches:\n')
    for m in mismatches:
        print(f"  {m['id']} ({m['module'][:15]}): {m['question']}")
        print(f"    answer={m['answer']} -> '{m['answer_text']}'")
        print(f"    but explanation starts with option {m['matching_option']} -> '{m['matching_text']}'")
        print()

    sys.exit(1)
