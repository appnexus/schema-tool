#!/bin/bash

# pre-commit-hook-static-dba-files.sh
#
# Purpose: Automatically commit static up/down files whenever an alter is
# added or updated.
#
# Usage:
#
#   Place this script in the same directory as config.json, and update
#   config.json to have the following value:
#
#   "pre_commit_hook": "pre-commit-hook-static-dba-files.sh"


# Utility function to write to stderr
echoerr() { echo "$@" 1>&2; }

# Utility function to exit if last command exited non-zero.
exit_if_err() {
  if [[ $? -ne 0 ]]
  then
    exit 1
  fi
}


# The schema-tool has to be run from the directory where config.json lives,
# which may not be the same location as where the root of the project.  So, we
# have to move the working directory of the script to the location of
# config.json (which is the same real path as this hook), but before doing so
# save the current working directory to a variable so that Git operations can
# be performed.

ORIG_DIR=$(pwd)
cd "$(dirname $(readlink $0))"

STAGED_FILES=$(cd $ORIG_DIR && git diff --cached --name-only --relative --diff-filter=ACMR)

STATIC_ALTER_DIR=$(python -c "import json; print json.loads(open('config.json').read())['static_alter_dir']")
if [[ $? -ne 0 ]]
then
  echoerr 'No static_alter_dir property found in config.json, but is required.'
  exit 1
fi

# Remove the .sql files in the static alter directory from the diff output
STAGED_FILES_SQL_ONLY=$(echo "$STAGED_FILES" | grep -v "$STATIC_ALTER_DIR" | grep -E '\.sql')

for f in $STAGED_FILES_SQL_ONLY
do
  NODE=$(grep -oE '^[0-9]+' <(echo $(basename $f)))
  exit_if_err

  UP_RESULT=$(schema gen-sql -q -w $NODE)
  exit_if_err

  DOWN_RESULT=$(schema gen-sql -q -w -d $NODE)
  exit_if_err

  # Add the up and down files to git
  ADD_UP=$(cd $ORIG_DIR && git add "*/$UP_RESULT")
  exit_if_err

  ADD_DOWN=$(cd $ORIG_DIR && git add "*/$DOWN_RESULT")
  exit_if_err

  echo "Added file to commit: $UP_RESULT"
  echo "Added file to commit: $DOWN_RESULT"
done
