# AutoDeduct Microtest Status

Status date: 2026-08-31

## How to read this report

The AutoDeduct microtest corpus used by the assessment is on the separate
`autodeduct-support-microtests` branch under `autodeduct-support/micro-tests`.
The final `auto-deduct` branch now copies twelve public assessment sources into
`tests/cases/` and runs them as categorized Docker regressions: six complete
proofs, one warning followed by a complete proof, three safe functional
boundaries, and two incomplete WP cases. The remaining assessment rows are
still historical evidence until they receive their own current expected-outcome
tests.

This report uses five states:

| State | Meaning |
| --- | --- |
| Confirmed component support | The relevant current component was rebuilt and its focused regression test passed. |
| Confirmed end to end | The original assessment source completed parse, inference, ISP/Eva, reachable-contract checking, and WP. |
| Partial pipeline support | Translation and contract checking completed, but final WP did not prove every goal. |
| Historical pass | The assessment PDF reported a complete successful chain, but the test has not yet been rerun against the final image. |
| Safe limitation | The tool reports a clear limitation rather than claiming a complete inferred contract. |
| Open or unverified | The case is not fixed end to end, or current evidence is insufficient to claim that it is fixed. |

## Versions checked

| Component | Revision checked | Result |
| --- | --- | --- |
| AutoDeduct | `auto-deduct` at `a29b9fa` | The mounted V1 CLI ran the original assessment sources. |
| TriCera | upstream master `96042c2427428907e2d82914b2651a470a80a6f1` | Used by the mounted candidate run. |
| Saida base image | `8634950e174995e59412b1f19b6200a00f74fd1d` | Base installed in `auto-deduct:saida-logic-check`. |
| Saida candidate stack | `870a275` on `45f9a35`, `30839dc`, and `97c6662` | Mounted, built, and installed inside the verification container before each candidate run. |
| ISP | master `a538c4e1ec5014fe45dd6e898c0aa5b4be739efa` | Used by the mounted candidate run. |

The mounted candidate run proves that these component revisions are compatible
for the listed end-to-end cases. It does not by itself prove every microtest.

## Fresh pipeline evidence

The included public ASE example was run with the current CLI mounted into the
existing `auto-deduct:tricera-master-96042` image:

1. Frama-C parsing passed.
2. Saida/TriCera inference passed. The earlier TriCera preprocessor-fallback
   failure no longer occurred after updating to `96042c2`.
3. ISP/Eva reported `ISP-W002`, which says that some unreachable statements
   did not receive propagated auxiliary annotations.
4. ISP's reachable-contract check passed with no missing contracts.
5. WP passed.

`ISP-W002` is now a visible non-blocking warning: AutoDeduct continues to the
reachable-contract check and WP. A complete WP proof with no missing reachable
contracts is still required for a successful result. This avoids discarding a
valid proof merely because an optional auxiliary annotation was not generated.

### Native ACSL contract recheck with the Saida candidate stack

The original, unchanged assessment sources on
`autodeduct-support-microtests` were run through the mounted AutoDeduct V1 CLI.
For every run, the candidate Saida worktree was built and installed inside the
container before invoking `autodeduct`, so the full path was exercised:
Saida/TriCera -> ISP/Eva -> reachable-contract check -> WP.

| Original source | Observed outcome | Interpretation |
| --- | --- | --- |
| `contract_predicate_helper.c` | Passed end to end; no missing reachable contracts; WP passed. | The restricted pure-predicate implementation fixes this native predicate case. `ISP-W001` and the preserved-`assigns` warning remain visible, but WP closes the proof. |
| `contract_behavior_helper.c` | Passed end to end; no missing reachable contracts; WP passed. | Native named behavior `assumes` and `ensures` are preserved through the complete pipeline. |
| `contract_logic_function_helper.c` | Saida/TriCera, ISP/Eva, and reachable-contract check passed; WP proved `17 / 18`. | The term-valued logic function is translated successfully. The remaining `typed_entry_requires` goal timed out with default Alt-Ergo, Alt-Ergo at 30 seconds, and Z3, so this is not a confirmed full proof yet. |
| `contract_old_logic_alias_reproducer.c` | Saida stops with `[SAIDA-E001]` before TriCera. | Correct safe limitation: global ACSL logic aliases with formal state labels are outside the supported reducer subset. |
| `contract_old_logic_alias_inline_rewrite.c` | Saida stops with the same `[SAIDA-E001]`. | Inlining the struct-valued alias alone does not help because `rememberedAlias` remains a global ACSL logic alias. This is not the same construct as a local `\let` alias. |

## Microtest status by pattern

