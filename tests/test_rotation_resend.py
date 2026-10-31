"""发送失败后旋转 180 度重发的回归测试。"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PIL import Image as PILImage

from astrbot_plugin_get_px.pixiv.constants import MAX_IMAGE_COUNT
from astrbot_plugin_get_px.pixiv.delivery import DeliveryMixin, rotate_image_180
from astrbot_plugin_get_px.pixiv.search import SearchMixin


def _make_png(path: Path) -> str:
    im = PILImage.new("RGB", (2, 1))
    im.putpixel((0, 0), (255, 0, 0))
    im.putpixel((1, 0), (0, 0, 255))
    im.save(path, format="PNG")
    return str(path)


def test_rotate_image_180_flips_pixels_in_place(tmp_path: Path) -> None:
    target = tmp_path / "img.png"
    _make_png(target)
    result = rotate_image_180(str(target))
    assert result == str(target)
    with PILImage.open(target) as im:
        assert im.getpixel((0, 0)) == (0, 0, 255)
        assert im.getpixel((1, 0)) == (255, 0, 0)


def test_rotate_image_180_missing_file_returns_none(tmp_path: Path) -> None:
    assert rotate_image_180(str(tmp_path / "nope.png")) is None


class _ResendHarness(DeliveryMixin):
    pass


class _SendEvent:
    def __init__(self):
        self.sent = []

    def get_sender_id(self):
        return "10001"

    def get_group_id(self):
        return ""

    def plain_result(self, text):
        return f"plain:{text}"

    def chain_result(self, chain):
        return list(chain)

    async def send(self, chain):
        self.sent.append(chain)


@pytest.mark.asyncio
async def test_resend_with_rotation_success() -> None:
    harness = _ResendHarness()
    event = _SendEvent()
    png = _make_png(Path("/tmp/px_rotation_ok.png"))
    ok = await harness._resend_with_rotation(
        event, path=png, title="标题", illust_id="42"
    )
    assert ok is True
    assert len(event.sent) == 1


@pytest.mark.asyncio
async def test_resend_with_rotation_send_failure_returns_false() -> None:
    class _FailingEvent(_SendEvent):
        async def send(self, chain):
            raise RuntimeError("blocked")

    harness = _ResendHarness()
    event = _FailingEvent()
    png = _make_png(Path("/tmp/px_rotation_fail.png"))
    assert (
        await harness._resend_with_rotation(
            event, path=png, title="标题", illust_id="42"
        )
        is False
    )
    assert event.sent == []


class _RotationFlowHarness(SearchMixin, DeliveryMixin):
    """驱动 _handle_search 走到逐条发送，下载桩返回真实图片文件。"""

    def __init__(self, png_path: str, send_event: "_FlowSendEvent"):
        self.config = {"p_coin_cost": 0}
        self.image_index = None
        self.checkin_store = None
        self.png_path = png_path
        self.send_event = send_event

    def _cfg_int(self, key, default, lo, hi):
        try:
            val = int(self.config.get(key, default))
        except (TypeError, ValueError):
            return default
        return val if lo <= val <= hi else default

    def _cfg_float(self, key, default, lo, hi):
        try:
            return float(self.config.get(key, default))
        except (TypeError, ValueError):
            return default

    def _cfg_str(self, key, default=""):
        return str(self.config.get(key, default))

    def _cfg_bool(self, key, default):
        return bool(self.config.get(key, default))

    def _check_rate_limit(self, user_id):
        return 0

    def _forward_threshold(self):
        return MAX_IMAGE_COUNT

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
        self, event, illusts, pick_count, *, source_key,
        dedupe_enabled=True, raw_count=0,
    ):
        return illusts[:pick_count]

    async def _fetch_source_candidates(
        self, event, tag, *, count=20, offset=0, aspect_ratio="",
        use_page_cursor=True, policy=None,
    ):
        illusts = [{"id": "123:0", "title": "测试图"}]
        return illusts, len(illusts), "pixiv:ranking:month"

    class _Downloader:
        def __init__(self, png_path: str):
            self.png_path = png_path

        async def download_for_send(self, *args, **kwargs):
            return self.png_path, "original", 1024

    @property
    def downloader(self):
        return self._Downloader(self.png_path)


class _FlowSendEvent:
    """前 fail_count 次 send 抛错，之后成功；attempted 记录全部调用。"""

    def __init__(self, fail_count: int):
        self.fail_count = fail_count
        self.calls = 0
        self.attempted = []
        self.sent = []

    def get_sender_id(self):
        return "10001"

    def get_group_id(self):
        return "group:1"

    def get_platform_name(self):
        return "qq_official"

    def get_self_id(self):
        return "self-bot"

    def plain_result(self, text):
        return f"plain:{text}"

    def chain_result(self, chain):
        return list(chain)

    async def send(self, chain):
        self.calls += 1
        self.attempted.append(chain)
        if self.calls <= self.fail_count:
            raise RuntimeError("risk-control blocked")
        self.sent.append(chain)


@pytest.mark.asyncio
async def test_send_exhausted_retries_then_rotation_resend_succeeds(
    tmp_path: Path, monkeypatch
) -> None:
    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    png = _make_png(tmp_path / "illust.png")
    send_event = _FlowSendEvent(fail_count=3)
    harness = _RotationFlowHarness(png, send_event)
    results = [
        result
        async for result in harness._handle_search(
            send_event, tag="", count_str="1"
        )
    ]
    assert send_event.calls == 4  # 3 次常规重试 + 1 次旋转重发
    assert len(send_event.sent) == 1  # 旋转重发成功，图片已发出
    attempted_text = "".join(
        str(item) for chain in send_event.attempted for item in chain
    )
    assert "已跳过" not in attempted_text
    assert results == []  # 全程未输出报错文本


@pytest.mark.asyncio
async def test_rotation_resend_also_failing_sends_skip_message(
    tmp_path: Path, monkeypatch
) -> None:
    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    png = _make_png(tmp_path / "illust.png")
    send_event = _FlowSendEvent(fail_count=99)
    harness = _RotationFlowHarness(png, send_event)
    results = [
        result
        async for result in harness._handle_search(
            send_event, tag="", count_str="1"
        )
    ]
    assert send_event.calls == 5  # 3 次常规重试 + 1 次旋转重发 + 1 次跳过提示
    assert send_event.sent == []
    attempted_text = "".join(
        str(item) for chain in send_event.attempted for item in chain
    )
    assert "已跳过" in attempted_text
    assert results == []
