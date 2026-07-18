"""数据真实性修复验证测试。

覆盖本次专项修复的核心改动：
1. _compute_is_degraded 降级判定逻辑（H1/H2/H3）
2. _validate_data_integrity 数据真实性校验机制（新增）
3. _parse_iso_time 时间解析健壮性
4. audit_logs 表扩展字段写入
5. broadcast_data_loop 异常兜底（H4）

运行方式：
    cd d:\Desktop\Success\mom-index
    python backend/test_data_authenticity_fix.py
"""
import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta

# 将项目根目录加入 sys.path，便于直接导入 backend.app 模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

# 抑制无关日志噪音
logging.basicConfig(level=logging.WARNING)

# ============ 测试结果统计 ============
test_results = []


def record(name: str, passed: bool, detail: str = ""):
    test_results.append({"name": name, "passed": passed, "detail": detail})
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))


# ============ 1. _compute_is_degraded 降级判定逻辑测试 ============
def test_compute_is_degraded():
    """验证 _compute_is_degraded 在各场景下的判定是否符合预期。"""
    print("\n[1] _compute_is_degraded 降级判定逻辑测试")
    print("-" * 60)

    from backend.app.data_service import _compute_is_degraded, _parse_iso_time

    # 场景 1: 全部参数缺失，应不降级（无法判定时不轻易降级，避免误伤）
    try:
        result = _compute_is_degraded(update_time=None)
        record("S1 全参数缺失返回 False", result is False)
    except Exception as e:
        record("S1 全参数缺失返回 False", False, str(e))

    # 场景 2: update_time 超过 24 小时 → 降级
    try:
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        result = _compute_is_degraded(update_time=old_time)
        record("S2 25h 前数据标记降级", result is True)
    except Exception as e:
        record("S2 25h 前数据标记降级", False, str(e))

    # 场景 3: update_time 在 1 小时内 → 不降级
    try:
        fresh_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        result = _compute_is_degraded(update_time=fresh_time)
        record("S3 10min 前数据不降级", result is False)
    except Exception as e:
        record("S3 10min 前数据不降级", False, str(e))

    # 场景 4: source_passed=False → 降级
    try:
        fresh_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        result = _compute_is_degraded(
            update_time=fresh_time,
            source_passed=False,
        )
        record("S4 source_passed=False 降级", result is True)
    except Exception as e:
        record("S4 source_passed=False 降级", False, str(e))

    # 场景 5: user_discussion_present=False → 降级
    try:
        fresh_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        result = _compute_is_degraded(
            update_time=fresh_time,
            source_passed=True,
            user_discussion_present=False,
        )
        record("S5 user_discussion=False 降级", result is True)
    except Exception as e:
        record("S5 user_discussion=False 降级", False, str(e))

    # 场景 6: DB 时间与 JSON provenance 时间偏差超过 1 小时 → 降级
    try:
        db_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        json_time = (datetime.now() - timedelta(hours=3)).isoformat()
        result = _compute_is_degraded(
            update_time=db_time,
            source_passed=True,
            user_discussion_present=True,
            json_provenance_time=json_time,
        )
        record("S6 DB/JSON 时间偏差 3h 降级", result is True)
    except Exception as e:
        record("S6 DB/JSON 时间偏差 3h 降级", False, str(e))

    # 场景 7: DB 时间与 JSON provenance 时间接近 → 不降级
    try:
        db_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        json_time = (datetime.now() - timedelta(minutes=5)).isoformat()
        result = _compute_is_degraded(
            update_time=db_time,
            source_passed=True,
            user_discussion_present=True,
            json_provenance_time=json_time,
        )
        record("S7 DB/JSON 时间接近不降级", result is False)
    except Exception as e:
        record("S7 DB/JSON 时间接近不降级", False, str(e))

    # 场景 8: 时间格式异常 → 降级（保守策略）
    try:
        result = _compute_is_degraded(update_time="invalid-time")
        record("S8 异常时间格式保守降级", result is True)
    except Exception as e:
        record("S8 异常时间格式保守降级", False, str(e))


# ============ 2. _parse_iso_time 时间解析测试 ============
def test_parse_iso_time():
    """验证时间解析函数对多种格式的兼容性。"""
    print("\n[2] _parse_iso_time 时间解析测试")
    print("-" * 60)

    from backend.app.data_service import _parse_iso_time

    # ISO 8601 带时区
    dt1 = _parse_iso_time("2026-07-19T10:30:09.123456+08:00")
    record("ISO 8601 带时区解析", dt1 is not None)

    # ISO 8601 不带时区
    dt2 = _parse_iso_time("2026-07-19T10:30:09")
    record("ISO 8601 不带时区解析", dt2 is not None)

    # 纯日期
    dt3 = _parse_iso_time("2026-07-19")
    record("纯日期解析", dt3 is not None and dt3.year == 2026)

    # None 输入
    record("None 输入返回 None", _parse_iso_time(None) is None)

    # 空字符串
    record("空字符串返回 None", _parse_iso_time("") is None)

    # 异常字符串
    record("异常字符串返回 None", _parse_iso_time("invalid") is None)


