## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/43

**Issue title:** Agent session state is not cleared between reviews for the same user


**Tier:** [x] Tier 1  [ ] Tier 2  [ ] Tier 3

**Problem summary:**
After a user initially calls a review for their portfolio and updates and calls the review again the orchestrator agent uses session state data from the first review instead of recalling the tools on the updated portfolio. 
Either the get or delete session function is broken and a successful fix would be tool calls being recalled after a portfolio change. This affects agent/memory/session_store.py.

**Branch name:** fix/43-agent-tools-session-clearing 

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger

**Is this right for me checklist:**

Part 1 — Understanding the Issue

[x] I can explain the problem and the expected behavior in 2–3 sentences without reading the issue.

Do I understand which part of the app is affected?

[x] I've located the relevant files and confirmed they exist in the codebase.

Do I understand what "done" looks like?

[x] I can describe a concrete before-and-after: what the user sees before the fix and what they see after.

Part 2 — Tier Fit

Is the tier a realistic match for where I am right now?

[x] If this is my first open source contribution: I'm choosing Tier 1.

[ ] If I've contributed to large codebases before: Tier 2 or 3 is fair game.

[ ] I'm not choosing a Tier 3 issue to "challenge myself" if I haven't completed a Tier 1 or 2 first — scope surprises in Week 9 don't have a safety net.

Part 3 — Codebase Readiness

Can I find the relevant code?

[x] I've found and read the specific code the issue references (not just the file — the function or section).

Do I understand the surrounding code well enough to change it safely?

[x] I've read enough surrounding context that I can write a rough plan for the fix without looking anything up.


Have I read the relevant test file?

[x] I've found the test file for my module and read at least one test end-to-end.

Part 4 — Scope and Time

How many others are already working on this issue?

[x] I've checked the issue comments and the ledger's Claims count, and I'm fine with how many others are on this issue.
Is the scope realistic for Weeks 8–9?

[x] I've estimated the time this will take and I'm confident I can complete it before the Week 9 deadline.


Are there any blockers or dependencies?

[x] This issue has no open blockers or dependencies on other unresolved issues.

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** [TODO: fill in after pushing — link to the commit adding tests/unit/test_orchestrator_session.py]

**Reproduction summary:**
Wrote a unit test (`tests/unit/test_orchestrator_session.py`) that drives `Orchestrator.run()` directly with a mocked Redis client: first review includes a resume (`skill_extractor` runs), second review removes the resume. `test_removed_tool_output_does_not_linger_in_session` fails, showing `skill_extractor`'s stale output from the first run is still present in the persisted session state after the resume was removed — confirming `session_state.update(results)` in `agent/orchestrator.py:66` merges but never prunes stale keys, and nothing in the codebase ever calls `session_store.delete()`.

**PLAN.md link:** [TODO: fill in after pushing — link to PLAN.md on this branch]

**Walkthrough video (recommended):** 

**Blockers or open questions:**
Unclear whether the original design intended `session_state` to accumulate across runs for some other purpose (e.g. partial/incremental reviews) — need to confirm a full-replace fix doesn't regress an intentional caching behavior before implementing in Week 9. Also, `Orchestrator`/`SessionStore` aren't wired into the live API yet (`core/services/review_service.py:282` is a stub), so there's no integration test to validate against once connected.