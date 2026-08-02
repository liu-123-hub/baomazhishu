#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝妈指数系统一键启动脚本：后台启动前后端服务，支持状态查询/停止/重启/日志查看。"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

RUN_DIR = ROOT / "logs" / "launcher"
PID_FILE = RUN_DIR / "pids.json"
LAUNCHER_LOG = RUN_DIR / "launcher.log"
BACKEND_LOG = RUN_DIR / "backend.log"
FRONTEND_LOG = RUN_DIR / "frontend.log"

SERVICES = {
    "backend": {
        "dir": BACKEND_DIR,
        "log": BACKEND_LOG,
        "port": 8000,
        "cmd": [sys.executable, "-u", "main.py"],
        "shell": False,
    },
    "frontend": {
        "dir": FRONTEND_DIR,
        "log": FRONTEND_LOG,
        "port": 5173,
        "cmd": "npm run dev",
        "shell": True,
    },
}

IS_WINDOWS = os.name == "nt"


class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def colorize(text: str, *colors: str) -> str:
    if not sys.stdout.isatty():
        return text
    return "".join(colors) + text + Color.RESET


def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    try:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        with open(LAUNCHER_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if IS_WINDOWS:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True


def kill_pid(pid: int, timeout: int = 10) -> bool:
    if not is_alive(pid):
        return True
    if IS_WINDOWS:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, timeout=15,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return True
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not is_alive(pid):
                return True
            time.sleep(0.3)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            return True
    time.sleep(0.5)
    return not is_alive(pid)


def load_pids() -> dict:
    if PID_FILE.exists():
        try:
            return json.loads(PID_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_pids(data: dict) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_ready(name: str, port: int, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_open("127.0.0.1", port):
            return True
        time.sleep(1)
    return False


def start_process(name: str):
    cfg = SERVICES[name]
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    log_fp = open(cfg["log"], "ab", buffering=0)
    sep = f"\n{'=' * 60}\n[{datetime.now()}] 启动 {name}\n{'=' * 60}\n"
    log_fp.write(sep.encode("utf-8"))

    popen_kwargs = dict(
        args=cfg["cmd"],
        cwd=str(cfg["dir"]),
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        shell=cfg["shell"],
    )

    if IS_WINDOWS:
        popen_kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        )
    else:
        popen_kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen(**popen_kwargs)
    except (OSError, FileNotFoundError) as e:
        log_fp.close()
        log(f"启动 {name} 失败: {e}", "ERROR")
        return None
    return proc.pid


def cmd_start(args) -> int:
    pids = load_pids()
    running = {n for n in SERVICES if n in pids and is_alive(pids[n]["pid"])}
    if running:
        log(f"以下服务已在运行: {', '.join(sorted(running))}（如需重启请用 restart）")
    to_start = [n for n in SERVICES if n not in running]
    if not to_start:
        log("所有服务均已运行，无需启动")
        return 0

    print(colorize("=== 启动宝妈指数系统 ===", Color.CYAN, Color.BOLD))
    for name in to_start:
        cfg = SERVICES[name]
        log(f"正在启动 {name} ...")
        pid = start_process(name)
        if pid is None:
            print(colorize(f"[X] {name} 启动失败，请检查环境或日志: {cfg['log']}", Color.RED))
            continue

        pids[name] = {
            "pid": pid,
            "started": datetime.now().isoformat(timespec="seconds"),
            "port": cfg["port"],
        }

        if cfg["port"]:
            log(f"等待 {name} 就绪（端口 {cfg['port']}）...")
            ready = wait_ready(name, cfg["port"], timeout=60)
            if ready:
                print(colorize(
                    f"[√] {name:<9} 已启动  PID={pid:<6} 端口={cfg['port']}",
                    Color.GREEN))
            else:
                print(colorize(
                    f"[!] {name:<9} 进程已启动(PID={pid})但端口未就绪，"
                    f"请查看日志: {cfg['log']}", Color.YELLOW))
        else:
            print(colorize(f"[√] {name:<9} 已启动  PID={pid}", Color.GREEN))

    save_pids(pids)
    print()
    print(colorize("访问地址:", Color.CYAN))
    print("  前端:  http://localhost:5173")
    print("  后端:  http://localhost:8000/docs")
    print()
    print("常用命令:")
    print("  python start.py status    查询状态")
    print("  python start.py stop      停止服务")
    print("  python start.py logs -f   实时日志")
    return 0


def cmd_status(args) -> int:
    pids = load_pids()
    if not pids:
        print(colorize("未发现已记录的服务（尚未启动或已停止）", Color.YELLOW))
        return 0

    print(colorize("=== 服务运行状态 ===", Color.CYAN, Color.BOLD))
    any_alive = False
    for name, info in pids.items():
        pid = info.get("pid", 0)
        alive = is_alive(pid)
        any_alive = any_alive or alive
        port = info.get("port")
        started = info.get("started", "-")

        if alive:
            status_str = colorize("运行中", Color.GREEN)
            port_str = ""
            if port:
                port_str = colorize(" (端口可连)", Color.GREEN) if port_open("127.0.0.1", port) \
                    else colorize(" (端口未响应)", Color.YELLOW)
        else:
            status_str = colorize("已停止", Color.RED)
            port_str = ""

        print(f"  {name:<10} {status_str}{port_str}")
        print(f"              PID={pid}  端口={port or '-'}  启动时间={started}")

    if not any_alive:
        print(colorize("\n所有服务均已停止", Color.YELLOW))
    return 0


def cmd_stop(args) -> int:
    pids = load_pids()
    if not pids:
        print(colorize("未发现需停止的服务", Color.YELLOW))
        return 0

    print(colorize("=== 停止服务 ===", Color.CYAN, Color.BOLD))
    stopped = []
    for name, info in pids.items():
        pid = info.get("pid", 0)
        if not is_alive(pid):
            print(colorize(f"[-] {name:<10} 进程已不在运行 (PID={pid})", Color.YELLOW))
            stopped.append(name)
            continue
        log(f"正在停止 {name} (PID={pid}) ...")
        ok = kill_pid(pid, timeout=10)
        if ok:
            print(colorize(f"[√] {name:<10} 已停止 (PID={pid})", Color.GREEN))
            stopped.append(name)
        else:
            print(colorize(f"[X] {name:<10} 停止失败 (PID={pid})，请手动终止", Color.RED))

    if len(stopped) == len(pids):
        try:
            PID_FILE.unlink()
        except OSError:
            pass
    else:
        remaining = {n: p for n, p in pids.items() if n not in stopped}
        save_pids(remaining)
    log(f"停止完成: {', '.join(stopped)}")
    return 0


def cmd_restart(args) -> int:
    cmd_stop(args)
    time.sleep(1)
    cmd_start(args)
    return 0


def cmd_logs(args) -> int:
    targets = [args.service] if args.service else list(SERVICES.keys())
    n = args.n
    follow = args.follow

    for name in targets:
        if name not in SERVICES:
            print(colorize(f"未知服务: {name}（可选: {', '.join(SERVICES)})", Color.RED))
            return 1

    if not follow:
        for name in targets:
            path = SERVICES[name]["log"]
            header = colorize(f"=== {name} ({path}) ===", Color.CYAN)
            print(header)
            if not path.exists():
                print(colorize("  (无日志)", Color.YELLOW))
                print()
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                for line in lines[-n:]:
                    print(line)
            except OSError as e:
                print(colorize(f"  读取失败: {e}", Color.RED))
            print()
        return 0

    print(colorize("实时跟踪日志（Ctrl+C 退出）...", Color.CYAN))
    handles = []
    try:
        for name in targets:
            path = SERVICES[name]["log"]
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.touch()
            fp = open(path, "rb")
            fp.seek(0, 2)
            handles.append((name, fp))

        while True:
            any_output = False
            for name, fp in handles:
                chunk = fp.read()
                if chunk:
                    any_output = True
                    text = chunk.decode("utf-8", errors="replace")
                    for line in text.splitlines():
                        print(f"[{name}] {line}")
            if not any_output:
                time.sleep(0.5)
    except KeyboardInterrupt:
        print(colorize("\n停止跟踪", Color.CYAN))
    finally:
        for _, fp in handles:
            try:
                fp.close()
            except OSError:
                pass
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="宝妈指数系统一键启动脚本（后台模式，跨平台）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python start.py start                       后台启动前后端\n"
            "  python start.py status                      查询运行状态\n"
            "  python start.py stop                        停止所有服务\n"
            "  python start.py restart                     重启所有服务\n"
            "  python start.py logs -n 100                 查看最后 100 行\n"
            "  python start.py logs -f --service backend   实时跟踪后端日志"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("start", help="后台启动前后端服务")
    sub.add_parser("status", help="查询服务运行状态")
    sub.add_parser("stop", help="停止所有服务")
    sub.add_parser("restart", help="重启所有服务")

    p_logs = sub.add_parser("logs", help="查看日志")
    p_logs.add_argument("-n", type=int, default=50, help="显示最后 N 行（默认 50）")
    p_logs.add_argument("-f", "--follow", action="store_true", help="实时跟踪日志")
    p_logs.add_argument(
        "--service", choices=list(SERVICES.keys()),
        help="指定服务（默认全部）",
    )

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    handlers = {
        "start": cmd_start,
        "status": cmd_status,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "logs": cmd_logs,
    }
    try:
        return handlers[args.command](args)
    except KeyboardInterrupt:
        print(colorize("\n已中断", Color.YELLOW))
        return 130
    except Exception as e:
        log(f"未捕获异常: {e}", "ERROR")
        print(colorize(f"异常: {e}", Color.RED))
        return 1


if __name__ == "__main__":
    sys.exit(main())
