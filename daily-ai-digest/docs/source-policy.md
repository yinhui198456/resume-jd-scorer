# Source Policy

The active whitelist is declared in `configs/sources.yml`. Tier 1 contains OpenAI News, the Codex changelog, Anthropic News, and three official GitHub release feeds. Tier 2 contains GitHub AI repository search sources, Codex/Claude Code skill repository searches, plus curated AI practice and methodology feeds. `36kr.com` is allowed as Tier 3 but is not actively collected. CSDN domains are blocked.

Tier 2 is intentionally signal-oriented rather than authority-oriented. It can surface hot AI projects, production practice, productivity workflows, and experienced-practitioner methodology, but those items still pass the same hard filters, weighted scoring, clustering, and digest quotas before delivery.

Current Tier 2 groups:

- GitHub hot AI projects from the official repository search API.
- Codex and Claude Code skill repositories from topic-constrained GitHub repository searches.
- AI practice and productivity feeds from curated practitioners.
- Methodology and experience-sharing feeds from curated AI practitioners.

Delivery uses explicit section quotas so Tier 2 signals are visible instead of being crowded out by Tier 1 official sources. The default compact digest contains 15 items: 6 top stories and 9 productivity projects.
