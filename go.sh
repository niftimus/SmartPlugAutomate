#!/bin/bash

eval "$(~/anaconda3/bin/conda shell.bash hook)"
conda activate SmartPlugAutomate
python smartcontrol.py "$@"

