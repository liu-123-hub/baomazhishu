# mini_logger —— 极简全链路日志系统

一套统一、完善且极致简化的日志系统，覆盖业务服务、中间件、工具模块的日志需求。
零冗余依赖（仅 Python 3.10+ 标准库），1 行代码完成初始化，5 个核心方法对应五级日志。

## 特性速览

| 维度 | 能力 |
| --- | --- |
| **统一规范** | UTC+8 毫秒时间戳、五级日志、链路 trace_id、服务标识、调用源 IP、用户标识等必填字段；JSON / 人类可读双模式 |
| **极简接入** | 1 行 `init`；5 个方法 `debug/info/warn/error/fatal`；自动上下文注入；核心体积 < 100KB |
| **多输出源** | 控制台 / 本地滚动文件（按日期+大小双维度切割，保留 30 天）/ 远端日志平台 |
| **安全脱敏** | 自动识别身份证 / 手机 / 银行卡 / API Key / 密码等敏感字段并遮蔽 |
| **动态级别** | `set_level()` 在线切换，无需重启 |
| **异常栈** | `error(msg, exc=e)` 自动写入完整 traceback；`@catch_exception` 装饰器；`sys.excepthook` 自动安装 |
| **异步落盘** | 后台单线程消费队列，主线程 `info()` 仅入队 O(1) |
| **背压控制** | 队列水位 >80% 丢 DEBUG；>95% 采样 INFO；满则按策略丢最旧 / 拒新 / 阻塞 |
| **资源控制** | 单条日志 64KB 截断；队列 65536 容量；自动清理过期文件 |

## 快速开始

```python
import mini_logger

# 1 行初始化
mini_logger.init(service="my-service", level="INFO")

# 5 个核心方法
mini_logger.debug("debug msg")
mini_logger.info("info msg", user_id="u1", action="login")
mini_logger.warn("warn msg")
mini_logger.error("error msg", exc=some_exception)
mini_logger.fatal("fatal msg")

# 程序退出时优雅关闭
mini_logger.shutdown()
```

## 链路追踪

`bind_context()` 注入上下文，同一请求/任务内所有日志自动携带相同 `trace_id`：

```python
# FastAPI 中间件示例
@app.middleware("http")
async def log_ctx(request: Request, call_next):
    token = mini_logger.bind_context(
        trace_id=request.headers.get("X-Trace-Id") or uuid.uuid4().hex,
        user_id=request.headers.get("X-User-Id", ""),
        client_ip=request.client.host,
    )
    try:
        return await call_next(request)
    finally:
        token.reset()
        mini_logger.clear_context()
```

未调用 `bind_context()` 时，`trace_id` 自动生成（UUID4 去横线）。

## 配置项

`init()` 支持的关键字参数（均有合理默认值）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `service` | str | `"default-service"` | 服务标识（必填建议） |
| `env` | str | `"dev"` | 环境标识 |
| `level` | LogLevel / str | `INFO` | 日志级别 |
| `console` | bool | `True` | 是否输出到控制台 |
| `file` | bool | `True` | 是否输出到本地文件 |
| `remote` | bool | `False` | 是否输出到远端 |
| `log_dir` | str | `"logs"` | 日志目录 |
| `file_max_size` | int | `10MB` | 单文件最大字节数 |
| `file_backup_count` | int | `30` | 保留文件数（天） |
| `remote_url` | str | `None` | 远端日志平台 URL |
| `remote_batch_size` | int | `50` | 远端批量大小 |
| `queue_maxsize` | int | `65536` | 异步队列容量 |
| `max_msg_bytes` | int | `64KB` | 单条日志最大字节 |
| `backpressure_warn` | float | `0.80` | 队列水位告警阈值 |
| `backpressure_drop` | float | `0.95` | 队列采样阈值 |
| `drop_policy` | str | `"oldest"` | 满时策略：`oldest` / `newest` / `block` |
| `json_console` | bool | `False` | 控制台是否输出 JSON |
| `include_location` | bool | `True` | 是否记录 module/func/line |
| `redact_enabled` | bool | `True` | 是否启用脱敏 |
| `extra_redact_keys` | list[str] | `[]` | 额外敏感字段名 |
| `catch_unhandled` | bool | `True` | 是否安装 sys.excepthook |

