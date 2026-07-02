# AutoDeduct C/ACSL Support Probes

- This directory contains public-safe synthetic C/ACSL probes.
- They test small C/ACSL patterns through the AutoDeduct pipeline.
- They are not industrial case studies.
- Conclusions apply only to tested patterns.
- For detailed raw results, see [MICRO_RESULTS.md](../MICRO_RESULTS.md).

## Quick public conclusion

| Feature or pattern | Current public conclusion | Evidence |
|---|---|---|
| Integers and if-statements | Supported in tested pattern | `micro_int_if_helper` |
| Basic assigns and \old | Supported in tested pattern | `micro_assigns_old` |
| Simple global array update | Supported in tested pattern | `micro_global_array_basic` |
| Simple struct values | Supported in tested pattern | `micro_struct_basic` |
| Floating-point arithmetic | Boundary: WP does not prove all goals | `micro_float_arithmetic` |
| Pointer arithmetic | Boundary: Aux/ISP failure | `micro_pointer_arithmetic` |
| Simple local static state | Unexpected pass; not enough to claim general support | `micro_local_static` |
| Persistent local static helper state | Boundary: WP does not prove all goals | `micro_local_static_helper_persistence` |
| Nested pointers | Boundary: WP does not prove all goals | `micro_nested_pointer` |
| ACSL logic functions | Boundary: WP does not prove all goals | `micro_acsl_logic_function` |
| Loop without invariant | Boundary: WP does not prove all goals | `micro_loop_without_invariant` |

## How to run

```bash
python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --timeout 600
```

Observed outcomes from the saved public run are listed in [MICRO_RESULTS.md](../MICRO_RESULTS.md).

## Interpretation

- "Supported" means the tested small pattern passes parse, Saida, ISP, and WP.
- "Boundary" means the probe exposes a current failing phase.
- "Unexpected pass" means the boundary is narrower than expected and needs a stronger probe.
