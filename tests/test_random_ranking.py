"""「男性向」按会话分级回退 Pixiv 月榜 / R18 周榜的回归测试。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_get_px.pixiv.safety import ContentSafetyPolicy
from astrbot_plugin_get_px.pixiv.search import SearchMixin


class _RankingClient:
    def __init__(self, ranking_pages=None):
        self.ranking_calls = []
        self.search_calls = []
        self.recommended_calls = []
        self.ranking_pages = list(ranking_pages or [])

    async def ranking(self, mode, offset=0):
        self.ranking_calls.append((mode, offset))
        if self.ranking_pages:
            return self.ranking_pages.pop(0)
        return [{"id": f"r-{mode}-{offset}"}]

    async def search(self, tag, offset=0, start_date=None, end_date=None):
        self.search_calls.append((tag, offset, start_date, end_date))
        return [{"id": f"s-{tag}"}]

    async def recommended(self, offset=0):
        self.recommended_calls.append(offset)
        return [{"id": "rec"}]


class _CursorIndex:
    def __init__(self, page_offset=0):
        self.page_offset = page_offset
        self.advances = []

    async def get_page_offset(self, scope, source_key):
        return self.page_offset

    async def advance_page_offset(self, scope, source_key, results_count):
        self.advances.append((source_key, results_count))
        return 0


class _FetchHarness(SearchMixin):
    def __init__(self, client, image_index=None, config=None):
        self.client = client
        self.image_index = image_index
        self.lolicon_client = None
        self.config = dict(config or {})

    def _cfg_int(self, key, default, lo, hi):
        try:
            val = int(self.config.get(key, default))
        except (TypeError, ValueError):
            return default
        return val if lo <= val <= hi else default

    def _init_client(self):
        pass


class _Event:
    def get_group_id(self):
        return "group:1"

    def get_sender_id(self):
        return "10001"


async def _fetch(harness, tag, offset=0, use_page_cursor=True, policy=None):
    return await harness._fetch_source_candidates(
        _Event(), tag, count=20, offset=offset, use_page_cursor=use_page_cursor,
        policy=policy or ContentSafetyPolicy(),
    )


@pytest.mark.asyncio
async def test_male_tag_uses_month_ranking() -> None:
    client = _RankingClient()
    harness = _FetchHarness(client)
    illusts, raw_count, source_key = await _fetch(harness, "男性向")
    assert client.ranking_calls == [("month", 0)]
    assert client.search_calls == []
    assert client.recommended_calls == []
    assert source_key == "pixiv:ranking:month"
    assert illusts == [{"id": "r-month-0"}]
    assert raw_count == 1


@pytest.mark.asyncio
async def test_male_tag_uses_week_r18_ranking_when_general_only_disabled() -> None:
    client = _RankingClient()
    harness = _FetchHarness(client)
    policy = ContentSafetyPolicy(general_only_enabled=False)
    illusts, _, source_key = await _fetch(harness, "男性向", policy=policy)
    assert client.ranking_calls == [("week_r18", 0)]
    assert source_key == "pixiv:ranking:week_r18"
    assert illusts == [{"id": "r-week_r18-0"}]


@pytest.mark.asyncio
async def test_male_tag_ranking_uses_page_cursor_offset() -> None:
    client = _RankingClient()
    index = _CursorIndex(page_offset=60)
    harness = _FetchHarness(client, image_index=index)
    _, _, source_key = await _fetch(harness, "男性向")
    assert client.ranking_calls == [("month", 60)]
    assert source_key == "pixiv:ranking:month"


@pytest.mark.asyncio
async def test_ranking_exhausted_page_wraps_cursor_and_refetches() -> None:
    client = _RankingClient(ranking_pages=[[], [{"id": "first-page"}]])
    index = _CursorIndex(page_offset=300)
    harness = _FetchHarness(client, image_index=index)
    illusts, _, source_key = await _fetch(harness, "男性向")
    assert client.ranking_calls == [("month", 300), ("month", 0)]
    assert index.advances == [("pixiv:ranking:month", 0)]
    assert illusts == [{"id": "first-page"}]
    assert source_key == "pixiv:ranking:month"


@pytest.mark.asyncio
async def test_other_tag_still_uses_popular_search() -> None:
    client = _RankingClient()
    harness = _FetchHarness(client)
    _, _, source_key = await _fetch(harness, "原神")
    assert client.search_calls[0][:2] == ("原神", 0)
    assert client.ranking_calls == []
    assert source_key == "pixiv:search:原神"


@pytest.mark.asyncio
async def test_empty_tag_still_uses_recommended() -> None:
    client = _RankingClient()
    harness = _FetchHarness(client)
    _, _, source_key = await _fetch(harness, "")
    assert client.recommended_calls == [0]
    assert client.ranking_calls == []
    assert source_key == "pixiv:recommended"
