# Initial AutoDeduct C/ACSL Support Probe Result Summary

This file summarizes the first observed behavior of the public-safe synthetic support probes.

The results were obtained using an AutoDeduct Docker environment with the split pipeline:

    Frama-C parse
    Saida functional inference
    ISP auxiliary inference
    WP verification

## Supported End-To-End Probes

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

## Expected Boundary Probes

    micro_float_arithmetic
      Observed boundary: WP did not prove all goals
      WP goals: 3/6

    micro_pointer_arithmetic
      Observed boundary: auxiliary inference stage

    micro_local_static
      Observed result: unexpected pass
      WP goals: 10/10
      Note: this simple test is not sufficient to claim general local-static support.

    micro_local_static_helper_persistence
      Observed boundary: WP did not prove all goals
      WP goals: 30/35
      Note: this stronger probe exercises persistent local static state across multiple helper calls.

    micro_nested_pointer
      Observed boundary: WP did not prove all goals
      WP goals: 6/8

    micro_acsl_logic_function
      Observed boundary: WP did not prove all goals
      WP goals: 6/11

    micro_loop_without_invariant
      Observed boundary: WP did not prove all goals
      WP goals: 2/8

## Interpretation

These probes are small feature checks. They are not intended to prove complete support for all variants of a C or ACSL feature. They provide reproducible examples for support exploration and regression testing.

## Additional Public Support Probes

The following additional public-safe micro-tests were added after the initial set:

    micro_valid_pointer_struct
      Result: supported_end_to_end
      WP goals: 12/12

    micro_enum_switch_basic
      Result: supported_end_to_end
      WP goals: 17/17

    micro_behavior_basic
      Result: supported_end_to_end
      WP goals: 12/12

    micro_array_struct_field_boundary
      Result: supported_end_to_end
      WP goals: 14/14

    micro_array_struct_read_helper_isp_crash
      Observed boundary: auxiliary inference stage

These results show that simple pointer-to-struct access, enum/switch control flow, simple ACSL behaviors, and simple array-of-struct field access can pass in the tested AutoDeduct pipeline.

A stronger array-of-struct helper-return pattern is being kept as a support-boundary probe, because it is closer to an observed auxiliary-inference failure pattern.
