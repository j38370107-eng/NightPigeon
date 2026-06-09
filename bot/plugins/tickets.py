import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands

from message_formatter import format_template, send_msg


class TicketCloseView(discord.ui.View):
    def __init__(self, bot, ticket_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_id = ticket_id
        self.custom_id = f"ticket_close_{ticket_id}"

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket_close_btn")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tickets_cog = self.bot.get_cog("Tickets")
        if tickets_cog:
            await tickets_cog._close_ticket(interaction, self.ticket_id)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple, custom_id="ticket_claim_btn")
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE tickets SET claimed_by=$1 WHERE id=$2", interaction.user.id, self.ticket_id)
        await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}", ephemeral=False)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.grey, custom_id="ticket_delete_btn")
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete(reason=f"Ticket deleted by {interaction.user}")


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _cfg(self, config):
        return config.get("plugins", {}).get("tickets", {})

    def _check(self, config, member, cmd):
        lvl = self.bot.get_cog("Levels")
        return (not lvl) or lvl.has_level(config, member, cmd)

    async def _close_ticket(self, ctx_or_interaction, ticket_id: int, reason: str = None):
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        guild = ctx_or_interaction.guild
        user = ctx_or_interaction.user if is_interaction else ctx_or_interaction.author
        config = await self.bot.config_loader.get_config(guild.id)
        cfg = self._cfg(config)
        msgs = cfg.get("messages", {})

        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM tickets WHERE id=$1 AND status='open'", ticket_id)
            if not row:
                return
            await conn.execute("UPDATE tickets SET status='closed', closed_at=$1 WHERE id=$2", datetime.now(timezone.utc), ticket_id)

        # Generate transcript
        channel = guild.get_channel(row["channel_id"])
        transcript_lines = []
        if channel:
            try:
                msgs_list = [m async for m in channel.history(limit=500, oldest_first=True)]
                for m in msgs_list:
                    transcript_lines.append(f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author}: {m.content}")
            except Exception:
                pass

        transcript = "\n".join(transcript_lines)

        # Send transcript to DM and channel
        ticket_user = guild.get_member(row["user_id"])
        if ticket_user and cfg.get("dm_transcript") and transcript:
            try:
                dm = await ticket_user.create_dm()
                for chunk in [transcript[i:i+1900] for i in range(0, len(transcript), 1900)][:5]:
                    await dm.send(f"```\n{chunk}\n```")
            except Exception:
                pass

        tc = cfg.get("transcript_channel")
        if tc and transcript:
            tc_chan = guild.get_channel(int(tc))
            if tc_chan:
                for chunk in [transcript[i:i+1900] for i in range(0, len(transcript), 1900)][:5]:
                    try:
                        await tc_chan.send(f"**Ticket #{row['ticket_number']} Transcript:**\n```\n{chunk}\n```")
                    except Exception:
                        pass

        msg = msgs.get("ticket_closed", "Ticket closed by {mod} | Reason: {reason}")
        text = format_template(msg, mod=user, reason=reason or "No reason")

        if channel:
            try:
                await channel.send(text)
                await asyncio.sleep(5)
                await channel.delete(reason="Ticket closed")
            except Exception:
                pass

    @commands.group(name="ticket", invoke_without_command=True)
    async def ticket_cmd(self, ctx):
        await ctx.send("Usage: `!ticket close/claim/delete/adduser/removeuser/rename/transcript/panel/blacklist`")

    @ticket_cmd.command(name="close")
    async def ticket_close(self, ctx, *, reason: str = None):
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id FROM tickets WHERE channel_id=$1 AND status='open'", ctx.channel.id)
        if not row:
            config = await self.bot.config_loader.get_config(ctx.guild.id)
            await ctx.send(self._cfg(config).get("messages", {}).get("not_a_ticket", "This command can only be used inside a ticket channel"))
            return
        await self._close_ticket(ctx, row["id"], reason)

    @ticket_cmd.command(name="claim")
    async def ticket_claim(self, ctx):
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id FROM tickets WHERE channel_id=$1 AND status='open'", ctx.channel.id)
        if not row:
            await ctx.send("Not a ticket channel")
            return
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "ticket_claim"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE tickets SET claimed_by=$1 WHERE id=$2", ctx.author.id, row["id"])
        await ctx.send(format_template(self._cfg(config).get("messages", {}).get("ticket_claimed", "Ticket claimed by {mod.mention}"), mod=ctx.author))

    @ticket_cmd.command(name="adduser")
    async def ticket_adduser(self, ctx, member: discord.Member):
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id FROM tickets WHERE channel_id=$1 AND status='open'", ctx.channel.id)
        if not row:
            await ctx.send("Not a ticket channel")
            return
        overwrite = ctx.channel.overwrites_for(member)
        overwrite.send_messages = True
        overwrite.view_channel = True
        await ctx.channel.set_permissions(member, overwrite=overwrite)
        async with self.bot.pool.acquire() as conn:
            await conn.execute("INSERT INTO ticket_participants (ticket_id, user_id, added_by) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
                               row["id"], member.id, ctx.author.id)
        await ctx.send(f"{member.mention} has been added to the ticket")

    @ticket_cmd.command(name="removeuser")
    async def ticket_removeuser(self, ctx, member: discord.Member):
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id FROM tickets WHERE channel_id=$1 AND status='open'", ctx.channel.id)
        if not row:
            return
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(f"{member.mention} has been removed from the ticket")

    @ticket_cmd.command(name="rename")
    async def ticket_rename(self, ctx, *, name: str):
        try:
            await ctx.channel.edit(name=name)
            await ctx.send(f"Ticket renamed to `{name}`")
        except Exception as e:
            await ctx.send(f"Error: {e}")

    @ticket_cmd.command(name="blacklist")
    async def ticket_blacklist_cmd(self, ctx, member: discord.Member = None, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "ticket_blacklist"):
            return
        if not member:
            # List blacklisted users
            async with self.bot.pool.acquire() as conn:
                rows = await conn.fetch("SELECT user_id, reason FROM ticket_blacklist WHERE guild_id=$1", ctx.guild.id)
            if not rows:
                msgs = self._cfg(config).get("messages", {})
                await ctx.send(msgs.get("blacklist_list_empty", "No users blacklisted from tickets"))
                return
            lines = [f"<@{r['user_id']}> — {r['reason'] or 'No reason'}" for r in rows]
            await ctx.send("**Ticket Blacklist:**\n" + "\n".join(lines))
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO ticket_blacklist (guild_id, user_id, reason, moderator_id) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING",
                ctx.guild.id, member.id, reason, ctx.author.id
            )
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(format_template(msgs.get("blacklist_success", "{user} has been blacklisted from tickets | Reason: {reason}"),
                                       user=member, reason=reason or "No reason"))

    @ticket_cmd.command(name="unblacklist")
    async def ticket_unblacklist_cmd(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "ticket_unblacklist"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM ticket_blacklist WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(format_template(msgs.get("unblacklist_success", "{user} removed from blacklist"), user=member))

    @ticket_cmd.group(name="panel", invoke_without_command=True)
    async def ticket_panel_group(self, ctx):
        await ctx.send("Usage: `!ticket panel create/addcategory/post/delete/list`")

    @ticket_panel_group.command(name="create")
    async def panel_create(self, ctx, name: str, panel_type: str = "button", channel: discord.TextChannel = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "ticket_panel"):
            return
        target = channel or ctx.channel
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO ticket_panels (guild_id, channel_id, panel_name, panel_type) VALUES ($1,$2,$3,$4) RETURNING id",
                ctx.guild.id, target.id, name, panel_type
            )
        await ctx.send(f"Ticket panel **{name}** created (ID: {row['id']})")

    @ticket_panel_group.command(name="post")
    async def panel_post(self, ctx, name: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "ticket_panel"):
            return
        async with self.bot.pool.acquire() as conn:
            panel = await conn.fetchrow("SELECT * FROM ticket_panels WHERE guild_id=$1 AND panel_name=$2", ctx.guild.id, name)
        if not panel:
            await ctx.send(f"Panel `{name}` not found")
            return

        channel = ctx.guild.get_channel(panel["channel_id"]) or ctx.channel

        async with self.bot.pool.acquire() as conn:
            categories = await conn.fetch("SELECT * FROM ticket_categories WHERE panel_id=$1 ORDER BY id", panel["id"])

        if panel["panel_type"] == "button":
            view = discord.ui.View(timeout=None)
            for cat in categories:
                btn = discord.ui.Button(label=cat["label"] or "Open Ticket",
                                        emoji=cat["emoji"] if cat["emoji"] else None,
                                        style=discord.ButtonStyle.blurple,
                                        custom_id=f"ticket_open_{panel['id']}_{cat['id']}")
                view.add_item(btn)
            if not categories:
                btn = discord.ui.Button(label="Open Ticket", style=discord.ButtonStyle.blurple,
                                        custom_id=f"ticket_open_{panel['id']}_0")
                view.add_item(btn)

            msg = await channel.send(panel["description"] or "**Open a ticket:**", view=view)
        else:
            options = [discord.SelectOption(label=cat["label"] or "Support", description=cat["description"] or "",
                                             emoji=cat["emoji"] if cat["emoji"] else None,
                                             value=str(cat["id"])) for cat in categories]
            if not options:
                options = [discord.SelectOption(label="Support", value="0")]
            select = discord.ui.Select(placeholder="Choose a category...", options=options, custom_id=f"ticket_select_{panel['id']}")
            view = discord.ui.View(timeout=None)
            view.add_item(select)
            msg = await channel.send(panel["description"] or "**Open a ticket:**", view=view)

        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE ticket_panels SET message_id=$1 WHERE id=$2", msg.id, panel["id"])
        await ctx.send(f"Panel **{name}** posted")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data:
            return
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("ticket_open_") or custom_id.startswith("ticket_select_"):
            await self._handle_ticket_open(interaction, custom_id)

    async def _handle_ticket_open(self, interaction: discord.Interaction, custom_id: str):
        guild = interaction.guild
        user = interaction.user
        config = await self.bot.config_loader.get_config(guild.id)
        cfg = self._cfg(config)
        msgs = cfg.get("messages", {})

        # Check blacklist
        async with self.bot.pool.acquire() as conn:
            bl = await conn.fetchrow("SELECT reason FROM ticket_blacklist WHERE guild_id=$1 AND user_id=$2", guild.id, user.id)
        if bl:
            await interaction.response.send_message(
                format_template(msgs.get("ticket_blacklisted", "You are blacklisted from opening tickets | Reason: {reason}"), reason=bl["reason"]),
                ephemeral=True
            )
            return

        # Check existing open ticket
        max_open = cfg.get("max_open_per_user", 1)
        async with self.bot.pool.acquire() as conn:
            open_count = await conn.fetchval("SELECT COUNT(*) FROM tickets WHERE guild_id=$1 AND user_id=$2 AND status='open'", guild.id, user.id)
        if open_count >= max_open:
            async with self.bot.pool.acquire() as conn:
                existing = await conn.fetchrow("SELECT channel_id FROM tickets WHERE guild_id=$1 AND user_id=$2 AND status='open' LIMIT 1", guild.id, user.id)
            chan_mention = f"<#{existing['channel_id']}>" if existing else "your existing ticket"
            await interaction.response.send_message(
                msgs.get("ticket_already_open", "You already have an open ticket at {channel.mention}").replace("{channel.mention}", chan_mention),
                ephemeral=True
            )
            return

        # Extract panel_id from custom_id
        parts = custom_id.split("_")
        panel_id = int(parts[2]) if len(parts) > 2 else 0

        async with self.bot.pool.acquire() as conn:
            panel = await conn.fetchrow("SELECT * FROM ticket_panels WHERE id=$1", panel_id)
            ticket_num = (await conn.fetchval("SELECT COALESCE(MAX(ticket_number), 0) + 1 FROM tickets WHERE guild_id=$1", guild.id))

        # Find category
        category = guild.get_channel(panel["category_id"]) if panel and panel.get("category_id") else None

        # Create channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        channel_name = f"ticket-{ticket_num:04d}"

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket opened by {user}"
            )
        except Exception as e:
            await interaction.response.send_message(f"Failed to create ticket: {e}", ephemeral=True)
            return

        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO tickets (guild_id, channel_id, user_id, panel_id, ticket_number) VALUES ($1,$2,$3,$4,$5) RETURNING id",
                guild.id, ticket_channel.id, user.id, panel_id, ticket_num
            )

        ticket_id = row["id"]

        # Welcome message + buttons
        welcome_msg = "Thank you for opening a ticket! A moderator will be with you shortly."
        await ticket_channel.send(f"{user.mention}\n{welcome_msg}", view=TicketCloseView(self.bot, ticket_id))

        await interaction.response.send_message(
            format_template(msgs.get("ticket_opened", "Your ticket has been opened in {channel.mention}"), channel=ticket_channel),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
