# auto-deduct-toolchain

This is a project for composing a formal verification toolchain using
TriCera, Frama-C and custom Frama-C plug-ins.

The development environment and toolchain are provided as a Dockerfile
under the GNU GPLv2 license. For full license conditions, please see
the [LICENSE](LICENSE) file

## Designed with VSCode in mind

While not at all necessary for using the image, it is designed with
Visual Studio Code in mind, and more specifically, using it as a container
for [remote development](https://code.visualstudio.com/docs/remote/remote-overview)
in VSCode. An example/template of a
[devcontainer configuration](https://code.visualstudio.com/docs/devcontainers/containers)
can be found in this repository, in `.devcontainer/devcontainer.json`.

Please note that the devcontainer will also mount a docker volume under
`/home/dev/persistent/repos/`. This is intended for persistent storage
between rebuilds of the devcontainer. You can of course use the ordinary
workspace folder provided by the devcontainer, but if you are on Windows
that folder typically resides on a Windows file system drive which will
make file access very slow inside the Linux container. This is very
noticable when compiling e.g. Scala applications.

## Building the docker image

In the examples we are using bash, but the syntax should be similar
in your command line shell of choice.

The dockerfile will download things using a Java runtime environment
(JRE). JRE needs to know about proxies, so if you are building the
container while behind a proxy please provide the appropriate values
according to the example below. (Also remember that you might have to
set your `HTTP_PROXY` and `HTTPS_PROXY` environment variables.)

Of course you are free to choose any tag you like for your image.

```shell
git clone https://github.com/rse-verification/toolchain.git
cd toolchain/Dockerfiles

# Use the following for normal builds
docker build -t auto-deduct:0.1.0 -t auto-deduct:latest -f AutoDeductDockerfile .

# Use the follwing behind a proxy
docker build --build-arg PROXY_HOST=<your.proxy.name> --build-arg PROXY_PORT=<port> -t auto-deduct:0.1.0 -t auto-deduct:latest -f AutoDeductDockerfile .
```

Please note that building the container can take quite a while since
a lot of OCAML modules for Frama-C are built from source during
the container build.

## Container contents

All tools and source code are installed in the container to be used by
the user `dev`. Password setup for this user is also `dev`.

Apart from Scala (used by TriCera) and Frama-C things installed under
`/home/dev/.local/...` there is also

* `/home/dev/repos/tricera` - Source code for
  [TriCera](https://github.com/uuverifiers/tricera) model checker.
  The binaries are built as part of the container build, and symbolic
  links are created in `/home/dev/.local/bin`

* `/home/dev/repos/saida` - Source code for the
  [Saida](https://github.com/rse-verification/saida) Frama-C plugin.
  The plugin is built and installed as an OCAML package as part of
  the container build.

* `/home/dev/repos/interface-specification-propagator` - Source code
  for the the [ISP (Interface Specification Propagator)](https://github.com/rse-verification/interface-specification-propagator) Frama-C plugin.
  The plugin is built and installed as an OCAML package as part of
  the container build.

* `/home/dev/repos/auto-deduct-examples` - Some helper scripts, and
  [a set of examples](https://github.com/rse-verification/auto-deduct-examples)
  on which the toolchain has been tested in practice.

## Starting the container

Once you have built the container, you can start it

```shell
docker run -it auto-deduct
```

## Contract assistant

The image includes an experimental helper for finding C helper functions that
are missing ACSL contracts:

```shell
autodeduct-contract-assistant path/to/file.c
```

You can also pass several files or a directory. Directories are scanned
recursively for `.c` and `.h` files:

```shell
autodeduct-contract-assistant path/to/case-study
```

If you are testing this from the source branch, rebuild the image first so the
new helper scripts are copied into `/home/dev/.local/bin`:

```shell
cd Dockerfiles
docker build -t auto-deduct:latest -f AutoDeductDockerfile .
```

By default, the assistant tries to use the ISP Frama-C plugin to generate the
missing-helper report, then falls back to its built-in source scan if Frama-C,
ISP, or the needed preprocessor setup is not available. The built-in scan is
also used to extract source snippets for the report and LLM prompt. This is a
deterministic pre-check; it does not prove or generate contracts.
When a directory is provided, the assistant builds a lightweight project-level
call graph across the scanned files, so a contracted function in `main.c` can
identify a missing helper contract in another `.c` file.

### Contract assistant architecture

The contract assistant is a thin workflow layer around Frama-C/ISP, the local
source files, and optional LLM draft generation:

```text
Host project folder
  |
  | mounted by scripts/autodeduct-contract-assistant-gui-docker
  v
AutoDeduct Docker container (/project)
  |
  +-- CLI: autodeduct-contract-assistant
  |
  +-- GUI: autodeduct-contract-assistant-gui
        |
        +-- Browse mounted Docker path
        +-- Run missing-helper analysis
        +-- Run Eva / WP
        +-- Generate editable LLM contract draft
```

The missing-helper analysis has two backends:

```text
C source files + headers + Frama-C options
  |
  v
backend=auto
  |
  +-- preferred: Frama-C + ISP
  |       |
  |       +-- ISP writes missing-helper JSON
  |       +-- AutoDeduct maps JSON entries back to source snippets
  |
  +-- fallback: built-in source scan
          |
          +-- Lightweight function and call graph scan
          +-- Used when Frama-C/ISP cannot parse the project yet
```

The LLM step is optional and draft-only:

```text
Missing helper list + source snippets
  |
  v
OpenAI API, if OPENAI_API_KEY is set
  |
  v
Editable ACSL draft JSON in the GUI
  |
  v
Temporary copy of the project, only for Run WP with Draft
  |
  v
Frama-C/WP draft validation
```

The normal `Run Eva` and `Run WP` buttons run Frama-C on the mounted source
files. The `Run WP with Draft` button is different: it inserts the edited draft
contracts into a temporary copy and validates that copy, so the original mounted
source files are not modified by the LLM draft flow.

The backend can be selected explicitly:

```shell
autodeduct-contract-assistant --backend auto path/to/case-study
autodeduct-contract-assistant --backend isp path/to/case-study
autodeduct-contract-assistant --backend source path/to/case-study
```

Use `--backend isp` when you want the command to fail instead of falling back to
the source scan. If the project needs include paths or macros before Frama-C can
parse it, pass the same options that you would pass to Frama-C:

```shell
autodeduct-contract-assistant \
  --frama-c-extra-args '-cpp-extra-args="-D__GNUC__=12 -Ioriginal"' \
  path/to/case-study
```

The ISP backend requires an AutoDeduct image that contains an ISP version
providing `-isp-missing-helper-contracts-json`.

Case-study sources are intentionally kept outside this toolchain repository.
Pass a local case-study path directly to the assistant, or mount that path into
Docker when using the container.

### Step-by-step Docker run

Build the image:

```shell
cd /path/to/auto-deduct-toolchain/Dockerfiles
docker build -t auto-deduct:latest -f AutoDeductDockerfile .
```

Run the CLI against a mounted project:

```shell
docker run -it --rm \
  -v "/path/to/case-study":/project \
  -w /project \
  auto-deduct:latest \
  /usr/bin/bash -l -c 'autodeduct-contract-assistant --backend auto .'
```

To force the precise ISP backend and fail if Frama-C/ISP cannot run:

```shell
docker run -it --rm \
  -v "/path/to/case-study":/project \
  -w /project \
  auto-deduct:latest \
  /usr/bin/bash -l -c 'autodeduct-contract-assistant --backend isp .'
```

To use only the fallback source scanner:

```shell
docker run -it --rm \
  -v "/path/to/case-study":/project \
  -w /project \
  auto-deduct:latest \
  /usr/bin/bash -l -c 'autodeduct-contract-assistant --backend source .'
```

For machine-readable output, use:

```shell
autodeduct-contract-assistant --json path/to/file.c
```

For an LLM-assisted workflow, the first supported step is to generate a prompt:

```shell
autodeduct-contract-assistant --llm-prompt contract-prompt.md path/to/file.c
```

The prompt is intended for draft ACSL suggestions only. Any suggested contract
must still be reviewed by a human and checked with Frama-C/WP/Eva.

### Browser UI

The same pre-check can be run through a small local browser UI. The easiest way
to use it with a real project is the host-side launcher script, which mounts a
local folder into Docker and starts the GUI:

```shell
scripts/autodeduct-contract-assistant-gui-docker /path/to/case-study-gms
```

Then open:

```text
http://localhost:8765
```

In the GUI, use the mounted container path printed by the script:

```text
Project path in container: /project
```

If you mounted a larger folder but only want to run one sub-example, use
`Browse Docker Path` in the GUI. It lists the Docker/container view of the
mounted folder, so you can click from `/project` into the exact subdirectory or
source file you want to analyze.

The GUI has a `Missing-helper backend` selector:

* `Auto`: try ISP/Frama-C first and fall back to the source scan.
* `ISP/Frama-C only`: fail if the ISP JSON report cannot be generated.
* `Source scan only`: use the lightweight source scanner without Frama-C.

If port `8765` is already busy, choose another host port:

```shell
scripts/autodeduct-contract-assistant-gui-docker --port 8781 /path/to/case-study-gms
```

Then open:

```text
http://localhost:8781
```

The page works with project paths that already exist inside the container.
This keeps the browser focused on Docker's view of the mounted source tree,
which is usually what Frama-C needs for larger case studies.

The launcher mounts the selected local project folder as:

```text
/project
```

The GUI also has `Run Eva` and `Run WP` buttons. These run Frama-C on the
selected `.c` files and show the command output. The same `Extra Frama-C
options` field is used by the ISP missing-helper backend, the Eva run, and the
WP run. Header files must be available through the mounted project path or
through include paths passed to Frama-C.

The GUI can optionally call the OpenAI API to draft ACSL contracts for missing
helper functions. The API key is read only from the environment and is not
stored in the repository. This is a runtime setting for the GUI container; it is
not used by `docker build`.

On macOS with `zsh`, provide the key after building the image and before
starting the GUI:

```shell
read -rs "OPENAI_API_KEY?OpenAI API key: "
echo
export OPENAI_API_KEY
export OPENAI_MODEL=gpt-4.1
```

In `bash`, the equivalent prompt is:

```shell
read -rsp "OpenAI API key: " OPENAI_API_KEY
echo
export OPENAI_API_KEY
export OPENAI_MODEL=gpt-4.1
```

Then start the GUI with the launcher as usual. The launcher passes
`OPENAI_API_KEY` and `OPENAI_MODEL` into Docker with environment variables. Use
`Generate Contract Draft` to ask the model for candidate contracts. The draft is
shown as editable JSON; use `Run WP with Draft` to approve it for a verification
attempt. Draft contracts are inserted only into a temporary copy of the mounted
project, so the original source files are not modified.

If a project needs preprocessor flags, add them in the `Extra Frama-C options`
field. For example, if a header expects GCC macros and project-local includes:

```text
-cpp-extra-args="-D__GNUC__=12 -Ioriginal"
```

Missing headers must still be available in the mounted project or through an
include path. If Frama-C reports `fatal error: some_header.h: No such file or
directory`, mount the folder containing that header or add the required include
path through `-cpp-extra-args`.

The launcher is a convenience wrapper around Docker. The equivalent manual
command is:

```shell
docker run -it --rm \
  -p 127.0.0.1:8765:8765 \
  -v "/path/to/case-study-gms":/project \
  -w /project \
  auto-deduct:latest \
  /usr/bin/bash -l -c 'autodeduct-contract-assistant-gui --host 0.0.0.0 --port 8765'
```

## Running the Frama-C GUI

If you want to use the Frama-C GUI, you will need an
[X-window server](https://en.wikipedia.org/wiki/X_Window_System)
running.

### On Windows

For Windows there are at least two X-servers

* [mobaXterm](https://mobaxterm.mobatek.net/)
* [VcXsrv](https://sourceforge.net/projects/vcxsrv/)

Make sure your server is started, then in your auto-deduct container
start the Frama-C GUI from the command line.

```shell
frama-c-gui
```

However, if you use the image as a devcontainer for Visual Studio
Code (VSCode), and run the GUI from a terminal inside VSCode,
VSCode integrates with WSL. WSL already has support for Wayland
and therefore there is no need for an extra X-server.

### On Linux

As long as you are running a GUI in your GNU/Linux distribution
chances are very high that you already have a server installed.
(There are two systems for GUIs on GNU/Linux, the X Window System
provided by X.Org Server, and Wayland. If you are running Wayland
chances are pretty high that you have some compatibility solution
installed.) However, in order use your host's X server, you
need start your container with additional arguments

```shell
docker run -it --env DISPLAY=$DISPLAY --volume /tmp/.X11-unix:/tmp/.X11-unix
```

### On Mac

On macOS, Docker Desktop does not provide an X server. Install
[XQuartz](https://www.xquartz.org/) before running the Frama-C GUI.

1. Install XQuartz, for example with Homebrew:

```shell
brew install --cask xquartz
```

2. Start XQuartz.
3. In XQuartz, open `Settings...` / `Preferences...`, go to the
   `Security` tab, and enable `Allow connections from network clients`.
4. Restart XQuartz after changing that setting.
5. If the setting is not visible in the GUI, enable it from a macOS
   terminal instead:

```shell
defaults write org.xquartz.X11 nolisten_tcp -bool false
osascript -e 'quit app "XQuartz"'
open -a XQuartz
```

6. In a macOS terminal, allow local X11 clients to connect:

```shell
DISPLAY=:0 /opt/X11/bin/xhost + 127.0.0.1
```

Then start the container with the display set to the special Docker
Desktop host name:

```shell
docker run -it --env DISPLAY=host.docker.internal:0 auto-deduct
```

You can check the X11 connection from inside the container before
starting the GUI:

```shell
xdpyinfo -display "$DISPLAY"
```

Inside the container, start the GUI:

```shell
frama-c-gui
```

When you are done, you can revoke the XQuartz access again from the
macOS terminal:

```shell
DISPLAY=:0 /opt/X11/bin/xhost - 127.0.0.1
```

If the GUI does not open, check that XQuartz is still running, that
network clients are enabled in XQuartz, and that the container sees
`DISPLAY=host.docker.internal:0`.
