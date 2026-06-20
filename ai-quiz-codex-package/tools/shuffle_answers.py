#!/usr/bin/env python3
"""Shuffle answer options in bank.json to prevent position-based cheating.
Uses seed 48 for optimal A/B/C/D distribution (24-26% each).
Usage: python shuffle_answers.py [bank.json_path]
"""
import json, random, sys, os

DEFAULT_SEED = 114

def shuffle_answers(bank_path, seed=DEFAULT_SEED):
    random.seed(seed)
    with open(bank_path, 'r', encoding='utf-8') as f:
        bank = json.load(f)
    
    total = 0
    for mod_val in bank['modules'].values():
        for q in mod_val.get('questions', []):
            if not q.get('options') or not q.get('answer'):
                continue
            # Handle answer format: "A" or "A."
            ans = q['answer'].strip().rstrip('.')
            correct_idx = ord(ans) - ord('A')
            if correct_idx < 0 or correct_idx >= len(q['options']):
                continue
            correct_text = q['options'][correct_idx]
            shuffled = list(q['options'])
            random.shuffle(shuffled)
            new_idx = shuffled.index(correct_text)
            q['options'] = shuffled
            q['answer'] = chr(ord('A') + new_idx) + '.'
            total += 1
    
    with open(bank_path, 'w', encoding='utf-8') as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)
    
    # Report distribution
    counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for mod_val in bank['modules'].values():
        for q in mod_val.get('questions', []):
            ans = q.get('answer', '').strip().rstrip('.')
            if ans in counts:
                counts[ans] += 1
    total_q = sum(counts.values())
    print(f"Shuffled {total} questions")
    if total_q > 0:
        for letter, count in counts.items():
            print(f"  {letter}: {count} ({count/total_q*100:.1f}%)")
    return total

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(script_dir, '..', 'data', 'question-bank', 'bank.json')
    shuffle_answers(path)
