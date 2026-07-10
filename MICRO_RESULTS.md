# AutoDeduct C/ACSL Micro-Test Results

This file summarizes fresh observations for public-safe synthetic support probes.
The probes are small C/ACSL patterns, not industrial case studies, and conclusions
apply only to the tested patterns.

Current observations were refreshed on 2026-07-10 inside `auto-deduct:latest`
with Frama-C 31.0 (Gallium).

Canonical public support results use `--lib-entry`:

```bash
python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --lib-entry --timeout 600
```

The table separates "the pipeline ran to WP" from "WP proved every goal." A
case that runs to WP but leaves goals unproved is a WP proof boundary, not a
pre-WP failure.

The saved observations use the split pipeline implemented by
`autodeduct-support/run_micro_tests.py`:

1. Frama-C parse
2. Saida functional inference
3. ISP auxiliary inference
4. WP verification

## Failure attribution

| Result | Attribution |
|---|---|
| `parse_failed` | Frama-C frontend / preprocessing / ACSL syntax |
| `func_failed` | Saida / functional inference / TriCera |
| `aux_failed` | ISP / auxiliary inference / Eva |
| `wp_ran_with_unproved_goals` | WP proof gap, weak contract, missing auxiliary facts, or solver limitation |
| harness missing | Not a tool-support result |

## Public conclusion table

| Feature or pattern | Current public conclusion | Evidence |
|---|---|---|
| Integers and if-statements | `supported_end_to_end` | `micro_int_if_helper`, WP proves `20/20` |
| Basic assigns and `\old` | `supported_end_to_end` | `micro_assigns_old`, WP proves `6/6` |
| Simple global array update | `supported_end_to_end` | `micro_global_array_basic`, WP proves `7/7` |
| Simple struct values | `supported_end_to_end` | `micro_struct_basic`, WP proves `8/8` |
| Simple pointer-to-struct field access | `supported_end_to_end` | `micro_valid_pointer_struct`, WP proves `7/7` |
| Enum and switch | `supported_end_to_end` | `micro_enum_switch_basic`, WP proves `15/15` |
| Simple ACSL behaviors | `supported_end_to_end` | `micro_behavior_basic`, WP proves `8/8` |
| Floating-point arithmetic | runs to WP but leaves `2/5` goals unproved | `micro_float_arithmetic`, WP proves `3/5` |
| Pointer arithmetic | `failed_at_aux` | `micro_pointer_arithmetic`, Aux/ISP exits `125` |
| Simple local static state | runs to WP but leaves `1/6` goals unproved | `micro_local_static`, WP proves `5/6` |
| Persistent local static helper state | runs to WP but leaves `5/31` goals unproved | `micro_local_static_helper_persistence`, WP proves `26/31` |
| Nested pointers | `unexpected_pass` under canonical `--lib-entry` | `micro_nested_pointer`, WP proves `4/4` |
| ACSL logic functions | `unexpected_pass` under canonical `--lib-entry` | `micro_acsl_logic_function`, WP proves `6/6` |
| Array-of-struct field access | `supported_end_to_end` | `micro_array_struct_field_boundary`, WP proves `9/9` |
| Array-of-struct helper read returning whole struct | `failed_at_aux`; `wp_control`, not pure inference evidence | `micro_array_struct_read_helper_isp_crash`, Aux/ISP exits `4` |
| Loop without invariant | runs to WP but leaves `5/7` goals unproved | `micro_loop_without_invariant`, WP proves `2/7` |

## Raw observed outcomes

| Probe | Kind | Classification | WP result | Notes |
|---|---|---|---:|---|
| `micro_int_if_helper` | `micro_supported` | `supported_end_to_end` | 20/20 proved | Supported in tested pattern. |
| `micro_assigns_old` | `micro_supported` | `supported_end_to_end` | 6/6 proved | Supported in tested pattern. |
| `micro_global_array_basic` | `micro_supported` | `supported_end_to_end` | 7/7 proved | Supported in tested pattern. |
| `micro_struct_basic` | `micro_supported` | `supported_end_to_end` | 8/8 proved | Supported in tested pattern. |
| `micro_valid_pointer_struct` | `micro_supported` | `supported_end_to_end` | 7/7 proved | Entry-contract-only pointer-to-struct field access. |
| `micro_enum_switch_basic` | `micro_supported` | `supported_end_to_end` | 15/15 proved | Supported in tested pattern. |
| `micro_behavior_basic` | `micro_supported` | `supported_end_to_end` | 8/8 proved | Supported in tested pattern. |
| `micro_float_arithmetic` | `micro_expected_unsupported` | `wp_ran_with_unproved_goals` | 3/5 proved; 2/5 unproved | Floating-point arithmetic reaches WP but is not fully proved. |
| `micro_pointer_arithmetic` | `micro_expected_unsupported` | `aux_failed` / `failed_at_aux` | - | Pointer arithmetic fails before WP. |
| `micro_local_static` | `micro_expected_unsupported` | `wp_ran_with_unproved_goals` | 5/6 proved; 1/6 unproved | This simple local-static case reaches WP but is not fully proved. |
| `micro_local_static_helper_persistence` | `micro_expected_unsupported` | `wp_ran_with_unproved_goals` | 26/31 proved; 5/31 unproved | Exercises persistent local static state across multiple helper calls. |
| `micro_nested_pointer` | `micro_expected_unsupported` | `unexpected_pass` | 4/4 proved | Canonical `--lib-entry` mode proves this case; see `autodeduct-support/PUBLIC_PROBE_DIAGNOSIS.md`. |
| `micro_acsl_logic_function` | `micro_expected_unsupported` | `unexpected_pass` | 6/6 proved | Canonical `--lib-entry` mode proves this case, so it is not current boundary evidence. |
| `micro_array_struct_field_boundary` | `micro_boundary` | `supported_end_to_end` | 9/9 proved | Array-of-struct field access passes in this tested pattern. |
| `micro_array_struct_read_helper_isp_crash` | `wp_control` | `aux_failed` / `failed_at_aux` | - | WP-control boundary reproducer with a manually written helper contract; not pure inference evidence. |
| `micro_loop_without_invariant` | `micro_expected_unsupported` | `wp_ran_with_unproved_goals` | 2/7 proved; 5/7 unproved | Loop-without-invariant case reaches WP but is not fully proved. |

No saved public micro-test in this table is classified as `parse_failed` or
`func_failed`.

## Interpretation

- `supported_end_to_end` means the tested small pattern passes parse, Saida, ISP, and WP, with all reported WP goals proved.
- `failed_at_aux` means the probe fails before WP because Aux/ISP does not produce the next artifact.
- `wp_ran_with_unproved_goals` means the WP command passes, but WP leaves one or more proof goals unproved.
- `unexpected_pass` means an expected-unsupported probe passed end to end under the canonical public command.
- `wp_control` tests are useful boundary reproducers, but they are not pure AutoDeduct inference evidence when they contain manually written helper contracts or auxiliary facts.
