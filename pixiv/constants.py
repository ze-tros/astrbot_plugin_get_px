"""Shared Pixiv delivery limits and platform identifiers."""

from zoneinfo import ZoneInfo

AIOCQHTTP_PLATFORM = "aiocqhttp"
MAX_IMAGE_COUNT = 20
DEFAULT_RANDOM_TAG = "男性向"
DEFAULT_SEARCH_RECENT_DAYS = 1095
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
# 无标签随机图在 Pixiv 侧映射到官方排行榜：强制普通分级开启走综合月榜；
# 关闭时走 R18 周榜（Pixiv 无 R18 月榜分榜）。排行榜池子大、均为近期高收藏作品。
PIXIV_RANDOM_RANKING_MODE = "month"
PIXIV_RANDOM_RANKING_R18_MODE = "week_r18"
