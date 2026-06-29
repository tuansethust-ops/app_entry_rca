---
name: app_entry_rca
description: Evidence-driven DUT-vs-REF Android app-entry root-cause analysis using the P1-P8 FTA taxonomy, routed diagnostic skills, and a deterministic Python workflow. Use when the user provides DUT and REF Perfetto/atrace traces and wants to identify why app launch is slower or different on DUT.
---

# App Entry RCA Workflow

Phân tích root cause cho Android app-entry latency bằng cách so sánh DUT với REF, sử dụng Perfetto/atrace traces, FTA taxonomy P1-P8 và các diagnostic skill được workflow router lựa chọn.

Đây là **top-level workflow**. Không chạy thủ công toàn bộ skill con. Hãy chạy deterministic Python orchestrator để workflow tự chọn skill theo candidate leaf và trace observability.

## When to use

Chạy workflow này khi user:

- cung cấp hai trace DUT và REF;
- muốn biết app launch chậm ở phase P1-P8 nào;
- muốn lấy toàn bộ leaf status và final actionable leaf;
- muốn deep-dive GC, kswapd, reclaim, Binder, block I/O, ART, RenderThread, GPU hoặc `activityIdle` tail.

## Inputs

### Required

- **DUT trace path** — trace của device cần điều tra.
- **REF trace path** — trace của device tham chiếu.

### Optional

- **Target package** — nên cung cấp khi trace có nhiều launch; nếu thiếu, workflow tự phát hiện.
- **Launch index** — zero-based launch candidate index, mặc định `0`.
- **Output directory** — mặc định `app_entry_rca_out`.
- **trace_processor_shell path** — backend ưu tiên cho Perfetto protobuf.
- **traceconv path** — fallback lossy khi không dùng được trace processor.
- **Strict validation** — dừng khi DUT/REF không đủ điều kiện so sánh.

Nếu hai trace chưa được gắn nhãn DUT/REF rõ ràng, không được tự đoán.

## Step 1: Resolve repository root and inputs

Chạy từ thư mục chứa:

```text
pyproject.toml
app_entry_rca/
taxonomy/
workflows/
skills/
```

Không hard-code tên version folder như `app_entry_rca_v8_ms_diff` hoặc `app_entry_rca_v9_p7_idle`.

Mọi path có dấu cách phải được đặt trong dấu nháy kép.

## Step 2: Check the environment

Chạy doctor trước khi phân tích:

```bash
python scripts/doctor.py --dut "<DUT_TRACE_PATH>" --ref "<REF_TRACE_PATH>"
```

Trên Windows có thể dùng:

```powershell
.\windows\doctor.ps1 -Dut "<DUT_TRACE_PATH>" -Ref "<REF_TRACE_PATH>"
```

Nếu thiếu dependency:

```bash
python -m pip install -r requirements.txt
```

Trên Windows có thể chạy:

```bat
install_windows.bat
```

Dừng workflow nếu:

- file DUT hoặc REF không tồn tại;
- taxonomy/workflow asset bị thiếu;
- trace không thể parse bằng bất kỳ backend nào;
- strict validation được bật và pair không comparable.

## Step 3: Run the deterministic workflow

### Standard command

```bash
python -m app_entry_rca.cli \
  --dut "<DUT_TRACE_PATH>" \
  --ref "<REF_TRACE_PATH>" \
  --out "<OUTPUT_DIR>" \
  --include-better-final
```

### With target package

```bash
python -m app_entry_rca.cli \
  --dut "<DUT_TRACE_PATH>" \
  --ref "<REF_TRACE_PATH>" \
  --out "<OUTPUT_DIR>" \
  --target "<PACKAGE_NAME>" \
  --include-better-final
```

### Preferred Perfetto SQL backend

```bash
python -m app_entry_rca.cli \
  --dut "<DUT_TRACE_PATH>" \
  --ref "<REF_TRACE_PATH>" \
  --out "<OUTPUT_DIR>" \
  --target "<PACKAGE_NAME>" \
  --trace-processor "<TRACE_PROCESSOR_SHELL_PATH>" \
  --backend perfetto \
  --include-better-final
```

