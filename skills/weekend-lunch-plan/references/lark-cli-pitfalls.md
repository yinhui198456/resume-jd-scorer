# lark-cli 飞书文档操作陷阱

> 已验证的 4 条陷阱，SOP 2.4 飞书文档归档时必须遵守。

---

## 陷阱1：docs +create 不可加 --parent-token

**现象**：`lark-cli docs +create --parent-token xxx` 报 `3380004` 错误
**原因**：Bot 无权限在指定父节点下创建文档
**正确做法**：不加 `--parent-token`，默认创建到 Bot 个人空间
```bash
lark-cli docs +create --api-version v2 --doc-format markdown --content "内容"
```

## 陷阱2：drive permission 的 type 位置

**现象**：`lark-cli drive permission.members create --type docx` 报错
**原因**：`type` 是 query parameter（用 `--params` 传入），不是 CLI 的 `--type` flag
**正确做法**：
```bash
lark-cli drive permission.members create \
  --params '{"type":"docx","token":"<doc_token>"}' \
  --data '{"member_type":"openid","member_id":"<open_id>","perm":"full_access","type":"user"}' \
  --yes
```

## 陷阱3：文档写入后正文为空

**现象**：`docs +create` 成功返回 doc_token，但 `docs +fetch` 回读正文为空
**原因**：content 参数中的特殊字符（如 `<title>` XML 标签）可能被转义或截断
**正确做法**：
1. 创建后立即 `docs +fetch --doc "<doc_token>" --format pretty` 回读验证
2. 验证条件：正文长度 > 50 字符，且包含"菜单"/"步骤"等关键标题
3. 验证失败 → 重试 stdin 方式重新写入

## 陷阱4：Markdown 内容中的特殊字符

**现象**：content 中含 `"`、`\`、换行符等导致 JSON 解析失败
**原因**：shell 中直接传 content 参数需要转义
**正确做法**：
- 使用 heredoc 或 stdin 方式传入内容
- 或将内容写入临时文件，用 `--file` 参数读取

---

## 完整工作流示例

```bash
# 1. 创建文档
doc_token=$(lark-cli docs +create --api-version v2 --doc-format markdown \
  --content "<title>2026-06-22 周末午餐</title>..." 2>&1 | grep -o 'docx:[a-zA-Z0-9]*')

# 2. 回读验证
lark-cli docs +fetch --doc "$doc_token" --format pretty

# 3. 授权给用户
lark-cli drive permission.members create \
  --params "{\"type\":\"docx\",\"token\":\"$doc_token\"}" \
  --data "{\"member_type\":\"openid\",\"member_id\":\"$open_id\",\"perm\":\"full_access\",\"type\":\"user\"}" \
  --yes
```
