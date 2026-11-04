#!/bin/bash
# Rebuild the submitted solver, evaluate the hidden instances, and write
# the validated per-instance results for the external metric engine.
set -e
mkdir -p /logs/verifier
python3 /tests/checker.py
