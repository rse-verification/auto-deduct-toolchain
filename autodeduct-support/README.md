# AutoDeduct C/ACSL Support Probes

This directory contains public-safe synthetic C/ACSL probes for the AutoDeduct
pipeline. They test small feature patterns, not industrial case studies, and
support claims mean supported only in the tested pattern.

## Canonical public mode

Run public results with `--lib-entry`:

```bash
python3 autodeduct-support/run_micro_tests.py --run-framac --run-split --lib-entry --timeout 600
```

`--lib-entry` matters because these probes use `entry` as a library-style entry
point. Without it, WP may create main-callability obligations that are not the
intended public support question.

## Reading results

- [MICRO_RESULTS.md](../MICRO_RESULTS.md) is the main public result table.
- [PUBLIC_PROBE_DIAGNOSIS.md](PUBLIC_PROBE_DIAGNOSIS.md) explains stale-result findings, probe quality notes, static-use checks, and WP-control caveats.

WP can run successfully as a command and still leave proof goals unproved.
`unexpected_pass` means an expected-unsupported probe passed end to end and is
too weak to show the intended boundary. `wp_control` tests are useful boundary
reproducers, but they are not pure AutoDeduct inference evidence when they
contain manually written helper contracts or auxiliary facts.
