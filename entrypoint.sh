#!/bin/bash

set -e

envsubst < "/schema-tool/config.tpl" > "/schemas/config.json"

wait-for-it $DB_HOST:$DB_PORT -t 0 -- /schema-tool/schema "$@"
