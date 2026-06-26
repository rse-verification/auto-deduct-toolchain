# Missing Helper Contract Case Study

This small example is intentionally incomplete from a modular verification
point of view. The entry point `main` has an ACSL contract, but it calls
`deposit_one` from `account.c`, and that helper has no ACSL contract.

The contract assistant should report `deposit_one` as a missing helper
contract.

Run the pre-check from the repository root:

```shell
autodeduct-contract-assistant examples/contract-assistant/missing-helper-contract
```

Or run it through Docker:

```shell
docker run -it --rm \
  -v "$PWD":/work \
  -w /work \
  auto-deduct \
  /usr/bin/bash -l -c 'autodeduct-contract-assistant examples/contract-assistant/missing-helper-contract'
```

Run the browser GUI against this example:

```shell
scripts/autodeduct-contract-assistant-gui-docker \
  examples/contract-assistant/missing-helper-contract
```

Then open `http://127.0.0.1:8765` and use:

```text
Project path in container: /project
```

`Run WP` is expected to struggle with the full postcondition for `main`
because the helper does not provide a contract describing how it changes
`account->balance`.

`Run Eva` may still finish cleanly because Eva can analyze the helper body
directly in this small example. The missing-contract problem is mainly visible
for modular proof with WP: callers need a callee contract such as `assigns` and
`ensures` clauses to reason about the call.
