# Skill Catalog

| Skill | Stage | Main responsibility |
|---|---|---|
| trace-ingestion | ingestion | Decode trace container, parse ftrace/slices/scheduler and expose capabilities |
| launch-context | context | Detect target, PIDs, cold/warm evidence and coherent markers |
| trace-validation | validation | Validate pair, endpoints, marker matrix and data-source coverage |
| phase-localizer | localization | Build P1-P8 boundaries/segments and activate candidate groups |
| running-analysis | diagnostic | Critical-thread CPU Running time |
| runnable-analysis | diagnostic | Scheduling delay and RenderThread CPU occupants |
| wait-dependency-analysis | diagnostic | Monitor/Binder dependencies, Sleeping and D state |
| block-io-analysis | diagnostic | D-state, blocked reason, file-fault and block events |
| memory-gc-analysis | diagnostic | Direct GC block, exact competition, overlap-only and reclaim |
| art-runtime-analysis | diagnostic | OAT/VDEX/artifact/class/native/resource bootstrap |
| render-frame-analysis | diagnostic | Traversal, HWUI, Vulkan, upload, GPU wait and buffers |
| system-interference-analysis | diagnostic | P8 CPU ownership, IRQ, dexopt and background starts |
| leaf-evaluator | evaluation | Evaluate all 151 leaves from declarative rules |
| evidence-graph-ranking | ranking | Deduplicate, rank and create six-part final leaves |
| report-generator | reporting | Write and validate output artifacts |

See each `skills/<name>/SKILL.md` for trigger, algorithm, metrics and limitations.
