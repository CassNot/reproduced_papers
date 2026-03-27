#!/usr/bin/env bash
set -euo pipefail

#python implementation.py --paper photonic_QGAN --config configs/ideal_selectable.json --mode ideal --ideal-digit 0 --runs 5

python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 0
python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 1
python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 2
python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 3
python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 4
python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 5
python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 6
python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 7
python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 8
python implementation.py --paper photonic_QGAN --config configs/digits_top1.json --mode ideal --ideal-digit 9
