"""标签搜索时间窗（search_recent_days）的回归测试。"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_get_px.pixiv.constants import SHANGHAI_TZ
from astrbot_plugin_get_px.pixiv.search import SearchMixin


def _expected_start(days: int | None) -> str | None:
    if days is None:
        return None
    today = datetime.now(SHANGHAI_TZ).date()
    return str(today - timedelta(days=days))


def _expected_end() -> str:
    return str(datetime.now(SHANGHAI_TZ).date())


class _WindowClient:
    def __init__(self, pages):
        self.calls = []
        self.pages = list(pages)

    async def search(self, tag, offset=0, start_date=None, end_date=None):
        self.calls.append((tag, offset, start_date, end_date))
        return self.pages.pop(0) if self.pages else []


class _WindowHarness(SearchMixin):
    def __init__(self, client, config=None):
        self.client = client
        self.image_index = None
        self.lolicon_client = None
        self.config = dict(config or {})

    def _cfg_int(self, key, default, lo, hi):
        try:
            val = int(self.config.get(key, default))
        except (TypeError, ValueError):
            return default
        return val if lo <= val <= hi else default


@pytest.mark.asyncio
async def test_search_uses_default_90_day_window() -> None:
    client = _WindowClient([[{"id": 1}]])
    harness = _WindowHarness(client)
    illusts = await harness._search_tag_with_window("原神", 0)
    assert client.calls == [
        ("原神", 0, _expected_start(90), _expected_end())
    ]
    assert illusts == [{"id": 1}]


@pytest.mark.asyncio
async def test_search_widens_to_triple_window_when_empty() -> None:
    client = _WindowClient([[], [{"id": 2}]])
    harness = _WindowHarness(client)
    illusts = await harness._search_tag_with_window("冷门标签", 0)
    assert [call[2] for call in client.calls] == [
        _expected_start(90),
        _expected_start(270),
    ]
    assert illusts == [{"id": 2}]


@pytest.mark.asyncio
async def test_search_falls_back_to_unlimited_window() -> None:
    client = _WindowClient([[], [], [{"id": 3}]])
    harness = _WindowHarness(client)
    illusts = await harness._search_tag_with_window("超冷门标签", 0)
    assert [call[2] for call in client.calls] == [
        _expected_start(90),
        _expected_start(270),
        None,
    ]
    assert illusts == [{"id": 3}]


@pytest.mark.asyncio
async def test_zero_days_disables_window() -> None:
    client = _WindowClient([[{"id": 4}]])
    harness = _WindowHarness(client, config={"search_recent_days": 0})
    illusts = await harness._search_tag_with_window("原神", 0)
    assert client.calls == [("原神", 0, None, _expected_end())]
    assert illusts == [{"id": 4}]


@pytest.mark.asyncio
async def test_all_windows_empty_returns_empty() -> None:
    client = _WindowClient([[], [], []])
    harness = _WindowHarness(client)
    illusts = await harness._search_tag_with_window("无人问津", 0)
    assert len(client.calls) == 3
    assert illusts == []
