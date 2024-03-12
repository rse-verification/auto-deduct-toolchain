#!/bin/bash

if [[ -z "${TRICERA_PATH}" ]]; then
  echo -e "${RED}Please set enivorment variable TRICERA_PATH before using this script"
fi
echo -e "${GRAY}Running all tests suites"
for d in * ; do
    # echo "$d"
    if [ -f $d/run_tests.sh ]; then
        echo -e "- Running $d test suite"
        cd $d
         ./run_tests.sh
        cd ..
    fi
done