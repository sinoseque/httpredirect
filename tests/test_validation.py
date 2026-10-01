import pytest

from app.main import UsageError, _require_args


def test_require_args_ok():
    assert _require_args(["a", "b"], 2, "/set a b") == ["a", "b"]


def test_require_args_short_raises():
    with pytest.raises(UsageError):
        _require_args(["solo"], 2, "/set nombre url")


def test_require_args_discards_extra():
    assert _require_args(["a", "b", "c"], 2, "/set a b") == ["a", "b"]


def test_usage_error_message_contains_usage():
    with pytest.raises(UsageError) as excinfo:
        _require_args([], 1, "/del nombre")
    assert "/del nombre" in str(excinfo.value)
