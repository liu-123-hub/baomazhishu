# -*- mode: python ; coding: utf-8 -*-
"""宝妈指数系统 PyInstaller 打包配置（onedir 模式）。

整合前端构建产物(frontend/dist)、后端应用、种子数据为独立可执行程序。
打包后由可执行文件统一提供 API 服务与前端静态资源（同源访问，无需代理）。

打包命令：
    pyinstaller mom_index.spec --noconfirm --clean

产物目录：
    dist/MomIndex/MomIndex(.exe)        可执行文件
    dist/MomIndex/_internal/            依赖与资源（_MEIPASS）
"""
import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

PROJECT_ROOT = os.path.abspath('.')

# 构建期需将 backend/ 与项目根加入 sys.path，以便 collect_submodules 发现本地包
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))
sys.path.insert(0, PROJECT_ROOT)

datas = []
binaries = []
hiddenimports = []

# ── 重型第三方依赖：含数据文件/动态导入，整体收集 ──
for pkg in ['akshare', 'pydantic', 'pydantic_settings', 'pydantic_core']:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# ── 本地业务包：analyzer / collectors / app / pipeline 全量子模块 ──
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

# ── 前端构建产物 → 只读资源 frontend_dist/ ──
datas += [('frontend/dist', 'frontend_dist')]

# ── 种子数据 JSON → 只读资源 data/（首次运行拷贝到可写数据目录）──
for jf in glob.glob(os.path.join(PROJECT_ROOT, 'data', '*.json')):
    datas += [(jf, 'data')]

a = Analysis(
    ['backend/run_prod.py'],
    pathex=[PROJECT_ROOT, os.path.join(PROJECT_ROOT, 'backend')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'tests', 'pytest', 'notebook', 'IPython',
        'torch', 'torchvision', 'torchaudio', 'tensorboard',
        'matplotlib', 'sklearn', 'scipy', 'sympy',
        'bokeh', 'plotly', 'seaborn', 'PyQt5', 'PySide2', 'PySide6',
    ],
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
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='MomIndex',
)
