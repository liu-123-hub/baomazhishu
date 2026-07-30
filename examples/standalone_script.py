"""示例 3：独立脚本接入 mini_logger

演示：
- 极简接入：仅 1 行 init
- 自动 trace_id（无需手动 bind_context）
- 异常自动落盘到滚动文件
- 程序退出时优雅关闭
"""

from __future__ import annotations

import sys

import mini_logger


def main() -> int:
    # === 仅 1 行 init ===
    mini_logger.init(
        service="batch-job",
        level="INFO",
        console=True,
        file=True,
        log_dir="logs/batch",
    )

    mini_logger.info("script start", argv=sys.argv[1:])

    try:
        # 业务逻辑
        for i in range(5):
            mini_logger.info("processing item", index=i, action="handle")
        # 模拟一个错误
        result = 10 / 0  # 故意触发异常
    except ZeroDivisionError as e:
        # 在 except 块内调用 error，自动捕获完整栈
        mini_logger.error("critical failure", exc=e, stage="compute")
        return 1
    finally:
        mini_logger.info("script end")
        # 优雅关闭，确保日志全部落盘
        mini_logger.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
