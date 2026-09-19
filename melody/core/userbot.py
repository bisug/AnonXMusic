# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


from pyrogram import Client

from melody import config, logger


class Userbot(Client):
    def __init__(self):
        """Set up assistant clients from SESSION1/2/3."""
        self.clients = []
        clients = {"one": "SESSION1", "two": "SESSION2", "three": "SESSION3"}
        for key, string_key in clients.items():
            name = f"AnonyUB{key[-1]}"
            session = getattr(config, string_key)
            setattr(
                self,
                key,
                Client(
                    name=name,
                    api_id=config.API_ID,
                    api_hash=config.API_HASH,
                    session_string=session,
                ),
            )

    async def boot_client(self, num: int, ub: Client):
        """Start one assistant; SystemExit if it can't post to the log group."""
        clients = {
            1: self.one,
            2: self.two,
            3: self.three,
        }
        client = clients[num]
        await client.start()
        if client not in self.clients:
            self.clients.append(client)
        try:
            await client.send_message(config.LOGGER_ID, "Assistant Started")
        except Exception as ex:
            raise SystemExit(
                f"Assistant {num} failed to send message in log group "
                f"({config.LOGGER_ID}): {ex}\n"
                f"Fix: add the assistant account to the log group "
                f"and ensure it can post there."
            )

        client.id = ub.me.id
        client.name = ub.me.first_name
        client.username = ub.me.username
        client.mention = ub.me.mention
        try:
            await ub.join_chat(config.SUPPORT_CHANNEL)
        except Exception as ex:
            logger.debug("Assistant %s could not join support channel: %s", num, ex)
        logger.info(f"Assistant {num} started as @{client.username}")

    async def boot(self):
        """Start all configured assistants."""
        if config.SESSION1:
            await self.boot_client(1, self.one)
        if config.SESSION2:
            await self.boot_client(2, self.two)
        if config.SESSION3:
            await self.boot_client(3, self.three)

    async def join_support_channel(self):
        """Rejoin the support channel once the bot resolves its link."""
        for client in self.clients:
            try:
                await client.join_chat(config.SUPPORT_CHANNEL)
            except Exception as ex:
                logger.debug("Assistant could not join support channel: %s", ex)

    async def exit(self):
        """Stop all assistants."""
        configured = []
        if config.SESSION1:
            configured.append(self.one)
        if config.SESSION2:
            configured.append(self.two)
        if config.SESSION3:
            configured.append(self.three)

        clients = list(dict.fromkeys([*self.clients, *configured]))
        for client in reversed(clients):
            if getattr(client, "is_connected", False):
                await client.stop()
        self.clients.clear()
        logger.info("Assistants stopped.")
