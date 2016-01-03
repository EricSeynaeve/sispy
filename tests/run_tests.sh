#! /bin/bash

TEST_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
SCRIPT_DIR=$(realpath "$TEST_DIR/../src")
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

func=''
src_files=( "$SCRIPT_DIR/SisPy/lib.py" )
test_files=( "$TEST_DIR/sispy_lib.py" )

error=0
for file in $src_files
do
	echo "II Checking $file for PEP8 conformity"
	pep8 --ignore E501 "$file" || error=1
done
for file in $test_files
do
	echo "II Checking $file for PEP8 conformity"
	pep8 --ignore E501 "$file" || error=1
	echo "II Running all tests in $file"
	py.test --cov-report term-missing --cov "$SCRIPT_DIR" "$file" "$@" || error=1
done

if (( $error != 0 ))
then
	echo "EE Errors found. See output for more details." 1>&2
fi
exit $error

# vim: set ai :
