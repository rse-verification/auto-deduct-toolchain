# AutoDeduct

AutoDeduct V1 packages a command-line formal-verification pipeline for C
programs. The pipeline combines Frama-C with Saida, TriCera, ISP/Eva, and WP.

The V1 release intentionally has no GUI and no LLM contract-generation
assistant. The original C files are never edited by the command. Generated
contracts, auxiliary annotations, logs, and the final JSON report are written
to a separate output directory.

## Pipeline

```text
C source files
      |
      v
Frama-C parse
      |
      v
Saida -> TriCera functional-contract inference
      |
      v
ISP + Eva auxiliary-annotation inference
      |
      v
ISP reachable-contract report
      |
      v
Frama-C WP verification
      |
      v
text summary + report.json
```

Saida is the Frama-C plugin that invokes TriCera to infer functional
contracts for helper functions below a contracted entry point. ISP consumes
that annotated C source and uses Eva-derived states to infer auxiliary ACSL
clauses for WP. ISP also owns the reachable-function analysis: AutoDeduct
passes ISP's `-isp-missing-helper-contracts` options through Frama-C and reads
the resulting `missing-helper-contracts.json`. AutoDeduct does not reimplement
the C parser or call graph, so function reachability and missing-contract
semantics stay aligned with ISP. A missing reachable contract makes the final
pipeline status `failed` even when a later command happens to exit zero.

## Public ASE 2024 example

