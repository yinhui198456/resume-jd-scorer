# Feishu Bot 消息方案设计

**日期：** 2026-06-30  
**目标：** 让飞书 App 中的 Bot 回复既易阅读又可操作，同时解决权限确认卡死问题。  
**约束：** 尽量只改配置、不改源码；Claude Code 与 Codex 两套 Bot 使用同一方案。

---

## 背景

当前两套 `claude-to-im` 桥接的配置均为：

```env
CTI_FEISHU_MESSAGE_STYLE=text
```

这导致：

1. **排版差**：Markdown 标记（如 `**加粗**`、`- 列表`）以纯文本形式发出，在飞书 App 中可读性差。
2. **权限卡死**：权限确认依赖交互卡片，但 `text` 模式下卡片交互链路异常，工具权限请求发出后没有 `approved/rejected/timeout` 响应，CLI 子进程一直阻塞。
3. **响应慢/无响应**：一旦某条消息触发权限请求，后续消息全部排队等待。

## 决策

经用户确认：

- **易阅读优先**于一键复制。
- 权限请求采用**全自动批准**。
- 尽量**只改配置**，两套 Bot **统一方案**。

## 方案

### 配置变更

对以下两个文件做相同修改：

- `/root/.claude-to-im/config.env`（Codex runtime）
- `/root/cti-claude-home/.claude-to-im/config.env`（Claude Code runtime）

**1. 移除 text 模式，恢复默认富文本行为**

```env
# CTI_FEISHU_MESSAGE_STYLE=text
```

移除后，桥接按内容自动选择消息类型：

- 简单 Markdown → `msg_type: post`（支持加粗、列表、行内代码、链接）
- 复杂 Markdown（代码块、表格）→ `msg_type: interactive` 卡片

**2. 开启全自动批准**

```env
CTI_AUTO_APPROVE=true
```

开启后，所有 `Read` / `Edit` / `Bash` / `Skill` 等工具权限请求直接通过，不再等待用户点击确认卡片。

### 数据流

```
用户消息 → 飞书 → 桥接 → claude/codex CLI
                          ↓
                    工具权限请求
                          ↓
              permission-broker（CTI_AUTO_APPROVE=true）
                          ↓
                     直接 approved
                          ↓
                    工具执行 → 结果返回 CLI
                          ↓
              桥接按内容选择 post / interactive 卡片
                          ↓
                         飞书
```

### 错误处理

- 若 `interactive` 卡片发送失败（如 `cardid is invalid`、rate limit），桥接现有逻辑会自动回退到 `post`；`post` 失败再回退到 `text`。
- 因权限确认链路被绕过，不存在权限等待超时问题。

## 验证计划

修改配置并重启两套桥接后执行：

1. 给 **Codex Bot** 发一条纯文本消息，确认收到排版正常的回复。
2. 给 **Claude Code Bot** 发一条纯文本消息，确认收到回复。
3. 给任一 Bot 发一条需要读文件/写文件的消息，确认不再因权限卡死。
4. 检查两个桥接日志，确认无新增 `cardid is invalid` 或权限等待相关错误。

## 风险

- 卡片在飞书 App 中的复制体验不如纯文本；如需完整原文，可后续在卡片底部增加“复制 Markdown 原文”按钮，但这需要改源码。
- `CTI_AUTO_APPROVE=true` 会降低安全边界，只应在可信的个人环境中使用。

## 后续可选项

若后续希望同时保留“易阅读”和“一键复制原文”，可考虑：

- 方案 A：改源码，在 `interactive` 卡片底部添加“复制原文”按钮。
- 方案 B：改源码，新增 `CTI_FEISHU_MESSAGE_STYLE=post` 强制所有普通回复走 `post`（比卡片更易复制，比 text 更好看）。

这些改动超出本次“只改配置”的范围，留待后续评估。
