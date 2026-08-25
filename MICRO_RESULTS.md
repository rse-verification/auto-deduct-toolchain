# AutoDeduct Public Micro Results

This report summarizes the 34 public-safe academic v3 source probes. Every result applies only to the exact source, entry contract, tool versions, and command profile used by the probe.

## Evaluation profiles

```text
Functional: --run-framac --run-split --lib-entry --baseline-group academic_functional_v3
RTE:        --run-framac --run-split --run-rte-wp --lib-entry --baseline-group academic_functional_v3
```

A positive result requires a clean functional backend, all expected helper contracts, no missing-contract marker, parseable generated output, ISP success, and a nonzero complete WP proof. A process return code of zero is not enough.

The RTE-enabled profile runs WP with runtime checks enabled. Its goal totals include the complete WP goal set for that run; they are not pure RTE-only counts.

## Result counts

| Snapshot | Rows | Results |
|---|---:|---|
| Functional academic v3 | 34 | 12 supported end to end; 12 functional boundaries; 4 auxiliary boundaries; 6 WP boundaries |
| RTE academic v3 | 34 | 15 complete RTE-enabled WP rows; 13 incomplete rows; 6 rows where RTE-enabled WP was not reached |

## How to read the table

- `Supported` means that every positive helper-inference, ISP, and WP gate passed.
- `Functional boundary` means that the first reliable evidence problem occurred in Saida, TriCera, or generated functional output.
- `Auxiliary boundary` means that functional inference was usable, but ISP failed.
- `WP boundary` means that the pipeline reached WP, but proof goals remained.
- A later WP control count is not support evidence when an earlier functional boundary has already been established.

The direct/rewrite pairs modify the input while keeping AutoDeduct unchanged. They show input-level workarounds and candidates for future tool automation, not completed tool improvements.

## Per-probe conclusions