The repository includes the public steering-system example under
`examples/ase-2024/`. The source is copied from the
[rse-verification/auto-deduct-examples](https://github.com/rse-verification/auto-deduct-examples/tree/main/ase-2024)
repository and retained with its attribution.

The example is associated with the ASE 2024 paper *An Exercise in Mind
Reading: Automatic Contract Inference for Frama-C*:
<https://doi.org/10.1007/978-3-031-55608-1_13>.

`stee.c` models a vehicle steering system. Its ACSL contract is attached to
the entry point `main` and expresses five requirements about primary steering
failure, vehicle movement, secondary steering, and electric-motor activation.
The helper functions are intentionally left without complete contracts so the
toolchain can infer them. See `examples/ase-2024/README.md` for provenance and
the Docker command. No Scania or private case-study files are included.

## Build the Docker image

Build from the repository root. This is important because the Dockerfile
copies the CLI from the top-level `bin/` directory.

```shell
git clone https://github.com/rse-verification/auto-deduct-toolchain.git
cd auto-deduct-toolchain
docker build \
  -t auto-deduct:1.0.0 \
  -t auto-deduct:latest \
  -f Dockerfiles/AutoDeductDockerfile .
```

On Apple Silicon, build and run the image as `linux/amd64` so the TriCera
preprocessing helper runs with its supported architecture:

```shell
docker build --platform linux/amd64 \
  -t auto-deduct:latest \
  -f Dockerfiles/AutoDeductDockerfile .
```

Behind a proxy, add the build arguments used by the image:

```shell
docker build \
  --build-arg PROXY_HOST=<proxy-host> \
  --build-arg PROXY_PORT=<proxy-port> \
  -t auto-deduct:latest \
  -f Dockerfiles/AutoDeductDockerfile .
```

The image contains configured versions of Frama-C, Saida, ISP, and TriCera.
The development branch currently uses ISP `master` because the older
`v0.3.1` tag predates the machine-readable missing-helper report used by this
CLI. Before publishing a V1 image, replace it with a released ISP tag or
commit and update the compatibility tests. The image also contains the SMT
solvers used by WP. The image is optional: the same
`bin/autodeduct` command can run on a host where the matching tools and their
dependencies are already installed.

## Run the CLI in Docker

Mount the directory containing the C project as `/work`. The output directory
is created in that mounted directory, while the input files remain unchanged.

```shell
docker run --rm \
  -v "$PWD":/work \
  -w /work \
  auto-deduct:latest \
  autodeduct path/to/main.c
```

For an Apple Silicon image built with the command above, add
`--platform linux/amd64` to `docker run` as well.

For a project directory, AutoDeduct recursively discovers `.c` translation
units. Header files are not passed as source inputs; provide additional header
directories with `--include`:

```shell
docker run --rm \
  -v "$PWD":/work \
  -w /work \
  auto-deduct:latest \
  autodeduct \
  --include /work/my-project/include \
  --entry-point main \
  --output-dir /work/my-project/autodeduct-output \
  /work/my-project
```

For explicit source files or several translation units:

```shell
docker run --rm \
  -v "$PWD":/work \
  -w /work \
  auto-deduct:latest \
  autodeduct \
  --include /work/include \
  --entry-point main \
  --output-dir /work/autodeduct-output \
  path/to/main.c path/to/helper.c
```

The command accepts C source files and project directories. Directory inputs
are searched recursively for `.c` files; common build, VCS, dependency, and
generated-output directories are skipped. Pass `--include` for header
directories that are not next to the source files.
Preprocessor/compiler flags can be passed with repeated
`--frama-c-option`, for example:

```shell
autodeduct \
  --frama-c-option=-cpp-extra-args=-DPLATFORM_TEST \
  --include include \
  src/main.c src/account.c
```

## CLI options

```text
autodeduct --help
autodeduct --version
autodeduct [options] SOURCE_OR_DIRECTORY [SOURCE_OR_DIRECTORY ...]
```

Useful options are:

* `--entry-point NAME` selects the contracted entry function; default is
  `main`.
* `--output-dir DIRECTORY` stores generated files and logs; default is
  `autodeduct-output`.
* `--include DIRECTORY` adds a C include directory and can be repeated.
* `--frama-c-option OPTION` forwards an option to the Frama-C stages and can
  be repeated.
* `--wp-option OPTION` forwards an option only to WP and can be repeated.
* `--wp-rte` adds WP runtime-error goals.
* `--timeout SECONDS` limits each external analysis stage; default is 300.
* `--json` prints the final machine-readable report to standard output.

The output directory contains `inferred.c` from Saida, `out.c` from ISP,
`contracts.json` (AutoDeduct's normalized summary),
`missing-helper-contracts.json` from ISP, one stdout and stderr log per stage,
and `report.json`. The ISP missing-helper report is required; if ISP does not
write valid JSON with a supported missing-contract field, the pipeline fails
at `contract-check` with an actionable error.

## Result and failure handling

The CLI returns exit code `0` only when parsing, Saida/TriCera, ISP/Eva, WP,
and the reachable-contract check all pass. It returns exit code `1` for
input, environment, timeout, parsing, inference, annotation, contract, or WP
failures.

The human report names the failing stage. `--json` is intended for CI and
skill integrations; it contains the same stage status, command, return code,
log paths, artifacts, contract reachability, and error information.

The command does not treat a process exit code as proof that the complete
contract was verified. It also checks that Saida and ISP produced their
expected generated files and that ISP reports contracts for all functions it
considers reachable from the entry point.

## V1 scope and limitations

V1 is a deterministic CLI pipeline. It does not include the former GUI or
LLM assistant, and it does not modify source files or automatically accept
generated contracts into the original project.

The underlying Saida and ISP plugins are experimental and retain their own
limitations. In particular, the current toolchain should not be treated as a
general solution for floating-point programs, unsupported pointer/array
patterns, local static state, or loops without suitable invariants. A
successful command is evidence for the selected input and tool versions, not
a universal proof that every possible execution is safe.

## Repository layout

* `bin/autodeduct` is the small executable entry point.
* `bin/autodeduct_pipeline.py` contains argument parsing, stage execution,
  ISP report handling, and report generation. It deliberately does not
  maintain a second C parser or call graph.
* `Dockerfiles/AutoDeductDockerfile` builds the Frama-C/Saida/TriCera/ISP
  environment and installs the CLI as `autodeduct`.
* `examples/ase-2024/` contains the attributed public steering-system example
  and its entry-point contract.
* `tests/test_autodeduct.py` tests ISP report parsing and orchestration behavior
  without requiring Docker or the analysis tools.

## License

The toolchain and command-line additions are provided under the GNU GPLv2.
See [LICENSE](LICENSE) for the full license text.
