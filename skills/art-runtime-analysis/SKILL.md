---
name: art-runtime-analysis
description: Analyze APK/DEX/OAT/VDEX/AppImage preparation, compiler artifacts, class initialization, JIT, linker, JNI, and native first-use work. Use for cold/prestarted launches or class/runtime-heavy app initialization.
---

# ART and Runtime Analysis

## Purpose

Separate artifact mapping/validation and runtime initialization from app lifecycle, resource I/O, and native rendering work.

## Trigger

Routed. Run when P3/P4/P5 ART/runtime candidate groups are activated.

## Required input

- Launch context and P3/P4 candidate intervals.
- ART/dex2oat/class/linker/native slices and file/page evidence.
- Optional package compiler-filter and artifact metadata.

## Workflow

1. Measure `OpenDexFilesFromOat`, AppImage/OAT/VDEX mapping, and artifact status/validation.
2. Measure dex/class verification, first-use class initialization, and JIT work.
3. Measure linker/dlopen/JNI/native initialization where observable.
4. Separate CPU execution from file/page waits and route I/O origin to block-I/O analysis.
5. Compare artifact status, compiler evidence, and paired DUT/REF deltas.

## Algorithm contract

Artifact duration is not automatically a compiler-filter problem. Status, file residency, version, and verification evidence determine the mechanism.

## Main outputs

- `open_dex_oat_ms`
- `artifact_status_ms`
- `class_init_ms`
- `native_init_ms`
- ART artifact and runtime findings

## Leaf and workflow integration

Feeds p3.bindapplication_or_activitystart.apk_dex_oat_and_vdex_preparation/p3.bindapplication_or_activitystart.native_library_and_linker_initialization/p4.activitystart_or_activityresume.app_side_class_code_and_native_first_use leaves. File-backed faults are linked to p5.activityresume_or_first_choreographer_doframe.reusable_file_or_page_or_storage_mechanism/P8 memory or storage origins.

## Guardrails

- Do not recommend compiler-filter changes when both artifacts are up-to-date without supporting evidence.
- Do not count AppImage/OAT parent and nested file waits additively.
- Class loading, class initialization, verification, and JIT are distinct mechanisms.
- App-owned first-use native work belongs to p4.activitystart_or_activityresume.app_side_class_code_and_native_first_use, not process bootstrap p3.bindapplication_or_activitystart.native_library_and_linker_initialization.

## Failure handling

- Keep artifact timing observable while marking compiler/root origin unresolved.
- Request package/artifact metadata when version/filter identity is unknown.

## Known limitation

Compiler filter/profile state may require `dumpsys package`, oatdump, or package snapshots not included in the trace.

## Implementation

- Manifest: `skills/art-runtime-analysis/skill.yaml`
- Deterministic implementation: `skills/art-runtime-analysis/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.
