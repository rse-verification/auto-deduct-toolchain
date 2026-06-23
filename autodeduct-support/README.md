# AutoDeduct C/ACSL Micro Support Tests

This directory contains public-safe synthetic C/ACSL micro-tests for exploring support boundaries of the AutoDeduct toolchain.

The tests are intentionally small and generic. They do not contain industrial case-study code.

## Purpose

The goal is to record how selected C and ACSL features behave across the AutoDeduct verification pipeline:

    1. Frama-C parsing
    2. Saida functional contract inference
    3. ISP auxiliary annotation inference
    4. WP verification

Some tests are expected to pass end-to-end. Other tests are expected support-boundary tests. A failure in an expected support-boundary test is not necessarily a bug; it records where the current pipeline reaches a known or suspected limitation.

## Contents

    autodeduct-support/
      cases.json
      micro-tests/
        supported/
        expected_unsupported/

## Micro-test groups

The `supported` group contains small tests expected to pass through the complete AutoDeduct pipeline:

    int_if_helper.c
    assigns_old.c
    global_array_basic.c
    struct_basic.c

The `expected_unsupported` group contains tests designed to exercise known or suspected support boundaries:

    float_arithmetic.c
    pointer_arithmetic.c
    local_static.c
    local_static_helper_persistence.c
    nested_pointer.c
    acsl_logic_function.c
    loop_without_invariant.c

## Manual pipeline

After entering an AutoDeduct environment, each micro-test can be run manually with the following split pipeline:

    frama-c -saida -main entry -saida-out=tmp_inferred_source_merged.c <test-file.c>
    frama-c -isp -isp-entry-point entry tmp_inferred_source_merged.c -isp-print-file out.c
    frama-c -wp -main entry out.c

The exact result can depend on the versions of AutoDeduct, Saida, ISP, Frama-C, WP, TriCera, and the configured SMT solvers.

## Interpretation

These tests are feature probes. They are not intended to prove complete support for all possible variants of a C or ACSL feature. They provide small reproducible examples for support exploration and regression testing.

## Public micro-test runner

This branch also contains a public-safe micro-test runner:

    autodeduct-support/run_micro_tests.py

It only reads `autodeduct-support/cases.json` and only runs cases whose module is `micro`.

Example commands inside an AutoDeduct environment:

    python3 autodeduct-support/run_micro_tests.py --run-framac
    python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --kind micro_supported --timeout 600
    python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --kind micro_expected_unsupported --timeout 600
