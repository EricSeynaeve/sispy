#! /bin/bash

# Wrapper script to start up all the test suits.
# Copyright (C) 2016  Eric Seynaeve
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
