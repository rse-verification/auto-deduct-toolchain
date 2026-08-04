# AutoDeduct Public Micro Probes

This directory contains public-safe synthetic C/ACSL probes for the AutoDeduct helper-inference pipeline.

## Paper-Model Input

The strict helper-inference profile uses this shape:

1. `entry` has the ACSL function contract.
2. `entry` calls unannotated helper functions.
3. Saida infers helper function contracts.
4. ISP infers auxiliary annotations.
5. WP verifies generated `out.c`.

Canonical public runs use `--lib-entry`. A positive helper-inference row requires backend pass, all expected helpers inferred, zero missing helpers, generated output parse pass, ISP pass, and nonzero complete WP goals.

## Files

- [../MICRO_RESULTS.md](../MICRO_RESULTS.md): human-readable public result table.
- [cases.json](cases.json): public manifest for the exported micro probes.
- [run_support_tests.py](run_support_tests.py): backend-aware public runner.
- [export_results_summary.py](export_results_summary.py): deterministic sanitized result exporter.
- [../autodeduct-support-results/academic-functional-v3.json](../autodeduct-support-results/academic-functional-v3.json): functional evidence snapshot.
- [../autodeduct-support-results/academic-rte-v3.json](../autodeduct-support-results/academic-rte-v3.json): RTE evidence snapshot.

## Commands

Run one probe:

```bash
python3 autodeduct-support/run_support_tests.py \
  --run-framac \
  --run-split \
  --lib-entry \
  --case helper_struct_basic \
  --timeout 600
```

Export a sanitized snapshot:

```bash
python3 autodeduct-support/export_results_summary.py \
  --repo-root "$PWD" \
  INPUT \
  OUTPUT
```

Do not treat entry-only success or process return code zero as helper-inference support.