# ============ 3. _validate_data_integrity 数据真实性校验测试 ============
def test_validate_data_integrity():
    """验证字段级/完整性/一致性校验逻辑。"""
    print("\n[3] _validate_data_integrity 数据真实性校验测试")
    print("-" * 60)

    from backend.app.data_service import _validate_data_integrity

    # 场景 1: 正常数据应通过
    sectors_ok = {
        "nasdaq": {
            "index": 55.5,
            "post_count": 20,
            "positive_ratio": 60.0,
            "update_time": datetime.now().isoformat(),
            "is_degraded": False,
        },
        "gold": {
            "index": 30.0,
            "post_count": 10,
            "positive_ratio": 50.0,
            "update_time": datetime.now().isoformat(),
            "is_degraded": False,
        },
    }
    provenance_ok = {
        "available": True,
        "is_real_data": True,
        "fingerprints": [{"source_name": "test", "passed": True, "record_count": 10}],
    }
    try:
        result = _validate_data_integrity(
            sectors_ok, provenance_ok, datetime.now().isoformat()
        )
        record("S1 正常数据通过校验", result["passed"] is True, f"issues={result['field_issues']}")
    except Exception as e:
        record("S1 正常数据通过校验", False, str(e))

    # 场景 2: index 超出范围应不通过
    sectors_bad_index = {
        "nasdaq": {
            "index": 150.0,
            "post_count": 20,
            "positive_ratio": 60.0,
            "update_time": datetime.now().isoformat(),
            "is_degraded": False,
        }
    }
    try:
        result = _validate_data_integrity(sectors_bad_index, provenance_ok, datetime.now().isoformat())
        record("S2 index 超范围被检出", result["passed"] is False and len(result["field_issues"]) > 0)
    except Exception as e:
        record("S2 index 超范围被检出", False, str(e))

    # 场景 3: positive_ratio 超范围
    sectors_bad_ratio = {
        "nasdaq": {
            "index": 50.0,
            "post_count": 20,
            "positive_ratio": 150.0,
            "update_time": datetime.now().isoformat(),
            "is_degraded": False,
        }
    }
    try:
        result = _validate_data_integrity(sectors_bad_ratio, provenance_ok, datetime.now().isoformat())
        record("S3 positive_ratio 超范围被检出", result["passed"] is False and len(result["field_issues"]) > 0)
    except Exception as e:
        record("S3 positive_ratio 超范围被检出", False, str(e))

    # 场景 4: 缺失 update_time
    sectors_no_time = {
        "nasdaq": {
            "index": 50.0,
            "post_count": 20,
            "positive_ratio": 60.0,
            "update_time": None,
            "is_degraded": False,
        }
    }
    try:
        result = _validate_data_integrity(sectors_no_time, provenance_ok, datetime.now().isoformat())
        record("S4 缺失 update_time 被检出", result["passed"] is False and len(result["integrity_issues"]) > 0)
    except Exception as e:
        record("S4 缺失 update_time 被检出", False, str(e))

    # 场景 5: 时间偏差超 24h
    sectors_time_diff = {
        "nasdaq": {
            "index": 50.0,
            "post_count": 20,
            "positive_ratio": 60.0,
            "update_time": (datetime.now() - timedelta(hours=48)).isoformat(),
            "is_degraded": False,
        },
        "gold": {
            "index": 50.0,
            "post_count": 20,
            "positive_ratio": 60.0,
            "update_time": datetime.now().isoformat(),
            "is_degraded": False,
        },
    }
    try:
        last_update = datetime.now().isoformat()
        result = _validate_data_integrity(sectors_time_diff, provenance_ok, last_update)
        record("S5 时间偏差 48h 被检出", result["passed"] is False and len(result["consistency_issues"]) > 0)
    except Exception as e:
        record("S5 时间偏差 48h 被检出", False, str(e))

    # 场景 6: provenance 缺失关键字段
    provenance_missing = {"available": True}
    try:
        result = _validate_data_integrity(sectors_ok, provenance_missing, datetime.now().isoformat())
        record("S6 provenance 缺失字段被检出", result["passed"] is False and len(result["integrity_issues"]) >= 2)
    except Exception as e:
        record("S6 provenance 缺失字段被检出", False, str(e))


# ============ 4. audit_logs 表扩展与写入测试 ============
async def test_audit_logs_extension():
    """验证审计日志新字段写入。"""
    print("\n[4] audit_logs 表扩展字段写入测试")
    print("-" * 60)

    from backend.app.config import settings
    from backend.app.database import db

    # 初始化数据库（执行 ALTER TABLE 升级）
    try:
        await db.init_database()
        record("数据库初始化成功（含 ALTER TABLE 升级）", True)
    except Exception as e:
        record("数据库初始化成功", False, str(e))
        return

    # 写入带新字段的审计日志
    test_fingerprint = "test_fp_abc123"
    try:
        await db.add_audit_log(
            username="test_user",
            action="test_data_authenticity_fix",
            endpoint="test_script",
            status="success",
            data_fingerprint=test_fingerprint,
            sector_code="nasdaq",
            sector_count=25,
            detail="数据真实性修复验证测试",
        )
        record("带新字段审计日志写入成功", True)
    except Exception as e:
        record("带新字段审计日志写入成功", False, str(e))
        return

    # 查询验证
    try:
        async with db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT data_fingerprint, sector_code, sector_count, detail FROM audit_logs "
                "WHERE data_fingerprint = ? ORDER BY id DESC LIMIT 1",
                (test_fingerprint,),
            )
            row = await cursor.fetchone()
            if row:
                record("新字段查询可读", True, f"fp={row[0]}, sector={row[1]}, count={row[2]}")
            else:
                record("新字段查询可读", False, "未找到记录")
    except Exception as e:
        record("新字段查询可读", False, str(e))


