#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
rm instance/quad-test.db
source .venv/bin/activate
pip install -e .
python -m pytest