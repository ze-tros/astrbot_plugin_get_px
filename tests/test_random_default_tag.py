"""无标签请求套用 random_tag 默认搜索标签的回归测试。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_get_px.pixiv.search import SearchMixin


class _TagCaptureHarness(SearchMixin):
    """轻量桩：只记录 _fetch_source_candidates 收到的 tag，取空结果快速短路。"""

    def __init__(self, config=None):
        self.config = dict(config or {})
        self.image_index = None
        self.checkin_store = None
        self.downloader = None
        self.captured_tags = []

    def _cfg_int(self, key, default, lo, hi):
        try:
            val = int(self.config.get(key, default))
        except (TypeError, ValueError):
            return default
        return val if lo <= val <= hi else default

    def _cfg_float(self, key, default, lo, hi):
        try:
            val = float(self.config.get(key, default))
        except (TypeError, ValueError):
            return default
        return val if lo <= val <= hi else default

    def _cfg_str(self, key, default=""):
        return str(self.config.get(key, default))

    def _cfg_bool(self, key, default):
        return bool(self.config.get(key, default))

    def _check_rate_limit(self, user_id):
        return 0

    def _forward_threshold(self):
        return 0

    async def _content_safety_policy(self, event):
        from astrbot_plugin_get_px.pixiv.safety import ContentSafetyPolicy

        return ContentSafetyPolicy()

    async def _blocked_query_term(self, query, policy=None):
        return ""

    def _filter_manga(self, illusts):
        return illusts

    async def _filter_blacklisted_illusts(self, illusts, policy=None):
        return illusts

    async def _pick_illusts(
        self,
        event,
        illusts,
        pick_count,
        *,
        source_key,
        dedupe_enabled=True,
        raw_count=0,
    ):
        return illusts[:pick_count]

    async def _fetch_source_candidates(
        self,
        event,
        tag,
        *,
        count=20,
        offset=0,
        aspect_ratio="",
        use_page_cursor=True,
        policy=None,
    ):
        self.captured_tags.append(tag)
        return [], 0, "pixiv:random"


class _Event:
    def get_sender_id(self):
        return "10001"

    def get_group_id(self):
        return ""

    def plain_result(self, text):
        return f"plain:{text}"


async def _run_search(harness, tag=""):
    event = _Event()
    results = [
        result async for result in harness._handle_search(event, tag=tag, count_str="")
    ]
    return results


@pytest.mark.asyncio
async def test_empty_tag_uses_default_random_tag() -> None:
    harness = _TagCaptureHarness()
    await _run_search(harness)
    assert harness.captured_tags == ["男性向"]


@pytest.mark.asyncio
async def test_blank_tag_is_treated_as_empty() -> None:
    harness = _TagCaptureHarness()
    await _run_search(harness, tag="   ")
    assert harness.captured_tags == ["男性向"]


@pytest.mark.asyncio
async def test_user_tag_is_never_overridden() -> None:
    harness = _TagCaptureHarness()
    await _run_search(harness, tag="原神")
    assert harness.captured_tags == ["原神"]


@pytest.mark.asyncio
async def test_random_tag_config_override() -> None:
    harness = _TagCaptureHarness(config={"random_tag": "百合"})
    await _run_search(harness)
    assert harness.captured_tags == ["百合"]


@pytest.mark.asyncio
async def test_blank_random_tag_restores_pure_random() -> None:
    """random_tag 显式留空表示恢复无标签纯随机，不得回退到内置默认值。"""
    harness = _TagCaptureHarness(config={"random_tag": ""})
    await _run_search(harness)
    assert harness.captured_tags == [""]


@pytest.mark.asyncio
async def test_user_tag_whitespace_is_stripped() -> None:
    harness = _TagCaptureHarness()
    await _run_search(harness, tag="  原神  ")
    assert harness.captured_tags == ["原神"]
