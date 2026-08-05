# -*- mode: python ; coding: utf-8 -*-
"""宝妈指数系统 PyInstaller 打包配置（onedir 模式，体积优化版）。

整合前端构建产物(frontend/dist)、后端应用、种子数据为独立可执行程序。
打包后由可执行文件统一提供 API 服务与前端静态资源（同源访问，无需代理）。

体积优化策略：
- 激进排除 numba/llvmlite(101MB)/PIL(12.7MB)/psycopg/Pythonwin 等本项目不使用的重型依赖
- strip=False：strip 会损坏 Windows api-ms-win-*.dll（API 转发器），导致 python313.dll 加载失败
- UPX 不在 spec 内启用：UPX 压缩 .dll（尤其 numpy OpenBLAS/CRT）会导致运行时崩溃
  改用构建后脚本对 .pyd 文件定向 UPX 压缩（安全），见 build_release.bat

打包命令：
    pyinstaller mom_index.spec --noconfirm --clean
    或一键优化构建：build_release.bat（含前端构建 + UPX 压缩）

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

# UPX 压缩目录：若项目内存在 upx/ 子目录则启用，否则跳过
UPX_DIR = os.path.join(PROJECT_ROOT, 'upx')
USE_UPX = os.path.isdir(UPX_DIR)

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

# ── 体积优化：排除本项目不使用的重型依赖 ──
#   numba/llvmlite : pandas 可选 JIT 加速，本项目未使用，省 ~101MB
#   PIL/Pillow     : 图像处理库，本项目不生成图片，省 ~12.7MB
#   psycopg*/asyncpg/asyncmy : PostgreSQL/MySQL 驱动，本项目用 aiosqlite，省 ~8MB
#   sqlalchemy     : ORM，本项目直接用 aiosqlite，省 ~0.4MB
#   Pythonwin/win32ui/pythoncom/pywintypes/win32com : Windows GUI/COM，Web 服务不需要，省 ~7MB
#   tkinter/pytest/tests/notebook/IPython : 测试/GUI/Notebook，生产不需要
#   torch/matplotlib/scipy/sklearn/sympy : 科学计算重型库，本项目未引用
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
    icon=None,
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
