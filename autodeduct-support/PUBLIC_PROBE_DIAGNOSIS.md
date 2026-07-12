# Public Probe Diagnosis

This file records the diagnostic audit of the public C/ACSL micro-tests. It
explains how to read the public support results, which cases changed under
canonical `--lib-entry` mode, and which probes need follow-up work.

## Canonical mode

Public support results use `--lib-entry`:

```bash
python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --lib-entry --timeout 600
```

The public probes use `entry` as a library-style entry point. With `--lib-entry`,
Frama-C and WP may assume the entry preconditions instead of trying to prove that
`entry` can be called from an arbitrary program initial state.

The fresh canonical audit was run inside `auto-deduct:latest` with Frama-C 31.0
(Gallium).

## Canonical results

| Case | Source file | Expected | Parse | Saida / Func | ISP / Aux | WP | WP goals | Classification | Result type |
|---|---|---|---|---|---|---|---:|---|---|
| `micro_int_if_helper` | `supported/int_if_helper.c` | `supported` | pass | pass | pass | pass | `20/20` | `supported_end_to_end` | expected |
| `micro_assigns_old` | `supported/assigns_old.c` | `supported` | pass | pass | pass | pass | `6/6` | `supported_end_to_end` | expected |
| `micro_global_array_basic` | `supported/global_array_basic.c` | `supported` | pass | pass | pass | pass | `7/7` | `supported_end_to_end` | expected |
| `micro_struct_basic` | `supported/struct_basic.c` | `supported` | pass | pass | pass | pass | `8/8` | `supported_end_to_end` | expected |
| `micro_valid_pointer_struct` | `supported/valid_pointer_struct.c` | `supported` | pass | pass | pass | pass | `7/7` | `supported_end_to_end` | expected |
| `micro_enum_switch_basic` | `supported/enum_switch_basic.c` | `supported` | pass | pass | pass | pass | `15/15` | `supported_end_to_end` | expected |
| `micro_behavior_basic` | `supported/behavior_basic.c` | `supported` | pass | pass | pass | pass | `8/8` | `supported_end_to_end` | expected |
| `micro_float_arithmetic` | `expected_unsupported/float_arithmetic.c` | `expected_unsupported` | pass | pass | pass | pass | `3/5` | `wp_ran_with_unproved_goals` | boundary |
| `micro_pointer_arithmetic` | `expected_unsupported/pointer_arithmetic.c` | `expected_unsupported` | pass | pass | fail `125` | unknown | `-` | `aux_failed` | boundary |
| `micro_local_static` | `expected_unsupported/local_static.c` | `expected_unsupported` | pass | pass | pass | pass | `5/6` | `wp_ran_with_unproved_goals` | boundary |
| `micro_local_static_helper_persistence` | `expected_unsupported/local_static_helper_persistence.c` | `expected_unsupported` | pass | pass | pass | pass | `26/31` | `wp_ran_with_unproved_goals` | boundary |
| `micro_nested_pointer` | `expected_unsupported/nested_pointer.c` | `expected_unsupported` | pass | pass | pass | pass | `4/4` | `supported_end_to_end` | unexpected pass |
| `micro_acsl_logic_function` | `expected_unsupported/acsl_logic_function.c` | `expected_unsupported` | pass | pass | pass | pass | `6/6` | `supported_end_to_end` | unexpected pass |
| `micro_array_struct_field_boundary` | `expected_unsupported/array_struct_field_boundary.c` | `boundary` | pass | pass | pass | pass | `9/9` | `supported_end_to_end` | boundary clarified |
| `micro_array_struct_read_helper_isp_crash` | `wp_control/array_struct_read_helper_isp_crash.c` | `expected_unsupported` | pass | pass | fail `4` | unknown | `-` | `aux_failed` | boundary |
| `micro_loop_without_invariant` | `expected_unsupported/loop_without_invariant.c` | `expected_unsupported` | pass | pass | pass | pass | `2/7` | `wp_ran_with_unproved_goals` | boundary |

No public case currently fails at Frama-C parse. In the saved command-returncode
table, no case has a nonzero Saida process return code; the stricter functional
cleanliness check below flags syntax-error text separately.

## Probe roles and helper inference

Pipeline success and helper-contract inference are separate conclusions.
`supported_end_to_end` means the split pipeline reached WP and proved all goals;
it does not by itself mean Saida inferred a helper contract.

| Probe role | Meaning |
|---|---|
| `helper_inference` | Contains an unannotated helper and is primary evidence for Saida helper-contract inference. |
| `entry_pipeline_control` | Has an entry contract only and mainly tests entry-contract, ISP, and WP compatibility. |
| `mixed_inference` | Reserved for probes that mix inferred helper facts with manually supplied helper or auxiliary facts. |
| `wp_control` | Reproducer or WP-control case; do not cite as pure inference evidence. |

