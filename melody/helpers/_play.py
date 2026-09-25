# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from pyrogram import enums, errors, types

from melody import anon, app, config, db, logger, queue, yt
from melody.helpers import utils


async def _safe_stream_url(url: str) -> bool:
    """Allow only http(s) URLs resolving to public addresses (SSRF guard).

    shortcut: DNS checked here, not by ffmpeg — a rebinding attacker could
    swap the record before playback. Blocks the common internal-target case.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    if config.STREAM_HOSTS and host.lower() not in config.STREAM_HOSTS:
        return False
    if not config.STREAM_HOSTS:
        return False

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM
        )
    except Exception as ex:
        logger.warning("Stream URL host resolution failed for %r: %s", host, ex)
        return False

    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            return False
    return True


async def join_assistant(m: types.Message, lang_dict: dict) -> bool:
    """Make sure the chat's assigned assistant has joined; False on failure.

    Shared by /play and channel play; replies with the error text itself.
    """
    chat_id = m.chat.id
    client = await db.get_client(chat_id)
    try:
        member = await app.get_chat_member(chat_id, client.id)
        if member.status in [
            enums.ChatMemberStatus.BANNED,
            enums.ChatMemberStatus.RESTRICTED,
        ]:
            try:
                await app.unban_chat_member(chat_id=chat_id, user_id=client.id)
            except Exception as ex:
                logger.error(f"Failed to unban assistant in {chat_id}: {ex}")
                await m.reply_text(
                    lang_dict["play_banned"].format(
                        app.name,
                        client.id,
                        client.mention,
                        f"@{client.username}" if client.username else None,
                    )
                )
                return False
    except errors.ChatAdminRequired:
        await m.reply_text(lang_dict["admin_required"])
        return False
    # Fresh sessions have no peer cache, so resolve_peer fails —
    # treat as "not a participant" and invite.
    except (errors.UserNotParticipant, errors.PeerIdInvalid):
        if m.chat.username:
            invite_link = m.chat.username
            try:
                await client.resolve_peer(invite_link)
            except Exception as ex:
                logger.warning(f"resolve_peer failed for {chat_id}: {ex}")
        else:
            try:
                invite_link = (await app.get_chat(chat_id)).invite_link
                if not invite_link:
                    invite_link = await app.export_chat_invite_link(chat_id)
            except errors.ChatAdminRequired:
                await m.reply_text(lang_dict["admin_required"])
                return False
            except Exception as ex:
                await m.reply_text(
                    lang_dict["play_invite_error"].format(type(ex).__name__)
                )
                return False

        umm = await m.reply_text(lang_dict["play_invite"].format(app.name))
        await asyncio.sleep(2)
        try:
            result = await client.join_chat(invite_link)
            # kurigram returns a request object instead of raising here.
            if isinstance(result, types.ChatJoinResultRequestSent):
                raise errors.InviteRequestSent
        except errors.UserAlreadyParticipant:
            pass
        except errors.InviteRequestSent:
            await asyncio.sleep(2)
            try:
                await app.approve_chat_join_request(chat_id, client.id)
            except errors.HideRequesterMissing:
                pass
            except Exception as ex:
                await umm.edit_text(
                    lang_dict["play_invite_error"].format(type(ex).__name__)
                )
                return False
        except Exception as ex:
            logger.error(f"Error joining chat - {chat_id}: {ex}")
            await umm.edit_text(lang_dict["play_invite_error"].format(type(ex).__name__))
            return False

        await umm.delete()
        await client.resolve_peer(chat_id)
    return True


def checkUB(play):
    async def wrapper(_, m: types.Message):
        if not m.from_user:
            return await m.reply_text(m.lang["play_user_invalid"])

        chat_id = m.chat.id
        if m.chat.type != enums.ChatType.SUPERGROUP:
            await m.reply_text(m.lang["play_chat_invalid"])
            return await app.leave_chat(chat_id)

        if not m.reply_to_message and (
            len(m.command) < 2 or (len(m.command) == 2 and m.command[1] == "-f")
        ):
            return await m.reply_text(m.lang["play_usage"])

        if queue.size(chat_id) >= config.QUEUE_LIMIT:
            return await m.reply_text(m.lang["play_queue_full"].format(config.QUEUE_LIMIT))

        force = m.command[0].endswith("force") or (
            len(m.command) > 1 and "-f" in m.command[1]
        )
        video = m.command[0][0] == "v" and config.VIDEO_PLAY
        shuffle = any(
            token.lower() in ("-shuffle", "-s") for token in m.command[1:]
        )
        url = utils.get_url(m)
        if url and yt.invalid(url):
            return await m.reply_text(m.lang["play_not_found"].format(config.SUPPORT_CHAT))
        m3u8 = url and not yt.valid(url)
        if m3u8 and not await _safe_stream_url(url):
            return await m.reply_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

        play_mode = await db.get_play_mode(chat_id)
        if play_mode or force:
            adminlist = await db.get_admins(chat_id)
            if (
                m.from_user.id not in adminlist
                and not await db.is_auth(chat_id, m.from_user.id)
                and not m.from_user.id in app.sudoers
            ):
                return await m.reply_text(m.lang["play_admin"])

        if chat_id not in db.active_calls:
            if not await join_assistant(m, m.lang):
                return

        if await db.get_cmd_delete(chat_id):
            try:
                await m.delete()
            except Exception:
                pass

        if chat_id in db.active_calls:
            return await play(_, m, force, m3u8, video, url, shuffle)

        async with anon.start_guard(chat_id) as allowed:
            if not allowed:
                return await m.reply_text(m.lang["processing"])
            return await play(_, m, force, m3u8, video, url, shuffle)

    return wrapper
