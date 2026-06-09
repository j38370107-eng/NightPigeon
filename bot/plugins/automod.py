import re
import asyncio
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands

from message_formatter import format_template, send_dm


ZALGO_RE = re.compile(r'[\u0300-\u036f\u0489\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]')
INVITE_RE = re.compile(r'discord\.gg/\S+|discord\.com/invite/\S+', re.IGNORECASE)
LINK_RE = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
PHISHING_DOMAINS = ["discordnitro.gift", "steamcommunity.ru", "dlscord.io", "discordapp.gifts"]
FAKE_NITRO_RE = re.compile(r'discord\.gift|free.*nitro|nitro.*free', re.IGNORECASE)


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._spam_buckets: dict = defaultdict(list)
        self._link_buckets: dict = defaultdict(list)
        self._last_messages: dict = defaultdict(list)

    async def _is_immune(self, member: discord.Member) -> bool:
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT 1 FROM automod_immune WHERE guild_id=$1 AND user_id=$2", member.guild.id, member.id)
        return row is not None

    async def _is_ignored(self, member: discord.Member) -> bool:
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT 1 FROM ignored_users WHERE guild_id=$1 AND user_id=$2 AND (expires_at IS NULL OR expires_at > $3)",
                                      member.guild.id, member.id, datetime.now(timezone.utc))
        return row is not None

    def _in_ignore_list(self, member: discord.Member, channel: discord.TextChannel, rule_cfg: dict) -> bool:
        ignore_roles = [int(r) for r in rule_cfg.get("ignore_roles", [])]
        ignore_channels = [int(c) for c in rule_cfg.get("ignore_channels", [])]
        if channel.id in ignore_channels:
            return True
        if any(r.id in ignore_roles for r in member.roles):
            return True
        return False

    def _in_only_list(self, member: discord.Member, channel: discord.TextChannel, rule_cfg: dict) -> bool:
        only_channels = [int(c) for c in rule_cfg.get("only_channels", [])]
        only_roles = [int(r) for r in rule_cfg.get("only_roles", [])]
        if only_channels and channel.id not in only_channels:
            return False
        if only_roles and not any(r.id in only_roles for r in member.roles):
            return False
        return True

    async def _take_action(self, message: discord.Message, rule_name: str, rule_cfg: dict, trigger: str = ""):
        guild = message.guild
        member = message.author
        config = await self.bot.config_loader.get_config(guild.id)
        msgs = rule_cfg.get("messages", {})
        action = rule_cfg.get("action", "delete")

        # Delete message first
        try:
            await message.delete()
        except Exception:
            pass

        # Channel response
        ch_msg = msgs.get("channel_response")
        if ch_msg:
            try:
                await message.channel.send(format_template(ch_msg, user=member, action=action, channel=message.channel, trigger=trigger))
            except Exception:
                pass

        # DM user
        dm_msg = msgs.get("user_dm")
        if dm_msg:
            await send_dm(member, dm_msg, user=member, server=guild, action=action, reason=rule_name)

        # Log
        log_msg = msgs.get("log_response")
        if log_msg:
            lg = self.bot.get_cog("Logging")
            if lg:
                chan = await lg._get_log_channel(guild, "automod")
                if chan:
                    try:
                        await chan.send(format_template(log_msg, user=member, channel=message.channel, trigger=trigger))
                    except Exception:
                        pass

        # Mute if action is mute
        if action == "mute":
            mute_role_id = config.get("plugins", {}).get("moderation", {}).get("mute_role")
            if mute_role_id:
                mute_role = guild.get_role(int(mute_role_id))
                if mute_role:
                    duration_mins = rule_cfg.get("mute_duration_minutes", 10)
                    from datetime import timedelta
                    expires = datetime.now(timezone.utc) + timedelta(minutes=duration_mins)
                    try:
                        await member.add_roles(mute_role, reason=f"Automod: {rule_name}")
                        async with self.bot.pool.acquire() as conn:
                            await conn.execute(
                                "INSERT INTO mutes (guild_id, user_id, expires_at, removed_roles) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING",
                                guild.id, member.id, expires, []
                            )
                    except Exception:
                        pass
        elif action == "kick":
            try:
                await member.kick(reason=f"Automod: {rule_name}")
            except Exception:
                pass
        elif action == "ban":
            try:
                await guild.ban(member, reason=f"Automod: {rule_name}", delete_message_days=1)
            except Exception:
                pass
        elif action == "warn":
            cases = self.bot.get_cog("Cases")
            if cases:
                await cases.create_case(guild.id, member.id, self.bot.user.id, "warn", f"Automod: {rule_name}")

        # Check escalation
        esc = self.bot.get_cog("Escalation")
        if esc:
            await esc.check_automod(guild, config, member, rule_name, message.channel)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if not isinstance(message.author, discord.Member):
            return

        config = await self.bot.config_loader.get_config(message.guild.id)
        am = config.get("plugins", {}).get("automod", {})
        if not am.get("enabled"):
            return

        if await self._is_immune(message.author):
            return
        if await self._is_ignored(message.author):
            return

        # Run all rules
        await self._check_spam(message, am)
        await self._check_bad_words(message, am)
        await self._check_invite_links(message, am)
        await self._check_mass_mentions(message, am)
        await self._check_caps_spam(message, am)
        await self._check_mass_emojis(message, am)
        await self._check_zalgo(message, am)
        await self._check_newline_spam(message, am)
        await self._check_mentionspam(message, am)
        await self._check_links(message, am)
        await self._check_wordfilter(message, am)
        await self._check_phishing(message, am)
        await self._check_repeated_text(message, am)

    async def _check_spam(self, message: discord.Message, am: dict):
        rule = am.get("spam", {})
        if not rule.get("enabled"):
            return
        if self._in_ignore_list(message.author, message.channel, rule):
            return
        key = (message.guild.id, message.author.id)
        now = datetime.now(timezone.utc)
        interval = rule.get("interval_seconds", 5)
        self._spam_buckets[key] = [t for t in self._spam_buckets[key] if (now - t).total_seconds() < interval]
        self._spam_buckets[key].append(now)
        if len(self._spam_buckets[key]) >= rule.get("max_messages", 5):
            self._spam_buckets[key].clear()
            await self._take_action(message, "spam", rule, trigger=message.content[:100])

    async def _check_bad_words(self, message: discord.Message, am: dict):
        rule = am.get("bad_words", {})
        if not rule.get("enabled"):
            return
        if self._in_ignore_list(message.author, message.channel, rule):
            return
        words = [w.lower() for w in rule.get("words", [])]
        content_lower = message.content.lower()
        for word in words:
            if word in content_lower:
                await self._take_action(message, "bad_words", rule, trigger=word)
                return

    async def _check_invite_links(self, message: discord.Message, am: dict):
        rule = am.get("invite_links", {})
        if not rule.get("enabled"):
            return
        if self._in_ignore_list(message.author, message.channel, rule):
            return
        if INVITE_RE.search(message.content):
            await self._take_action(message, "invite_links", rule)

    async def _check_mass_mentions(self, message: discord.Message, am: dict):
        rule = am.get("mass_mentions", {})
        if not rule.get("enabled"):
            return
        count = len(message.mentions) + len(message.role_mentions)
        if count >= rule.get("max_mentions", 5):
            await self._take_action(message, "mass_mentions", rule, trigger=str(count))

    async def _check_caps_spam(self, message: discord.Message, am: dict):
        rule = am.get("caps_spam", {})
        if not rule.get("enabled"):
            return
        content = message.content
        if len(content) < rule.get("min_length", 10):
            return
        if rule.get("ignore_emojis"):
            content = re.sub(r'<[^>]+>', '', content)
        if rule.get("ignore_short_words"):
            content = " ".join(w for w in content.split() if len(w) > 2)
        letters = [c for c in content if c.isalpha()]
        if not letters:
            return
        caps_pct = sum(1 for c in letters if c.isupper()) / len(letters) * 100
        if caps_pct >= rule.get("caps_percentage", 70):
            await self._take_action(message, "caps_spam", rule)

    async def _check_mass_emojis(self, message: discord.Message, am: dict):
        rule = am.get("mass_emojis", {})
        if not rule.get("enabled"):
            return
        emoji_count = len(re.findall(r'<a?:\w+:\d+>|[\U00010000-\U0010FFFF]', message.content))
        if emoji_count >= rule.get("max_emojis", 10):
            await self._take_action(message, "mass_emojis", rule)

    async def _check_zalgo(self, message: discord.Message, am: dict):
        rule = am.get("zalgo", {})
        if not rule.get("enabled"):
            return
        if ZALGO_RE.search(message.content):
            await self._take_action(message, "zalgo", rule)

    async def _check_newline_spam(self, message: discord.Message, am: dict):
        rule = am.get("newline_spam", {})
        if not rule.get("enabled"):
            return
        if message.content.count('\n') >= rule.get("max_newlines", 10):
            await self._take_action(message, "newline_spam", rule)

    async def _check_mentionspam(self, message: discord.Message, am: dict):
        rule = am.get("mentionspam", {})
        if not rule.get("enabled"):
            return
        total_mentions = len(message.mentions) + len(message.role_mentions)
        if total_mentions >= rule.get("max_mentions_per_message", 5):
            await self._take_action(message, "mentionspam", rule, trigger=str(total_mentions))

    async def _check_links(self, message: discord.Message, am: dict):
        rule = am.get("links", {})
        if not rule.get("enabled"):
            return
        if self._in_ignore_list(message.author, message.channel, rule):
            return
        links = LINK_RE.findall(message.content)
        if not links:
            return
        if rule.get("block_all_links"):
            await self._take_action(message, "links", rule, trigger=links[0])
            return
        whitelist = [d.lower() for d in rule.get("whitelist_domains", [])]
        blacklist = [d.lower() for d in rule.get("blacklist_domains", [])]
        for link in links:
            domain = re.sub(r'https?://(www\.)?', '', link).split('/')[0].lower()
            if whitelist and domain in whitelist:
                continue
            if blacklist and domain in blacklist:
                await self._take_action(message, "links", rule, trigger=link)
                return

    async def _check_wordfilter(self, message: discord.Message, am: dict):
        rule = am.get("wordfilter", {})
        if not rule.get("enabled"):
            return
        if self._in_ignore_list(message.author, message.channel, rule):
            return
        normalize_map = rule.get("normalize_map", {"0":"o","1":"i","3":"e","4":"a","5":"s","7":"t","@":"a","$":"s","!":"i"})
        content = message.content.lower()
        normalized = content
        for k, v in normalize_map.items():
            normalized = normalized.replace(k, v)
        for word in rule.get("words", []):
            # Support wildcards
            pattern = word.lower().replace("*", ".*")
            if re.search(pattern, content) or re.search(pattern, normalized):
                await self._take_action(message, "wordfilter", rule, trigger=word)
                return

    async def _check_phishing(self, message: discord.Message, am: dict):
        rule = am.get("phishing", {})
        if not rule.get("enabled"):
            return
        if self._in_ignore_list(message.author, message.channel, rule):
            return
        content = message.content.lower()
        if rule.get("check_fake_nitro") and FAKE_NITRO_RE.search(content):
            await self._take_action(message, "phishing", rule, trigger="fake nitro")
            return
        if rule.get("check_links"):
            for domain in PHISHING_DOMAINS:
                if domain in content:
                    await self._take_action(message, "phishing", rule, trigger=domain)
                    return
        if rule.get("check_ip_links") and re.search(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', content):
            await self._take_action(message, "phishing", rule, trigger="IP link")
            return

    async def _check_repeated_text(self, message: discord.Message, am: dict):
        rule = am.get("repeated_text", {})
        if not rule.get("enabled"):
            return
        if not message.content:
            return
        try:
            from difflib import SequenceMatcher
        except ImportError:
            return
        key = (message.guild.id, message.author.id)
        self._last_messages[key] = self._last_messages[key][-5:]
        for prev in self._last_messages[key]:
            ratio = SequenceMatcher(None, message.content, prev).ratio()
            if ratio >= rule.get("threshold", 0.85):
                self._last_messages[key].clear()
                await self._take_action(message, "repeated_text", rule)
                return
        self._last_messages[key].append(message.content)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await self.bot.config_loader.get_config(member.guild.id)
        am = config.get("plugins", {}).get("automod", {})
        if not am.get("enabled"):
            return
        rule = am.get("alts", {})
        if not rule.get("enabled"):
            return
        min_age = rule.get("min_account_age_days", 30)
        age = (datetime.now(timezone.utc) - member.created_at).days
        if age < min_age:
            action = rule.get("action", "kick")
            if action == "kick":
                await send_dm(member, rule.get("messages", {}).get("user_dm", ""), user=member, server=member.guild, action=action, trigger=str(age))
                try:
                    await member.kick(reason=f"Automod: alt account (age {age} days)")
                except Exception:
                    pass
            elif action == "ban":
                try:
                    await member.guild.ban(member, reason=f"Automod: alt account (age {age} days)")
                except Exception:
                    pass
            lg = self.bot.get_cog("Logging")
            if lg:
                await lg.log_action(member.guild, "automod", "automod",
                                    user=member, trigger=str(age))


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