Current helper-inference evidence from the saved canonical run:

| Case | Probe role | Inferred helper contracts | Missing inferred contracts | Interpretation |
|---|---|---:|---:|---|
| `micro_int_if_helper` | `helper_inference` | 1 | 0 | Saida inferred the helper contract for `nonnegative_helper`. |
| `micro_local_static_helper_persistence` | `helper_inference` | 0 | 1 | Saida did not infer a helper contract for `next_count`; the case still reaches WP with unproved goals. |
| `micro_array_struct_read_helper_isp_crash` | `wp_control` | 0 | 1 | The helper contract is written in the source, so this is boundary evidence, not helper-inference evidence. |

All other current public probes are `entry_pipeline_control`: their successful
pipeline result should not be described as helper-contract inference.

The updated runner also records obvious TriCera syntax-error text in functional
stderr. The saved canonical logs contain that text for these entry-only probes:

| Case | Pipeline command result | Functional-inference interpretation |
|---|---|---|
| `micro_pointer_arithmetic` | Saida process returned `0`, later failed at Aux/ISP. | Do not treat the functional phase as clean. |
| `micro_nested_pointer` | Saida process returned `0`, later proved WP `4/4`. | Do not cite as clean Saida evidence. |
| `micro_acsl_logic_function` | Saida process returned `0`, later proved WP `6/6`. | Do not cite as clean Saida evidence. |

## Stale documentation findings

The old public table used non-canonical results for several rows. The strongest
stale-result findings are:

| Case | Old non-canonical result | Canonical result | Meaning |
|---|---|---|---|
| `micro_nested_pointer` | WP `6/8`, boundary | WP `4/4`, `unexpected_pass` | The old boundary was caused by missing `--lib-entry`. |
| `micro_acsl_logic_function` | WP `6/11`, boundary | WP `6/6`, `unexpected_pass` | The old boundary was caused by missing `--lib-entry`. |
| `micro_local_static` | WP `10/10`, `unexpected_pass` | WP `5/6`, boundary | Canonical mode exposes a WP proof gap. |

Other cases keep the same broad conclusion but have different WP goal counts
with `--lib-entry`, so public result tables should always state the canonical
command used to produce the evidence.

## Effect of `--lib-entry`

This table compares the canonical run with a non-`--lib-entry` split-pipeline
control. Public conclusions should use the canonical column.

| Case | Canonical classification | Canonical WP | Non-canonical classification | Non-canonical WP | Changed |
|---|---|---:|---|---:|---|
| `micro_int_if_helper` | `supported_end_to_end` | `20/20` | `supported_end_to_end` | `20/20` | no |
| `micro_assigns_old` | `supported_end_to_end` | `6/6` | `supported_end_to_end` | `11/11` | goal count |
| `micro_global_array_basic` | `supported_end_to_end` | `7/7` | `supported_end_to_end` | `11/11` | goal count |
| `micro_struct_basic` | `supported_end_to_end` | `8/8` | `supported_end_to_end` | `16/16` | goal count |
| `micro_valid_pointer_struct` | `supported_end_to_end` | `7/7` | `supported_end_to_end` | `11/11` | goal count |
| `micro_enum_switch_basic` | `supported_end_to_end` | `15/15` | `supported_end_to_end` | `17/17` | goal count |
| `micro_behavior_basic` | `supported_end_to_end` | `8/8` | `supported_end_to_end` | `12/12` | goal count |
| `micro_float_arithmetic` | `wp_ran_with_unproved_goals` | `3/5` | `wp_ran_with_unproved_goals` | `3/6` | goal count |
| `micro_pointer_arithmetic` | `aux_failed` | `-` | `aux_failed` | `-` | no |
| `micro_local_static` | `wp_ran_with_unproved_goals` | `5/6` | `supported_end_to_end` | `10/10` | classification |
| `micro_local_static_helper_persistence` | `wp_ran_with_unproved_goals` | `26/31` | `wp_ran_with_unproved_goals` | `30/35` | goal count |
| `micro_nested_pointer` | `supported_end_to_end` | `4/4` | `wp_ran_with_unproved_goals` | `6/8` | classification |
| `micro_acsl_logic_function` | `supported_end_to_end` | `6/6` | `wp_ran_with_unproved_goals` | `6/11` | classification |
| `micro_array_struct_field_boundary` | `supported_end_to_end` | `9/9` | `supported_end_to_end` | `14/14` | goal count |
| `micro_array_struct_read_helper_isp_crash` | `aux_failed` | `-` | `aux_failed` | `-` | no |
| `micro_loop_without_invariant` | `wp_ran_with_unproved_goals` | `2/7` | `wp_ran_with_unproved_goals` | `2/8` | goal count |

