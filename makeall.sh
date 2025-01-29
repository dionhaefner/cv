#!/bin/bash

set -e

for f in config-*.yaml; do
    # cut off the .yaml extension and config- prefix
    outname=$(basename $f .yaml | cut -c 8-)
    python generate.py $f -o generated/$outname.pdf
done