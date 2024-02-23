# toolchain

This is a project for composing a formal verification toolchain using
TriCera, Frama-C and custom Frama-C plug-ins.

The development environment and toolchain is provided in as a docker
container.

## Building the docker container

In the examples we are using bash, but the syntax should be similar
in your command line shell of choice.

The dockerfile will download things using a java runtime environment
(JRE). JRE needs to know about proxies, so if you are building the
container while behind a proxy please provide the appropriate values
according to the example below. (Also remember that you might have to
set your `HTTP_PROXY` and `HTTPS_PROXY` environment variables.)

Of course you are free to choose any tag you like for your image.

```shell
git clone https://github.com/rse-verification/toolchain.git
cd toolchain/Dockerfiles

# Use the following for normal builds
docker build -t auto-deduct:0.1.0 -t auto-deduct:latest -f DevEnvDockerfile .

# Use the follwing behind a proxy
docker build --build-arg PROXY_HOST=<your.proxy.name> --build-arg PROXY_PORT=<port> -t auto-deduct:0.1.0 -t auto-deduct:latest -f DevEnvDockerfile .
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

* Since the source for the `ISP` (Interface Specification Propagator)
  is private, you will have to clone and build the project yourself.

  ```shell
  cd /home/dev/repos
  git clone https://github.com/rse-verification/interface-specification-propagator.git
  cd interface-specification-propagator
  dune build @install
  dune install
  ```

## Starting the container

Once you have built the container, you can start it

```shell
docker run -it auto-deduct
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

### On Linux

As long as you are running a GUI in your GNU/Linux distribution
chances are very high that you already have a server installed.
(There are two systems for GUIs on GNU/Linux, the X Window System
provided by X.Org Server, and Wayland. If you are running Wayland
chances are pretty high that you have some copatibility solution
installed.) If the Frama-C GUI doesn't work out-of-the-box it is
beyond this README to solve the problem.

### On Mac

To be done.
