"""
Обробник розсилок
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
import os
from pathlib import Path

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.error import TelegramError

from database.models import DatabaseManager, Broadcast, BroadcastQueue

logger = logging.getLogger(__name__)

# Шлях до завантажених файлів
PROJECT_ROOT = Path(__file__).parent.parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"


class BroadcastHandler:
    """Обробник для масових розсилок"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_processing = False
        self.delay_between_messages = 0.05  # 50ms затримка між повідомленнями (20 msg/sec)
    
    async def process_pending_broadcasts(self):
        """Обробити всі pending розсилки"""
        if self.is_processing:
            logger.info("Broadcast processing already in progress")
            return
        
        try:
            self.is_processing = True
            
            with DatabaseManager() as db:
                # Знаходимо pending розсилки
                pending_broadcasts = db.query(Broadcast).filter(
                    Broadcast.status == 'pending'
                ).order_by(Broadcast.created_at).all()
                
                for broadcast in pending_broadcasts:
                    await self._process_broadcast(broadcast)
                    
        except Exception as e:
            logger.error(f"Error processing broadcasts: {e}")
        finally:
            self.is_processing = False
    
    async def _process_broadcast(self, broadcast: Broadcast):
        """Обробити одну розсилку"""
        try:
            with DatabaseManager() as db:
                # Оновлюємо статус на processing
                broadcast.status = 'processing'
                broadcast.started_at = datetime.utcnow()
                db.commit()
            
            logger.info(f"Starting broadcast {broadcast.id} to {broadcast.total_recipients} users")
            
            # Список для збору помилок та всіх логів
            error_logs = []
            full_logs = []
            
            # Отримуємо чергу
            with DatabaseManager() as db:
                queue_items = db.query(BroadcastQueue).filter(
                    BroadcastQueue.broadcast_id == broadcast.id,
                    BroadcastQueue.status == 'pending'
                ).all()
                
                sent_count = 0
                failed_count = 0
                
                for item in queue_items:
                    try:
                        # Перевіряємо чи є message_blocks для відправки кількох повідомлень
                        if broadcast.message_blocks:
                            import json
                            blocks = json.loads(broadcast.message_blocks)
                            success = await self._send_multiple_messages(
                                telegram_id=item.telegram_id,
                                blocks=blocks
                            )
                        else:
                            # Стара система - одне повідомлення
                            success = await self._send_broadcast_message(
                                telegram_id=item.telegram_id,
                                message_text=broadcast.message_text,
                                attachment_type=broadcast.attachment_type,
                                attachment_url=broadcast.attachment_url,
                                button_text=broadcast.button_text,
                                button_url=broadcast.button_url
                            )
                        
                        if success:
                            item.status = 'sent'
                            item.sent_at = datetime.utcnow()
                            sent_count += 1
                            # Додаємо успішний лог
                            success_detail = f"✓ User ID: {item.telegram_id} - Successfully sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                            full_logs.append(success_detail)
                        else:
                            item.status = 'failed'
                            item.error_message = 'Unknown error'
                            failed_count += 1
                            error_detail = f"✗ User ID: {item.telegram_id} - Failed: Unknown error"
                            full_logs.append(error_detail)
                            
                    except Exception as e:
                        item.status = 'failed'
                        error_msg = str(e)
                        item.error_message = error_msg
                        failed_count += 1
                        
                        # Додаємо детальний лог помилки
                        import traceback
                        error_detail = f"User ID: {item.telegram_id}\nError: {error_msg}\nTraceback:\n{traceback.format_exc()}\n{'='*50}"
                        error_logs.append(error_detail)
                        
                        # Додаємо короткий лог у загальний
                        full_log_entry = f"✗ User ID: {item.telegram_id} - Failed: {error_msg}"
                        full_logs.append(full_log_entry)
                        
                        logger.error(f"Error sending to {item.telegram_id}: {e}")
                    
                    # Затримка між повідомленнями
                    await asyncio.sleep(self.delay_between_messages)
                
                # Оновлюємо статистику
                broadcast.sent_count = sent_count
                broadcast.failed_count = failed_count
                broadcast.status = 'completed'
                broadcast.completed_at = datetime.utcnow()
                
                # Зберігаємо консолідований лог помилок
                if error_logs:
                    broadcast.error_log = "\n\n".join(error_logs)
                
                # Зберігаємо повний лог
                if full_logs:
                    full_log_header = f"Broadcast #{broadcast.id} - {broadcast.title or 'Untitled'}\n"
                    full_log_header += f"Started: {broadcast.started_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    full_log_header += f"Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    full_log_header += f"Total: {broadcast.total_recipients}, Sent: {sent_count}, Failed: {failed_count}\n"
                    full_log_header += "=" * 60 + "\n\n"
                    broadcast.full_log = full_log_header + "\n".join(full_logs)
                
                db.commit()
                
                logger.info(f"Broadcast {broadcast.id} completed: {sent_count} sent, {failed_count} failed")
                
        except Exception as e:
            logger.error(f"Error processing broadcast {broadcast.id}: {e}")
            
            with DatabaseManager() as db:
                broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast.id).first()
                if broadcast:
                    broadcast.status = 'failed'
                    db.commit()
    
    async def _send_broadcast_message(
        self,
        telegram_id: int,
        message_text: Optional[str],
        attachment_type: Optional[str],
        attachment_url: Optional[str],
        button_text: Optional[str],
        button_url: Optional[str]
    ) -> bool:
        """Відправити повідомлення одному користувачу"""
        try:
            # Створюємо клавіатуру якщо є посилання
            reply_markup = None
            if button_url and button_text:
                keyboard = [[InlineKeyboardButton(text=button_text, url=button_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Визначаємо чи це локальний файл чи URL
            is_local_file = False
            file_path = None
            
            if attachment_url:
                if attachment_url.startswith('/uploads/'):
                    # Це локальний файл
                    is_local_file = True
                    # Видаляємо /uploads/ з початку
                    relative_path = attachment_url.replace('/uploads/', '')
                    file_path = UPLOADS_DIR / relative_path
                    
                    if not file_path.exists():
                        logger.error(f"File not found: {file_path}")
                        return False
            
            # Відправляємо залежно від типу
            if attachment_type == 'image' and attachment_url:
                if is_local_file:
                    with open(file_path, 'rb') as photo_file:
                        await self.bot.send_photo(
                            chat_id=telegram_id,
                            photo=photo_file,
                            caption=message_text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown' if message_text else None
                        )
                else:
                    await self.bot.send_photo(
                        chat_id=telegram_id,
                        photo=attachment_url,
                        caption=message_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown' if message_text else None
                    )
                    
            elif attachment_type == 'video' and attachment_url:
                if is_local_file:
                    with open(file_path, 'rb') as video_file:
                        await self.bot.send_video(
                            chat_id=telegram_id,
                            video=video_file,
                            caption=message_text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown' if message_text else None,
                            supports_streaming=True
                        )
                else:
                    await self.bot.send_video(
                        chat_id=telegram_id,
                        video=attachment_url,
                        caption=message_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown' if message_text else None,
                        supports_streaming=True
                    )
                    
            elif attachment_type in ('file', 'document') and attachment_url:
                if is_local_file:
                    with open(file_path, 'rb') as doc_file:
                        await self.bot.send_document(
                            chat_id=telegram_id,
                            document=doc_file,
                            caption=message_text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown' if message_text else None
                        )
                else:
                    await self.bot.send_document(
                        chat_id=telegram_id,
                        document=attachment_url,
                        caption=message_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown' if message_text else None
                    )
                    
            elif message_text:
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                logger.warning(f"No content to send for broadcast to {telegram_id}")
                return False
            
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error sending to {telegram_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending to {telegram_id}: {e}")
            return False
    
    async def _send_multiple_messages(self, telegram_id: int, blocks: list) -> bool:
        """Відправити кілька повідомлень на основі блоків"""
        try:
            text_blocks = [b for b in blocks if b.get('type') == 'text']
            media_blocks = [b for b in blocks if b.get('type') in ('image', 'video', 'document')]
            button_blocks = [b for b in blocks if b.get('type') == 'button']
            
            # Якщо є текст та медіа, відправляємо перше повідомлення з текстом + перше медіа + кнопка
            if text_blocks and media_blocks:
                first_media = media_blocks[0]
                first_button = button_blocks[0] if button_blocks else None
                
                # Відправляємо перше повідомлення
                await self._send_single_message(
                    telegram_id=telegram_id,
                    text=text_blocks[0].get('content'),
                    media_type=first_media.get('type'),
                    media_url=first_media.get('fileUrl'),
                    button_text=first_button.get('buttonText') if first_button else None,
                    button_url=first_button.get('buttonUrl') if first_button else None
                )
                
                # Відправляємо решту медіа окремо
                for media in media_blocks[1:]:
                    await asyncio.sleep(0.1)  # Невелика затримка між повідомленнями
                    await self._send_single_message(
                        telegram_id=telegram_id,
                        text=None,
                        media_type=media.get('type'),
                        media_url=media.get('fileUrl'),
                        button_text=None,
                        button_url=None
                    )
            
            # Якщо є тільки медіа
            elif media_blocks:
                first_button = button_blocks[0] if button_blocks else None
                
                # Перше медіа з кнопкою
                await self._send_single_message(
                    telegram_id=telegram_id,
                    text=None,
                    media_type=media_blocks[0].get('type'),
                    media_url=media_blocks[0].get('fileUrl'),
                    button_text=first_button.get('buttonText') if first_button else None,
                    button_url=first_button.get('buttonUrl') if first_button else None
                )
                
                # Решта медіа без кнопок
                for media in media_blocks[1:]:
                    await asyncio.sleep(0.1)
                    await self._send_single_message(
                        telegram_id=telegram_id,
                        text=None,
                        media_type=media.get('type'),
                        media_url=media.get('fileUrl'),
                        button_text=None,
                        button_url=None
                    )
            
            # Якщо є тільки текст
            elif text_blocks:
                first_button = button_blocks[0] if button_blocks else None
                await self._send_single_message(
                    telegram_id=telegram_id,
                    text=text_blocks[0].get('content'),
                    media_type=None,
                    media_url=None,
                    button_text=first_button.get('buttonText') if first_button else None,
                    button_url=first_button.get('buttonUrl') if first_button else None
                )
            else:
                logger.warning(f"No content to send for broadcast to {telegram_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending multiple messages to {telegram_id}: {e}")
            return False
    
    async def _send_single_message(
        self,
        telegram_id: int,
        text: str = None,
        media_type: str = None,
        media_url: str = None,
        button_text: str = None,
        button_url: str = None
    ) -> bool:
        """Відправити одне повідомлення"""
        try:
            # Створюємо клавіатуру якщо є кнопка
            reply_markup = None
            if button_url and button_text:
                keyboard = [[InlineKeyboardButton(text=button_text, url=button_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Визначаємо чи це локальний файл
            is_local_file = False
            file_path = None
            
            if media_url:
                if media_url.startswith('/uploads/'):
                    is_local_file = True
                    relative_path = media_url.replace('/uploads/', '')
                    file_path = UPLOADS_DIR / relative_path
                    
                    if not file_path.exists():
                        logger.error(f"File not found: {file_path}")
                        return False
            
            # Відправляємо залежно від типу
            if media_type == 'image' and media_url:
                if is_local_file:
                    with open(file_path, 'rb') as photo_file:
                        await self.bot.send_photo(
                            chat_id=telegram_id,
                            photo=photo_file,
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown' if text else None
                        )
                else:
                    await self.bot.send_photo(
                        chat_id=telegram_id,
                        photo=media_url,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown' if text else None
                    )
                    
            elif media_type == 'video' and media_url:
                if is_local_file:
                    with open(file_path, 'rb') as video_file:
                        await self.bot.send_video(
                            chat_id=telegram_id,
                            video=video_file,
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown' if text else None,
                            supports_streaming=True
                        )
                else:
                    await self.bot.send_video(
                        chat_id=telegram_id,
                        video=media_url,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown' if text else None,
                        supports_streaming=True
                    )
                    
            elif media_type in ('file', 'document') and media_url:
                if is_local_file:
                    with open(file_path, 'rb') as doc_file:
                        await self.bot.send_document(
                            chat_id=telegram_id,
                            document=doc_file,
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown' if text else None
                        )
                else:
                    await self.bot.send_document(
                        chat_id=telegram_id,
                        document=media_url,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown' if text else None
                    )
                    
            elif text:
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending single message to {telegram_id}: {e}")
            raise
