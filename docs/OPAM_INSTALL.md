# OPAM installation

This is the first reproducible OPAM installation path for AutoDeduct. It does
not change the existing Docker installation.

## What is managed by OPAM

The installer creates a private OPAM root and the named switch
`autodeduct-31`. The switch contains:

- OCaml 4.14.2;
- Frama-C 31.0;
- Saida from tag `v0.5.0` and its recorded commit;
- ISP from tag `v0.3.1` and its recorded commit;
- Why3 1.8.2;
- Alt-Ergo Free 2.4.3.

Alt-Ergo 2.4.3-free is installed and listed by Why3, but Why3 reports its
version as unrecognized. CVC4 1.8 and Z3 4.8.12 are recognized by Why3.

Saida and ISP are installed from their upstream OPAM metadata. Their complete
OPAM files are not copied into this repository.

OPAM is configured with the official archive mirror
`https://opam.ocaml.org/cache`. This is a preferred archive source, not a
replacement for package source URLs. If an archive is not present in the
mirror, OPAM may fall back to the original upstream URL.

TriCera is not an OPAM package. The installer checks out its exact Git commit,
builds it with SBT 1.9.8, and keeps its source and build files under the
managed prefix.

## What is outside OPAM

The installer checks or installs these system components on Ubuntu 24.04:

- Java 21;
- Z3 and CVC4;
- C compiler and build tools;
- GTK, Cairo, GMP, expat, Graphviz, source-view, zlib, and related development
  libraries;
- Git, curl, OPAM, Python, and the other packages listed in the installer.

The installer does not install a system OCaml compiler. OCaml comes from the
private OPAM switch.

The internal certificate used by the existing Dockerfile is never downloaded,
installed, or copied by this installer.

## Supported platforms

Version 1 supports:

- Ubuntu 24.04;
- Ubuntu 24.04 running under WSL2.

Native Windows and native macOS are not supported by this installer.

Keep the managed prefix in the Linux filesystem when using WSL2. A path under
`/mnt/c` can make OCaml and Scala builds much slower.

## Prerequisites

You need:

- Bash;
- network access to the public Git repositories and package archives;
- OPAM 2.1 or later, unless using `--install-system-deps`;
- sudo only when using `--install-system-deps`;
- enough disk space for an OCaml switch and the TriCera build.

The default prefix is `$HOME/.local/share/autodeduct`. The default switch is
`autodeduct-31`.

## One-command installation

From the repository root:

```shell
bash scripts/install-with-opam.sh --install-system-deps --yes
```

The installer writes the activation file, manifest, and OPAM package list
under the prefix.

## Activation

```shell
source "$HOME/.local/share/autodeduct/env.sh"
```

This changes only the current shell. The installer does not edit `.profile`,
`.bashrc`, or another shell startup file.

You can use another switch or prefix:

```shell
bash scripts/install-with-opam.sh \
  --switch autodeduct-31 \
  --prefix "$HOME/.local/share/autodeduct"
```

## Checks

Run the quick check:

```shell
bash scripts/check-opam-installation.sh --quick
```

Run the full paper-model smoke test:

```shell
bash scripts/check-opam-installation.sh --full
```

The full check uses the pinned ASE-2024 AutoDeduct paper artifact from
`auto-deduct-examples/ase-2024/stee.c`. The default profile is `paper`. It
checks Frama-C parsing, Saida inference, retained TriCera output, inferred
helper contracts, generated-source parsing, ISP output, and WP proof results.
It requires a nonzero WP goal total and requires every goal to be proved.

The strict library-entry profile is separate:

```shell
AUTODEDUCT_SMOKE_PROFILE=library-entry \
  bash scripts/check-opam-installation.sh --full
```

The acceptance test uses the positive paper profile by default. The profile is
printed by the checker. The strict `library-entry` profile is not the
installation gate. The mandatory paper smoke test proves exactly 236/236 WP
goals.

The GitHub Actions release gate runs the shell checks and all five checker
self-tests before building `OpamInstallTestDockerfile` without cache. The test
image runs quick validation, the full paper check, a second installation, and
a final quick check. Build and runtime logs are retained only when a step
fails.

## Proxy use

Standard `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` variables are preserved.
For the Java/SBT part, a proxy can also be supplied without putting it in the
environment:

```shell
bash scripts/install-with-opam.sh \
  --proxy-host proxy.example.org \
  --proxy-port 8080 \
  --install-system-deps --yes
```

Proxy values and credentials are not printed and are not written to the
manifest.

## Dry run and update behavior

Inspect the plan without changing files:

```shell
bash scripts/install-with-opam.sh --dry-run
```

The dry run is read-only. A real installation still requires Ubuntu 24.04.

The installer uses the versions in `opam/versions.env`. It does not update a
moving branch. Saida, ISP, TriCera, the examples repository, and the OPAM
repository are all resolved to fixed commits. Re-running the installer reuses
matching managed checkouts and the named switch. A conflicting checkout or
switch fails with an actionable message.

To update a version, change the version file deliberately, update its commit,
run the metadata check, and run the installer again. The installer does not
remove old files outside its managed prefix.

## Cleanup

The installer keeps all new source, build, OPAM, and command files under the
prefix. To remove this installation, remove that exact prefix after checking
that it is the intended directory. The installer never removes a user
directory or an independent TriCera checkout.

## Known limitations

- The system package versions depend on the Ubuntu 24.04 archive available to
  the host. The manifest records the installed package versions.
- TriCera downloads its Scala dependencies and its prebuilt `tri-pp` during
  the build.
- The current contract assistant behavior is unchanged. The full installer
  smoke test uses ISP's documented `-isp-print-file` source transformation.
- Case-study sources and the existing AutoDeduct examples are not modified.
- The installer does not claim native Windows or macOS support.

## Difference from the Docker installation

The existing Dockerfile remains unchanged. It installs tools in a container,
uses the container user's default OPAM state, and also installs GUI themes and
the existing helper commands.

The OPAM installer uses a user-owned prefix, a private named OPAM switch,
explicit Git commits, an activation file, and a provenance manifest. It does
not install the Dockerfile's internal certificate and does not change shell
startup files.
