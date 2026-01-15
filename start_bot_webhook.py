#!/usr/bin/env python3
"""
Запуск Telegram бота через webhooks (для production)
"""
import asyncio
import logging
from main import bot_instance

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Запуск бота через webhooks"""
    try:
        logger.info("Запуск Telegram бота в режимі webhooks...")
        await bot_instance.start_webhook()
    except KeyboardInterrupt:
        logger.info("Отримано сигнал переривання")
    except Exception as e:
        logger.error(f"Помилка запуску webhook бота: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
