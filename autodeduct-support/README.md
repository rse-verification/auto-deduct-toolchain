# AutoDeduct Public Support Probes

This directory contains public-safe C/ACSL probes for the AutoDeduct helper-inference pipeline. It tests exact program patterns, not complete language features. It contains no industrial case-study source. Run the backend-aware Python runner inside an AutoDeduct environment, and read the results in [`MICRO_RESULTS.md`](../MICRO_RESULTS.md).

## Paper-model input

A strict support probe has this form:

1. `entry` has the only ACSL function contract.
2. `entry` calls one or more helpers without written function contracts.
3. Saida and TriCera infer the helper contracts.
4. ISP and Eva infer auxiliary annotations.
5. WP proves the generated program.

Canonical public runs use `--lib-entry`. A row is positive only when every evidence gate passes.

## Repository map

| File or directory | Purpose |
|---|---|
| [`cases.json`](cases.json) | Public manifest, source paths, evidence roles, profiles, and rewrite links |
| [`micro-tests/helper_inference/`](micro-tests/helper_inference/) | Direct strict helper-inference probes |
| [`micro-tests/helper_inference_rewrites/`](micro-tests/helper_inference_rewrites/) | Controlled rewrites and reductions |
| [`run_support_tests.py`](run_support_tests.py) | Runs parse, Saida, ISP, WP, and optional RTE-enabled WP |
| [`export_results_summary.py`](export_results_summary.py) | Produces deterministic sanitized JSON |
| [`tests/`](tests/) | Unit tests for command construction, classification, and export |
| [`../MICRO_RESULTS.md`](../MICRO_RESULTS.md) | Concise human-readable conclusions with source links |
| [`../autodeduct-support-results/`](../autodeduct-support-results/) | Frozen public functional and RTE evidence |

## Quick result map

| Tested pattern | Current conclusion | Evidence |
|---|---|---|
| Integer branch, simple struct, enum/switch, `assigns` + `\old` | Supported in the tested forms | [`MICRO_RESULTS.md`](../MICRO_RESULTS.md) |
| Two helper levels and repeated helper call contexts | Supported in the tested forms | [`MICRO_RESULTS.md`](../MICRO_RESULTS.md) |
| Local static state, float, pointer arithmetic, nested pointers | Functional-inference boundaries | [`academic-functional-v3.json`](../autodeduct-support-results/academic-functional-v3.json) |
| Array-of-struct return/rewrite patterns | Auxiliary-inference boundary | [`MICRO_RESULTS.md`](../MICRO_RESULTS.md) |
| Loop without invariant and several array reductions | Reach WP, but proof remains incomplete | [`MICRO_RESULTS.md`](../MICRO_RESULTS.md) |
| Stack pointer, logic function, behavior, predicate | Direct forms fail; selected rewrites pass | [`MICRO_RESULTS.md`](../MICRO_RESULTS.md) |

## Run one probe

```bash
python3 autodeduct-support/run_support_tests.py \
  --run-framac \
  --run-split \
  --lib-entry \
  --case helper_struct_basic \
  --timeout 600
```

Run the public functional baseline:

```bash
python3 autodeduct-support/run_support_tests.py \
  --run-framac \
  --run-split \
  --lib-entry \
  --baseline-group academic_functional_v3 \
  --timeout 1200
```

Run the separate RTE-enabled profile:

```bash
python3 autodeduct-support/run_support_tests.py \
  --run-framac \
  --run-split \
  --run-rte-wp \
  --lib-entry \
  --baseline-group academic_functional_v3 \
  --timeout 1200
```

## Interpret a result

- `supported_end_to_end`: all expected helper contracts were inferred, generated files parsed, ISP passed, and WP proved a nonzero complete goal set.
- `failed_at_func`: the first evidence boundary is Saida/TriCera or generated functional output.
- `failed_at_aux`: helper inference succeeded, but ISP did not produce a usable result.
- `failed_at_wp`: the pipeline reached WP, but goals remain unproved.

Do not generalize one probe to every program that uses the same C or ACSL feature.
