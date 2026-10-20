#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 vikingux and the LANDDY .lnd contributors
"""lnd_check · nombre corto del validador (el que usa la spec). Ejecuta lnd_check_v12.py con los mismos argumentos."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lnd_check_v12

if __name__ == "__main__":
    sys.exit(lnd_check_v12.main(sys.argv[1:]))
