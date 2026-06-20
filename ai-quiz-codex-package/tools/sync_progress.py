#!/usr/bin/env python3
"""Sync progress.json with bank.json.

Run after modifying bank.json (adding/removing questions). Ensures:
1. modules_progress[*].total_topics matches actual question counts in bank.json
2. question_tracking remains active-only: only learned/skipped/answered questions
   should have records
3. Tracking records whose question IDs are no longer in bank.json are reported
   but not pruned automatically

Usage: python sync_progress.py [bank_path] [progress_path]
Defaults to the standard interview-prep paths.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BANK = ROOT_DIR / "data" / "question-bank" / "bank.json"
DEFAULT_PROGRESS = ROOT_DIR / "data" / "tracking" / "progress.json"


def sync(bank_path=None, progress_path=None, dry_run=False):
    bank_path = Path(bank_path or DEFAULT_BANK)
    progress_path = Path(progress_path or DEFAULT_PROGRESS)

    with open(bank_path, 'r') as f:
        bank = json.load(f)
    with open(progress_path, 'r') as f:
        progress = json.load(f)

    all_bank_ids = set()
    module_counts = {}
    for mod_key, mod_data in bank['modules'].items():
        qs = mod_data['questions']
        module_counts[mod_key] = len(qs)
        for q in qs:
            all_bank_ids.add(q['id'])

    if 'question_tracking' not in progress:
        progress['question_tracking'] = {}

    existing_ids = set(progress['question_tracking'].keys())
    untracked_bank_ids = all_bank_ids - existing_ids
    removed_ids = existing_ids - all_bank_ids
    added_tracking_records = 0

    # Prune removed entries (warn but don't delete by default)
    if removed_ids:
        print(f"⚠️  {len(removed_ids)} question(s) in tracking but not in bank: {sorted(removed_ids)}")
        # Optional: uncomment to auto-prune
        # for qid in removed_ids:
        #     del progress['question_tracking'][qid]

    # Update total_topics per module
    updated_modules = []
    for mod_key, count in module_counts.items():
        if mod_key in progress['modules_progress']:
            old = progress['modules_progress'][mod_key].get('total_topics', 0)
            if old != count:
                progress['modules_progress'][mod_key]['total_topics'] = count
                updated_modules.append(f"  {mod_key}: {old} → {count}")

    # Update bank metadata
    today = datetime.now().strftime('%Y-%m-%d')
    bank['version'] = today
    bank['last_updated'] = today

    # Report
    print(f"\nSync summary:")
    print(f"  Total questions in bank: {len(all_bank_ids)}")
    print(f"  New tracking entries added: {added_tracking_records}")
    print(f"  Untracked bank questions left as new: {len(untracked_bank_ids)}")
    if removed_ids:
        print(f"  Removed (in tracking but not bank): {len(removed_ids)}")
    if updated_modules:
        print(f"  Modules with updated total_topics:")
        for line in updated_modules:
            print(line)
    else:
        print(f"  No module total_topics changes needed")

    if not dry_run:
        with open(bank_path, 'w') as f:
            json.dump(bank, f, ensure_ascii=False, indent=2)
        with open(progress_path, 'w') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Written: {bank_path}, {progress_path}")
    else:
        print(f"\n🔍 Dry run — no files written")

    return added_tracking_records, len(updated_modules)


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    bp = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '--dry-run' else None
    pp = sys.argv[2] if len(sys.argv) > 2 else None
    sync(bp, pp, dry_run=dry)
