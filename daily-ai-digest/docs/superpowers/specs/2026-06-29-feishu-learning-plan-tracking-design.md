# Feishu Learning Plan Tracking Design

## Goal

Extend Daily AI Digest so that when the user explicitly expresses interest in a daily news item, topic, or project, the system can record it into the Feishu spreadsheet `学习计划追踪 2026`, sheet `主任务`, without writing duplicate rows or overwriting user-managed planning fields.

This design defines the MCP calling model and read/write rules only. It does not implement the MCP server or write to the spreadsheet.

## Confirmed document target

- Feishu spreadsheet title: `学习计划追踪 2026`
- Spreadsheet token: `R4LAsRmQKhfMXYtV7UacSeaGngg`
- Target sheet title: `主任务`
- Target sheet id: `349176`
- Observed grid: 20 columns, 225 rows
- Frozen rows: 1

The target is a regular Feishu spreadsheet (`/sheets/...`), not a Feishu Bitable document. The integration must use Feishu Sheets APIs through an MCP abstraction rather than Bitable APIs.

## Current `主任务` schema

The sheet currently uses columns A-I:

| Column | Field | Notes |
|---|---|---|
| A | `任务序号` | Existing format is `LNN`; current max observed value is `L35`. |
| B | `方向` | Existing values include `大模型`, `行业学习`, `综合能力`, `基础设施`, `Agentic Coding`. |
| C | `任务项` | Main learning task title. |
| D | `输出` | Expected learning artifact or deliverable. |
| E | `状态` | Existing values are mainly `待开始`, `进行中`, `已完成`. |
| F | `月份` | Existing format is `YYYY 年 M 月`. |
| G | `优先级` | Existing values are `高`, `中`, `低`. |
| H | `备注` | Free-form context, source references, progress notes. |
| I | `链接` | Source link or related document link. |

Columns J-T exist but are not part of the current task schema and must remain untouched by this feature.

## MCP calling model

Daily AI Digest must not call Feishu REST APIs directly from pipeline code. It should call a small Feishu Sheets MCP interface. The MCP server may internally use Feishu Sheets v3/v2 endpoints, but the digest pipeline only depends on MCP tools.

Required MCP tools:

### `feishu_sheets.get_sheets`

Input:

```json
{
  "spreadsheet_token": "R4LAsRmQKhfMXYtV7UacSeaGngg"
}
```

Output:

```json
{
  "sheets": [
    {
      "sheet_id": "349176",
      "title": "主任务",
      "row_count": 225,
      "column_count": 20,
      "frozen_row_count": 1
    }
  ]
}
```

Use this tool to resolve the target sheet id from title. The implementation must fail clearly if `主任务` is not present.

### `feishu_sheets.read_values`

Input:

```json
{
  "spreadsheet_token": "R4LAsRmQKhfMXYtV7UacSeaGngg",
  "sheet_id": "349176",
  "range": "A1:I225"
}
```

Output:

```json
{
  "values": [
    ["任务序号", "方向", "任务项", "输出", "状态", "月份", "优先级", "备注", "链接"]
  ]
}
```

Use this tool before every write to validate the header, find existing rows, compute the next task id, and detect duplicates.

### `feishu_sheets.append_values`

Input:

```json
{
  "spreadsheet_token": "R4LAsRmQKhfMXYtV7UacSeaGngg",
  "sheet_id": "349176",
  "range": "A:I",
  "values": [
    ["L36", "Agentic Coding", "Graphify 项目学习 - 代码知识图谱管理", "Graphify 学习笔记 + 在 daily-ai-digest 项目中的实践案例", "待开始", "2026 年 6 月", "中", "资讯关联：2026-06-29 每日 AI 资讯；将代码/文档转为知识图谱；GitHub 5,154⭐", "https://github.com/safishamsi/graphify"]
  ]
}
```

Use this tool only after duplicate checks pass. It must append A-I only.

### `feishu_sheets.update_values`

Input:

```json
{
  "spreadsheet_token": "R4LAsRmQKhfMXYtV7UacSeaGngg",
  "sheet_id": "349176",
  "range": "H36:I36",
  "values": [
    ["原备注；再次出现：2026-06-29 每日 AI 资讯", "https://github.com/safishamsi/graphify"]
  ]
}
```

Use this tool for existing rows only. Default updates are limited to `备注`, empty `链接`, and empty `月份`.

### `feishu_sheets.find_task`

This is a logical helper that can be implemented inside the MCP server or the digest client. It should search the values returned by `read_values`.

Input:

```json
{
  "values": [["任务序号", "方向", "任务项", "输出", "状态", "月份", "优先级", "备注", "链接"]],
  "task_name": "Graphify 项目学习",
  "source_url": "https://github.com/safishamsi/graphify"
}
```

Output:

```json
{
  "matched": false,
  "row_number": null,
  "reason": "no duplicate link or title"
}
```

Duplicate detection priority:

1. Same source URL in column I.
2. Highly similar task name in column C.
3. Same project/topic mentioned in column H.

## Trigger policy

The integration must not automatically record all digest items. It records only when the user clearly expresses interest.

Accepted trigger examples:

- `关注这个`
- `加入学习计划`
- `这个后续跟进`
- `记录到学习计划`
- `这个项目我想研究`
- A direct reference to a digest item title followed by a recording intent.

Non-triggers:

- General positive feedback such as `不错`, `有意思`, `可以`.
- Requests to resend or reformat the daily digest.
- Fully automatic daily runs.

## Daily recommendation suppression

The daily digest should use the same `主任务` read model as a recommendation
guardrail. Before final selection, compare GitHub/productivity project
candidates with existing learning-plan rows:

