# Weekend Lunch Plan Codex Instructions

当用户在本仓库中发出“周末午餐建议”、询问周末吃什么、午餐方案、家庭备餐计划、现有食材推荐、确认菜单或饭后菜品反馈时，优先使用 `$weekend-lunch-plan` skill。

该 skill 位于 `.agents/skills/weekend-lunch-plan/SKILL.md`。如果隐式触发不稳定，可显式使用：

```text
$weekend-lunch-plan 周末午餐建议
```

日常使用时不要要求用户手工运行脚本。由 Codex 按 skill SOP 调用预检、审核、记录和反馈脚本；只有在调试或验收时才手工运行脚本。