| Microtest or pattern | Current status | Explanation |
| --- | --- | --- |
| `supported/int_if_helper.c` | Confirmed end to end | Current V1 image passes the unchanged source. |
| Basic struct field helper | Confirmed end to end | Current V1 image passes `helper_struct_basic.c`. |
| Enum and switch helper | Confirmed end to end with warning | Current V1 image passes `helper_enum_switch_basic.c` with `-lib-entry`; ISP-W002 remains visible but WP is complete. |
| Side effect with `assigns` and `\old` | Confirmed end to end | Current V1 image passes `helper_assigns_old_basic.c` with `-lib-entry`. |
| Two-level call chain | Confirmed end to end | Current V1 image passes `helper_two_level_call_chain.c` with `-lib-entry`. |
| Same helper in two call contexts | Confirmed end to end | Current V1 image passes `helper_multiple_call_contexts.c`. |
| Whole-struct return | Confirmed end to end | Current V1 image passes `helper_struct_return_whole.c` with `-lib-entry`. |
| Scalar return rewrite | Historical pass | The PDF reported complete verification after the documented source-level rewrite. |
| Enum-indexed array, whole-struct return | Confirmed component support | TriCera master has a passing `enum-indexed-struct.c` regression and ISP master has enum-indexed struct ptests. The exact AutoDeduct microtest has not yet been rerun end to end. |
| Enum-indexed scalar struct field | Confirmed component support with a qualification | TriCera default reconstruction proves safety but can infer only the input restriction. With `-solutionReconstruction:wp`, it infers `records[1].level == \result`. AutoDeduct does not yet select this option. |
| Fixed integer-indexed struct field | Open or unverified | ISP supports selected bounded index paths, but this exact end-to-end microtest has not been rerun with current TriCera. |
| Integer-indexed array of structs, whole return | Open or unverified | The PDF identified ISP as the previous boundary. Current ISP preserves basic index identity but does not prove full general aggregate support. |
| Dynamic scalar-array read | Open or unverified | The PDF left one WP goal unresolved. No fresh complete run exists. |
| Fixed array-of-struct scalar read | Open or unverified | The PDF left one WP goal unresolved. No fresh complete run exists. |
| Single global struct scalar read | Open or unverified | The PDF left two WP goals unresolved. No fresh complete run exists. |
| Dynamic global-array update | Open or unverified | The PDF left two WP goals unresolved. A fixed-index rewrite is evidence about a changed input, not a general tool fix. |
| Valid pointer store | Open | The experimental TriCera fork branch is not in upstream master and has not been integrated into AutoDeduct. |
| Entry local stack pointer | Open | A rewrite exists in the assessment corpus, but the original interface shape has not been freshly verified end to end. |
| ACSL logic function | Partial pipeline support | The original `contract_logic_function_helper.c` now passes Saida/TriCera, ISP/Eva, and the reachable-contract check with no missing contracts. WP proves `17 / 18`; the remaining `typed_entry_requires` goal also timed out with Alt-Ergo at 30 seconds and with Z3. |
| ACSL behavior contract | Confirmed end to end | The unchanged `contract_behavior_helper.c` passes the full pipeline. The new Saida behavior-aware processing preserves native behavior `assumes` and `ensures`; no plain-ensures rewrite is required. |
| ACSL predicate | Confirmed end to end | The unchanged `contract_predicate_helper.c` passes the full pipeline. The new Saida typed-AST predicate expansion handles this pure predicate definition without requiring an inline rewrite. |
| ACSL global logic alias under `\old` | Safe limitation | Both original alias sources stop before TriCera with `[SAIDA-E001]` rather than being unsafely reduced. The separate local `\let` alias fix does not cover global ACSL logic declarations with state labels. |
| Persistent local static state | Confirmed incomplete-WP boundary | Current V1 regression reports the missing `next_count` contract and incomplete WP proof. Model the state explicitly in a reviewed contract. |
| Floating-point arithmetic | Confirmed safe functional boundary | Current V1 regression reports that TriCera does not support `float` and rejects the fallback. |
| Pointer arithmetic | Confirmed safe functional boundary | Current V1 regression stops at TriCera's functional-input syntax boundary. |
| Nested pointer store | Confirmed safe functional boundary | Current V1 regression stops at TriCera's functional-input syntax boundary; V1 does not infer the required multi-level validity, aliasing, and frame model. |
| Loop without an invariant | Confirmed incomplete-WP boundary | Current V1 regression reaches WP but leaves loop-related obligations unresolved. Add reviewed loop annotations. |
| Missing forward declaration | Open or unverified | This is an input/preprocessing configuration issue. The final CLI must be rerun on the case with the required declarations and include options. |

## ISP-specific coverage

ISP master has focused regression tests for the parts it owns:

| ISP tests | Meaning |
| --- | --- |
| `isp_040` and `isp_041` | Conditional and repeated pointer mutation annotations, including the original CDL-2651 area. |
| `isp_045`, `isp_047`, and `isp_048` | Enum-indexed structs and direct constant/enum-indexed struct fields. |
| `isp_046` | Nested array/struct access is reported as an explicit limitation. |
| `isp_049`, `isp_050`, and `isp_051` | Bounded expansion, too-wide expansion, and unbounded-index handling. |

Three tested but unmerged ISP branches add small improvements:

1. `cdl-2651-isp-pure-logic-validation`: preserve defined ACSL logic and
   predicate bodies without a false global-annotation warning.
2. `cdl-2651-isp-index-expansion-boundary-tests`: cover signed intervals and
   declared-array-extent boundary cases.
3. `cdl-2651-isp-diagnostics-docs`: clarify the meaning of standalone ISP
   warnings versus AutoDeduct's fail-closed policy.

They should be rebased onto ISP master before merge. They improve diagnosis and
boundary handling; none makes the unsupported functional cases above fully
supported.

## Recommended next step

The twelve categorized public cases are now copied into the final AutoDeduct
repository as Docker integration regressions. Add the three rerun native ACSL
sources with their observed outcomes: complete success for behavior and
predicate definitions, and an expected incomplete WP result for the logic
function case. Expand the suite with the remaining public assessment corpus,
with one expected outcome per test:

* complete success with proof-goal count;
* expected safe limitation and diagnostic code; or
* known open case.

That will turn the historical PDF into repeatable release evidence and prevent
a rewrite-based workaround from being mistaken for a general capability.
