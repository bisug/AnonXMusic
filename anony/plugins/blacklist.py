# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import StopPropagation, filters, types

from anony import anon, app, db, lang, logger


# Central enforcement: blacklisted chats are fully ignored. A guard in the
# lowest handler group swallows every update from them before any command,
# service-message, or callback handler in group >= 0 can run.
@app.on_message(app.bl_chats, group=-1)
async def _bl_chat_guard(_, __):
    raise StopPropagation


_bl_chat_cb = filters.create(
    lambda _, __, q: q.message is not None
    and getattr(q.message, "chat", None) is not None
    and q.message.chat.id in app.bl_chats
)


@app.on_callback_query(_bl_chat_cb, group=-1)
async def _bl_chat_cb_guard(_, __):
    raise StopPropagation


@app.on_message(filters.command(["blacklist", "unblacklist", "whitelist"]) & app.sudoers)
@lang.language()
async def _blacklist(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["bl_usage"].format(m.command[0]))

    try:
        chat_id = m.command[1]
        if not str(chat_id).startswith("@"):
            chat_id = int(chat_id)
        else:
            chat_id = (await app.get_chat(chat_id)).id
    except Exception as ex:
        logger.warning("Blacklist target resolution failed for %r: %r", m.command[1], ex)
        return await m.reply_text(m.lang["bl_invalid"])

    # mongo.add_blacklist classifies by a leading "-" (chat vs user); mirror it
    # so the runtime filter matches what gets persisted.
    is_chat = str(chat_id).startswith("-")
    runtime = app.bl_chats if is_chat else app.bl_users

    if m.command[0] == "blacklist":
        if chat_id in db.blacklisted or chat_id in app.bl_users:
            return await m.reply_text(m.lang["bl_already"])
        runtime.add(chat_id)
        await db.add_blacklist(chat_id)
        if is_chat and chat_id in db.active_calls:
            await anon.stop(chat_id)
        await m.reply_text(m.lang["bl_added"])
    else:
        if chat_id not in db.blacklisted and chat_id not in app.bl_users:
            return await m.reply_text(m.lang["bl_not"])
        runtime.discard(chat_id)
        await db.del_blacklist(chat_id)
        await m.reply_text(m.lang["bl_removed"])
