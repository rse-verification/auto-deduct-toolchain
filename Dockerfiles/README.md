# AutoDeduct
This Docker image is produced as an artifact for the paper  'AutoDeduct:
 Automated Deductive Verification', submitted to the tool demonstrations track
 of TACAS 2025. It contains the AutoDeduct toolchain for automated deductive
 verification of C code with Frama-C using contrace inference.

# Smokephase / quickguide
The docker image has been created and tested on Ubuntu 22.04 running in
Virtualbox on a Windows 10 host.

To load and then run the docker file, run:
```bash
  docker load --input auto-deduct.tar
  docker run -it auto-deduct
```

For the smokephase, we recommend trying running autodeduct on the two programs
included in the paper, with the following commands:
```bash
  ./autodeduct -lib-entry ~/repos/auto-deduct-examples/tacas-2025/stee.c
  ./autodeduct -lib-entry ~/repos/auto-deduct-examples/tacas-2025/saturate.c
```
The total time for inferring contracts and verifying both programs should be less
than one minute on a standard laptop.
The output should show that the program is verified by the WP plugin of Frama-C.
The final annotated file is saved as ~/repos/auto-deduct-examples/tacas-2025/out.c

# About the toolchain
Autodeduct takes as input a C-file, where the entry-point is annotated with an
ACSL contract, and attempts to verify it using the WP. Before verifying with WP,
it first infers contracts, using two separate Frama-C plugins. First, it runs
the plugin for 'functional inference', then the plugin for 'auxiliary inference'.
If the inference steps succeeds, this produces a fully annotated version of the
program, where all functions now are equipped with a function contract.
Lastly, autodeduct, calls the WP plugin to verify (1) that each function
satisfies its inferred contract and (2) that the entry-point satisfies its
contract (for which WP will make use of the inferred contracts).

Aside from the final output file (see smokephase), the intermediate file produced
by the functional inference part may also be of interest, it will be stored in:
~/repos/auto-deduct-examples/tacas-2025/tmp_inferred_source_merged.c


# Running AutoDeduct
  To run the contract inference and and verification using autodeduct, we
  provide the script 'autodeduct'.
```bash
  ./autodeduct [OPTIONS] <file>

    Options

        -func: Run the functional annotations inference with Saida.
        -aux: Run the auxiliary annotations inference with ISP.
        -wp: Run the WP verification.
        -lib-entry: Include the -lib-entry flag in all Frama-C commands.
        -main <function_name>: Specify the main entry point for the analysis.
         Defaults to "main" if not provided.

    Arguments

        <file>: The name of the C source file to infer contracts for and verify using WP.

    Behavior

        Default Mode: If no options (-func, -aux, -wp) are provided, the script runs all three commands.
        Custom Entry Point: The -main option allows you to specify the function name that Frama-C will use as the entry point. If this option is omitted, the default function "main" is used.
        Lib-entry mode: This causes the analysis to treat all global variables
         as non-deterministically initialised. If omitted, standard C semantics
         of global variable initialisation is used (e.g., ints are initialised to 0)
        Directory Change: The script automatically changes to the directory containing the specified file before running any commands.
```

# Artifact Organisation
The organisation of the software and examples in the Docker image is as follows
         * ~/repos/saida: Contains the Frama-C plugin responsible for the
          'functional contract inference'
         * ~/repos/interface-specification-propagator: contains the software
          responsible for the 'auxiliary contract inference'
         * ~/repos/tricera: contains the TriCera tool that serves as the backend
           for the functional contract inference.
         * ~/repos/autodeduct-examples/tacas
           Contains the two example files from the paper

# Reuse / Repurpose
To repurpose the software, we have several entry points.

To extend the functional inference, the starting point would be the file
~/repos/saida/src/main.ml.

The back-end for the contract inference, TriCera, can also be extended, with the
recommended starting point being the file
~/repose/tricera/src/tricera/concurrency/CCReader.scala.

To repurpose the auxiliary inference part, the recommended starting point would
be the file
~/repos/interface-specification-propagator/blob/master/src/isp_visitor.ml

To change the usage of the tool-chain, and how to verify with WP, the script
~/autodeduct can be modified.
