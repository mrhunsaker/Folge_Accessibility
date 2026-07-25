#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Backward-compatible entry point.

The canonical entry point is now:
    folge-cli pipeline <guide.json> [output-dir] [--targets ...] [--provider ...]

This shim delegates to the package module.
"""
from folge_cli.pipeline import main

if __name__ == "__main__":
    main()
