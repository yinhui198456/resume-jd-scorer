# Skill 目录统一维护规范

## 目标

`/opt/personal-agent-workspace` 是 Codex 和 Claude Code 共用的个人代理工作区。

所有自定义项目 Skill 必须在这个工作区内统一维护，避免 Codex、Claude Code、项目目录各维护一份不同版本。

## 目录规范

唯一主源目录：

```text
/opt/personal-agent-workspace/skills/<skill-name>/
```

主源目录中维护完整 Skill 内容：

```text
skills/<skill-name>/
├── SKILL.md
├── scripts/
├── templates/
├── references/
└── assets/
```

不是每个 Skill 都需要 `scripts/`、`templates/`、`references/`、`assets/`，但如果存在，必须放在主源目录内。

## 发现入口

### Codex / 项目入口

项目内入口只能是 symlink：

```text
<project>/.agents/skills/<skill-name> -> /opt/personal-agent-workspace/skills/<skill-name>
```

工作区根入口也只能是 symlink：

```text
/opt/personal-agent-workspace/.agents/skills/<skill-name> -> /opt/personal-agent-workspace/skills/<skill-name>
```

### Claude Code 入口

Claude Code 的入口只能是 symlink 或同步副本：

```text
~/.claude/skills/<skill-name> -> /opt/personal-agent-workspace/skills/<skill-name>
```

优先使用 symlink。只有在 symlink 不可用时，才使用 `sync-skills.sh` 复制同步。

## 命名规范

目录名必须与 `SKILL.md` frontmatter 的 `name` 一致。

示例：

```yaml
---
name: weekend-lunch-plan
description: ...
---
```

对应目录：

```text
skills/weekend-lunch-plan/
```

历史短名只能作为 alias symlink：

```text
skills/weekend-lunch -> weekend-lunch-plan
~/.claude/skills/weekend-lunch -> /opt/personal-agent-workspace/skills/weekend-lunch-plan
```

alias 不能保存独立 `SKILL.md`。

## 当前自定义项目 Skill

| Skill | 主源目录 | 项目目录 | 兼容别名 |
|---|---|---|---|
| `ai-quiz` | `skills/ai-quiz/` | `ai-quiz-codex-package/` | 无 |
| `weekend-lunch-plan` | `skills/weekend-lunch-plan/` | `weekend-lunch-plan-codex/` | `weekend-lunch` |

通用 marketplace / 系统 Skill 不强制迁移到工作区；本规范只约束绑定个人项目代码和数据的自定义 Skill。

## 修改流程

修改 Skill 时：

1. 只编辑主源目录：
   ```text
   /opt/personal-agent-workspace/skills/<skill-name>/
   ```
2. 不直接编辑：
   ```text
   <project>/.agents/skills/<skill-name>/
   ~/.claude/skills/<skill-name>/
   ```
3. 修改后运行：
   ```bash
   ./sync-skills.sh --check
   ```
4. 如 Claude Code 入口不是 symlink，运行：
   ```bash
   ./sync-skills.sh <skill-name>
   ```
5. 提交时同时提交：
   - `skills/<skill-name>/`
   - 必要的项目测试
   - 必要的规范文档变更

## 新增 Skill 流程

1. 创建主源目录：
   ```bash
   mkdir -p /opt/personal-agent-workspace/skills/<skill-name>
   ```

2. 创建 `SKILL.md`，其中 `name` 必须等于目录名。

3. 创建项目入口 symlink：
   ```bash
   ln -s ../../../skills/<skill-name> <project>/.agents/skills/<skill-name>
   ```

4. 创建工作区根入口 symlink：
   ```bash
   ln -s ../../skills/<skill-name> /opt/personal-agent-workspace/.agents/skills/<skill-name>
   ```

5. 创建 Claude Code 入口 symlink：
   ```bash
   ln -s /opt/personal-agent-workspace/skills/<skill-name> ~/.claude/skills/<skill-name>
   ```

6. 运行校验：
   ```bash
   ./sync-skills.sh --check
   ```

## 禁止项

- 禁止在多个目录维护不同版本的 `SKILL.md`。
- 禁止把项目内 `.agents/skills/<skill-name>` 当主源。
- 禁止把 `~/.claude/skills/<skill-name>` 当主源。
- 禁止 alias 目录保存独立内容。
- 禁止从 Claude Code 目录反向覆盖工作区主源。

## 校验命令

```bash
./sync-skills.sh --check
```

通过标准：

- `skills/<skill-name>/SKILL.md` 存在。
- `SKILL.md` frontmatter `name` 与目录名一致。
- 项目 `.agents/skills/<skill-name>` 指向主源。
- Claude Code `~/.claude/skills/<skill-name>` 指向主源，或内容与主源一致。
- alias 是 symlink，不是独立目录。