## 日志字段标准

每条日志记录的字段（JSON 输出格式）：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `ts` | str | ✓ | ISO8601 时间戳，UTC+8，毫秒精度，如 `2026-07-31T14:30:00.123+08:00` |
| `level` | str | ✓ | `DEBUG` / `INFO` / `WARN` / `ERROR` / `FATAL` |
| `service` | str | ✓ | 服务标识 |
| `trace_id` | str | ✓ | 链路追踪 ID（UUID4 去横线） |
| `msg` | str | ✓ | 日志消息 |
| `span_id` | str | ✗ | 子段 ID（bind_context 自动生成） |
| `request_id` | str | ✗ | 请求 ID |
| `user_id` | str | ✗ | 用户唯一标识 |
| `client_ip` | str | ✗ | 调用源 IP |
| `tenant` | str | ✗ | 租户标识 |
| `module` | str | ✗ | 代码模块名（`__name__`） |
| `func` | str | ✗ | 函数名 |
| `line` | int | ✗ | 行号 |
| `err_type` | str | ✗ | 异常类名 |
| `err_stack` | str | ✗ | 完整 traceback（多行字符串） |
| `extra` | dict | ✗ | 业务扩展字段 |

## 脱敏规则

### 字段名匹配（值替换为 `***`）

`password` / `passwd` / `pwd` / `secret` / `token` / `apikey` / `api_key` / `access_token` /
`refresh_token` / `authorization` / `credit_card` / `card_no` / `id_card` / `ssn`

可通过 `extra_redact_keys=["my_field"]` 扩展。

### 字符串扫描（局部遮蔽）

| 类型 | 模式 | 遮蔽策略 |
| --- | --- | --- |
| 身份证号 | 18 位数字（最后位可为 X） | 前 6 + 后 4，中间用 ★ |
| 手机号 | 1 开头 11 位数字 | 前 3 + `****` + 后 4 |
| 银行卡号 | 16-19 位连续数字 | 前 4 + `*` + 后 4 |

## 异常捕获

### 1. 显式捕获

```python
try:
    risky_operation()
except Exception as e:
    mini_logger.error("operation failed", exc=e)
```

### 2. except 块内自动捕获

```python
try:
    risky_operation()
except Exception:
    mini_logger.error("operation failed")  # 自动捕获当前异常栈
```

### 3. 装饰器

```python
@mini_logger.catch_exception("task failed", reraise=True)
def my_task():
    ...
```

### 4. 未处理异常

`sys.excepthook` 自动安装（`catch_unhandled=True`），未捕获的异常以 FATAL 级别记录完整栈。

## 性能与可靠性

### 异步管道

```
源 → 上下文注入 → 脱敏 → 格式化 → 有界队列(背压) → [console / file / remote]
```

- 主线程 `info()` 等仅做内存操作（构造 record + 入队），耗时 < 10μs
- 后台单线程消费，批量 flush 文件 handler
- 单条日志超过 64KB 自动截断，防止内存膨胀

### 背压策略

| 队列水位 | 行为 |
| --- | --- |
| `< 80%` | 正常入队 |
| `>= 80%` | DEBUG 级别直接丢弃 |
| `>= 95%` | INFO 级别 50% 采样（按线程 id 奇偶） |
| 队列满 | 按 `drop_policy` 处理：`oldest` 丢最旧 / `newest` 拒新 / `block` 等待 50ms |

### 文件滚动

