#!/usr/bin/env bash

# Creating a coverage report for multiple packages while using the profile
# flag is not allowed. This script allows us to get around this.

set -e
echo "" > coverage.txt

for d in $(go list ./... | grep -v vendor); do
    go test -race -coverprofile=profile.out -covermode=atomic $d
    if [ -f profile.out ]; then
        cat profile.out >> coverage.txt
        rm profile.out
    fi
done
