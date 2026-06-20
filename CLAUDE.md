# Personal Agent Workspace Rules

## Scope
当前工作区用于个人 SOP 场景验证，包括：
- AI 刷题 SOP
- 周末午餐建议 SOP
- 后续 AI 资讯 / 项目周报类 SOP

## General Rules
1. 默认只读分析，不主动修改文件。
2. 需要修改文件时，必须先说明将修改哪些文件、修改原因和影响范围。
3. 涉及 data、sop、scripts、配置文件的修改，必须先等待用户确认。
4. 输出类内容优先写入 output/ 或项目内指定输出目录。
5. 不允许删除历史数据文件；如需清理，只能先生成清理建议。
6. 不要跨项目混用上下文：处理 ai-quiz 时只读取 ai-quiz-codex-package；处理 lunch 时只读取 weekend-lunch-plan-codex。
7. 所有结论必须基于当前工作区文件，不要凭空假设已有文件内容。
