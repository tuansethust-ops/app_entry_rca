# Cline Compliance Fix

This package fixes the Cline compliance issues reported for `app-entry-rca`.

## Fixed

1. Added canonical `skills/app-entry-rca/` copy.
2. Synchronized `.cline/skills/app-entry-rca/SKILL.md` and `skills/app-entry-rca/SKILL.md`.
3. Added required sections to `app-entry-rca` SKILL.md:
   - Algorithm contract
   - Leaf and workflow integration
   - Known limitation
4. Added `skills/app-entry-rca/skill.yaml` and `skills/app-entry-rca/skill.py` so the canonical skills tree remains test-compatible.
5. Updated `workflows/app_entry_rca/WORKFLOW.md` to explicitly mention `error_policy.fail_fast: true`.

## Verification

```bash
python -m compileall app_entry_rca skills workflows scripts -q
pytest -q
```

Result: `26 passed, 1 skipped`.
