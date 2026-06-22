# Initial Micro-Test Result Summary

This file summarizes the first observed behavior of the public-safe synthetic micro-tests.

The results were obtained using an AutoDeduct Docker environment with the split pipeline:

    Frama-C parse
    Saida functional inference
    ISP auxiliary inference
    WP verification

## Expected-supported tests

    micro_int_if_helper
      Result: supported_end_to_end
      WP goals: 20/20

    micro_assigns_old
      Result: supported_end_to_end
      WP goals: 11/11

    micro_global_array_basic
      Result: supported_end_to_end
      WP goals: 11/11

    micro_struct_basic
      Result: supported_end_to_end
      WP goals: 16/16

## Expected support-boundary tests

    micro_float_arithmetic
      Observed boundary: WP did not prove all goals
      WP goals: 3/6

    micro_pointer_arithmetic
      Observed boundary: auxiliary inference stage

    micro_nested_pointer
      Observed boundary: WP did not prove all goals
      WP goals: 6/8

    micro_acsl_logic_function
      Observed boundary: WP did not prove all goals
      WP goals: 6/11

    micro_loop_without_invariant
      Observed boundary: WP did not prove all goals
      WP goals: 2/8

    micro_local_static
      Observed result: unexpected pass
      WP goals: 10/10
      Note: this simple test is not sufficient to claim general local-static support.

## Interpretation

These tests are small feature probes. They are not intended to prove complete support for all variants of a C or ACSL feature. They provide reproducible examples for support exploration and regression testing.

## Additional local-static boundary probe

A stronger local-static boundary test was added after the initial run:

    micro_local_static_helper_persistence

This test uses a helper function with persistent local static state and calls it twice from the entry point.

Observed result:

    micro_local_static_helper_persistence
      Result: expected support boundary
      Observed boundary: WP did not prove all goals
      WP goals: 30/35

This result is more useful than the simple `micro_local_static` test, which unexpectedly passed end-to-end.
