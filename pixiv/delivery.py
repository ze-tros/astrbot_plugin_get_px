from __future__ import annotations

import asyncio

from astrbot.api.all import Image, Plain, logger
from astrbot.api.event import AstrMessageEvent

LOG_PREFIX = "[GetPx]"


def rotate_image_180(path: str) -> str | None:
    """把图片原地旋转 180 度并保持原格式，失败返回 None。"""
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as im:
            fmt = im.format or "PNG"
            rotated = im.rotate(180)
        rotated.save(path, format=fmt)
        return path
    except Exception:
        return None


class DeliveryMixin:
    """提供发送失败时的用户友好提示与旋转重发。"""

    @staticmethod
    def _friendly_send_error(error: Exception) -> str:
        """生成友善的发送错误提示。"""
        error_str = str(error).lower()
        if isinstance(error, asyncio.TimeoutError) or "timeout" in error_str:
            return "图片上传超时，可能是图片太大或网络较慢，建议降低图片质量设置"
        if "cdn" in error_str or "upload" in error_str:
            return "图片上传到服务器失败，请稍后再试"
        if "network" in error_str or "connect" in error_str:
            return "网络连接异常，请检查网络后重试"
        return "发送失败，请稍后再试"

    async def _resend_with_rotation(
        self,
        event: AstrMessageEvent,
        *,
        path: str,
        title: str,
        illust_id: str,
    ) -> bool:
        """常规重试耗尽后，把图片旋转 180 度再发送一次。

        旋转会改变文件字节，可绕开部分平台对同一图片文件的重复拦截。
        返回是否发送成功。"""
        rotated_path = await asyncio.to_thread(rotate_image_180, path)
        if rotated_path is None:
            logger.warning(
                f"{LOG_PREFIX} 图片旋转失败，放弃旋转重发: "
                f"illust_id={illust_id}"
            )
            return False
        content = [
            Plain(f"🎨 {title} (ID: {illust_id})"),
            Image.fromFileSystem(rotated_path),
        ]
        try:
            await event.send(event.chain_result(content))
            logger.info(f"{LOG_PREFIX} 作品旋转重发成功: illust_id={illust_id}")
            return True
        except Exception as exc:
            logger.warning(
                f"{LOG_PREFIX} 作品旋转重发失败: "
                f"illust_id={illust_id} error_type={type(exc).__name__}"
            )
            return False
