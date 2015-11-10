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
#
# Last modified: 16 July 2014


# Utility function to write to stderr
echoerr() { echo "$@" 1>&2; }

# Utility function to exit if last command exited non-zero.
ensure() {
  if [[ $? -ne 0 ]] ; then
    echoerr "Could not execute task: $1"
    echoerr "Exiting..."
    exit 1
  fi
}


# This part is a bit tricky. In terms of getting the correct directories to
# work with. This makes the assumption that the alters sit in the root of the
# directory. This may not always be the case, but we can't reliably call `pwd`
# from this context. Sometimes git (seemingly) changes up the root directory
# of where the hooks are called from. Because of this we have to be limited
# to this assumption.
#
# If you need to change this, simply edit ORIG_DIR below

HOOK_DIR="$( cd "$(dirname "$0")" ; pwd -P  )"
ORIG_DIR="$HOOK_DIR/../.."
cd $ORIG_DIR

STAGED_FILES=$(cd $ORIG_DIR && git diff --cached --name-only --relative --diff-filter=ACMR)

STATIC_ALTER_DIR=$(/usr/bin/env python2.7 -c "import json; print json.loads(open('config.json').read())['static_alter_dir']")

if [[ $? -ne 0 ]]
then
  echoerr 'No static_alter_dir property found in config.json, but is required.'
  exit 1
fi

# Remove the .sql files in the static alter directory from the diff output
STAGED_FILES_SQL_ONLY=$(echo "$STAGED_FILES" | grep -v "$STATIC_ALTER_DIR" | grep -E '\.sql')
SEEN=()

for f in $STAGED_FILES_SQL_ONLY
do
  NODE=$(grep -oE '^[0-9]+' <(echo $(basename $f)))
  if [[ $? -ne 0 ]]
  then
    echo "Skipping invalid filename: $(basename $f)" 1>&2
    continue
  fi

  SKIP=0
  for var in "${SEEN[@]}"
  do
    if [[ "${var}" == "$NODE" ]]
    then
      SKIP=1
    fi
  done

  if [[ $SKIP -eq 1 ]]
  then
    continue
  fi


  SEEN+=($NODE)

  UP_RESULT=$(schema gen-sql -q -w $NODE)
  ensure "Generate UP alter for $NODE"

  DOWN_RESULT=$(schema gen-sql -q -w -d $NODE)
  ensure "Generate DOWN alter for $NODE"

  # Add the up and down files to git
  ADD_UP=$(cd $ORIG_DIR && git add "$UP_RESULT")
  ensure "Add $UP_RESULT to git"

  ADD_DOWN=$(cd $ORIG_DIR && git add "$DOWN_RESULT")
  ensure "Add $DOWN_RESULT to git"

  echo "Added file to commit (up):   $UP_RESULT"
  echo "Added file to commit (down): $DOWN_RESULT"
done
