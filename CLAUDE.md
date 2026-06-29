# Personal Agent Workspace Rules

## Scope
当前工作区用于个人 SOP 场景验证，包括：
- AI 刷题 SOP
- 周末午餐建议 SOP
- 后续 AI 资讯 / 项目周报类 SOP

该目录是 Codex 和 Claude Code 共用的个人代理工作区。两类代理都应把 `/opt/personal-agent-workspace` 作为当前项目与数据的权威根目录；不要回退到 `/root/codex_ds` 或其它旧目录。

## General Rules
1. 默认只读分析，不主动修改文件。
2. 需要修改文件时，必须先说明将修改哪些文件、修改原因和影响范围。
3. 涉及 data、sop、scripts、配置文件的修改，必须先等待用户确认。
4. 输出类内容优先写入 output/ 或项目内指定输出目录。
5. 不允许删除历史数据文件；如需清理，只能先生成清理建议。
6. 不要跨项目混用上下文：处理 ai-quiz 时只读取 ai-quiz-codex-package；处理 lunch 时只读取 weekend-lunch-plan-codex。
7. 所有结论必须基于当前工作区文件，不要凭空假设已有文件内容。
8. 对话内输出大段内容时必须做轻量排版，尤其是飞书 bot 场景：按主题分块、块之间留空行、优先使用短编号列表，每块控制在 3-7 条短句，避免长段落和大表格；内容过长时分多条消息发送。

## Skill Directory Standard

1. 自定义项目 Skill 的唯一主源目录是：
   `/opt/personal-agent-workspace/skills/<skill-name>/`
2. `skills/<skill-name>/` 内维护完整 Skill 内容，包括 `SKILL.md`、`scripts/`、`templates/`、`references/` 等。
3. 项目内 `.agents/skills/<skill-name>` 只能是指向主源目录的 symlink，不能维护第二份 Skill 内容。
4. Claude Code 的 `~/.claude/skills/<skill-name>` 只能是指向主源目录的 symlink，或由 `sync-skills.sh` 从主源同步出的副本。
5. 目录名应与 `SKILL.md` frontmatter 的 `name` 保持一致；历史短名只能作为 symlink alias。
6. 修改 Skill 时只改 `skills/<skill-name>/` 主源；禁止直接修改项目内 `.agents/skills/` 或 `~/.claude/skills/` 的副本。
7. 详细规范维护在 `docs/SKILLS_UNIFIED.md`，同步/校验脚本为 `sync-skills.sh`。
8. 新增 Skill 的具体步骤见 `docs/SKILLS_UNIFIED.md` 的“新增 Skill 流程”。

## Shared Skills

### AI刷题
Skill主源：
/opt/personal-agent-workspace/skills/ai-quiz

项目目录：
/opt/personal-agent-workspace/ai-quiz-codex-package

涉及题库、学习进度、错题、学习日志写入时，必须使用锁：
/opt/personal-agent-workspace/.locks/ai-quiz.lock

### 周末午餐推荐
Skill主源：
/opt/personal-agent-workspace/skills/weekend-lunch-plan

兼容别名：
/opt/personal-agent-workspace/skills/weekend-lunch -> weekend-lunch-plan

项目目录：
/opt/personal-agent-workspace/weekend-lunch-plan-codex

涉及库存、偏好、历史菜单、复盘记录写入时，必须使用锁：
/opt/personal-agent-workspace/.locks/weekend-lunch.lock

### 金坛项目周报
Skill主源：
/opt/personal-agent-workspace/skills/jintan-weekly-report-sop

项目目录：
/opt/personal-agent-workspace/jintan-weekly-report-sop

涉及周报生成、校验、版式检查或修复时，优先进入项目目录操作；输出类内容写入项目 `output/` 目录。

### 简历 JD 匹配度评估
Skill主源：
/opt/personal-agent-workspace/skills/resume-jd-scorer

项目目录：
/opt/personal-agent-workspace/resume-jd-scorer

涉及简历评估、JD 匹配度分析、上传 JD/简历文件时使用。

### 每日 AI 资讯摘要（待建 Skill）
项目目录：
/opt/personal-agent-workspace/daily-ai-digest

该 Skill 尚未创建，目前只在项目目录内维护代码与配置。

## Git 凭证配置

工作区项目如需推送到 GitHub，使用全局 Git 凭证文件：

- 凭证文件：`~/.git-credentials`
- 格式：`https://<token>:x-oauth-basic@github.com`
- 权限：`chmod 600 ~/.git-credentials`
- 启用凭证助手：`git config --global credential.helper store`

配置完成后，所有项目的 `git push origin <branch>` / `git pull` 都会自动读取 token，无需每次输入。

**注意**：
- token 文件不要提交到仓库，也不要写入 `CLAUDE.md` 等共享文档正文。
- token 泄露后应立即到 GitHub Settings → Developer settings → Personal access tokens 中轮换。

### Multi-session Rules
飞书多个会话可以并行读取同一工作区，但写共享数据前必须：
1. 说明写入文件；
2. 说明写入原因；
3. 等待用户确认；
4. 使用 flock 锁；
5. 写入后提示 git status 摘要。
