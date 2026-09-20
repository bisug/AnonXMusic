# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


import time

from pyrogram import enums, types

from melody import config, logger
from melody.helpers import utils


def progress_line(played: str, duration: str, steps: int = 10) -> str:
    """`01:23 ————◉——————— 03:45` bar; same math as the inline timer."""
    cur = utils.to_seconds(played)
    total = utils.to_seconds(duration)
    pos = min(int((cur / total) * steps), steps - 1) if total > 0 else 0
    bar = "—" * pos + "◉" + "—" * (steps - pos - 1)
    return f"{played} {bar} {duration}"


def _time(sec: int) -> str:
    return time.strftime("%M:%S", time.gmtime(sec))


def build_np(
    lang: dict,
    media,
    chat_id: int,
    playing: bool = True,
    played: str = None,
    thumb: str = None,
    photo: bool = True,
):
    """Build the rich now-playing panel for `media`.

    photo=False drops the picture block (chats where the bot can't send media).
    """
    blocks = []
    if photo:
        image = thumb or media.thumbnail or config.DEFAULT_THUMB
        blocks.append(
            types.InputRichBlockPhoto(photo=types.InputMediaPhoto(image))
        )

    if media.url:
        blocks.append(
            types.InputRichBlockParagraph(
                text=types.RichTextUrl(text=media.title or "Unknown", url=media.url)
            )
        )
    else:
        blocks.append(
            types.InputRichBlockParagraph(
                text=types.RichTextBold(text=media.title or "Unknown")
            )
        )

    meta = "🔴 LIVE" if media.is_live else media.duration
    blocks.append(
        types.InputRichBlockParagraph(
            text=f"{meta} • {lang['rich_requested'].format(media.user or 'Unknown')}"
        )
    )

    if not media.is_live and played:
        blocks.append(
            types.InputRichBlockButtons(
                buttons=[
                    types.RichMessageButton(
                        text=progress_line(played, media.duration),
                        callback_data=f"controls status {chat_id}",
                    )
                ]
            )
        )

    blocks.append(
        types.InputRichBlockButtons(
            buttons=[
                types.RichMessageButton(
                    text=lang["rich_pause"] if playing else lang["rich_resume"],
                    style=(
                        enums.ButtonStyle.PRIMARY
                        if playing
                        else enums.ButtonStyle.SUCCESS
                    ),
                    callback_data=f"controls {'pause' if playing else 'resume'} {chat_id}",
                ),
                types.RichMessageButton(
                    text=lang["rich_replay"],
                    callback_data=f"controls replay {chat_id}",
                ),
                types.RichMessageButton(
                    text=lang["rich_skip"],
                    callback_data=f"controls skip {chat_id}",
                ),
                types.RichMessageButton(
                    text=lang["rich_stop"],
                    style=enums.ButtonStyle.DANGER,
                    callback_data=f"controls stop {chat_id}",
                ),
            ]
        )
    )
    return types.InputRichMessage(blocks=blocks)


async def edit_placeholder(
    message: types.Message, chat_id: int, media, lang: dict, thumb: str = None
) -> bool:
    """Swap the placeholder message for the rich panel; False on any failure
    (caller falls back to the classic text + inline-keyboard UI)."""
    if not config.RICH_UI:
        return False

    played = "00:00" if media.duration_sec else None
    try:
        await message.edit_text(
            rich_message=build_np(lang, media, chat_id, played=played, thumb=thumb)
        )
        return True
    except Exception as ex:
        logger.warning("rich panel send failed for %s: %r", chat_id, ex)
        # Bot may lack photo rights in this chat: retry without the picture.
        try:
            await message.edit_text(
                rich_message=build_np(
                    lang, media, chat_id, played=played, thumb=thumb, photo=False
                )
            )
            return True
        except Exception as ex:
            logger.warning("rich panel fallback failed for %s: %r", chat_id, ex)
            return False


async def refresh_np(
    chat_id: int, playing: bool = None, message: types.Message = None
):
    """Re-render the current track's rich panel (progress or pause state)."""
    from melody import app, db, lang, queue

    if not config.RICH_UI:
        return None
    media = queue.get_current(chat_id)
    if not media or not media.rich_ui or not media.message_id:
        return None

    if playing is None:
        playing = await db.playing(chat_id)
    played = _time(min(media.time, media.duration_sec)) if media.duration_sec else None
    _lang = await lang.get_lang(chat_id)
    rich = build_np(_lang, media, chat_id, playing=playing, played=played)
    try:
        if message is not None:
            return await message.edit_text(rich_message=rich)
        return await app.edit_message_text(
            chat_id=chat_id, message_id=media.message_id, rich_message=rich
        )
    except Exception as ex:
        logger.warning("rich refresh failed for %s: %r", chat_id, ex)
        return None