- 文件名：`{log_dir}/{service}-{YYYY-MM-DD}.log`
- 滚动条件：日期变化（自然切换）或单文件 ≥ `file_max_size`
- 大小滚动：`service-date.log` → `service-date.log.1` → `.2` → ...
- 启动时清理超过 `file_backup_count` 的旧文件

## 完整 API

```python
mini_logger.init(**kwargs)              # 初始化（1 行）
mini_logger.debug(msg, **extra)         # DEBUG 级别
mini_logger.info(msg, **extra)         # INFO 级别
mini_logger.warn(msg, **extra)          # WARN 级别
mini_logger.error(msg, exc=None, **extra)  # ERROR 级别
mini_logger.fatal(msg, exc=None, **extra)   # FATAL 级别
mini_logger.get_logger()                # 获取 Logger 单例
mini_logger.set_level(level)            # 动态切换级别
mini_logger.bind_context(...)           # 注入上下文，返回 token
mini_logger.clear_context()             # 清空上下文
mini_logger.shutdown(timeout=2.0)       # 优雅关闭
mini_logger.catch_exception(msg, *, reraise=True)  # 异常捕获装饰器
```

## 接入示例

仓库 `examples/` 目录提供 3 个完整示例：

| 文件 | 场景 | 演示要点 |
| --- | --- | --- |
| `examples/fastapi_app.py` | FastAPI Web 服务 | 中间件注入 trace_id、敏感字段脱敏、异常栈捕获 |
| `examples/collector_usage.py` | 数据采集器 | 长任务批处理、`@catch_exception` 装饰器、动态级别切换 |
| `examples/standalone_script.py` | 独立脚本 | 极简 1 行 init、自动 trace_id、异常自动落盘 |

运行示例：

```bash
# 在项目根目录执行
PYTHONPATH=. python examples/standalone_script.py
PYTHONPATH=. python examples/collector_usage.py
```

## 测试

```bash
# 运行全部测试
python -m pytest tests/

# 运行并查看覆盖率
python -m pytest tests/ --cov=mini_logger --cov-report=term-missing
```

测试覆盖：175 个用例，覆盖率 95%+。涵盖：

- `LogConfig` / `LogLevel` 配置与转换
- 上下文注入、协程/线程隔离、token reset
- 脱敏：身份证 / 手机 / 银行卡 / 自定义字段、嵌套 dict / list
- 格式化：JSON / 人类可读、必填字段、可选字段
- ConsoleHandler / RollingFileHandler / RemoteHandler 各路径
- 异步队列、背压三策略、动态级别
- excepthook 安装 / 触发 / 队列满容错
- 异常栈捕获：显式 / except 块自动 / 装饰器 / 未处理
- 端到端：FastAPI 中间件、采集器批处理、独立脚本

## 设计文档

详细设计文档见 `mini_logger/README.md`（本文件）。核心架构决策：

1. **零依赖**：仅使用 Python 标准库（`contextvars` / `threading` / `queue` / `json` / `re` / `inspect`），便于嵌入任何项目
2. **单线程消费**：避免多线程竞争文件句柄，简化背压实现
3. **contextvars**：原生支持 asyncio 协程隔离，且 `run_in_executor` 派发的线程池任务自动继承
4. **JSON 优先**：文件 sink 始终输出 JSON，便于 ELK / Loki 等平台解析；控制台可人类可读
5. **背压而非阻塞**：默认 `oldest` 策略保证最新日志优先落盘，DEBUG 在高压下自动丢弃

## 模块结构

```
mini_logger/
├── __init__.py          # 公开 API 入口
├── config.py            # LogConfig / LogLevel 配置
├── context.py           # contextvars 上下文 + ContextToken
├── formatter.py         # JSON / 人类可读格式化
├── redactor.py          # 敏感信息脱敏
├── handlers.py          # ConsoleHandler / RollingFileHandler / RemoteHandler
├── core.py              # Logger 主体：异步队列、背压、动态级别、excepthook
└── exceptions.py        # @catch_exception 装饰器
```
