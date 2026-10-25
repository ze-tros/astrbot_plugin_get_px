"""Shared Pixiv delivery limits and platform identifiers."""

from zoneinfo import ZoneInfo

AIOCQHTTP_PLATFORM = "aiocqhttp"
MAX_IMAGE_COUNT = 20
DEFAULT_RANDOM_TAG = "男性向"
DEFAULT_SEARCH_RECENT_DAYS = 90
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
# 「男性向」在 Pixiv 侧映射到官方男性向日榜：全年代热门排序会返回老图，
# 日榜则是"最近一两天 + 高收藏"的作品池，同时满足新图与质量要求。
PIXIV_MALE_DAILY_RANKING_MODE = "day_male"
PIXIV_MALE_DAILY_RANKING_SOURCE_KEY = "pixiv:ranking:day_male"
