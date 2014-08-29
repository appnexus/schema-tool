#!/bin/bash

STDOUT_FILE='/tmp/schema-tool-test-stdout'
STDERR_FILE='/tmp/schema-tool-test-stderr'

# output functions
error() { echo -e "[\033[1;31merror\033[0m]: $1"; }
success() { echo -e "[\033[1;32merror\033[0m]: $1"; }



# main runner code
files=`find . -path "./commands/*" | grep -v '\.swp$'`

for file in $files; do
    python $file 1>$STDOUT_FILE 2>$STDERR_FILE
    ret=$?
    if [ $ret -ne 0 ] ; then
        error "$(basename $file) failed"
        error "STDOUT: $(<$STDOUT_FILE)"
        error "STDERR: $(<$STDERR_FILE)"
        exit $ret
    else
        success "$(basename $file) passed"
    fi
done



