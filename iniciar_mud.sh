#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")"
./venv/bin/python3 main.pyw
