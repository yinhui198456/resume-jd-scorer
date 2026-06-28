#!/usr/bin/env python3
"""周报生成-校验-修复流水线。

用法：
    python3 report_pipeline.py [config_path]

退出码：
    0 - 通过，可直接使用
    1 - 参数/运行错误
    2 - 需要人工审查
"""
import json
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

from report_engine_v9 import (
    ExcelParser,
    ReportGenerator,
    load_config_simple,
    resolve_config_paths,
)
from validate_report_tone import validate_tone
from validate_weekly_report import validate_document


AUTO_FIXABLE_KEYWORDS = ['空编号', 'eastAsia', '模糊用语', 'Markdown', '占位符']
HUMAN_REQUIRED_KEYWORDS = ['gridSpan', 'vMerge', '重复内容', '页面1', '首页留白', '合并单元格']


def classify_issue(issue):
    """Return 'auto' if the issue can be fixed automatically, else 'human'."""
    for kw in AUTO_FIXABLE_KEYWORDS:
        if kw in issue:
            return 'auto'
    for kw in HUMAN_REQUIRED_KEYWORDS:
        if kw in issue:
            return 'human'
    return 'human'


def apply_fix(doc_path, issue):
    """Apply an automatic fix for a single issue.

    Returns a description of the fix, or None if no automatic fix is available.
    """
    # Placeholder: actual fixes implemented in report_auto_fix.py (Task 6)
    return None


def run_generation(config_path):
    """Generate the weekly report Word document."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f'配置文件不存在: {config_path}')

    config = load_config_simple(config_path)
    config_dir = os.path.dirname(os.path.abspath(config_path))
    config = resolve_config_paths(config, config_dir)

    xlsx_path = config.get('source', {}).get('xlsx_path', '')
    template_path = config.get('source', {}).get('template_path', '')
    output_dir = config.get('source', {}).get('output_dir', '')

    parser = ExcelParser(config)
    data = parser.parse(xlsx_path)

    generator = ReportGenerator(config, data)
    report_info = generator.generate(template_path, output_dir)
    if not report_info:
        raise RuntimeError('文档生成失败')

    # Also generate email body for downstream use
    email_body = generator.generate_email_body(report_info)
    email_path = os.path.join(
        output_dir, 'email_body_' + report_info['filename'].replace('.docx', '.txt')
    )
    with open(email_path, 'w', encoding='utf-8') as f:
        f.write(email_body)

    report_info['email_path'] = email_path
    return report_info


def run_validation(doc_path, xlsx_path=None):
    """Run structural and tone validation on a generated docx."""
    if xlsx_path is None:
        xlsx_path = os.path.join(PROJECT_DIR, 'data', '金坛二期项目跟进表.xlsx')
    return {
        'structure': validate_document(doc_path, xlsx_path),
        'tone': validate_tone(doc_path),
    }


def run_pipeline(config_path, max_iterations=3):
    """Generate, validate, auto-fix, and re-validate the weekly report."""
    report_info = run_generation(config_path)
    doc_path = report_info['doc_path']
    xlsx_path = os.path.join(PROJECT_DIR, 'data', '金坛二期项目跟进表.xlsx')

    fixes_applied = []
    validation = None

    for iteration in range(max_iterations):
        validation = run_validation(doc_path, xlsx_path)
        all_issues = []
        for result in validation.values():
            all_issues.extend(result.get('issues', []))

        if not all_issues:
            return {
                'report': report_info,
                'validation': validation,
                'fixes_applied': fixes_applied,
                'human_review_needed': False,
            }

        auto_issues = [i for i in all_issues if classify_issue(i) == 'auto']
        human_issues = [i for i in all_issues if classify_issue(i) == 'human']

        if human_issues:
            # Structural or ambiguous issues need human review.
            return {
                'report': report_info,
                'validation': validation,
                'fixes_applied': fixes_applied,
                'human_review_needed': True,
                'human_issues': human_issues,
            }

        if not auto_issues:
            # No fixable issues but still failing; give up and ask human.
            return {
                'report': report_info,
                'validation': validation,
                'fixes_applied': fixes_applied,
                'human_review_needed': True,
                'human_issues': all_issues,
            }

        # Apply one round of auto-fixes.
        round_fixes = []
        for issue in auto_issues:
            fix_desc = apply_fix(doc_path, issue)
            if fix_desc:
                round_fixes.append(fix_desc)
        if not round_fixes:
            # Nothing could be fixed automatically.
            return {
                'report': report_info,
                'validation': validation,
                'fixes_applied': fixes_applied,
                'human_review_needed': True,
                'human_issues': all_issues,
            }
        fixes_applied.extend(round_fixes)

    return {
        'report': report_info,
        'validation': validation,
        'fixes_applied': fixes_applied,
        'human_review_needed': True,
        'human_issues': all_issues,
    }


if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJECT_DIR, 'config.yaml')
    try:
        result = run_pipeline(config_path)
    except Exception as e:
        print(json.dumps({'status': 'ERROR', 'error': str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(2 if result.get('human_review_needed') else 0)