## Direct source WP comparison

Direct source WP is useful as a control, but it is not the same as the
AutoDeduct split pipeline. The split pipeline runs Saida, then ISP, then WP on
generated `out.c`.

| Case | Direct source WP | Split-pipeline WP | Difference |
|---|---:|---:|---|
| `micro_float_arithmetic` | `3/4` | `3/5` | Both leave goals unproved; generated `out.c` has a different proof surface. |
| `micro_pointer_arithmetic` | `4/4` | not reached | Direct WP passes, but ISP/Aux fails before `out.c` reaches WP. |
| `micro_local_static` | `2/3` | `5/6` | Both leave goals unproved; generated `out.c` has a different proof surface. |
| `micro_local_static_helper_persistence` | `6/10` | `26/31` | Both leave goals unproved; generated `out.c` has a different proof surface. |
| `micro_nested_pointer` | `4/4` | `4/4` | No proof-result difference in canonical mode. |
| `micro_acsl_logic_function` | `4/4` | `6/6` | Both prove all goals; generated `out.c` has more goals. |
| `micro_loop_without_invariant` | `1/4` | `2/7` | Both leave goals unproved; generated `out.c` has a different proof surface. |
| `micro_array_struct_read_helper_isp_crash` | `12/12` | not reached | Direct WP passes, but ISP/Aux fails before `out.c` reaches WP. |

## Boundary and issue classification

| Category | Current cases |
|---|---|
| Frama-C parse issue | None in the public run. |
| Saida issue | None in the public run. |
| ISP issue | `micro_pointer_arithmetic`, `micro_array_struct_read_helper_isp_crash`. |
| WP proof issue | `micro_float_arithmetic`, `micro_local_static`, `micro_local_static_helper_persistence`, `micro_loop_without_invariant`. |
| Stale result issue | `micro_nested_pointer`, `micro_acsl_logic_function`, `micro_local_static`, plus goal-count changes in several passing cases. |
| Test too weak issue | `micro_nested_pointer`, `micro_acsl_logic_function`. |

## Static audit

The public tests intentionally contain local static variables only in the
local-static probes:

| File | Static use | Intent |
|---|---|---|
| `expected_unsupported/local_static.c` | local static variable | Simple local-static probe. |
| `expected_unsupported/local_static_helper_persistence.c` | local static variable | Stronger persistent-state helper probe. |

No file-scope static variables were found. No static functions were found. No
other public test currently uses `static`.

## Inference audit

Public support probes should prefer an entry-point ACSL contract and should let
Saida and ISP infer helper contracts or auxiliary facts where possible.

Most current probes are entry-only controls. Pointer and array tests may write
top-level `\valid`, `assigns`, or range facts in the entry contract; those facts
should not be described as inferred. The only current positive public helper
inference evidence is `micro_int_if_helper`.

`micro_local_static_helper_persistence` is still useful because it contains an
unannotated helper, but the current Saida output says no inferred contract was
found for that helper. `micro_array_struct_read_helper_isp_crash` has a manually
written helper contract and is `wp_control`, so it should be cited only as a
boundary reproducer.

## Cases needing stronger probes

| Case | Reason |
|---|---|
| `micro_nested_pointer` | Proves `4/4` with `--lib-entry`; needs a stronger nested-pointer pattern. |
| `micro_acsl_logic_function` | Proves `6/6` with `--lib-entry`; needs a stronger logic-function pattern. |

Boundary cases that still provide useful evidence:

| Case | Current evidence |
|---|---|
| `micro_float_arithmetic` | WP runs but leaves goals unproved. |
| `micro_local_static` | WP runs but leaves goals unproved. |
| `micro_local_static_helper_persistence` | WP runs but leaves goals unproved. |
| `micro_loop_without_invariant` | WP runs but leaves goals unproved. |
| `micro_pointer_arithmetic` | ISP/Aux fails before WP. |
| `micro_array_struct_read_helper_isp_crash` | ISP/Aux fails before WP in a `wp_control` reproducer. |

## Public documentation policy

- Keep `MICRO_RESULTS.md` as the main result table.
- Keep `autodeduct-support/README.md` short.
- Do not commit generated `autodeduct-support-results/`.
- Do not commit Python bytecode or `__pycache__`.
- Treat support claims as "supported in tested pattern," not as broad C or ACSL support.
