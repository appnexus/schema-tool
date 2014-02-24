#!/usr/bin/env bash

# Just a clean-up task to be run on Jenkins after each api-schemas
# to tell the other build-tasks to re-dump the DB.

echo 'api-schemas' > /tmp/last_build_type
echo 'New Contents of /tmp/last_build_type: '
echo -n '  '
cat /tmp/last_build_type
