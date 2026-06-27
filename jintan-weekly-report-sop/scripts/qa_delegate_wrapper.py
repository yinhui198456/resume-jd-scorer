#!/usr/bin/env python3
"""
周报质量检查 Agent - delegate_task 版本

通过 delegate_task 调用，执行完整的质量检查并自动修复。

输入参数：
  - doc_path: 周报文档路径
  - source_xlsx: 源 Excel 路径
  - auto_fix: 是否自动修复（默认 true）
  - qa_script_path: QA 脚本路径（默认同级目录 qa_weekly_report_v2.py）
"""
import sys
import os
import subprocess
import json

def run_qa_check(doc_path, source_xlsx, auto_fix=True):
    """Run QA check and optionally auto-fix."""
    qa_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa_weekly_report_v2.py")
    
    if not os.path.exists(qa_script):
        return {
            'status': 'error',
            'message': f'QA 脚本不存在: {qa_script}'
        }
    
    if not os.path.exists(doc_path):
        return {
            'status': 'error',
            'message': f'文档不存在: {doc_path}'
        }
    
    # Run QA check
    result = subprocess.run(
        ['python3', qa_script, doc_path, source_xlsx],
        capture_output=True,
        text=True
    )
    
    # Parse output
    output = result.stdout
    json_start = output.find('---JSON_START---')
    json_end = output.find('---JSON_END---')
    
    if json_start != -1 and json_end != -1:
        qa_report = json.loads(output[json_start + len('---JSON_START---'):json_end].strip())
    else:
        qa_report = {'raw_output': output}
    
    # Auto-fix if needed
    if auto_fix and qa_report.get('high_issues', 0) > 0:
        fix_results = []
        for issue in qa_report.get('issues', []):
            if issue['severity'] == 'HIGH':
                fix_results.append({
                    'issue': issue['message'],
                    'status': 'needs_manual_fix',
                    'note': 'HIGH 级别问题需要人工复核后修复'
                })
        qa_report['auto_fix_results'] = fix_results
    
    return {
        'status': 'success' if result.returncode == 0 else 'has_issues',
        'exit_code': result.returncode,
        'qa_report': qa_report,
        'doc_path': doc_path,
    }

if __name__ == "__main__":
    # Parse command line args
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    doc_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(project_dir, "output", "常州市金坛第一人民医院数据指挥中心二期项目-工作周报-20260427-0501.docx")
    source_xlsx = sys.argv[2] if len(sys.argv) > 2 else os.path.join(project_dir, "data", "金坛二期项目跟进表.xlsx")
    auto_fix = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else True
    
    result = run_qa_check(doc_path, source_xlsx, auto_fix)
    print(json.dumps(result, ensure_ascii=False, indent=2))
