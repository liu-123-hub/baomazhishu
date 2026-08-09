import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

PROJECT_ROOT = os.path.abspath('.')

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))
sys.path.insert(0, PROJECT_ROOT)

UPX_DIR = os.path.join(PROJECT_ROOT, 'upx')
USE_UPX = False

datas = []
binaries = []
hiddenimports = []

for pkg in ['akshare', 'pydantic', 'pydantic_settings', 'pydantic_core']:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

for pkg in ['analyzer', 'collectors', 'app']:
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass
hiddenimports += ['pipeline']

# ── uvicorn 运行时按需导入的协议/循环/生命周期模块 ──
hiddenimports += [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
]
hiddenimports += collect_submodules('aiosqlite')
hiddenimports += collect_submodules('httpx')

datas += [(os.path.join(PROJECT_ROOT, 'icon.ico'), '.')]
datas += [(os.path.join(PROJECT_ROOT, 'icon.png'), '.')]

datas += [('frontend/dist', 'frontend_dist')]

for jf in glob.glob(os.path.join(PROJECT_ROOT, 'data', '*.json')):
    datas += [(jf, 'data')]

excludes = [
    'numba', 'llvmlite',
    'PIL', 'Pillow',
    'psycopg2', 'psycopg', 'psycopg_binary', 'asyncpg', 'asyncmy',
    'sqlalchemy',
    'Pythonwin', 'win32ui', 'pythoncom', 'pywintypes', 'win32com',
    'tkinter', 'tests', 'pytest', 'notebook', 'IPython',
    'torch', 'torchvision', 'torchaudio', 'tensorboard',
    'matplotlib', 'sklearn', 'scipy', 'sympy',
    'bokeh', 'plotly', 'seaborn', 'PyQt5', 'PySide2', 'PySide6',
    'coverage', 'pytest_asyncio',
    'cryptography', 'pdfminer', 'pdfminer.six',
]

a = Analysis(
    ['backend/run_prod.py'],
    pathex=[PROJECT_ROOT, os.path.join(PROJECT_ROOT, 'backend')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MomIndex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=USE_UPX,
    upx_dir=UPX_DIR if USE_UPX else None,
    console=True,
    disable_windowed_traceback=False,
    icon=os.path.join(PROJECT_ROOT, 'icon.ico'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=USE_UPX,
    upx_dir=UPX_DIR if USE_UPX else None,
    name='MomIndex',
)
