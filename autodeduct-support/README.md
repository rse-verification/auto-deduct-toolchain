# AutoDeduct Public Support Probes

This directory contains public-safe C/ACSL probes for the AutoDeduct helper-inference pipeline. The probes test exact program patterns under a named tool version and command profile. They do not define universal support for a complete C or ACSL feature, and they contain no industrial case-study source.

Start with [`../MICRO_RESULTS.md`](../MICRO_RESULTS.md) for the source-linked result table.

## Paper-model input

A strict support probe has this form:

1. `entry` has the only written ACSL function contract.
2. `entry` calls one or more helpers without written function contracts.
3. Saida and TriCera infer the helper contracts.
4. ISP and Eva infer auxiliary annotations.
5. WP verifies the generated program.

Canonical public runs use `--lib-entry`.

A positive row requires all of the following:

- the functional backend is clean;
- every expected helper contract is inferred;
- no missing-contract marker remains;
- generated Saida output parses;
- ISP produces usable output;
- WP reports a nonzero goal set and proves every goal.

A process return code of zero is not sufficient evidence of support.

## Repository map

| File or directory | Purpose |
|---|---|
| [`cases.json`](cases.json) | Manifest, source paths, profiles, expected helpers, and direct/rewrite links |
| [`micro-tests/helper_inference/`](micro-tests/helper_inference/) | Direct strict helper-inference probes |
| [`micro-tests/helper_inference_rewrites/`](micro-tests/helper_inference_rewrites/) | Controlled input rewrites and reductions |
| [`run_support_tests.py`](run_support_tests.py) | Backend-aware parse, Saida, ISP, WP, and optional RTE runner |
| [`export_results_summary.py`](export_results_summary.py) | Deterministic sanitized evidence exporter |
| [`tests/`](tests/) | Unit tests for command construction, classification, and export |
| [`../MICRO_RESULTS.md`](../MICRO_RESULTS.md) | Human-readable conclusions with source links |
| [`../autodeduct-support-results/`](../autodeduct-support-results/) | Frozen functional and RTE-enabled machine evidence |

## Quick result map

| Tested pattern family | Current conclusion |
|---|---|
| Integer branch, simple struct, enum/switch, selected `assigns` and `\old` | Supported in the tested forms |
| Two helper levels, repeated helper call contexts, simple whole-struct return | Supported in the tested forms |
| Local static state, floating point, pointer arithmetic, nested pointers | Functional-inference boundaries in the tested forms |
| Selected array-of-struct helper patterns | Auxiliary-inference boundary |
| Loop without an inferred invariant and selected array/global-state reductions | Reach WP, but proof remains incomplete |
| Selected pointer and ACSL specification forms | Direct forms fail; some input-level rewrites pass |

## Input-level rewrites

The direct/rewrite pairs keep the AutoDeduct implementation unchanged and modify the input source or specification. They are diagnostic experiments and possible user workarounds. They are not completed improvements to AutoDeduct itself.

A tool-level improvement is established only when the original direct input passes unchanged after AutoDeduct is modified and rebuilt.

Some rewrites change several details at once. A passing rewrite therefore identifies a useful direction, but it does not always isolate one unique root cause or prove full semantic equivalence for every program context.

## Run the evaluation

Run one probe:

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

- `supported_end_to_end`: all positive evidence gates pass.
- `failed_at_func`: the first reliable boundary is Saida/TriCera or generated functional output.
- `failed_at_aux`: functional inference is usable, but ISP does not produce a usable result.
- `failed_at_wp`: the pipeline reaches WP, but one or more goals remain unproved.

Do not generalize one probe to every program that uses the same C or ACSL feature.
