# Cron Script Path Bug (2026-05-31)

## 症状
`daily-interview-study-reminder` (job `395ff1b42f88`) 推送了 5 道题且新题直接暴露了答案。脚本没跑起来，LLM 凭记忆编题。

## 根因
cron job 配置的 script 路径解析错误：
```
workdir: /root/.hermes/profiles/learning
script (配置): workspace/interview-prep/scripts/prepare_daily_quiz.py
实际查找: /root/.hermes/profiles/learning/scripts/workspace/interview-prep/scripts/prepare_daily_quiz.py
                                               ^^^^^^^^ 系统多拼了一层 scripts/
正确路径: /root/.hermes/profiles/learning/workspace/interview-prep/scripts/prepare_daily_quiz.py
```

## 修复方案
脚本路径改为绝对路径，不能依赖相对路径：
```
script: /root/.hermes/profiles/learning/workspace/interview-prep/scripts/prepare_daily_quiz.py
```

## 教训
cron 系统对 `workdir` + `script` 的拼接逻辑会在 script 路径前自动加一层 `scripts/`（因为 cron job 的 script 默认预期放在 `~/.hermes/profiles/<name>/scripts/` 下）。如果脚本不在那个默认目录下，必须用**绝对路径**。

## 连锁后果
脚本失败 → LLM 拿不到 JSON 数据源 → 凭训练记忆编了 5 道题 → 新题答案直接暴露 → 完全违背「致命陷阱 1」和交互式出题设计。
