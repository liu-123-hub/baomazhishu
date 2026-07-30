"""示例 2：数据采集器接入 mini_logger

演示：
- 长任务批处理场景，使用 trace_id 贯穿整次采集
- 多源数据采集，部分失败不影响整体
- @catch_exception 装饰器自动记录异常并重新抛出
- 动态调整日志级别（如线上排查时切到 DEBUG）
"""

from __future__ import annotations

import time
import uuid

import mini_logger


def init_collector_logger():
    """采集器日志初始化。"""
    mini_logger.init(
        service="data-collector",
        env="prod",
        level="INFO",
        console=True,
        file=True,
        log_dir="logs/collector",
        file_backup_count=30,  # 保留 30 天
        redact_enabled=True,
    )


@mini_logger.catch_exception("collector step failed", reraise=False)
def collect_from_source(source: str, batch_size: int = 100) -> int:
    """从单个数据源采集。失败时自动记录异常但不再抛出。"""
    mini_logger.info("collecting", source=source, batch_size=batch_size)

    # 模拟采集过程
    if source == "broken-source":
        raise ConnectionError(f"{source} unreachable")

    # 模拟成功采集到 N 条数据
    time.sleep(0.05)
    count = batch_size
    mini_logger.info("batch done", source=source, count=count)
    return count


def run_collection():
    """执行一次完整采集任务。"""
    # 给整次采集一个统一 trace_id
    trace_id = f"collect-{uuid.uuid4().hex[:12]}"
    token = mini_logger.bind_context(trace_id=trace_id)
    try:
        mini_logger.info("collection task start", trace_id=trace_id)

        sources = ["guba", "xueqiu", "ths_finance", "broken-source", "xhs"]
        total = 0
        for src in sources:
            # 单源失败不影响其他源
            cnt = collect_from_source(src, batch_size=50)
            if cnt:
                total += cnt

        mini_logger.info("collection task done", total=total)
        return total
    finally:
        token.reset()
        mini_logger.clear_context()


def demonstrate_dynamic_level():
    """演示动态调整日志级别（线上排查场景）。"""
    mini_logger.info("current level is INFO, debug logs are suppressed")
    mini_logger.debug("this debug log won't appear")  # 被过滤

    # 线上排查问题：临时切换到 DEBUG
    mini_logger.set_level("DEBUG")
    mini_logger.info("switched to DEBUG level")
    mini_logger.debug("now debug logs are visible", detail="for troubleshooting")

    # 排查完毕切回 INFO
    mini_logger.set_level("INFO")
    mini_logger.debug("this debug log won't appear again")


if __name__ == "__main__":
    init_collector_logger()
    try:
        total = run_collection()
        print(f"\n=== Collected {total} records ===\n")

        demonstrate_dynamic_level()
    finally:
        mini_logger.shutdown()
