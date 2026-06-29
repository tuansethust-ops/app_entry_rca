# Adding a Skill

1. Create `skills/<name>/skill.yaml`, `SKILL.md` and `skill.py`.
2. Declare `stage`, `requires`, `trigger`, interface and produced metrics in `skill.yaml`.
3. Implement `run(state, config)`.
4. Check observability before measuring.
5. Write paired raw metrics under both `state.metrics["DUT"]` and `state.metrics["REF"]`.
6. Emit `SkillFinding` records for meaningful observations and limitations.
7. Add candidate-group routing to `candidate_analyzer_mapping.yaml`.
8. Add leaf rules only when a reliable metric/evidence contract exists.
9. Add contract, missing-evidence and integration tests.

A skill measures evidence. It does not directly declare a root cause.
