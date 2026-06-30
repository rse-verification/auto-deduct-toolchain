# AutoDeduct C/ACSL Support Probes Demo

This demo shows how to run a small public-safe support probe and how to read the result.

## Purpose

The public support probes are small C/ACSL examples. They are not industrial case studies. They are used to check which C and ACSL patterns pass through the AutoDeduct pipeline.

## Run One Supported Probe

**Example:**

```bash
python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --case micro_int_if_helper --timeout 600
```

**Expected meaning:**

* **Frama-C parse:** pass
* **Func / Saida:** pass
* **Aux / ISP:** pass
* **WP:** pass
* **Conclusion:** `supported_end_to_end`

## Run One Expected-Boundary Probe

**Example:**

```bash
python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --case micro_pointer_arithmetic --timeout 600
```

**Expected meaning:**

* The case is expected to expose a support boundary.
* A failure in the intended phase is useful evidence, not necessarily a bug in the test.

## Run All Public Probes

```bash
python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --timeout 600
```

## Result Location

Results are written under:
```text
autodeduct-support-results/public-micro/
```

The main summary is:
```text
autodeduct-support-results/public-micro/summary.md
```

## How to Interpret Conclusions

| Conclusion | Meaning |
| :--- | :--- |
| `supported_end_to_end` | Parse, Saida, ISP, and WP all pass. |
| `failed_at_aux` | The auxiliary inference phase fails. |
| `failed_at_wp` | WP runs but does not prove all goals. |
| `expected_unsupported` | The test exposes an expected support boundary. |
| `unexpected_pass` | A boundary probe passed and needs a sharper test. |

## Why This Helps

The probes make support boundaries small and reproducible. They help separate tool limitations from large module-specific problems.
