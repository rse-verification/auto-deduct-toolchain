# AutoDeduct C/ACSL Support Probes

- This directory contains public-safe C/ACSL support probes for AutoDeduct.
- It tests small C and ACSL patterns across parsing, inference, and proof phases.
- It does not contain industrial code or private source artifacts.
- Run it with `python3 autodeduct-support/run_micro_tests.py --run-framac --run-split`.
- Read the saved result notes in `MICRO_RESULTS.md`.

## Contents

| File or directory | Purpose |
|---|---|
| `cases.json` | Lists each probe, its source file, expected support class, and entry point. |
| `run_micro_tests.py` | Runs the public-safe probes and writes per-probe result files. |
| `micro-tests/supported/` | Contains probes expected to pass through the full split pipeline. |
| `micro-tests/expected_unsupported/` | Contains probes for known or suspected support boundaries. |
| `../MICRO_RESULTS.md` | Summarizes the currently saved public result observations. |

## Probe Groups

| Test group | Example tests | Expected meaning |
|---|---|---|
| `micro_supported` | `micro_int_if_helper`, `micro_struct_basic`, `micro_valid_pointer_struct`, `micro_enum_switch_basic` | These probes should pass parsing, Saida, ISP, and WP in the tested pipeline. |
| `micro_expected_unsupported` | `micro_float_arithmetic`, `micro_pointer_arithmetic`, `micro_nested_pointer`, `micro_loop_without_invariant` | These probes intentionally exercise support boundaries. A failure can be the expected result. |
| `micro_boundary` | `micro_array_struct_field_boundary` | These probes clarify a boundary by checking a smaller or simpler variant. |

## Current Public Results

| Result class | Probes | Current observation |
|---|---|---|
| `supported_end_to_end` probes | `micro_int_if_helper`, `micro_assigns_old`, `micro_global_array_basic`, `micro_struct_basic`, `micro_valid_pointer_struct`, `micro_enum_switch_basic`, `micro_behavior_basic`, `micro_array_struct_field_boundary` | These probes passed the saved public split-pipeline run. |
| Expected boundary probes | `micro_float_arithmetic`, `micro_pointer_arithmetic`, `micro_local_static_helper_persistence`, `micro_nested_pointer`, `micro_acsl_logic_function`, `micro_array_struct_read_helper_isp_crash`, `micro_loop_without_invariant` | These probes reached a known or suspected support boundary in the saved public results. |
| Unexpected pass probes | `micro_local_static` | This simple local-static probe passed, so it is not enough to claim a general local-static limitation. |

The exact output can vary with AutoDeduct, Frama-C, Saida, ISP, WP, TriCera, solver versions, and timeout settings.

## How To Run

Run all public probes inside an environment where `frama-c`, Saida, ISP, and WP are available:

```bash
python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --timeout 600
```

Run only probes expected to pass:

```bash
python3 autodeduct-support/run_micro_tests.py --kind micro_supported --run-framac --run-split --timeout 600
```

Run one probe:

```bash
python3 autodeduct-support/run_micro_tests.py --case micro_int_if_helper --run-framac --run-split --timeout 600
```

The runner uses the entry point `entry` for every probe.

The split pipeline is:

```bash
frama-c -quiet <test-file.c>
frama-c -saida -main entry -saida-out=tmp_inferred_source_merged.c <test-file.c>
frama-c -isp -isp-entry-point entry tmp_inferred_source_merged.c -isp-print-file out.c
frama-c -wp -main entry out.c
```

Runner output is written under:

```text
autodeduct-support-results/public-micro/
```

## How To Interpret Results

`supported_end_to_end` means the probe passed Frama-C parsing, Saida, ISP, and WP, with all reported WP goals proved.

`failed_at_func`, `failed_at_aux`, and `failed_at_wp` identify the first split-pipeline phase that did not complete successfully.

For an expected boundary probe, a failure in the intended phase is useful evidence. It records a small reproducible support boundary rather than a regression by itself.

For an unexpected pass, the tested pattern is smaller than the real boundary. Keep the probe, but refine the claim before using it as evidence.

These probes are feature checks, not complete proofs of support for every form of a C or ACSL feature.

## Future Work

- Keep adding small public-safe probes when a support boundary is found.
- Split broad probes into smaller variants so each one explains one feature.
- Re-run the suite when AutoDeduct, Frama-C, Saida, ISP, WP, or solver versions change.
- Keep public result summaries separate from private or source-specific reports.
