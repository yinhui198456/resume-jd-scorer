#!/usr/bin/env python3
"""Interactive quiz question reader — reads from bank.json and outputs formatted text.
The LLM MUST relay this output verbatim. Never reconstruct questions from memory.

Usage:
    python3 scripts/get_question.py next M08_Agent架构          # Next unlearned question
    python3 scripts/get_question.py review                       # Next due review question (today)
    python3 scripts/get_question.py by_id Q-088                  # Specific question by ID
    python3 scripts/get_question.py next_in_module M08_Agent架构 Q-089  # Next after Q-089
"""

import json
import sys
import os
from datetime import datetime, date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
BANK_PATH = os.path.join(ROOT_DIR, 'data', 'question-bank', 'bank.json')
PROGRESS_PATH = os.path.join(ROOT_DIR, 'data', 'tracking', 'progress.json')

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def find_module_id(modules, partial):
    """Find module key matching partial name."""
    for key in modules:
        if partial in key:
            return key
    return None

def format_question(q, format_type='text'):
    """Output question in a clean format."""
    if format_type == 'md':
        # Output directly displayable Markdown
        qid = q['id']
        module = q.get('_module_hint', '')
        question = q['question']
        options = q.get('options', [])
        labels = ['A', 'B', 'C', 'D']
        
        lines = []
        lines.append(f"**📝 {qid} | {module}**")
        lines.append(f"{question}")
        lines.append("")
        for i, opt in enumerate(options):
            if i < len(labels):
                lines.append(f"{labels[i]}. {opt}")
        
        lines.append("")
        return '\n'.join(lines)
    
    # Default text format (machine readable)
    lines = []
    lines.append(f"QID|{q['id']}")
    lines.append(f"MODULE|{q.get('_module_hint', '')}")
    lines.append(f"QUESTION|{q['question']}")
    labels = ['A', 'B', 'C', 'D']
    for i, opt in enumerate(q['options']):
        lines.append(f"OPT|{labels[i]}|{opt}")
    lines.append(f"ANSWER|{q['answer'].rstrip('.')}")
    lines.append(f"END")
    return '\n'.join(lines)

def get_by_id(qid, format_type='text'):
    bank = load_json(BANK_PATH)
    for mod_key, mod_data in bank['modules'].items():
        for q in mod_data['questions']:
            if q['id'] == qid:
                q['_module_hint'] = mod_key
                print(format_question(q, format_type))
                return
    print(f"ERROR|Question {qid} not found")

def get_next_unlearned(module_partial, format_type='text'):
    bank = load_json(BANK_PATH)
    progress = load_json(PROGRESS_PATH)
    
    mod_key = find_module_id(bank['modules'], module_partial)
    if not mod_key:
        print(f"ERROR|Module '{module_partial}' not found. Available: {', '.join(bank['modules'].keys())}")
        return
    
    tracking = progress.get('question_tracking', {})
    questions = bank['modules'][mod_key]['questions']
    
    # Find first unlearned question
    for q in questions:
        tid = q['id']
        t = tracking.get(tid, {})
        if t.get('first_learned') is None:
            q['_module_hint'] = mod_key
            print(format_question(q, format_type))
            return
    
    # All learned, show completion
    print(f"COMPLETE|Module {mod_key} - all {len(questions)} questions learned")

def get_next_in_module(module_partial, after_qid, format_type='text'):
    bank = load_json(BANK_PATH)
    
    mod_key = find_module_id(bank['modules'], module_partial)
    if not mod_key:
        print(f"ERROR|Module '{module_partial}' not found")
        return
    
    questions = bank['modules'][mod_key]['questions']
    found_current = False
    for q in questions:
        if found_current:
            q['_module_hint'] = mod_key
            print(format_question(q, format_type))
            return
        if q['id'] == after_qid:
            found_current = True
    
    print(f"COMPLETE|{after_qid} is the last question in {mod_key}")

def get_due_review():
    """Get the first question due for review today."""
    progress = load_json(PROGRESS_PATH)
    bank = load_json(BANK_PATH)
    today = str(date.today())
    
    tracking = progress.get('question_tracking', {})
    for qid, t in tracking.items():
        if t.get('first_learned') and not t.get('first_learned') is None:
            next_rev = t.get('next_review', '')
            if next_rev and next_rev <= today:
                # Find this question in bank
                for mod_key, mod_data in bank['modules'].items():
                    for q in mod_data['questions']:
                        if q['id'] == qid:
                            q['_module_hint'] = mod_key
                            print(format_question(q))
                            return
    print("NO_REVIEW|No questions due for review today")


def get_next_auto_switch(current_module_partial, format_type='text'):
    """Get next question. If current module is done, auto-switch to next module with unlearned questions."""
    bank = load_json(BANK_PATH)
    progress = load_json(PROGRESS_PATH)
    
    module_order = list(bank['modules'].keys())
    
    # Find current module index
    current_mod_key = find_module_id(bank['modules'], current_module_partial)
    start_idx = 0
    if current_mod_key and current_mod_key in module_order:
        start_idx = module_order.index(current_mod_key)
    
    # Try current module first, then subsequent modules
    for i in range(start_idx, len(module_order)):
        mod_key = module_order[i]
        tracking = progress.get('question_tracking', {})
        questions = bank['modules'][mod_key]['questions']
        
        # Find first unlearned question
        for q in questions:
            tid = q['id']
            t = tracking.get(tid, {})
            if t.get('first_learned') is None:
                q['_module_hint'] = mod_key
                print(f"AUTO_SWITCH|{mod_key}")
                print(format_question(q, format_type))
                return
        
        # If this module is done and it's not the starting one, report it
        if mod_key != current_mod_key:
            print(f"MODULE_DONE|{mod_key}")
    
    # All modules done
    print("COMPLETE|All modules completed! You've learned all questions in the bank.")

if __name__ == '__main__':
    # Parse arguments
    args = sys.argv[1:]
    format_type = 'text'
    if '--format' in args:
        idx = args.index('--format')
        if idx + 1 < len(args):
            format_type = args[idx + 1]
            args = args[:idx] + args[idx+2:] # Remove --format flag
    
    if not args:
        print(__doc__)
        sys.exit(1)
    
    cmd = args[0]
    
    if cmd == 'by_id' and len(args) >= 2:
        get_by_id(args[1], format_type)
    elif cmd == 'next' and len(args) >= 2:
        get_next_unlearned(args[1], format_type)
    elif cmd == 'next_in_module' and len(args) >= 3:
        get_next_in_module(args[1], args[2], format_type)
    elif cmd == 'auto_next' and len(args) >= 2:
        get_next_auto_switch(args[1], format_type)
    elif cmd == 'review':
        # Review logic needs format support too, but usually handled differently
        pass
    else:
        print(__doc__)
