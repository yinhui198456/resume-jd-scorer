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

此前尝试过默认富文本模式，但发现 **interactive 卡片在飞书 App 移动端无法复制内容**（PC 端可以），而 **post 消息既可渲染加粗/列表，又可在移动端复制**。因此需要在桥接中新增对 `post` 消息模式的显式支持。

## 决策

经用户确认：

- **易阅读优先**，同时要求**移动端可复制**。
- 权限请求采用**全自动批准**。
- 两套 Bot **统一方案**。
- 接受小范围源码改动，但需记录补丁以便升级维护。

## 源码改动位置

实际 Feishu 适配器源码位于上游仓库：

- `/root/.codex/skills/Claude-to-IM/src/lib/bridge/adapters/feishu-adapter.ts`

Skill 包装仓库通过 `npm run build` 把上游代码打包进：

- `/root/.codex/skills/claude-to-im/dist/daemon.mjs`

两套运行时（Codex / Claude Code）的 skill 路径都是 `/root/.codex/skills/claude-to-im` 的 symlink，因此改一份源码、构建一次，两套同时生效。

### 具体改动

在 `feishu-adapter.ts` 的 `send()` 方法中，让 `CTI_FEISHU_MESSAGE_STYLE` 支持三个值：

| 值 | 行为 |
|---|---|
| `text` | 调用 `sendAsText()`，纯文本 |
| `post` | 调用 `sendAsPost()`，强制所有普通回复走 post |
| 未设置/其他 | 保持现有行为：`hasComplexMarkdown()` 为真时走卡片，否则走 post |

权限卡片逻辑不变；因配置 `CTI_AUTO_APPROVE=true`，权限请求不再走到 `sendPermissionCard()`。

## 配置变更

对以下两个文件做相同修改：

- `/root/.claude-to-im/config.env`（Codex runtime）
- `/root/cti-claude-home/.claude-to-im/config.env`（Claude Code runtime）

```env
# 注释掉或删除原 text 模式
# CTI_FEISHU_MESSAGE_STYLE=text

# 新增
CTI_FEISHU_MESSAGE_STYLE=post
CTI_AUTO_APPROVE=true
```

## 升级维护与覆盖风险

**问题**：以后升级 `claude-to-im` 上游版本时，本次源码改动会被覆盖吗？

**答案**：会。上游仓库 `/root/.codex/skills/Claude-to-IM` 如果拉取新版本，本地未合并的修改可能被覆盖。

**缓解措施**：

1. **最小化改动**：只增加一个 `post` 分支，改动行数尽量少。
2. **在 Claude-to-IM 仓库提交**：把改动 commit 到 `/root/.codex/skills/Claude-to-IM`，保留本地修改记录。
3. **保留 patch 文件**：在 `/opt/personal-agent-workspace/docs/superpowers/patches/` 保存本次 diff，升级后可快速重打。
4. **文档化**：在本设计文档中记录改动点，方便升级后对照。
5. **长期方案**：如果上游官方支持 `post` 模式，可废弃本地 patch。

## 数据流

```
用户消息 → 飞书 → 桥接 → claude/codex CLI
                          ↓
                    工具权限请求
                          ↓
              CTI_AUTO_APPROVE=true → 直接通过
                          ↓
                    工具执行 → 结果返回 CLI
                          ↓
              桥接强制用 msg_type: post 发回飞书
                          ↓
                         飞书
```

### 错误处理

- 若 `interactive` 卡片发送失败（如 `cardid is invalid`、rate limit），桥接现有逻辑会自动回退到 `post`；`post` 失败再回退到 `text`。
- 因权限确认链路被绕过，不存在权限等待超时问题。

## 验证计划

修改源码、构建、重启两套桥接后执行：

1. 在 `/root/.codex/skills/Claude-to-IM` 中修改 `feishu-adapter.ts`，增加 `post` 分支。
2. 在 `/root/.codex/skills/claude-to-im` 中执行 `npm run build`，确认 `dist/daemon.mjs` 更新成功。
3. 修改两个 `config.env`：
   - `/root/.claude-to-im/config.env`
   - `/root/cti-claude-home/.claude-to-im/config.env`
   设置 `CTI_FEISHU_MESSAGE_STYLE=post` 和 `CTI_AUTO_APPROVE=true`。
4. 重启两套桥接。
5. 给 **Codex Bot** 发一条含加粗/列表/行内代码的消息，确认是 post 格式、移动端可复制。
6. 给 **Claude Code Bot** 发同样内容，确认一致。
7. 给任一 Bot 发一条需要读文件/写文件的消息，确认不卡权限。
8. 检查两个桥接日志，确认无 `cardid is invalid`、无权限等待相关错误。
9. 把本次源码 diff 保存到 `/opt/personal-agent-workspace/docs/superpowers/patches/2026-06-30-feishu-post-mode.patch`。

## 风险

- **post 对复杂排版的限制**：代码块、表格在 post 中的渲染不如 interactive 卡片精美，但满足“可读 + 移动端可复制”的核心需求。
- **安全边界降低**：`CTI_AUTO_APPROVE=true` 会让所有工具权限自动通过，只应在可信的个人环境中使用。
- **升级覆盖风险**：源码改动在上游 `claude-to-im` 升级时可能被覆盖，需通过本地 commit + patch 文件缓解（见“升级维护与覆盖风险”）。

## 后续可选项

若后续希望进一步提升复杂内容的排版，同时保留复制能力，可考虑：

- **方案 A**：改源码，在 `interactive` 卡片底部添加“复制 Markdown 原文”按钮，用于代码块/表格场景。
- **方案 B**：对代码块/表格仍用 interactive 卡片，但对普通文字强制用 post，让用户根据内容类型自动切换。

这些改动超出本次范围，留待后续评估。
