# Compact Feishu Post Design

## Goal

Deliver one concise, readable daily AI digest through the existing
`Codex-学习助理` Feishu application in the current group. The visible message
contains 8 top stories and 3 candidate stories, with each top-story summary no
longer than 100 Unicode characters and written as a complete explanation.

## Scope

This change affects selection, display-oriented text generation, rendering, and
Feishu delivery. It does not add a Bot, change credentials, delete historical
runs, or enable the systemd timer.

## Message Layout

The system sends one Feishu rich-text Post message.

1. Title: `每日 AI 资讯｜M月D日`
2. Status line: source health plus `8 条重点 · 3 条候选`, using actual counts
   when fewer items are available.
3. Top stories: numbered 1 through 8. Each entry contains:
   - bold Chinese title;
   - one complete summary of at most 100 Unicode characters, including any ellipsis;
   - one `查看原文` link to the representative primary source.
4. Candidate stories: up to 3 one-line entries containing title and one link.

The visible Post omits run IDs, empty sections, `why_it_matters`, raw URLs, and
secondary cluster links. The persisted Markdown digest and run checkpoints keep
the full operational metadata needed for diagnosis.

## Selection and Clustering

`configs/filters.yml` sets `top_stories: 8` and `candidates: 3`.

The existing topic-overlap clustering is too broad: one shared tag can combine
unrelated releases, research, and company news. The replacement is conservative:
items are grouped only when their normalized titles are equal after case folding
and whitespace normalization. Otherwise each item remains independent. The
highest-scoring item is the representative, and only its canonical URL is shown.

Ordering remains deterministic: score descending, then stable item ID. Items at
or above the digest threshold fill the top section first. Remaining eligible
items fill the candidate section up to its quota.

## Summary Length Control

The MiniMax system prompt asks for a complete Chinese summary within 100 characters. The
renderer applies a deterministic final guard: normalize whitespace, preserve
text of length 100 or less, and truncate longer text to 99 characters plus `…`.
This protects the Feishu layout when model output violates the prompt.

## Delivery Architecture

The delivery adapter adds `send_post(payload, delivery_key)` and continues to
use the existing tenant-token flow and `im/v1/messages` endpoint. The request
uses `msg_type: post`; `content` contains the Feishu `zh_cn` Post structure with
`text` and `a` elements. No CardKit APIs, callbacks, or new permissions are
introduced.

`run_daily()` persists the Markdown digest before delivery, builds the compact
Post from selected `DigestItem` records and source health, then sends it using
the existing idempotency delivery key. A delivery failure leaves the digest and
attempt state available for retry. Normal digests use `send_post`; total-source
fault digests continue to use the existing `send_text` path.

## Error Handling

- Fewer than 8 top stories or 3 candidates: show actual counts without empty
  placeholder sections.
- Missing canonical URL: render the title and summary without a link.
- MiniMax returns a long summary: truncate deterministically to 100 characters.
- Feishu rejects the Post: preserve the rendered digest and failed delivery
  state; do not silently fall back to the former verbose message.
- Total source failure: retain the existing fault-digest behavior.

## Verification

Automated tests must prove:

- selection is limited to 8 top stories and 3 candidates;
- unrelated items sharing a topic tag are not clustered;
- each visible top story has at most one link;
- summaries are complete explanations of at most 100 characters;
- empty sections and `why_it_matters` do not appear in the Post payload;
- Feishu delivery uses `msg_type: post` and the existing target chat;
- historical plain-text fault delivery remains operational;
- the complete test suite and configuration validation pass.

After automated verification, one explicit user-approved Feishu smoke message
will validate rendering in the current group before any timer is enabled.
