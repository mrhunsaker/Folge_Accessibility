#!/usr/bin/env python3
"""GUI entry point for the Folge Vision Pipeline."""

from dotenv import load_dotenv
from folge.gui.app import main

load_dotenv()
main()
