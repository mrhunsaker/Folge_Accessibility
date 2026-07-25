# -*- mode: python ; coding: utf-8 -*-
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""
PyInstaller spec for folge-cli.

Build with:
    pyinstaller pyinstaller/folge-cli.spec
"""
import os

block_cipher = None

# Data files to bundle (accessible at runtime via sys._MEIPASS)
datas = [
    ("templates", "templates"),
    ("pdf-accessibility.lua", "."),
    ("docx-accessibility.lua", "."),
    ("accessibility.lua", "."),
    ("config.yaml", "."),
]

# Only include schemas/ if it has real files (not just .gitkeep)
schemas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas")
if os.path.isdir(schemas_dir):
    schema_files = [
        f for f in os.listdir(schemas_dir)
        if f != ".gitkeep" and os.path.isfile(os.path.join(schemas_dir, f))
    ]
    if schema_files:
        datas.append(("schemas", "schemas"))

a = Analysis(
    [os.path.join("src", "folge_cli", "__main__.py")],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "jsonschema",
        "jsonschema._validators",
        "jinja2",
        "jinja2.ext",
        "yaml",
        "dotenv",
        "requests",
        "fitz",  # pymupdf
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "mkdocs",
        "mkdocs.material",
        "mkdocs.contrib.search",
        "pymdown",
        "pymdown.extensions",
        "weasyprint",  # has C deps, installed separately on target
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="folge-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
