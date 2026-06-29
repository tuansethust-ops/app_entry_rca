# Output Contract

## Leaf result

Every predefined leaf records:

- taxonomy identity: phase, group, leaf ID/name;
- status, causality and confidence;
- observability state;
- metric name/unit and paired DUT/REF values;
- threshold and interpretation;
- required and observed evidence;
- taxonomy action when evidence is missing.

## Final leaf

Every case-specific final leaf contains six mandatory diagnostic fields:

1. Symptom
2. Location
3. Mechanism
4. Origin
5. Ownership
6. Action

It also records:

- mapped taxonomy leaves;
- evidence and rejected alternatives;
- verification plan;
- transparent score breakdown;
- `local_delta_ms`: DUT−REF delta of the candidate window;
- `exclusive_contribution_ms`: paired mechanism-specific contribution when it can be estimated without using a parent duration;
- `nested_deltas_ms`: state or child-window deltas used as evidence;
- `overlap_group`: identifier used to prevent double counting;
- `additive`: currently false for candidate timings because parent/child and cross-phase metrics overlap;
- `delta_note`: interpretation guardrail.

The engine never sums local and nested candidate deltas to reproduce the end-to-end regression.

## Millisecond-difference summary

`ms_diff_summary.json` contains:

- the first-frame proxy DUT/REF values and delta;
- the main observed contributor windows;
- exclusive/attributed contribution estimates where available;
- nested state/sub-window deltas;
- overlap groups and non-additive flags.

Example:

```json
{
  "endpoint": {"delta_ms": 140.405, "semantics": "finishDrawing_start"},
  "contributors": [
    {
      "title": "First traversal / RecyclerView initial layout",
      "local_delta_ms": 74.241,
      "exclusive_contribution_ms": 51.557,
      "nested_deltas_ms": {"traversal_running_ms": 48.429},
      "overlap_group": "P6_FIRST_TRAVERSAL",
      "additive": false
    }
  ]
}
```

## Missing evidence

- Missing on both sides: `NOT_OBSERVABLE`.
- Missing on one side for a duration metric: normally `INSUFFICIENT_EVIDENCE`.
- Explicit event-presence rules may use `DUT_ONLY` or `REF_ONLY`.
- Missing evidence is never silently converted to zero or `EQUIVALENT`.
