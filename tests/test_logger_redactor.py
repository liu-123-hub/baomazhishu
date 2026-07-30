"""脱敏模块测试"""

import pytest

from mini_logger.redactor import (
    redact_string,
    redact_dict,
    redact_any,
    _mask_middle,
)


class TestMaskMiddle:
    def test_normal(self):
        assert _mask_middle("1234567890", 4, 4) == "1234**7890"

    def test_short_string_all_masked(self):
        assert _mask_middle("ab", 4, 4) == "**"

    def test_custom_mask_char(self):
        # 长度 10，保留首 4 + 尾 4，中间 2 位用 ★
        assert _mask_middle("1234567890", 4, 4, "★") == "1234★★7890"


class TestRedactString:
    def test_idcard(self):
        s = "用户身份证 110101199003078888 已登记"
        out = redact_string(s)
        assert "110101199003078888" not in out
        assert "110101" in out  # 前 6 位保留
        assert "8888" in out  # 后 4 位保留
        assert "★" in out

    def test_idcard_with_x(self):
        s = "11010119900307888X"
        out = redact_string(s)
        assert "11010119900307888X" not in out

    def test_phone(self):
        s = "联系电话 13812345678"
        out = redact_string(s)
        assert "13812345678" not in out
        assert "138" in out
        assert "5678" in out
        assert "****" in out

    def test_bankcard(self):
        s = "银行卡 6222020200011111222"
        out = redact_string(s)
        assert "6222020200011111222" not in out
        assert "6222" in out
        assert "1222" in out

    def test_no_match_returns_original(self):
        s = "普通字符串无敏感信息"
        assert redact_string(s) == s

    def test_empty_string(self):
        assert redact_string("") == ""

    def test_multiple_sensitive(self):
        s = "id=110101199003078888 phone=13812345678"
        out = redact_string(s)
        assert "110101199003078888" not in out
        assert "13812345678" not in out


class TestRedactDict:
    def test_sensitive_keys_replaced(self):
        data = {
            "username": "alice",
            "password": "secret123",
            "token": "tok_abcdef",
            "api_key": "k_123",
        }
        out = redact_dict(data)
        assert out["username"] == "alice"
        assert out["password"] == "***"
        assert out["token"] == "***"
        assert out["api_key"] == "***"

    def test_nested_dict(self):
        data = {
            "user": {
                "name": "bob",
                "password": "p@ss",
                "info": {"secret": "s"},
            }
        }
        out = redact_dict(data)
        assert out["user"]["name"] == "bob"
        assert out["user"]["password"] == "***"
        assert out["user"]["info"]["secret"] == "***"

    def test_string_value_scanned(self):
        data = {"note": "phone 13812345678 called"}
        out = redact_dict(data)
        assert "13812345678" not in out["note"]

    def test_list_of_dicts(self):
        data = {"items": [{"password": "p1"}, {"name": "x"}]}
        out = redact_dict(data)
        assert out["items"][0]["password"] == "***"
        assert out["items"][1]["name"] == "x"

    def test_list_of_strings(self):
        data = {"phones": ["13812345678", "普通"]}
        out = redact_dict(data)
        assert "13812345678" not in out["phones"][0]
        assert out["phones"][1] == "普通"

    def test_extra_sensitive_keys(self):
        data = {"my_field": "v"}
        out = redact_dict(data, extra_keys=["my_field"])
        assert out["my_field"] == "***"

    def test_cycle_protection(self):
        data = {"a": 1}
        data["self"] = data  # 自引用
        out = redact_dict(data)
        # 不应递归爆栈
        assert "self" in out

    def test_non_dict_values_preserved(self):
        data = {"count": 42, "ratio": 3.14, "flag": True, "none": None}
        out = redact_dict(data)
        assert out["count"] == 42
        assert out["ratio"] == 3.14
        assert out["flag"] is True
        assert out["none"] is None


class TestRedactAny:
    def test_dict_dispatch(self):
        out = redact_any({"password": "x"})
        assert out["password"] == "***"

    def test_string_dispatch(self):
        out = redact_any("phone 13812345678")
        assert "13812345678" not in out

    def test_other_types_passthrough(self):
        assert redact_any(42) == 42
        assert redact_any(None) is None
        assert redact_any([1, 2, 3]) == [1, 2, 3]
