#!/usr/bin/env bash
python app_entry_rca.py --dut "$1" --ref "$2" --out "${3:-app_entry_rca_out}" --include-better-final
