# AutoDeduct Public Micro Results

This is the public-safe academic v3 result snapshot for synthetic C/ACSL micro probes. Conclusions apply only to the tested patterns.

## Profile

Functional profile:

```text
--run-framac --run-split --lib-entry --baseline-group academic_functional_v3
```

RTE profile:

```text
--run-framac --run-split --run-rte-wp --lib-entry --baseline-group academic_functional_v3
```

The functional and RTE profiles are separate. RTE totals come from WP with runtime checks enabled and are not pure RTE-only obligation counts.

## Counts

| Snapshot | Rows | Results |
|---|---:|---|
| Functional academic v3 | 31 | 12 `supported_end_to_end`, 9 `failed_at_func`, 6 `failed_at_wp`, 4 `failed_at_aux` |
| RTE academic v3 | 31 | 12 `rte_goals_proved`, 13 `failed_at_rte_wp_goals`, 6 `rte_not_reached` |

Positive helper-inference evidence requires backend pass, all expected helpers inferred, zero missing helpers, generated output parse pass, ISP pass, and nonzero complete WP goals. Process return code zero alone is not evidence of support.

## Direct And Rewrite Links

| Direct case | Rewrite case | Result |
|---|---|---|
| `helper_valid_pointer_store` | `helper_valid_pointer_store_simpler` | Rewrite passes end to end. |
| `helper_global_array_update` | `helper_global_array_update_fixed_index` | Rewrite is smaller but still fails at WP. |
| `helper_enum_indexed_array_struct_return` | `helper_array_struct_output_parameter_rewrite` | Rewrite still fails at Aux/ISP. |
| `helper_enum_indexed_array_struct_return` | `helper_int_indexed_array_scalar_return` | Rewrite still fails at Aux/ISP. |
| `helper_stack_pointer` | `helper_stack_pointer_return_value_rewrite` | Rewrite passes end to end. |
| `contract_logic_function_helper` | `contract_logic_inline_rewrite` | Rewrite passes end to end. |
| `contract_behavior_helper` | `contract_behavior_plain_ensures_rewrite` | Rewrite passes end to end. |
| `contract_predicate_helper` | `contract_predicate_inline_rewrite` | Rewrite passes end to end. |
| `helper_int_indexed_array_scalar_return` | `helper_int_indexed_scalar_array_return` | Rewrite reaches WP but leaves one goal unproved. |
| `helper_int_indexed_array_scalar_return` | `helper_fixed_index_array_struct_scalar_return` | Rewrite reaches WP but leaves one goal unproved. |
| `helper_fixed_index_array_struct_scalar_return` | `helper_single_global_struct_scalar_return` | Rewrite reaches WP but leaves two goals unproved. |

## Machine Evidence

- `autodeduct-support-results/academic-functional-v3.json`
- `autodeduct-support-results/academic-rte-v3.json`

The JSON files contain per-case details, source hashes, backend status, first failed component, helper-contract counts, and WP goals.
