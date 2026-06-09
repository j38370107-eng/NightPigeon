import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import discord
from discord.ext import commands

from message_formatter import format_template, send_dm
from duration_parser import parse_duration


class Escalation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {guild_id: {user_id: {rule_name: {"count": int, "last": datetime}}}}
        self._automod_counts: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"count": 0, "last": None})))

    async def _apply_action(self, guild: discord.Guild, member, action: str, reason: str, duration: str = None):
        mod = self.bot.get_cog("Moderation")
        if not mod or not member:
            return
        mute_role_id = None
        config = await self.bot.config_loader.get_config(guild.id)
        cfg_mod = config.get("plugins", {}).get("moderation", {})
        mute_role_id = cfg_mod.get("mute_role")

        if action == "warn":
            cases = self.bot.get_cog("Cases")
            if cases:
                await cases.create_case(guild.id, member.id, self.bot.user.id, "warn", reason)
        elif action == "mute" and mute_role_id:
            role = guild.get_role(int(mute_role_id))
            if role:
                td = None
                if duration:
                    td, _, _ = parse_duration(duration)
                expires = datetime.now(timezone.utc) + td if td else None
                try:
                    await member.add_roles(role, reason=reason)
                    async with self.bot.pool.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO mutes (guild_id, user_id, expires_at, removed_roles) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING",
                            guild.id, member.id, expires, []
                        )
                except Exception:
                    pass
        elif action == "kick":
            try:
                await member.kick(reason=reason)
            except Exception:
                pass
        elif action == "ban":
            td = None
            if duration:
                td, _, _ = parse_duration(duration)
            expires = datetime.now(timezone.utc) + td if td else None
            try:
                await guild.ban(member, reason=reason, delete_message_days=1)
                if expires:
                    async with self.bot.pool.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO temp_bans (guild_id, user_id, expires_at) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
                            guild.id, member.id, expires
                        )
            except Exception:
                pass

    async def check_manual(self, ctx, config: dict, member: discord.Member, action_type: str):
        esc_cfg = config.get("plugins", {}).get("escalation", {})
        if not esc_cfg.get("enabled") or not esc_cfg.get("manual", {}).get("enabled"):
            return

        async with self.bot.pool.acquire() as conn:
            all_cases = await conn.fetch(
                "SELECT action FROM cases WHERE guild_id=$1 AND user_id=$2",
                ctx.guild.id, member.id
            )

        case_counts = {}
        for row in all_cases:
            a = row["action"]
            case_counts[a] = case_counts.get(a, 0) + 1
        case_counts["any"] = len(all_cases)

        thresholds = esc_cfg.get("manual", {}).get("thresholds", [])
        msgs = esc_cfg.get("manual", {}).get("messages", {})

        for t in thresholds:
            tracked = t.get("tracked_type", "warn")
            count = t.get("count", 0)
            actual = case_counts.get(tracked, 0)
            if actual >= count:
                action = t.get("action", "warn")
                reason = t.get("reason", "Escalation triggered")
                duration = t.get("duration")
                await self._apply_action(ctx.guild, member, action, reason, duration)
                cases = self.bot.get_cog("Cases")
                case_id = 0
                if cases:
                    case_id = await cases.create_case(ctx.guild.id, member.id, self.bot.user.id, action, reason, duration)
                msg = msgs.get("escalation_triggered", "{user} has been {action}d due to repeated infractions | Case: {case_id}")
                await ctx.send(format_template(msg, user=member, action=action, case_id=str(case_id)))
                await send_dm(member, msgs.get("escalation_dm", "You have been {action}d in {server} for: {reason}"),
                              user=member, server=ctx.guild, action=action, reason=reason)

    async def check_automod(self, guild: discord.Guild, config: dict, member, rule_name: str, channel=None):
        esc_cfg = config.get("plugins", {}).get("escalation", {})
        if not esc_cfg.get("enabled") or not esc_cfg.get("automod", {}).get("enabled"):
            return

        reset_hours = esc_cfg.get("automod", {}).get("reset_after_hours", 24)
        bucket = self._automod_counts[guild.id][member.id][rule_name]
        now = datetime.now(timezone.utc)

        if bucket["last"] and (now - bucket["last"]) > timedelta(hours=reset_hours):
            bucket["count"] = 0

        bucket["count"] += 1
        bucket["last"] = now

        rule_thresholds = esc_cfg.get("automod", {}).get("rules", {}).get(rule_name, {}).get("thresholds", [])
        msgs = esc_cfg.get("automod", {}).get("messages", {})

        best = None
        for t in rule_thresholds:
            if bucket["count"] >= t.get("count", 0):
                best = t

        if best:
            action = best.get("action", "warn")
            reason = best.get("reason", f"Automod: {rule_name}")
            duration = best.get("duration")
            await self._apply_action(guild, member, action, reason, duration)
            cases = self.bot.get_cog("Cases")
            case_id = await cases.create_case(guild.id, member.id, self.bot.user.id, action, reason) if cases else 0
            msg = msgs.get("escalation_triggered", "{user} has been {action}d for repeated {rule} violations | Case: {case_id}")
            if channel:
                try:
                    await channel.send(format_template(msg, user=member, action=action, rule=rule_name, case_id=str(case_id)))
                except Exception:
                    pass
            await send_dm(member, msgs.get("escalation_dm", "You have been {action}d in {server} for: {reason}"),
                          user=member, server=guild, action=action, reason=reason)


async def setup(bot):
    await bot.add_cog(Escalation(bot))
