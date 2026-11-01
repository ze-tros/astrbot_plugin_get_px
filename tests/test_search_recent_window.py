"""标签搜索时间窗（search_recent_days）与收藏倒序的回归测试。"""

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
async def test_search_uses_default_three_year_window() -> None:
    client = _WindowClient([[{"id": 1, "total_bookmarks": 10}]])
    harness = _WindowHarness(client)
    illusts = await harness._search_tag_with_window("原神", 0)
    assert client.calls == [
        ("原神", 0, _expected_start(1095), _expected_end())
    ]
    assert illusts == [{"id": 1, "total_bookmarks": 10}]


@pytest.mark.asyncio
async def test_search_sorts_by_bookmarks_desc() -> None:
    client = _WindowClient(
        [[
            {"id": "low", "total_bookmarks": 12},
            {"id": "top", "total_bookmarks": 900},
            {"id": "mid", "total_bookmarks": 300},
            {"id": "none", "total_bookmarks": None},
        ]]
    )
    harness = _WindowHarness(client)
    illusts = await harness._search_tag_with_window("某标签", 0)
    assert [item["id"] for item in illusts] == ["top", "mid", "low", "none"]


@pytest.mark.asyncio
async def test_search_widens_to_triple_window_when_empty() -> None:
    client = _WindowClient([[], [{"id": 2, "total_bookmarks": 7}]])
    harness = _WindowHarness(client)
    illusts = await harness._search_tag_with_window("冷门标签", 0)
    assert [call[2] for call in client.calls] == [
        _expected_start(1095),
        _expected_start(3285),
    ]
    assert illusts == [{"id": 2, "total_bookmarks": 7}]


@pytest.mark.asyncio
async def test_search_falls_back_to_unlimited_window() -> None:
    client = _WindowClient(
        [
            [],
            [],
            [
                {"id": "old", "total_bookmarks": 5},
                {"id": "new", "total_bookmarks": 800},
            ],
        ]
    )
    harness = _WindowHarness(client)
    illusts = await harness._search_tag_with_window("超冷门标签", 0)
    assert [call[2] for call in client.calls] == [
        _expected_start(1095),
        _expected_start(3285),
        None,
    ]
    # 放宽到不限的结果同样按收藏倒序
    assert [item["id"] for item in illusts] == ["new", "old"]


@pytest.mark.asyncio
async def test_zero_days_disables_window() -> None:
    client = _WindowClient([[{"id": 4, "total_bookmarks": 5}]])
    harness = _WindowHarness(client, config={"search_recent_days": 0})
    illusts = await harness._search_tag_with_window("原神", 0)
    assert client.calls == [("原神", 0, None, _expected_end())]
    assert illusts == [{"id": 4, "total_bookmarks": 5}]


@pytest.mark.asyncio
async def test_custom_window_days() -> None:
    client = _WindowClient([[{"id": 5, "total_bookmarks": 1}]])
    harness = _WindowHarness(client, config={"search_recent_days": 180})
    await harness._search_tag_with_window("原神", 0)
    assert client.calls == [("原神", 0, _expected_start(180), _expected_end())]


@pytest.mark.asyncio
async def test_empty_window_returns_empty() -> None:
    client = _WindowClient([[], [], []])
    harness = _WindowHarness(client)
    illusts = await harness._search_tag_with_window("无人问津", 0)
    assert len(client.calls) == 3  # 三年 → 九年 → 不限，逐级放宽后仍为空
    assert illusts == []
