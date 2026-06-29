@echo off
python app_entry_rca.py --dut "%~1" --ref "%~2" --out "%~3" --include-better-final
