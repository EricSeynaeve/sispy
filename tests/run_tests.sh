#! /bin/bash

TEST_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
SCRIPT_DIR=$(realpath "$TEST_DIR/../src")
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

func=''
files="$TEST_DIR/sispy_lib.py"

py.test --cov-report term-missing --cov "$SCRIPT_DIR" "$files" "$@"
