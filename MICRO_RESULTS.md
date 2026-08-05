# AutoDeduct Public Micro Results

This report summarizes the public-safe academic v3 probes. A result applies only to the exact source, contract, tool versions, and command profile used by the probe.

## Evaluation profile

```text
Functional: --run-framac --run-split --lib-entry --baseline-group academic_functional_v3
RTE:        --run-framac --run-split --run-rte-wp --lib-entry --baseline-group academic_functional_v3
```

A positive result requires a clean functional backend, all expected helper contracts, no missing-contract marker, parseable generated output, ISP success, and a nonzero complete WP proof. A process return code of zero is not enough.

## Result counts

| Snapshot | Rows | Results |
|---|---:|---|
| Functional academic v3 | 31 | 12 supported end to end; 9 functional boundaries; 4 auxiliary boundaries; 6 WP boundaries |
| RTE academic v3 | 31 | 12 complete RTE-enabled WP rows; 13 incomplete rows; 6 rows where RTE was not reached |

`wp_with_rte_goals` is the complete WP goal set with runtime checks enabled. It is not a pure RTE-only count.

## Per-probe conclusions

| Probe and source | Tested pattern | Result | First evidence boundary | WP |
|---|---|---|---|---:|
| [`micro_int_if_helper`](autodeduct-support/micro-tests/supported/int_if_helper.c) | Integer helper with a branch | Supported | - | 20/20 |
| [`micro_local_static_helper_persistence`](autodeduct-support/micro-tests/expected_unsupported/local_static_helper_persistence.c) | Persistent local static state | Functional boundary | TriCera translation: static variable with contract is unsupported | 26/31 later control goals |
| [`helper_struct_basic`](autodeduct-support/micro-tests/helper_inference/helper_struct_basic.c) | Simple struct field result | Supported | - | 14/14 |
| [`helper_enum_switch_basic`](autodeduct-support/micro-tests/helper_inference/helper_enum_switch_basic.c) | Enum and switch in a helper | Supported | - | 20/20 |
| [`helper_valid_pointer_store`](autodeduct-support/micro-tests/helper_inference/helper_valid_pointer_store.c) | Entry passes a valid pointer to a helper | Functional boundary | TriCera parser error in generated contract form | 13/14 later control goals |
| [`helper_global_array_update`](autodeduct-support/micro-tests/helper_inference/helper_global_array_update.c) | Dynamic global-array update | WP boundary | Two proof goals remain | 34/36 |
| [`helper_assigns_old_basic`](autodeduct-support/micro-tests/helper_inference/helper_assigns_old_basic.c) | Helper side effect with `assigns` and `\old` | Supported | - | 20/20 |
| [`helper_stack_pointer`](autodeduct-support/micro-tests/helper_inference/helper_stack_pointer.c) | Address of an entry-local variable passed to helper | Functional-output boundary | Saida output does not parse | - |
| [`helper_two_level_call_chain`](autodeduct-support/micro-tests/helper_inference/helper_two_level_call_chain.c) | Entry -> helper A -> helper B | Supported | - | 27/27 |
| [`helper_multiple_call_contexts`](autodeduct-support/micro-tests/helper_inference/helper_multiple_call_contexts.c) | Same helper called from two contexts | Supported | - | 19/19 |
| [`contract_logic_function_helper`](autodeduct-support/micro-tests/helper_inference/contract_logic_function_helper.c) | ACSL logic function guides helper inference | Functional boundary | TriCera parser error | 14/15 later control goals |
| [`contract_behavior_helper`](autodeduct-support/micro-tests/helper_inference/contract_behavior_helper.c) | ACSL behaviors guide helper inference | Functional boundary | No usable inferred helper contract | 15/17 later control goals |
| [`contract_predicate_helper`](autodeduct-support/micro-tests/helper_inference/contract_predicate_helper.c) | ACSL predicate guides helper inference | Functional boundary | TriCera parser error near predicate | 13/15 later control goals |
| [`helper_float_arithmetic`](autodeduct-support/micro-tests/helper_inference/helper_float_arithmetic.c) | Floating-point helper arithmetic | Functional boundary | TriCera `Ecfloat` translation is unimplemented | 9/13 later control goals |
| [`helper_pointer_arithmetic`](autodeduct-support/micro-tests/helper_inference/helper_pointer_arithmetic.c) | Pointer arithmetic in helper | Functional boundary | TriCera parser error | - |
| [`helper_nested_pointer`](autodeduct-support/micro-tests/helper_inference/helper_nested_pointer.c) | Nested-pointer store | Functional boundary | TriCera parser error | 8/10 later control goals |
| [`helper_loop_without_invariant`](autodeduct-support/micro-tests/helper_inference/helper_loop_without_invariant.c) | Loop without inferred invariant | WP boundary | Helper contract is inferred, but loop proof is incomplete | 11/16 |
| [`helper_valid_pointer_store_simpler`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_valid_pointer_store_simpler.c) | Pointer operation kept inside helper | Supported after rewrite | - | 13/13 |
| [`helper_global_array_update_fixed_index`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_global_array_update_fixed_index.c) | Fixed-index global-array update | WP boundary after rewrite | One proof goal remains | 13/14 |
| [`helper_struct_return_whole`](autodeduct-support/micro-tests/helper_inference/helper_struct_return_whole.c) | Helper returns a complete struct | Supported | - | 25/25 |
| [`helper_enum_indexed_array_struct_return`](autodeduct-support/micro-tests/helper_inference/helper_enum_indexed_array_struct_return.c) | Enum-indexed array of structs; whole-struct return | Auxiliary boundary | ISP fails | - |
| [`helper_array_struct_output_parameter_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_array_struct_output_parameter_rewrite.c) | Output-parameter rewrite of array/struct return | Auxiliary boundary | ISP still fails | - |
| [`helper_int_indexed_array_struct_return`](autodeduct-support/micro-tests/helper_inference/helper_int_indexed_array_struct_return.c) | Integer-indexed array of structs; whole-struct return | Auxiliary boundary | ISP fails | - |
| [`helper_int_indexed_array_scalar_return`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_int_indexed_array_scalar_return.c) | Integer index; return only one struct field | Auxiliary boundary | ISP still fails | - |
| [`helper_stack_pointer_return_value_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/helper_stack_pointer_return_value_rewrite.c) | Replace stack-pointer interface with scalar return | Supported after rewrite | - | 17/17 |
| [`contract_logic_inline_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/contract_logic_inline_rewrite.c) | Inline logic-function expression | Supported after rewrite | - | 17/17 |
| [`contract_behavior_plain_ensures_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/contract_behavior_plain_ensures_rewrite.c) | Replace behaviors with plain implication-style `ensures` | Supported after rewrite | - | 17/17 |
| [`contract_predicate_inline_rewrite`](autodeduct-support/micro-tests/helper_inference_rewrites/contract_predicate_inline_rewrite.c) | Inline predicate body | Supported after rewrite | - | 17/17 |
| [`helper_int_indexed_scalar_array_return`](autodeduct-support/micro-tests/helper_inference/helper_int_indexed_scalar_array_return.c) | Dynamic index into a scalar array | WP boundary | One proof goal remains | 20/21 |
| [`helper_fixed_index_array_struct_scalar_return`](autodeduct-support/micro-tests/helper_inference/helper_fixed_index_array_struct_scalar_return.c) | Fixed index into array of structs; scalar return | WP boundary | One proof goal remains | 17/18 |
| [`helper_single_global_struct_scalar_return`](autodeduct-support/micro-tests/helper_inference/helper_single_global_struct_scalar_return.c) | Single global struct; scalar field return | WP boundary | Two proof goals remain | 13/15 |

## Main conclusions

- The tested positive subset includes integer branches, simple structs, enum/switch control, selected old-state/frame conditions, two-level call chains, repeated call contexts, whole-struct return, and several simplified rewrites.
- The strongest functional boundaries are local static state, stack-pointer interfaces, floating-point translation, pointer arithmetic, nested pointers, and selected ACSL logic/behavior/predicate forms.
- Array-of-struct helper patterns remain an ISP boundary even after several reductions.
- A rewrite is successful only when the complete helper-inference, ISP, and WP chain passes. Smaller code is not automatically supported.

## Machine evidence

- [`academic-functional-v3.json`](autodeduct-support-results/academic-functional-v3.json)
- [`academic-rte-v3.json`](autodeduct-support-results/academic-rte-v3.json)