# ============ 5. broadcast_data_loop 异常兜底测试 ============
async def test_broadcast_loop_resilience():
    """验证 broadcast_data_loop 在异常时不会终止循环。"""
    print("\n[5] broadcast_data_loop 异常兜底测试")
    print("-" * 60)

    from backend.app import main as main_module
    from backend.app.config import settings

    # 模拟 data_service._compute_dashboard_overview 抛异常
    call_count = {"value": 0}

    async def fake_compute_with_exception():
        call_count["value"] += 1
        if call_count["value"] < 3:
            raise RuntimeError(f"模拟异常 #{call_count['value']}")
        return {"code": 200, "data": {"avg_index": 50.0}}

    # 模拟 manager.connection_count > 0 触发广播
    class FakeManager:
        connection_count = 1
        broadcasted = []

        async def broadcast_data(self, msg_type, data):
            self.broadcasted.append(data)

    fake_manager = FakeManager()
    original_data_service = main_module.data_service
    original_manager = main_module.manager
    original_interval = settings.WS_BROADCAST_INTERVAL

    main_module.data_service._compute_dashboard_overview = fake_compute_with_exception
    main_module.manager = fake_manager
    settings.WS_BROADCAST_INTERVAL = 0.05  # 测试用短间隔

    try:
        # 启动循环，运行 0.3 秒后取消
        task = asyncio.create_task(main_module.broadcast_data_loop())
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # 验证：循环未终止，至少调用了 3 次（前 2 次抛异常，第 3 次成功）
        record("异常未终止循环", call_count["value"] >= 3, f"调用次数={call_count['value']}")
        # 验证：成功后正常广播
        record("异常后成功广播", len(fake_manager.broadcasted) >= 1)
    except Exception as e:
        record("异常未终止循环", False, str(e))
    finally:
        main_module.data_service = original_data_service
        main_module.manager = original_manager
        settings.WS_BROADCAST_INTERVAL = original_interval


# ============ 6. _compute_dashboard_overview 集成测试 ============
async def test_dashboard_overview_integration():
    """集成测试：调用 _compute_dashboard_overview 验证响应结构。"""
    print("\n[6] _compute_dashboard_overview 集成测试")
    print("-" * 60)

    from backend.app.data_service import _compute_dashboard_overview

    try:
        result = await _compute_dashboard_overview()
        record("接口返回 code=200", result.get("code") == 200)

        data = result.get("data") or {}
        if data:
            # 验证新增的 data_integrity 字段
            integrity = data.get("data_integrity")
            record("data_integrity 字段存在", integrity is not None)
            if integrity:
                record("integrity.passed 字段存在", "passed" in integrity)
                record("integrity.field_issues 字段存在", "field_issues" in integrity)
                record("integrity.integrity_issues 字段存在", "integrity_issues" in integrity)
                record("integrity.consistency_issues 字段存在", "consistency_issues" in integrity)
                record("integrity.checked_at 字段存在", "checked_at" in integrity)

            # 验证 sectors 中 is_degraded 字段为 bool 类型（动态计算结果）
            sectors = data.get("sectors") or {}
            if sectors:
                first_sector = next(iter(sectors.values()))
                record("sectors.is_degraded 为 bool", isinstance(first_sector.get("is_degraded"), bool))
                record("sectors.update_time 存在", first_sector.get("update_time") is not None)

            # 验证 degraded_sectors 字段
            record("degraded_sectors 字段存在", "degraded_sectors" in data)
            record("valid_sector_count 字段存在", "valid_sector_count" in data)
    except Exception as e:
        record("接口返回 code=200", False, str(e))


# ============ 主测试入口 ============
async def main():
    print("=" * 70)
    print("   数据真实性修复验证测试")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 同步测试
    test_parse_iso_time()
    test_compute_is_degraded()
    test_validate_data_integrity()

    # 异步测试
    await test_audit_logs_extension()
    await test_broadcast_loop_resilience()
    await test_dashboard_overview_integration()

    # 汇总
    print("\n" + "=" * 70)
    print("   测试结果汇总")
    print("=" * 70)
    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed
    print(f"  总用例: {total}，通过: {passed}，失败: {failed}")
    if failed:
        print("\n  失败用例:")
        for r in test_results:
            if not r["passed"]:
                print(f"    ❌ {r['name']} — {r['detail']}")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
