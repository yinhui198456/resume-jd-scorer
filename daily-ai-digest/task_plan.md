# Fix digest quota and degraded collection

## Goal
Ensure the daily digest respects configured output quotas and records actionable source failures without deleting prior run data.

## Current Phase
Complete

## Phases

### Phase 1: Diagnose
- [x] Reproduce each source failure independently
- [x] Trace quota configuration through selection and rendering
- [x] Record root causes
- **Status:** complete

### Phase 2: TDD implementation
- [x] Add failing tests for quota selection
- [x] Add failing tests for persisted collection failures
- [x] Implement minimal fixes
- **Status:** complete

### Phase 3: Verification
- [x] Run focused and full test suites
- [x] Run configuration and static checks
- [x] Perform a non-delivering live collection verification
- **Status:** complete

### Phase 4: Handoff
- [x] Summarize changes, evidence, and remaining risks
- **Status:** complete

## Decisions Made

| Decision | Rationale |
|---|---|
| Preserve the successful 2026-06-23 run | Historical data must not be deleted or overwritten |
| Do not send another digest during repair | Verification should not create duplicate external messages |
| Select at most 10 top stories and 10 candidates | This is the currently implemented section subset and matches configured quotas |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Web research connector HTTP 403 | 1 | Switched to direct probes of official endpoints |
| Planning progress patch context mismatch | 1 | Re-read files and applied narrower patch |
| Review command used project-relative paths from repository root | 1 | Re-ran review from the project directory |
