import discord
from discord.ext import commands

from message_formatter import format_template


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _cfg(self, config):
        return config.get("plugins", {}).get("reaction_roles", {})

    def _check(self, config, member, cmd):
        lvl = self.bot.get_cog("Levels")
        return (not lvl) or lvl.has_level(config, member, cmd)

    @commands.group(name="rr", invoke_without_command=True)
    async def rr_cmd(self, ctx):
        await ctx.send("Usage: `!rr create/add/post/remove/edit/setmax/setrequired/delete/list/info`")

    @rr_cmd.command(name="create")
    async def rr_create(self, ctx, name: str, panel_type: str = "button", channel: discord.TextChannel = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "rr"):
            return
        target = channel or ctx.channel
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO reaction_role_panels (guild_id, channel_id, panel_name, panel_type) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING",
                ctx.guild.id, target.id, name, panel_type
            )
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(format_template(msgs.get("rr_created", "Panel {trigger} created"), trigger=name))

    @rr_cmd.command(name="add")
    async def rr_add(self, ctx, panel_name: str, role: discord.Role, emoji_or_label: str, *, description: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "rr"):
            return
        async with self.bot.pool.acquire() as conn:
            panel = await conn.fetchrow("SELECT id FROM reaction_role_panels WHERE guild_id=$1 AND panel_name=$2", ctx.guild.id, panel_name)
        if not panel:
            await ctx.send(format_template(self._cfg(config).get("messages", {}).get("rr_not_found", "Panel {trigger} not found"), trigger=panel_name))
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO reaction_role_entries (panel_id, guild_id, role_id, emoji, label, description) VALUES ($1,$2,$3,$4,$5,$6)",
                panel["id"], ctx.guild.id, role.id, emoji_or_label, role.name, description
            )
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(format_template(msgs.get("rr_entry_added", "Role {trigger} added to panel {reason}"),
                                       trigger=role.name, reason=panel_name))

    @rr_cmd.command(name="post")
    async def rr_post(self, ctx, panel_name: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "rr"):
            return
        async with self.bot.pool.acquire() as conn:
            panel = await conn.fetchrow("SELECT * FROM reaction_role_panels WHERE guild_id=$1 AND panel_name=$2", ctx.guild.id, panel_name)
        if not panel:
            msgs = self._cfg(config).get("messages", {})
            await ctx.send(format_template(msgs.get("rr_not_found", "Panel {trigger} not found"), trigger=panel_name))
            return

        async with self.bot.pool.acquire() as conn:
            entries = await conn.fetch("SELECT * FROM reaction_role_entries WHERE panel_id=$1 ORDER BY position, id", panel["id"])

        channel = ctx.guild.get_channel(panel["channel_id"]) or ctx.channel

        if panel["panel_type"] == "button":
            view = discord.ui.View(timeout=None)
            for entry in entries[:25]:
                btn = discord.ui.Button(
                    label=entry["label"] or "Get Role",
                    emoji=entry["emoji"] if entry["emoji"] and not entry["emoji"].startswith("<") else None,
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"rr_{panel['id']}_{entry['role_id']}"
                )
                view.add_item(btn)
            msg = await channel.send(panel["description"] or f"**{panel_name}**", view=view)

        elif panel["panel_type"] == "dropdown":
            options = []
            for entry in entries[:25]:
                options.append(discord.SelectOption(
                    label=entry["label"] or "Role",
                    description=entry["description"] or "",
                    emoji=entry["emoji"] if entry["emoji"] and len(entry["emoji"]) <= 2 else None,
                    value=str(entry["role_id"])
                ))
            if not options:
                await ctx.send("No entries in this panel")
                return
            select = discord.ui.Select(placeholder="Select a role...", options=options, custom_id=f"rr_select_{panel['id']}")
            view = discord.ui.View(timeout=None)
            view.add_item(select)
            msg = await channel.send(panel["description"] or f"**{panel_name}**", view=view)

        else:
            msg = await channel.send(panel["description"] or f"**{panel_name}**")
            for entry in entries:
                try:
                    await msg.add_reaction(entry["emoji"])
                except Exception:
                    pass

        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE reaction_role_panels SET message_id=$1 WHERE id=$2", msg.id, panel["id"])

        msgs = self._cfg(config).get("messages", {})
        await ctx.send(format_template(msgs.get("rr_posted", "Panel {trigger} posted in {channel.mention}"),
                                       trigger=panel_name, channel=channel))

    @rr_cmd.command(name="delete")
    async def rr_delete(self, ctx, panel_name: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "rr"):
            return
        async with self.bot.pool.acquire() as conn:
            row = await conn.execute("DELETE FROM reaction_role_panels WHERE guild_id=$1 AND panel_name=$2", ctx.guild.id, panel_name)
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(format_template(msgs.get("rr_deleted", "Panel {trigger} deleted"), trigger=panel_name))

    @rr_cmd.command(name="list")
    async def rr_list(self, ctx):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT panel_name, panel_type FROM reaction_role_panels WHERE guild_id=$1", ctx.guild.id)
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not rows:
            msgs = self._cfg(config).get("messages", {})
            await ctx.send(msgs.get("rr_list_empty", "No reaction role panels found"))
            return
        lines = [f"**{r['panel_name']}** ({r['panel_type']})" for r in rows]
        await ctx.send("**Reaction Role Panels:**\n" + "\n".join(lines))

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data:
            return
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("rr_"):
            await self._handle_rr_interaction(interaction, custom_id)

    async def _handle_rr_interaction(self, interaction: discord.Interaction, custom_id: str):
        guild = interaction.guild
        member = interaction.user
        config = await self.bot.config_loader.get_config(guild.id)
        msgs = self._cfg(config).get("messages", {})

        if custom_id.startswith("rr_select_"):
            panel_id = int(custom_id.split("_")[2])
            values = interaction.data.get("values", [])
            if not values:
                return
            role_id = int(values[0])
        else:
            parts = custom_id.split("_")
            panel_id = int(parts[1])
            role_id = int(parts[2])

        async with self.bot.pool.acquire() as conn:
            panel = await conn.fetchrow("SELECT * FROM reaction_role_panels WHERE id=$1", panel_id)
        if not panel:
            await interaction.response.send_message("Panel not found", ephemeral=True)
            return

        # Check required role
        required_id = panel.get("required_role")
        if required_id and not any(r.id == int(required_id) for r in member.roles):
            await interaction.response.send_message(
                format_template(msgs.get("rr_missing_required", "You need {trigger} to use this panel"), trigger=f"<@&{required_id}>"),
                ephemeral=True
            )
            return

        role = guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("Role not found", ephemeral=True)
            return

        if role in member.roles:
            await member.remove_roles(role, reason="Reaction role")
            await interaction.response.send_message(
                format_template(msgs.get("rr_role_removed", "You no longer have {trigger}"), trigger=role.name),
                ephemeral=True
            )
        else:
            # Check max roles
            max_roles = panel.get("max_roles", 0)
            if max_roles:
                async with self.bot.pool.acquire() as conn:
                    panel_roles = await conn.fetch("SELECT role_id FROM reaction_role_entries WHERE panel_id=$1", panel_id)
                panel_role_ids = {r["role_id"] for r in panel_roles}
                current_panel_roles = [r for r in member.roles if r.id in panel_role_ids]
                if len(current_panel_roles) >= max_roles:
                    await interaction.response.send_message(
                        msgs.get("rr_max_reached", "You have reached the maximum number of roles for this panel"),
                        ephemeral=True
                    )
                    return

            await member.add_roles(role, reason="Reaction role")
            await interaction.response.send_message(
                format_template(msgs.get("rr_role_given", "You have been given {trigger}"), trigger=role.name),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
