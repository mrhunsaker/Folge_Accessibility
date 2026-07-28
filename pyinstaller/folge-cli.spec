# -*- mode: python ; coding: utf-8 -*-
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""
PyInstaller spec for folge-cli.

Build with (from anywhere, cwd does not matter):
    pyinstaller pyinstaller/folge-cli.spec
    # or
    cd pyinstaller && pyinstaller folge-cli.spec

Note: PyInstaller does NOT change the process cwd to the spec file's
directory -- cwd remains whatever it was when the `pyinstaller` command
was invoked. What PyInstaller *does* provide is the `SPECPATH` global
(injected into this file's namespace before exec), which is always the
absolute path of the directory containing this .spec file, regardless
of the invocation cwd. That's what we use to reliably locate the repo
root one level up.
"""
import os

block_cipher = None

# SPECPATH is provided by PyInstaller itself (not a normal Python
# global) and is always the absolute directory containing this spec
# file (i.e. <repo>/pyinstaller), independent of the caller's cwd.
PROJECT_ROOT = os.path.dirname(SPECPATH)  # noqa: F821

# Data files to bundle (accessible at runtime via sys._MEIPASS)
datas = [
    (os.path.join(PROJECT_ROOT, "templates"), "templates"),
    (os.path.join(PROJECT_ROOT, "pdf-accessibility.lua"), "."),
    (os.path.join(PROJECT_ROOT, "docx-accessibility.lua"), "."),
    (os.path.join(PROJECT_ROOT, "accessibility.lua"), "."),
    (os.path.join(PROJECT_ROOT, "config.yaml"), "."),
]

# Only include schemas/ if it has real files (not just .gitkeep)
schemas_dir = os.path.join(PROJECT_ROOT, "schemas")
if os.path.isdir(schemas_dir):
    schema_files = [
        f for f in os.listdir(schemas_dir)
        if f != ".gitkeep" and os.path.isfile(os.path.join(schemas_dir, f))
    ]
    if schema_files:
        datas.append((schemas_dir, "schemas"))

a = Analysis(
    [os.path.join(PROJECT_ROOT, "src", "folge_cli", "__main__.py")],
    pathex=[os.path.join(PROJECT_ROOT, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "jsonschema",
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
