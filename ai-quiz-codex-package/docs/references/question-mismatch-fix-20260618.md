# Q26 题干-选项不匹配修复记录 (2026-06-18)

## 现象
用户反馈：「这题好像有问题，答案中没有看到优势」

## 根因
Q-M05_FunctionCalling26 题干是「相比传统的 API 调用，Function Calling 的最大优势是什么？」
但选项全部是 OpenAI vs Anthropic 的 API 响应结构差异 — 题干和选项完全不匹配。
属于典型串题/编辑错误。

## 诊断命令
```bash
cd /root/.hermes/profiles/learning/workspace/interview-prep
python3 -c "
import json
with open('question-bank/bank.json') as f:
    bank = json.load(f)
for mod_name, mod_data in bank['modules'].items():
    for q in mod_data.get('questions', []):
        if q.get('id') == 'Q-M05_FunctionCalling26':
            print('Question:', q['question'])
            print('Options:', q['options'])
            print('Answer:', q['answer'])
            print('Explanation:', q['explanation'])
            break
"
```

## 修复方式
根据 explanation 内容，将题干改为与选项匹配的问题：
```python
q['question'] = 'OpenAI 和 Anthropic 在 Function Calling 的 API 响应结构上有什么主要区别？'
```

## ⚠️ 注意：修改 bank.json 后 hash 失效
修改 bank.json 后，quiz_bot 的 P4 hash 校验会拒绝判题（日志 hash ≠ 题库 hash）。
**必须**重新运行 `quiz_bot.py --format md next` 获取最新 hash 后才能继续判题。

## 预防建议
定期运行题库审计脚本检查 question/explanation/options 一致性。