### Lossy fallback with traceconv

```bash
python -m app_entry_rca.cli \
  --dut "<DUT_TRACE_PATH>" \
  --ref "<REF_TRACE_PATH>" \
  --out "<OUTPUT_DIR>" \
  --traceconv "<TRACECONV_PATH>" \
  --backend systrace \
  --include-better-final
```

### Windows helper

```powershell
.\windows\run.ps1 `
  -Dut "<DUT_TRACE_PATH>" `
  -Ref "<REF_TRACE_PATH>" `
  -Out "<OUTPUT_DIR>" `
  -Target "<PACKAGE_NAME>" `
  -IncludeBetterFinal
```

Các option khác khi cần:

```text
--launch-index <N>
--strict-validation
--include-correlation-candidates
--workflow <WORKFLOW_YAML_PATH>
```

Không thay workflow bằng ad-hoc SQL hoặc ước lượng thủ công, trừ khi workflow lỗi. Nếu fallback thủ công là bắt buộc, phải báo rõ workflow step nào thất bại và evidence nào bị mất.

## Step 4: Verify generated artifacts

Xác nhận output directory có các file sau:

```text
analysis_summary.json
validation.json
launch_context.json
phase_comparison.json
routing.json
observability.json
skill_runs.json
skill_findings.json
raw_metrics.json
ms_diff_summary.json
all_leaf_nodes.json
all_leaf_nodes.csv
final_leaves.json
final_leaf.json
evidence_graph.json
automation_coverage.json
taxonomy_changes.json
report.md
```

Nếu `final_leaf.json` rỗng, phải kiểm tra theo thứ tự:

1. `validation.json`
2. `observability.json`
3. `routing.json`
4. `skill_runs.json`
5. `all_leaf_nodes.json`

Không được kết luận “DUT không có vấn đề” chỉ vì không tạo được final leaf.

## Step 5: Read results in the correct order

Đọc theo thứ tự:

1. `validation.json`
2. `launch_context.json`
3. `analysis_summary.json`
4. `phase_comparison.json`
5. `ms_diff_summary.json`
6. `final_leaf.json`
7. `final_leaves.json`
8. `evidence_graph.json`
9. `report.md`

## Step 6: Present the summary to the user

Luôn trình bày:

1. **Validation**
   - `COMPARABLE`, `PARTIALLY_COMPARABLE` hoặc `NOT_COMPARABLE`;
   - comparability score;
   - actual launch type: cold, prestarted-cold, warm hoặc hot;
   - missing capability hoặc marker mismatch.

2. **Primary endpoints**
   - input → first presented-frame metric nếu FrameTimeline có sẵn;
   - nếu không, input → `finishDrawing`/DrawFrames proxy;
   - input → system_server `activityIdle::server` end.

3. **P7 semantics**
   - P7 bắt đầu tại first-frame completion;
   - P7 kết thúc tại **end của `IActivityClientController::activityIdle::server` trong system_server**;
   - báo riêng:
     - first-frame → activityIdle server start;
     - `activityIdle::server` handler duration;
     - monitor contention/state decomposition trong server handler.

4. **Phase comparison**
   - phase/candidate group nào DUT regression;
   - phase/candidate group nào DUT better;
   - P2/P3 overlap và P4/P5 nesting phải được ghi rõ.

5. **Top DUT_REGRESSION leaves**
   - score, confidence, causality;
   - `local_delta_ms`;
   - `exclusive_contribution_ms` khi có;
   - `nested_deltas_ms`;
   - `overlap_group` và `additive`.

6. **Primary final actionable leaf**
   - Symptom;
   - Location;
   - Mechanism;
   - Origin;
   - Ownership;
   - Action;
   - Verification plan.

7. **DUT-better leaves**
   - đặc biệt khi chúng bù cho local regression và làm endpoint tổng tốt hơn.

8. **Observability limitations**
   - các leaf `NOT_OBSERVABLE` quan trọng;
   - instrumentation cần bổ sung.

## Step 7: Candidate deep-dive

Khi user muốn phân tích sâu một leaf hoặc phase:

- đọc `final_leaves.json` để lấy full final-leaf fields;
- đọc `all_leaf_nodes.json` để xem trạng thái toàn taxonomy;
- đọc `skill_findings.json` để xem raw evidence;
- đọc `evidence_graph.json` để theo dependency/interference edges;
- đọc `raw_metrics.json` để kiểm tra DUT/REF values;
- đọc `phase_comparison.json` để kiểm tra phase window và overlap.

Tiếp tục kiểm tra candidate theo flow:

```text
candidate leaf
→ applicability
→ observability
→ DUT/REF delta
→ critical object
→ Running/Runnable/Waiting/D-state/GC/Render decomposition
→ candidate-specific analyzer
→ dependency traversal
→ origin attribution
→ reject alternatives
→ critical-path contribution
→ final actionable leaf
```

## Important interpretation rules

1. **Never sum overlapping deltas.** Parent, child và cross-phase contributor có thể overlap.
2. **`NOT_OBSERVABLE` does not mean equal.** Thiếu evidence là unknown.
3. **GC overlap alone is correlation-only.** Cần direct block hoặc exact resource competition.
4. **kswapd activity alone is correlation-only.** Cần exact overlap/interference edge hoặc reclaim consequence.
5. **D-state alone is not storage root cause.** Cần blocked reason, file/page hoặc request attribution.
6. **CPU total alone is not contention.** Cần critical Runnable interval và blocker overlap.
7. **P2 can overlap P3.** Không cộng như sequential phases.
8. **P5 is a nested work domain.** Có thể share wall time với P4.
9. **P8 is cross-cutting.** Không cộng như phase thứ tám.
10. **`finishDrawing` is a proxy.** Ưu tiên FrameTimeline/SurfaceFlinger present data khi có.
11. **P7 ends at system_server activityIdle handler end.** Không dùng marker idle mơ hồ nếu server slice có sẵn.
12. **Umbrella duration is not automatically RCA.** Cần sub-mechanism evidence.
13. **Correlation-only leaves must not become primary RCA.** Chỉ `DIRECT` hoặc `CONTRIBUTING` mới được rank làm final candidate mặc định.
14. **A local DUT regression may coexist with a faster total DUT endpoint.** Báo cả hai.
15. **Do not modify generated evidence files.** Ghi nhận xét của Cline vào file riêng như `<OUTPUT_DIR>/cline_summary.md`.

## Failure handling

Nếu workflow thất bại:

1. báo command đã chạy;
2. báo step/skill thất bại;
3. trích lỗi ngắn gọn;
4. nêu file output nào đã sinh;
5. không tạo kết luận RCA vượt quá evidence hiện có;
6. đề xuất đúng một hành động khắc phục cụ thể.


## CPU Core/Frequency Skill

- `cpu-core-frequency-analysis` enriches P1-P7 node/leaf intervals with CPU core, migration, cluster, and CPU frequency evidence.
- Output artifact: `cpu_core_frequency.json`.
- Missing CPU-frequency counters are treated as `NOT_OBSERVABLE`, not equal.

## Positional Cline form

Cline may be called with two trace paths directly:

```text
/app_entry_rca <DUT_TRACE_PATH> <REF_TRACE_PATH>
```

When invoked this way, treat the first positional path as DUT and the second positional path as REF, then run:

```bash
python scripts/run_app_entry_rca.py "<DUT_TRACE_PATH>" "<REF_TRACE_PATH>" --backend perfetto --include-better-final
```

If the user adds a package name or output directory, convert them to named flags:

```bash
python scripts/run_app_entry_rca.py "<DUT_TRACE_PATH>" "<REF_TRACE_PATH>" \
  --target "<PACKAGE_NAME>" \
  --out "<OUTPUT_DIR>" \
  --backend perfetto \
  --include-better-final
```

Default Trace Processor path is project-local:

```text
tools/perfetto/trace_processor_shell
tools/perfetto/trace_processor_shell.exe
```

Only pass `--trace-processor` when the executable is outside `tools/perfetto/`.