1. Normalize GitHub links in column I to the repository root
   (`https://github.com/<owner>/<repo>`), so release URLs and repository URLs
   match the same project.
2. Also compare candidate title/body with existing task names and notes for
   non-GitHub productivity items.
3. If the project/topic already exists, do not recommend it again by default.

Allowed exceptions:

- The current item is a recent feature, launch, release, or capability update
  for that project.
- GitHub stars have grown quickly since the last local star snapshot. The
  default threshold is at least +500 stars and +15%, configured by
  `learning_plan_suppression` in `configs/filters.yml`.

Operational behavior:

- The daily digest should fail open if the Feishu read is unavailable: continue
  delivery without suppression rather than blocking the daily post.
- Store GitHub star snapshots locally under `data/state/github_star_history.json`
  so later runs can detect sudden growth.
- This suppression affects recommendations only; it must not write to the
  Feishu sheet and must not change existing `主任务` rows.

## Row creation rules

### Task id

Compute the next task id from existing `任务序号` values matching `L\d+`.

Current observed max is `L35`, so the next appended task is `L36`.

Do not fill historical gaps such as `L03`, `L06`, `L07`, or `L08`; gaps may carry user-specific meaning.

### Field mapping

| Field | Rule |
|---|---|
| `任务序号` | `L{max+1}`. |
| `方向` | Derived from the digest item type; defaults to `大模型`. |
| `任务项` | Concise project/topic learning title. |
| `输出` | Expected learning artifact, usually `学习笔记 + 实践案例` or `调研报告 + 对比分析`. |
| `状态` | Defaults to `待开始`. |
| `月份` | Current Asia/Shanghai month, formatted as `YYYY 年 M 月`. |
| `优先级` | Defaults to `中`. |
| `备注` | Source date, digest context, summary, star count if available. |
| `链接` | Source URL. |

### Direction mapping

| Digest item type | `方向` |
|---|---|
| Claude Code, Codex, AI coding tools, agentic coding workflows | `Agentic Coding` |
| Agent frameworks, MCP, RAG, LLM tools, model infrastructure | `大模型` |
| Productivity methods, note-taking, writing, personal workflows | `综合能力` |
| Industry policy, industry cases, business domain analysis | `行业学习` |
| Server, proxy, deployment, local infrastructure | `基础设施` |

### Priority mapping

| User intent | `优先级` |
|---|---|
| `重点关注`, `马上看`, `优先研究` | `高` |
| `感兴趣`, `记录一下`, `后续看` | `中` |
| `先收藏`, `有空再看`, `备选` | `低` |

### Status mapping

New rows default to `待开始`.

Only set `进行中` or `已完成` when the user explicitly requests it. Do not write long progress text into `状态`; detailed progress belongs in `备注` or a child sheet.

## Duplicate handling

Before appending, read `A1:I225` and check duplicates.

If a duplicate exists:

- Do not create a new task id.
- Do not overwrite `状态`, `优先级`, `任务项`, or `输出`.
- If `链接` is empty and the current source URL is known, fill it.
- Append a short source note to `备注` if it is not already present:
  - `；再次出现：2026-06-29 每日 AI 资讯`

If no duplicate exists, append a new row.

## Child sheet policy

Do not create child sheets on first interest capture.

Suggest creating a child sheet only when one of these conditions is true:

- The user says `做专题跟踪`.
- The same topic appears at least three times.
- The user asks to break the topic into a learning plan.
- The item needs multiple sources, practice steps, or competitor comparison.

Child sheet names should follow existing style:

`任务 {编号}-{简短主题}`

Example:

`任务 36-Graphify 项目学习`

## Confirmation policy

The first implementation should ask for confirmation before writing.

Pre-write confirmation format:

```text
准备记录：L36｜Agentic Coding｜Graphify 项目学习｜优先级：中｜状态：待开始。确认写入？
```

Post-write confirmation format:

```text
已记录：L36｜Graphify 项目学习｜待开始｜中
```

For duplicate updates:

```text
已更新已有任务：L36｜Graphify 项目学习｜补充来源到备注
```

## Error handling

The MCP/client layer must return explicit errors for:

- Missing `主任务` sheet.
- Header mismatch: A-I are not exactly the expected fields.
- Missing read permission.
- Missing write permission.
- Invalid spreadsheet token.
- Task id conflict.
- Duplicate detection ambiguity.
- Feishu API non-zero response code.
- Network timeout.

The user-facing response must be concise and actionable, for example:

```text
未写入：飞书应用没有该表格写权限。需要给当前应用添加文档协作者权限或补充 Sheets 写权限。
```

## Security and configuration

- Do not store `app_secret`, tenant tokens, or document tokens in source code.
- Use the existing Feishu app credentials from environment/config where possible.
- Log request ids and error codes, not credentials.
- Do not print tenant access tokens.
- Keep spreadsheet token configurable even though the first target is fixed.

## Testing requirements

Unit tests should cover:

- Header validation.
- Next `LNN` id calculation.
- Gap preservation.
- Direction mapping.
- Priority mapping.
- Duplicate detection by link.
- Duplicate detection by title.
- Duplicate update payload generation.
- New row payload generation.
- Refusal to write on header mismatch.

Integration tests should use fake MCP responses and must not call real Feishu APIs by default.

A real Feishu smoke test requires explicit user confirmation and should perform one controlled append/update against a test row or test spreadsheet before touching `主任务`.

## Non-goals

- Automatically recording every daily digest item.
- Creating child sheets automatically on first interest.
- Reformatting the existing `主任务` sheet.
- Migrating historical rows.
- Replacing the current Feishu message delivery logic.
- Using Bitable APIs for this spreadsheet.
