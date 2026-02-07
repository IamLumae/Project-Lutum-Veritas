# -*- mode: python ; coding: utf-8 -*-
# =============================================
# Lutum Veritas - Backend PyInstaller Spec File
# =============================================
# Builds the FastAPI backend into a frozen executable.
# Run with: pyinstaller build_backend.spec
#
# Uses Python 3.12 (primp has no 3.14 wheel!)

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

# === Third-party packages with binary extensions / dynamic imports ===
# These need collect_all because they load .pyd/.so files or use importlib magic.

packages_to_collect = [
    'uvicorn',
    'fastapi',
    'starlette',
    'pydantic',
    'pydantic_core',
    'primp',
    'ddgs',
    'camoufox',
    'trafilatura',
    'lxml',
    'bs4',           # beautifulsoup4
    'search_engines',
    'sse_starlette',
    'requests',
    'anyio',
    'httpcore',
    'httpx',
    'certifi',
    'charset_normalizer',
    'idna',
    'urllib3',
    'courlan',
    'htmldate',
    'justext',
    'nest_asyncio',   # Used as fallback in camoufox_scraper.py
    'playwright',     # camoufox needs playwright's Python API (NOT the 96 MB driver/)
    'browserforge',   # camoufox dependency - has .zip data files in headers/data/ and fingerprints/data/
    'language_tags',  # camoufox dependency - has .json data files in data/json/
]

all_datas = []
all_binaries = []
all_hiddenimports = []

for pkg in packages_to_collect:
    try:
        datas, binaries, hiddenimports = collect_all(pkg)
        all_datas += datas
        all_binaries += binaries
        all_hiddenimports += hiddenimports
    except Exception as e:
        print(f"WARNING: collect_all('{pkg}') failed: {e}")

# === Strip playwright's 96 MB driver/ directory (node.js + browsers) ===
# Camoufox only needs playwright's Python API, not the bundled browsers.
# Camoufox has its own Firefox binary in %LOCALAPPDATA%\camoufox\.
import os
_before_datas = len(all_datas)
_before_bins = len(all_binaries)
all_datas = [(src, dst) for src, dst in all_datas
             if 'playwright' not in src or 'driver' not in src.replace('/', os.sep)]
all_binaries = [(src, dst) for src, dst in all_binaries
                if 'playwright' not in src or 'driver' not in src.replace('/', os.sep)]
print(f"Stripped playwright driver: datas {_before_datas} -> {len(all_datas)}, "
      f"binaries {_before_bins} -> {len(all_binaries)}")

# === Metadata needed by packages using importlib.metadata ===
metadata_packages = [
    'primp', 'pydantic', 'pydantic-core', 'fastapi', 'starlette',
    'uvicorn', 'camoufox', 'ddgs', 'trafilatura', 'playwright', 'browserforge',
]
for pkg in metadata_packages:
    try:
        all_datas += copy_metadata(pkg)
    except Exception as e:
        print(f"WARNING: copy_metadata('{pkg}') failed: {e}")

# === Extra hidden imports that PyInstaller often misses ===
extra_hiddenimports = [
    # Uvicorn internals (loaded dynamically via __import__)
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'uvicorn.logging',
    # Email (sometimes missed)
    'email.mime.multipart',
    'email.mime.text',
    # Multipart form handling
    'multipart',
    # Our local packages (not pip-installed, found via --paths)
    'lutum',
    'lutum.core',
    'lutum.core.log_config',
    'lutum.core.config',
    'lutum.core.api_config',
    'lutum.core.security',
    'lutum.core.exceptions',
    'lutum.core.llm_client',
    'lutum.analyzer',
    'lutum.analyzer.web_analyzer',
    'lutum.extractor',
    'lutum.extractor.content',
    'lutum.scrapers',
    'lutum.scrapers.base',
    'lutum.scrapers.camoufox_scraper',
    'lutum.researcher',
    'lutum.researcher.pipeline',
    'lutum.researcher.overview',
    'lutum.researcher.plan',
    'lutum.researcher.search',
    'lutum.researcher.scraper',
    'lutum.researcher.clarify',
    'lutum.researcher.context_state',
    'lutum.researcher.prompts',
    'lutum.researcher.prompts.academic_conclusion',
    'lutum.researcher.prompts.academic_plan',
    'lutum.researcher.prompts.bereichs_synthesis',
    'lutum.researcher.prompts.dossier',
    'lutum.researcher.prompts.final_synthesis',
    'lutum.researcher.prompts.meta_synthesis',
    'lutum.researcher.prompts.pick_urls',
    'lutum.researcher.prompts.report_parser',
    'lutum.researcher.prompts.think',
    # Backend routes/services (imported dynamically via __package__ check)
    'lutum_backend',
    'lutum_backend.routes',
    'lutum_backend.routes.chat',
    'lutum_backend.routes.health',
    'lutum_backend.routes.research',
    'lutum_backend.routes.ask',
    'lutum_backend.services',
    'lutum_backend.services.lutum_service',
    # Deep question pipeline (imported via bare import in ask.py)
    'deep_question_pipeline',
    # Bare route imports (main.py uses "from routes.chat import" in Script Mode)
    # These need pathex=['lutum_backend'] to be found
    'routes',
    'routes.chat',
    'routes.health',
    'routes.research',
    'routes.ask',
    'services',
    'services.lutum_service',
]

all_hiddenimports += extra_hiddenimports

# === Data files ===
# deep_question_pipeline.py is included via hidden_import + pathex (as Python module)
# www/ contains the frontend SPA (served by FastAPI at /)
all_datas += [('lutum_backend/www', 'www')]

# === Analysis ===
a = Analysis(
    ['lutum_backend/main.py'],
    pathex=['.', 'lutum_backend'],   # '.' for lutum/deep_question_pipeline, 'lutum_backend' for bare routes.*
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # === HEAVY PACKAGES NOT NEEDED BY LUTUM ===
        'torch',            # 312 MB - pulled by trafilatura->nltk chain
        'transformers',     # 43 MB - not needed
        'sklearn',          # 14 MB - not needed
        'scikit-learn',
        # numpy is NEEDED by camoufox/utils.py - DO NOT EXCLUDE
        'scipy',            # Not needed
        'pandas',           # Not needed
        'matplotlib',       # Not needed
        'PIL',              # Not needed
        'Pillow',
        'sympy',            # Not needed
        'babel',            # 28 MB - locale data, not needed
        'tiktoken',         # Not needed
        'tokenizers',       # Not needed (7 MB)
        # NOTE: playwright Python module is INCLUDED (camoufox needs the API)
        # But playwright's 96 MB driver/ binaries are stripped below
        # === OTHER UNUSED ===
        'tkinter',
        'test',
        'unittest',
        'Pythonwin',        # 6 MB - not needed
        'win32com',         # COM automation, not needed
        'nltk',             # pulls heavy deps, trafilatura works without it
        'IPython',
        'notebook',
        'jupyter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # True = onedir mode
    name='lutum-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # UPX can trigger AV false positives
    console=True,               # Console for stderr logging (Tauri captures it)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='lutum-backend',
)
