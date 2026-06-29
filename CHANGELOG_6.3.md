# Changelog 6.3.0 — Cline Skill Contracts

- Added valid YAML frontmatter to every canonical and Cline-discoverable `SKILL.md`.
- Ensured each `name` exactly matches its skill directory.
- Rewrote all 15 capability skills using a common contract: Purpose, Trigger, Required input, Workflow, Algorithm contract, Main outputs, Integration, Guardrails, Failure handling, Limitation, Implementation, and Tests.
- Expanded the master `app-entry-rca` skill using the same contract.
- Updated leaf counts to 271 and automatic rule count to 70.
- Added tests for frontmatter parsing, description quality, canonical/wrapper synchronization, and required sections.
- No metric or RCA algorithm was changed in this release.
