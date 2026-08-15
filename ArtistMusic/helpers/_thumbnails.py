# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Type         : API Based Telegram Music Bot
#
# Bot          : @ArtistApibot
# Channel      : https://t.me/artistbots
# GitHub       : https://github.com/elevenyts/ArtistMusic
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================
import os
import asyncio
import aiohttp
from PIL import (
    Image,
    ImageDraw,
    ImageFilter,
    ImageFont
)
from ArtistMusic import config
from ArtistMusic.helpers import Track

SIZE = (1280, 720)
BRAND_TEXT = "✦ 𝗔𝗿𝘁𝗶𝘀𝘁𝗕𝗼𝘁𝘀 ✦"
BRAND_X = 40
BRAND_Y = 30
ACCENT_COLOR = (255, 196, 61, 255)   # warm gold accent for "X"
PILL_COLOR = (0, 0, 0, 110)          # translucent pill behind text


def _load_font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


class Thumbnail:
    def __init__(self):
        self.brand_font = _load_font(
            [
                "ArtistMusic/helpers/Raleway-BoldItalic.ttf",
                "ArtistMusic/helpers/Raleway-Bold.ttf",
            ],
            30
        )

    async def save_thumb(self, output_path: str, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(output_path, "wb") as f:
                    f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=SIZE) -> str:
        try:
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_ultra.png"
            if os.path.exists(output):
                return output
            await self.save_thumb(temp, song.thumbnail)
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._generate_sync,
                temp,
                output,
                song,
                size
            )
        except Exception:
            return config.DEFAULT_THUMB

    def _draw_brand(self, bg: Image.Image):
        """Draws an attractive glowing badge-style watermark on bg (RGBA)."""
        draw = ImageDraw.Draw(bg)

        # split text so "X" can be highlighted in accent color
        prefix, x_char, suffix = "✦ 𝗔𝗿𝘁𝗶𝘀𝘁𝗕𝗼𝘁𝘀 ✦"

        # measure full text box for the pill background
        full_text = prefix + x_char + suffix
        bbox = draw.textbbox((0, 0), full_text, font=self.brand_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        pad_x, pad_y = 22, 14
        pill_box = (
            BRAND_X - pad_x,
            BRAND_Y - pad_y,
            BRAND_X + text_w + pad_x,
            BRAND_Y + text_h + pad_y,
        )

        # 1. translucent rounded pill so text pops on any thumbnail
        pill_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        pill_draw = ImageDraw.Draw(pill_layer)
        pill_draw.rounded_rectangle(pill_box, radius=(text_h + pad_y * 2) // 2, fill=PILL_COLOR)
        bg.alpha_composite(pill_layer)

        # 2. soft glow behind the text (blurred duplicate)
        glow_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.text((BRAND_X, BRAND_Y), full_text, font=self.brand_font, fill=(255, 196, 61, 200))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(6))
        bg.alpha_composite(glow_layer)

        # 3. crisp drop shadow
        shadow_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        shadow_draw.text((BRAND_X + 2, BRAND_Y + 2), full_text, font=self.brand_font, fill=(0, 0, 0, 190))
        bg.alpha_composite(shadow_layer)

        # 4. final crisp text, drawn segment by segment for the accent color
        draw = ImageDraw.Draw(bg)
        cx = BRAND_X
        draw.text((cx, BRAND_Y), prefix, font=self.brand_font, fill=(255, 255, 255, 255))
        cx += draw.textlength(prefix, font=self.brand_font)
        draw.text((cx, BRAND_Y), x_char, font=self.brand_font, fill=ACCENT_COLOR)
        cx += draw.textlength(x_char, font=self.brand_font)
        draw.text((cx, BRAND_Y), suffix, font=self.brand_font, fill=(255, 255, 255, 255))

        return bg

    def _generate_sync(
        self,
        temp: str,
        output: str,
        song: Track,
        size=SIZE
    ) -> str:
        try:
            with Image.open(temp) as temp_img:
                src = temp_img.convert("RGBA")
                src_ratio = src.width / src.height
                dst_ratio = size[0] / size[1]
                if src_ratio > dst_ratio:
                    new_h = size[1]
                    new_w = int(new_h * src_ratio)
                else:
                    new_w = size[0]
                    new_h = int(new_w / src_ratio)
                resized = src.resize((new_w, new_h))
                left = (new_w - size[0]) // 2
                top = (new_h - size[1]) // 2
                bg = resized.crop(
                    (left, top, left + size[0], top + size[1])
                ).convert("RGBA")

            bg = self._draw_brand(bg)

            bg.convert("RGB").save(output)
            try:
                os.remove(temp)
            except OSError:
                pass
            return output
        except Exception:
            return config.DEFAULT_THUMB
