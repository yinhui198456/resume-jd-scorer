#!/usr/bin/env python3
"""
题库结构对齐脚本 V2 —— 基于模块结构修复 ID。
适配新版 bank.json 结构 (含 modules 字典)。
"""

import json
import os
import re
import shutil
from collections import defaultdict

# === 配置 ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
BANK_PATH = os.path.join(ROOT_DIR, "data", "question-bank", "bank.json")
PROGRESS_PATH = os.path.join(ROOT_DIR, "data", "tracking", "progress.json")
BACKUP_DIR = os.path.join(ROOT_DIR, "data", "backup_structure_fix_v2")

def extract_seq_from_id(qid):
    """从 ID 中提取数字序号"""
    if not qid: return 0
    # 匹配末尾的数字
    match = re.search(r'(\d+)$', qid)
    if match:
        return int(match.group(1))
    return 0

def main():
    # 1. 备份
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(BANK_PATH):
        shutil.copy(BANK_PATH, os.path.join(BACKUP_DIR, f"bank.json.bak.{int(os.path.getmtime(BANK_PATH))}"))
    if os.path.exists(PROGRESS_PATH):
        shutil.copy(PROGRESS_PATH, os.path.join(BACKUP_DIR, f"progress.json.bak"))

    # 2. 加载数据
    with open(BANK_PATH, 'r', encoding='utf-8') as f:
        bank = json.load(f)
    
    progress = {}
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, 'r', encoding='utf-8') as f:
            progress = json.load(f)

    print(f"Loaded bank.json. Modules: {list(bank.get('modules', {}).keys())}")
    
    migration_map = {}
    total_fixed = 0

    # 3. 遍历模块
    if 'modules' not in bank:
        print("ERROR: No 'modules' key found in bank.json")
        return

    for mod_key, mod_data in bank['modules'].items():
        if 'questions' not in mod_data:
            continue
            
        questions = mod_data['questions']
        print(f"\nProcessing {mod_key}: {len(questions)} questions")
        
        # Step A: 提取序号并去重
        # 我们用一个字典来存 {seq: question_data}
        # 如果有多个题目有相同的 seq，我们要决定保留哪个或重新编号
        
        seq_map = defaultdict(list)
        for q in questions:
            old_id = q.get('id', '')
            seq = extract_seq_from_id(old_id)
            seq_map[seq].append(q)
        
        # Step B: 重建列表
        new_questions = []
        new_seq = 1
        
        # 按原序号排序遍历
        for seq in sorted(seq_map.keys()):
            group = seq_map[seq]
            # 如果这个序号下有多题（冲突），按原样保留但分配新序号
            # 如果序号是 0（解析失败），也保留
            
            for q in group:
                old_id = q.get('id', '')
                
                # 生成新 ID: Q-M01_LLM基础01
                # 注意：mod_key 已经是 M01_LLM基础 这种格式了
                new_id = f"Q-{mod_key}{new_seq:02d}"
                
                # 记录迁移
                if old_id:
                    migration_map[old_id] = new_id
                
                # 更新题目 ID
                q['id'] = new_id
                
                # 清洗 answer
                if 'answer' in q and isinstance(q['answer'], str):
                    clean_ans = q['answer'].strip().rstrip('.。．').strip().upper()
                    if clean_ans in ['A', 'B', 'C', 'D']:
                        q['answer'] = clean_ans
                        # 检查是否真的改了
                        # if q['answer'] != old_ans: print(f"  Fixed answer for {new_id}")
                
                new_questions.append(q)
                new_seq += 1
        
        # 更新模块数据
        mod_data['questions'] = new_questions
        total_fixed += len(new_questions)
        print(f"  -> Renumbered 1 to {new_seq-1}")

    # 4. 写入 Bank
    with open(BANK_PATH, 'w', encoding='utf-8') as f:
        json.dump(bank, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved bank.json. Total questions processed: {total_fixed}")

    # 5. 更新 Progress Tracking
    # tracking 是一个列表，包含 {'qid': '...', ...}
    # 我们需要把里面的 qid 替换掉
    tracking_count = 0
    if 'question_tracking' in progress:
        for item in progress['question_tracking']:
            old_qid = item.get('qid')
            if old_qid in migration_map:
                new_qid = migration_map[old_qid]
                item['qid'] = new_qid
                tracking_count += 1
        
        with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
        print(f"✅ Updated {tracking_count} tracking records in progress.json")
    
    # 6. 保存映射表
    map_path = os.path.join(BACKUP_DIR, "migration_map_v2.json")
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(migration_map, f, indent=2, ensure_ascii=False)

    print(f"✅ Done! Migration map saved to {map_path}")

if __name__ == "__main__":
    main()
