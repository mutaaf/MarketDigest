"""Send messages via python-telegram-bot."""

import asyncio

from telegram import Bot
from telegram.constants import ParseMode
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import get_settings
from src.digest.formatter import split_message
from src.utils.logging_config import get_logger

logger = get_logger("telegram")


class TelegramDelivery:
    def __init__(self):
        settings = get_settings()
        self._token = settings.telegram.bot_token
        self._chat_ids = settings.telegram.chat_ids

        if not self._token or not self._chat_ids:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")

    async def _send_message(self, text: str, chat_id: str) -> bool:
        """Send a single message (≤4096 chars) to a specific chat."""
        bot = Bot(token=self._token)
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return True
        except Exception as e:
            logger.error(f"Telegram send failed for chat {chat_id}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        reraise=True,
    )
    async def _send_with_retry(self, text: str, chat_id: str) -> bool:
        return await self._send_message(text, chat_id)

    async def _send_to_chat(self, chat_id: str, messages: list[str]) -> bool:
        """Send all message parts to a single chat ID."""
        success = True
        for i, msg in enumerate(messages):
            try:
                await self._send_with_retry(msg, chat_id)
                logger.info(f"Chat {chat_id}: part {i + 1}/{len(messages)} sent ({len(msg)} chars)")
                if i < len(messages) - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Chat {chat_id}: failed to send part {i + 1}: {e}")
                success = False
        return success

    async def send_digest(self, content: str) -> dict[str, bool]:
        """Send digest content to all recipients, auto-splitting if needed."""
        messages = split_message(content)
        logger.info(f"Sending digest ({len(messages)} part(s), {len(content)} chars) to {len(self._chat_ids)} recipient(s)")

        results: dict[str, bool] = {}
        for idx, chat_id in enumerate(self._chat_ids):
            results[chat_id] = await self._send_to_chat(chat_id, messages)
            if idx < len(self._chat_ids) - 1:
                await asyncio.sleep(1)  # Brief pause between recipients

        succeeded = sum(1 for v in results.values() if v)
        logger.info(f"Digest delivered to {succeeded}/{len(results)} recipient(s)")
        return results

    def send_digest_sync(self, content: str) -> bool:
        """Synchronous wrapper for send_digest. Returns True if all succeeded."""
        results = asyncio.run(self.send_digest(content))
        return all(results.values())

    async def send_test_message(self, chat_id: str | None = None) -> bool:
        """Send a test message. If chat_id given, send to that one only; else send to all."""
        test_msg = (
            "🤖 <b>Market Digest Bot — Test Message</b>\n\n"
            "✅ Bot is connected and working!\n"
            "📊 Digests will be delivered to this chat.\n\n"
            "<i>Configuration verified successfully.</i>"
        )
        targets = [chat_id] if chat_id else self._chat_ids
        try:
            for target in targets:
                await self._send_with_retry(test_msg, target)
            return True
        except Exception as e:
            logger.error(f"Test message failed: {e}")
            return False
