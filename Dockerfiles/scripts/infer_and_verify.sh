#!/bin/bash
if [ "$#" -eq  "0" ]
  then
    echo "Usage: Give as argument the name for file to infer contracts for and verify with WP"
else
    echo -e "\n################################################"
    echo "# Inferring functional annotations with Saida #"
    echo -e "###############################################\n"
    frama-c -saida $1
    echo -e "###############################################\n\n"
    echo "#############################################"
    echo "# Inferring auxilliary annotations with ISP #"
    echo -e "#############################################\n"
    frama-c -isp tmp_inferred_source_merged.c -isp-print-file out.c
    echo -e "###############################################\n\n"
    echo -e "##############################################"
    echo "############### Verifying with WP ##############"
    echo -e "##############################################\n"
    frama-c -wp out.c
fi
