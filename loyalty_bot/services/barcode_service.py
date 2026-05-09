import asyncio
import io
from pathlib import Path
from uuid import UUID

import barcode
from barcode.writer import ImageWriter
from PIL import Image

from loyalty_bot.core.config import settings
from loyalty_bot.core.exceptions import BarcodeGenerationError
from loyalty_bot.core.logger import get_logger

logger = get_logger(__name__)

TARGET_WIDTH = 400
TARGET_HEIGHT = 150


class BarcodeService:
    """Генерация Code128 PNG и сохранение на диск."""

    def __init__(self, storage_path: str | Path = settings.BARCODE_STORAGE_PATH) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def generate(self, card_number: str, user_id: UUID) -> Path:
        # python-barcode и Pillow синхронные — уносим в thread pool, чтобы
        # не блокировать event loop при пике регистраций.
        return await asyncio.to_thread(self._generate_sync, card_number, user_id)

    def _generate_sync(self, card_number: str, user_id: UUID) -> Path:
        try:
            code128 = barcode.get_barcode_class("code128")
            writer = ImageWriter()
            instance = code128(card_number, writer=writer)

            buf = io.BytesIO()
            instance.write(
                buf,
                options={
                    "module_height": 12.0,
                    "module_width": 0.3,
                    "font_size": 10,
                    "text_distance": 3,
                    "quiet_zone": 2,
                    "background": "white",
                    "foreground": "black",
                    "write_text": True,
                },
            )
            buf.seek(0)

            # Приводим к фиксированному 400x150 на белом — бот всегда отдаёт
            # картинку одного формата.
            src = Image.open(buf).convert("RGB")
            canvas = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), "white")
            src.thumbnail((TARGET_WIDTH - 20, TARGET_HEIGHT - 20))
            offset = (
                (TARGET_WIDTH - src.width) // 2,
                (TARGET_HEIGHT - src.height) // 2,
            )
            canvas.paste(src, offset)

            out_path = self.storage_path / f"{user_id}.png"
            canvas.save(out_path, format="PNG", optimize=True)
            logger.info(
                "barcode_generated",
                card_number=card_number,
                user_id=str(user_id),
                path=str(out_path),
            )
            return out_path
        except Exception as exc:
            logger.exception("barcode_generation_failed", card_number=card_number)
            raise BarcodeGenerationError(str(exc)) from exc
