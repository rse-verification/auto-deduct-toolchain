#!/bin/bash

# sh colors
# GREEN='\033[;32m'
# RED='\033[;31m'
# GRAY='\033[;37m'
GREEN='\e[32m'
RED='\e[31m'
YELLOW='\e[1;33m'
GRAY='\e[0;37m'

for d in * ; do
    if [ -f $d/run_test.sh ]; then
        echo -e "- Running $d test"
        cd $d
        ./run_test.sh 2>&1 >/dev/null
        test_status=$?
        cd ..

        case "$test_status" in
            0)
                echo -e "${GREEN}Test succeded ${GRAY}"
                ;;
            1)
                echo -e "${YELLOW}Test succeded, but with Saida error ${GRAY}"
                ;;
            2)
                echo -e "${YELLOW}Test succeded, but with ISP error ${GRAY}"
                ;;
            3)
                echo -e "${YELLOW}Test succeded, but with both ISP and Saida error ${GRAY}"
                ;;
            4)
                echo -e "${RED}Test failed due to verification error ${GRAY}"
                ;;
            5)
                echo -e "${RED}Test failed due to both verification and Saida error ${GRAY}"
                ;;
            6)
                echo -e "${RED}Test failed due to both verification and ISP error ${GRAY}"
                ;;
            7)
                echo -e "${RED}Test failed due to verification, ISP and Saida errors ${GRAY}"
                ;;
            *)
        esac
        # if [ $test_status -ne 0 ]; then
        #     echo -e "${RED}Test failed with status ${test_status} ${GRAY}"
        # else
        #     echo -e "${GREEN}Test succeded ${GRAY}"
        # fi
    fi
done