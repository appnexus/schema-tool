#!/usr/bin/env bash

./schema init
./schema down all --force
./schema up -v && ./schema down all -v
