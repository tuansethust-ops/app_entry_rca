# Architecture

## Design principle

The project separates four concerns:

1. **Workflow orchestration**: order, routing, error policy and execution record.
2. **Capability skills**: reusable measurement logic.
3. **Taxonomy**: P1-P8 groups, 151 candidate leaves and declarative evaluation rules.
4. **Evidence/ranking**: convert observations into case-specific final leaves without double counting.

## Data flow

```text
DUT trace + REF trace
        |
        v
Trace ingestion and capability detection
        |
        v
Coherent launch context and validation
        |
        v
P1-P8 localization + candidate-group activation
        |
        v
Running / Runnable / Wait / I/O / GC / ART / Render / P8 skills
        |
        v
Declarative leaf evaluation
        |
        v
Evidence graph + deduplication + ranking
        |
        v
JSON / CSV / Markdown artifacts
```

## Phase semantics

- **P1**: input delivery to launch request entering system_server.
- **P2**: framework orchestration represented by functional system_server segments. Output includes `functional_sum_ms` and overlap-safe `wall_union_ms`.
- **P3**: cold-only process bring-up. Ends at `bindApplication` delivery.
- **P4**: app callback/lifecycle context.
- **P5**: resource/data/content work domain nested inside callbacks.
- **P6**: traversal through first-frame submission/finishDrawing proxy.
- **P7**: post-first-frame tail ending at the end of
  `IActivityClientController::activityIdle::server` in system_server.
- **P8**: cross-cutting system interference; never a sequential phase.

## Routing

`phase-localizer` activates candidate groups for every observed phase because the output must include regression, better and equivalent leaves. `router.py` converts groups to capability skills using `candidate_analyzer_mapping.yaml` and adds evidence-driven skills such as ART for cold launches and Render for traces with frame markers.

Every selection reason is written to `routing.json` and `skill_runs.json`.

## Evidence levels

- **DIRECT**: critical path directly waits or executes the measured operation.
- **CONTRIBUTING**: exact overlap/resource contention supports contribution.
- **CORRELATION_ONLY**: timing overlaps but causal dependency is unproven.
- **REJECTED**: missing, equivalent, not applicable or superseded evidence.

## Final leaf model

Every case-specific final leaf contains:

1. Symptom
2. Location
3. Mechanism
4. Origin
5. Ownership
6. Action

`verification` is stored separately because it is mandatory to promote a high-confidence hypothesis to confirmed RCA.

## Known limitations

- Text systrace cannot expose all Perfetto SQL tables or transaction IDs.
- No thermal/app-version/compiler snapshot is available unless supplied externally.
- `finishDrawing` is not actual display present.
- Cpuset/uclamp policy needs dedicated task-profile/counter traces for direct proof.
