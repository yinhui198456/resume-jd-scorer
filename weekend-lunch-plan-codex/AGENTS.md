# Weekend Lunch Plan Codex Instructions

当用户在本仓库中发出“周末午餐建议”、询问周末吃什么、午餐方案、家庭备餐计划、现有食材推荐、确认菜单或饭后菜品反馈时，优先使用 `$weekend-lunch-plan` skill。

Skill主源位于 `/opt/personal-agent-workspace/skills/weekend-lunch-plan/`。

项目内 `.agents/skills/weekend-lunch-plan` 只能是指向主源目录的 symlink，不维护第二份 Skill 内容。

兼容入口 `.agents/skills/weekend-lunch-plan/SKILL.md` 仍可读取，但实际内容来自工作区主源。

如果隐式触发不稳定，可显式使用：

```text
$weekend-lunch-plan 周末午餐建议
```

日常使用时不要要求用户手工运行脚本。由 Codex 按 skill SOP 调用预检、审核、记录和反馈脚本；只有在调试或验收时才手工运行脚本。

输出午餐方案或操作步骤到当前对话时，必须做轻量排版：按菜单、采购/准备、逐道菜、关键提醒分块；块之间留空行；优先使用短编号列表；避免长段落和大表格。飞书 bot 场景下内容过长时分多条消息发送。
