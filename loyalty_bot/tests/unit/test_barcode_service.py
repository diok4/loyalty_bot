import uuid
from pathlib import Path

import pytest
from PIL import Image

from loyalty_bot.services.barcode_service import (
    BarcodeService,
    TARGET_HEIGHT,
    TARGET_WIDTH,
)


@pytest.mark.asyncio
async def test_generate_creates_png(tmp_storage: Path):
    svc = BarcodeService(storage_path=tmp_storage)
    user_id = uuid.uuid4()

    path = await svc.generate("LC1234567890123456", user_id)

    assert path.exists()
    assert path.suffix == ".png"
    with Image.open(path) as img:
        assert img.size == (TARGET_WIDTH, TARGET_HEIGHT)
        assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_generate_filename_uses_user_id(tmp_storage: Path):
    svc = BarcodeService(storage_path=tmp_storage)
    user_id = uuid.uuid4()
    path = await svc.generate("LC0000000000000001", user_id)
    assert path.name == f"{user_id}.png"
