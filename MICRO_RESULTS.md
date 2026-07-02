# AutoDeduct C/ACSL Micro-Test Results

This file summarizes saved observations for public-safe synthetic support probes.
The probes are small C/ACSL patterns, not industrial case studies, and conclusions
apply only to the tested patterns.

The saved observations use the split pipeline implemented by
`autodeduct-support/run_micro_tests.py`:

1. Frama-C parse
2. Saida functional inference
3. ISP auxiliary inference
4. WP verification

## Public conclusion table

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

## Raw observed outcomes

| Probe | Observed outcome | WP goals | Notes |
|---|---|---:|---|
| `micro_int_if_helper` | `supported_end_to_end` | 20/20 | Supported in tested pattern. |
| `micro_assigns_old` | `supported_end_to_end` | 11/11 | Supported in tested pattern. |
| `micro_global_array_basic` | `supported_end_to_end` | 11/11 | Supported in tested pattern. |
| `micro_struct_basic` | `supported_end_to_end` | 16/16 | Supported in tested pattern. |
| `micro_float_arithmetic` | Boundary: WP did not prove all goals | 3/6 | Floating-point arithmetic boundary. |
| `micro_pointer_arithmetic` | Boundary: auxiliary inference stage | - | Pointer arithmetic boundary. |
| `micro_local_static` | Unexpected pass | 10/10 | This simple probe is not enough to claim general local-static support. |
| `micro_local_static_helper_persistence` | Boundary: WP did not prove all goals | 30/35 | Exercises persistent local static state across multiple helper calls. |
| `micro_nested_pointer` | Boundary: WP did not prove all goals | 6/8 | Nested-pointer boundary. |
| `micro_acsl_logic_function` | Boundary: WP did not prove all goals | 6/11 | ACSL logic-function boundary. |
| `micro_loop_without_invariant` | Boundary: WP did not prove all goals | 2/8 | Loop-without-invariant boundary. |
| `micro_valid_pointer_struct` | `supported_end_to_end` | 12/12 | Additional public probe. |
| `micro_enum_switch_basic` | `supported_end_to_end` | 17/17 | Additional public probe. |
| `micro_behavior_basic` | `supported_end_to_end` | 12/12 | Additional public probe. |
| `micro_array_struct_field_boundary` | `supported_end_to_end` | 14/14 | Additional public boundary-clarifying probe. |
| `micro_array_struct_read_helper_isp_crash` | Boundary: auxiliary inference stage | - | Additional public boundary probe. |

## Interpretation

- "Supported" means the tested small pattern passes parse, Saida, ISP, and WP.
- "Boundary" means the probe exposes a current failing phase.
- "Unexpected pass" means the boundary is narrower than expected and needs a stronger probe.
