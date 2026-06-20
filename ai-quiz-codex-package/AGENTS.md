# AI Quiz Codex Instructions

This repository is a deterministic AI interview quiz system migrated from the Hermes `quiz-bot` skill.

## Trigger

When the user says `开始AI刷题`, `开始刷题`, `刷题`, `下一题`, or asks to practice AI interview questions, use the repo skill `ai-quiz-codex` and start immediately.

## Required Workflow

- Run all commands from the project root.
- Get every question from `python3 engine/quiz_bot.py --format md next`.
- Relay script output exactly; do not rewrite questions, options, or grading output.
- After showing a question, stop and wait for the user's answer.
- If the user replies with only `A`, `B`, `C`, or `D`, read `data/tracking/quiz_bot_state.json` for `current_qid`, then run:
  `python3 engine/quiz_bot.py --format md answer <current_qid> <option>`
- After grading, immediately run:
  `python3 engine/quiz_bot.py --format md next`
- Do not invent questions, answers, explanations, QIDs, or progress numbers.

## Useful Commands

- Start quiz: `python3 engine/quiz_bot.py --format md next`
- Review: `python3 engine/quiz_bot.py --format md review`
- Status: `python3 engine/quiz_bot.py status`
- Intercepts: `python3 engine/quiz_bot.py intercepts`

## Data Rules

`question_tracking` is active-only. Only learned, answered, or skipped questions should have records. Do not create empty `first_learned: null` tracking records for unseen questions.
