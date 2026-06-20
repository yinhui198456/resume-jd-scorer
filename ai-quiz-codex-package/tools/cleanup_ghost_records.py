#!/usr/bin/env python3
"""
清理 tracking.json 中的"幽灵记录" + 补全 module 字段 + 重算 topics_done

⚠️ 使用前必须备份 progress.json！

【幽灵记录】first_learned=null 的空记录，quiz_session.py（已 DEPRECATED）历史写入。
【补全 module】从 QID 前缀推断 module key。
【重算 topics_done】从 active tracking 重新统计各模块已学题数。

用法：
    cd ~/.hermes/profiles/learning/workspace/interview-prep
    python3 scripts/cleanup_ghost_records.py [--dry-run]
"""
import json
import os
import shutil
import argparse
from datetime import datetime
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
PROGRESS_PATH = os.path.join(ROOT_DIR, 'data', 'tracking', 'progress.json')

# QID 前缀 → module key 映射（与 bank.json modules 严格对应）
MODULE_MAP = {
    'M01_LLM基础': 'M01_LLM基础',
    'M02_Transformer': 'M02_Transformer',
    'M03_Prompt工程': 'M03_Prompt工程',
    'M04_Context工程': 'M04_Context工程',
    'M05_FunctionCalling': 'M05_FunctionCalling',
    'M06_MCP协议': 'M06_MCP协议',
    'M07_Skills': 'M07_Skills',
    'M08_Agent架构': 'M08_Agent架构',
    'M09_框架选型': 'M09_框架选型',
    'M10_MultiAgent': 'M10_MultiAgent',
    'M11_RAG': 'M11_RAG',
    'M12_Memory': 'M12_Memory',
    'M13_安全评估': 'M13_安全评估',
    'M14_推理部署': 'M14_推理部署',
    'M15_成本优化': 'M15_成本优化',
    'M16_AgenticCoding': 'M16_AgenticCoding',
    'M17_工程化': 'M17_工程化',
    'M18_系统设计': 'M18_系统设计',
    'M19_VLM多模态': 'M19_VLM多模态',
}


def cleanup_progress(progress):
    """Return a cleaned progress object plus summary stats.

    Tracking is active-only: records without first_learned are ghosts and are
    removed. Active records keep or receive their module field, and
    modules_progress[*].topics_done is recomputed from active tracking records.
    """
    p = json.loads(json.dumps(progress))
    tracking = p.get('question_tracking', {})
    ghost = [qid for qid, t in tracking.items() if not t.get('first_learned')]
    active = [qid for qid in tracking if qid not in ghost]

    module_fixed = 0
    for qid, t in tracking.items():
        if not t.get('module'):
            for prefix, mod in MODULE_MAP.items():
                if qid.startswith(f'Q-{prefix}'):
                    t['module'] = mod
                    module_fixed += 1
                    break

    mod_count = Counter()
    for qid, t in tracking.items():
        mod = t.get('module')
        if mod and t.get('first_learned'):
            mod_count[mod] += 1

    mp = p.get('modules_progress', {})
    for mod, count in mod_count.items():
        if mod not in mp:
            mp[mod] = {}
        mp[mod]['topics_done'] = count
    p['modules_progress'] = mp

    for qid in ghost:
        del tracking[qid]
    p['question_tracking'] = tracking

    return p, {
        'ghost_count': len(ghost),
        'active_count': len(active),
        'module_fixed': module_fixed,
        'module_counts': dict(mod_count),
    }


def main():
    parser = argparse.ArgumentParser(description='清理 tracking.json 幽灵记录')
    parser.add_argument('--dry-run', action='store_true', help='只查看，不修改')
    args = parser.parse_args()

    with open(PROGRESS_PATH) as f:
        p = json.load(f)
    tracking = p.get('question_tracking', {})
    cleaned, stats = cleanup_progress(p)

    print(f'=== 清理前 ===')
    print(f'  tracking 总记录: {len(tracking)}')
    ghost = [qid for qid, t in tracking.items() if not t.get('first_learned')]
    print(f'  幽灵记录: {len(ghost)}')
    active = [qid for qid in tracking if qid not in ghost]
    print(f'  活跃记录: {len(active)}')
    print(f"  补全 module 字段: {stats['module_fixed']} 条")

    if args.dry_run:
        print()
        print('=== [DRY RUN] 将要执行 ===')
        print(f"  删除幽灵记录: {stats['ghost_count']} 条")
        print(f'  重算 topics_done 后各模块:')
        for mod, count in sorted(stats['module_counts'].items()):
            print(f'    {mod}: {count}')
        return

    # 备份 + 保存
    backup = f'{PROGRESS_PATH}.bak-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    shutil.copy(PROGRESS_PATH, backup)
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print()
    print(f'=== 清理后 ===')
    print(f'  备份: {backup}')
    print(f"  tracking 总记录: {len(cleaned.get('question_tracking', {}))}")
    print(f"  真实活跃题数: {stats['active_count']}")
    print(f'  重算 topics_done:')
    for mod, count in sorted(stats['module_counts'].items(), key=lambda x: -x[1]):
        print(f'    {mod}: {count}')


if __name__ == '__main__':
    main()
