"""Shared Pixiv delivery limits and platform identifiers."""

from zoneinfo import ZoneInfo

AIOCQHTTP_PLATFORM = "aiocqhttp"
MAX_IMAGE_COUNT = 20
DEFAULT_RANDOM_TAG = "男性向"
DEFAULT_SEARCH_RECENT_DAYS = 90
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
# 无标签随机图在 Pixiv 侧映射到官方月榜：综合月榜没有男性向分榜，但池子
# 比日榜更大，同为近期高收藏作品，重复率更低。
PIXIV_RANDOM_RANKING_MODE = "month"
PIXIV_RANDOM_RANKING_SOURCE_KEY = "pixiv:ranking:month"