| Probe and source | Tested pattern | Result | First evidence boundary | WP |
|---|---|---|---|---:|
| [`micro_int_if_helper`](autodeduct-support/micro-tests/supported/int_if_helper.c) | Integer helper with a branch | Supported | - | 20/20 |
| [`micro_local_static_helper_persistence`](autodeduct-support/micro-tests/expected_unsupported/local_static_helper_persistence.c) | Persistent local static state | Functional boundary | TriCera translation rejects the tested static-state form | Later control: 26/31 |
| [`helper_struct_basic`](autodeduct-support/micro-tests/helper_inference/helper_struct_basic.c) | Simple struct-field result | Supported | - | 14/14 |
| [`helper_enum_switch_basic`](autodeduct-support/micro-tests/helper_inference/helper_enum_switch_basic.c) | Enum and switch in a helper | Supported | - | 20/20 |
| [`helper_valid_pointer_store`](autodeduct-support/micro-tests/helper_inference/helper_valid_pointer_store.c) | Entry passes a valid pointer to a helper | Functional boundary | TriCera parser error in the generated contract form | Later control: 13/14 |
| [`helper_global_array_update`](autodeduct-support/micro-tests/helper_inference/helper_global_array_update.c) | Dynamic global-array update | WP boundary | Two proof goals remain | 34/36 |
| [`helper_assigns_old_basic`](autodeduct-support/micro-tests/helper_inference/helper_assigns_old_basic.c) | Helper side effect with `assigns` and `\old` | Supported | - | 20/20 |
| [`helper_stack_pointer`](autodeduct-support/micro-tests/helper_inference/helper_stack_pointer.c) | Address of an entry-local variable passed to a helper | Functional-output boundary | Generated Saida output does not parse | - |
| [`helper_two_level_call_chain`](autodeduct-support/micro-tests/helper_inference/helper_two_level_call_chain.c) | Entry calls helper A, which calls helper B | Supported | - | 27/27 |
| [`helper_multiple_call_contexts`](autodeduct-support/micro-tests/helper_inference/helper_multiple_call_contexts.c) | Same helper called from two contexts | Supported | - | 19/19 |
| [`contract_logic_function_helper`](autodeduct-support/micro-tests/helper_inference/contract_logic_function_helper.c) | ACSL logic function guides helper inference | Functional boundary | TriCera parser error | Later control: 14/15 |
| [`contract_behavior_helper`](autodeduct-support/micro-tests/helper_inference/contract_behavior_helper.c) | ACSL behaviors guide helper inference | Functional boundary | No usable inferred helper contract | Later control: 15/17 |
| [`contract_predicate_helper`](autodeduct-support/micro-tests/helper_inference/contract_predicate_helper.c) | ACSL predicate guides helper inference | Functional boundary | TriCera parser error near the predicate translation | Later control: 13/15 |
| [`helper_float_arithmetic`](autodeduct-support/micro-tests/helper_inference/helper_float_arithmetic.c) | Floating-point helper arithmetic | Functional boundary | TriCera floating-point translation is unimplemented for the tested form | Later control: 9/13 |
| [`helper_pointer_arithmetic`](autodeduct-support/micro-tests/helper_inference/helper_pointer_arithmetic.c) | Pointer arithmetic in a helper | Functional boundary | TriCera parser error | - |
| [`helper_nested_pointer`](autodeduct-support/micro-tests/helper_inference/helper_nested_pointer.c) | Nested-pointer store in an unannotated helper | Functional boundary | TriCera parser error | Later control: 8/10 |
| [`helper_loop_without_invariant`](autodeduct-support/micro-tests/helper_inference/helper_loop_without_invariant.c) | Loop without an inferred invariant | WP boundary | Helper contract is inferred, but loop proof is incomplete | 11/16 |
| [`helper_valid_pointer_store_simpler`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_valid_pointer_store_simpler.c) | Pointer operation kept inside the helper | Supported after input rewrite | - | 13/13 |
| [`helper_global_array_update_fixed_index`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_global_array_update_fixed_index.c) | Fixed-index global-array update | WP boundary after input rewrite | One proof goal remains | 13/14 |
| [`helper_struct_return_whole`](autodeduct-support/micro-tests/helper_inference/helper_struct_return_whole.c) | Helper returns a complete struct | Supported | - | 25/25 |
| [`helper_enum_indexed_array_struct_return`](autodeduct-support/micro-tests/helper_inference/helper_enum_indexed_array_struct_return.c) | Enum-indexed array of structs; whole-struct return | Auxiliary boundary | ISP fails after usable functional inference | - |
| [`helper_array_struct_output_parameter_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_array_struct_output_parameter_rewrite.c) | Scalar-field-return rewrite of the array/struct helper | Auxiliary boundary after input rewrite | ISP still fails | - |
| [`helper_int_indexed_array_struct_return`](autodeduct-support/micro-tests/helper_inference/helper_int_indexed_array_struct_return.c) | Integer-indexed array of structs; whole-struct return | Auxiliary boundary | ISP fails after usable functional inference | - |
| [`helper_int_indexed_array_scalar_return`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_int_indexed_array_scalar_return.c) | Integer index; helper returns one struct field | Auxiliary boundary after input rewrite | ISP still fails | - |
| [`helper_stack_pointer_return_value_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_stack_pointer_return_value_rewrite.c) | Replace the stack-pointer output interface with a scalar return | Supported after input rewrite | - | 17/17 |
| [`contract_logic_inline_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/contract_logic_inline_rewrite.c) | Inline the tested logic-function expression | Supported after input rewrite | - | 17/17 |
| [`contract_behavior_plain_ensures_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/contract_behavior_plain_ensures_rewrite.c) | Replace the tested behaviors with plain implication-style `ensures` | Supported after input rewrite | - | 17/17 |
| [`contract_predicate_inline_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/contract_predicate_inline_rewrite.c) | Inline the tested predicate body | Supported after input rewrite | - | 17/17 |
| [`helper_int_indexed_scalar_array_return`](autodeduct-support/micro-tests/helper_inference/helper_int_indexed_scalar_array_return.c) | Dynamic index into a scalar array | WP boundary | One proof goal remains | 20/21 |
| [`helper_fixed_index_array_struct_scalar_return`](autodeduct-support/micro-tests/helper_inference/helper_fixed_index_array_struct_scalar_return.c) | Fixed index into an array of structs; scalar return | WP boundary | One proof goal remains | 17/18 |
| [`helper_single_global_struct_scalar_return`](autodeduct-support/micro-tests/helper_inference/helper_single_global_struct_scalar_return.c) | Single global struct; scalar-field return | WP boundary | Two proof goals remain | 13/15 |
| [`contract_old_logic_alias_reproducer`](autodeduct-support/micro-tests/helper_inference/contract_old_logic_alias_reproducer.c) | Old-state scalar/struct ACSL logic aliases | Functional boundary | TriCera parser error: `func_backend_parser` | Later control: 12/12 |
| [`contract_old_logic_alias_inline_rewrite`](autodeduct-support/micro-tests/helper_inference/contract_old_logic_alias_inline_rewrite.c) | Partial inline reduction of the old-state alias pair | Functional boundary | Same TriCera parser error: `func_backend_parser` | Later control: 12/12 |
| [`helper_missing_forward_declaration`](autodeduct-support/micro-tests/helper_inference/helper_missing_forward_declaration.c) | Helper call before a prototype | Input-compatibility boundary | Missing inferred contract block: `func_backend_output` | Later control: 11/11 |

The case identifier `helper_array_struct_output_parameter_rewrite` is retained for frozen evidence compatibility. The current source returns one scalar field; it does not use an output parameter.

## Interpretation of selected rewrites

- The tested pointer rewrites pass, which is consistent with interface shape being important. The current pairs change several details and do not isolate one unique cause.
- The tested logic-function and predicate rewrites pass after inlining the exact expressions used by the probes. This is not a claim that arbitrary ACSL definitions can always be eliminated safely.
- The tested behavior rewrite preserves the two conditional postconditions used by that probe. It is not a general equivalence result for arbitrary ACSL behaviors.
- Fixed-index and array/struct reductions simplify the programs but do not establish complete support.
- The old-state logic-alias pair does not establish a workaround: the partial inline rewrite keeps the functional parser boundary.
- The missing-forward-declaration probe is an input-compatibility test, not a general claim about valid modern C helper support.

## Main conclusions

- The tested positive subset includes integer branches, simple structs, enum/switch control, selected old-state and frame conditions, two-level call chains, repeated call contexts, whole-struct return, and several simplified input rewrites.
- Observed functional boundaries in the tested forms include persistent local static state, caller/stack-pointer interfaces, floating-point translation, pointer arithmetic, nested pointers, and selected ACSL logic, behavior, and predicate forms.
- Selected array-of-struct helper patterns remain an ISP boundary after several reductions.
- Loops without inferred invariants and selected array/global-state forms reach WP but leave proof goals.
- A rewrite is successful only when the complete helper-inference, ISP, and WP chain passes. Smaller code is not automatically supported.

## Machine evidence

- [`academic-functional-v3.json`](autodeduct-support-results/academic-functional-v3.json)
- [`academic-rte-v3.json`](autodeduct-support-results/academic-rte-v3.json)

The three added probes form two issue families rather than a complete root-cause isolation. The old-state alias pair is not yet a fully minimal root-cause isolation, and no successful workaround is established. The forward-declaration source is not valid modern C without a prototype, so helper prototypes are a current input requirement; a corrected companion probe is future work. Conclusions apply only to these frozen inputs and named profiles.
