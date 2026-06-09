import time
import yaml
from typing import Optional

DEFAULT_CONFIG = {
    "prefix": "!",
    "levels": {"users": {}, "roles": {}, "commands": {}},
    "tags": {},
    "plugins": {
        "moderation": {
            "enabled": True,
            "mute_role": None,
            "dm_on_action": True,
            "mute_remove_roles": False,
            "mute_dm_time_updates": False,
            "ban_delete_message_days": 1,
            "messages": {
                "ban_success": "{user} has been banned | Case: {case_id}",
                "forceban_success": "{user.id} has been banned | Case: {case_id}",
                "unban_success": "{user.id} has been unbanned | Case: {case_id}",
                "tempban_success": "{user} has been temp banned | Duration: {duration} | Case: {case_id}",
                "softban_success": "{user} has been softbanned | Case: {case_id}",
                "kick_success": "{user} has been kicked | Case: {case_id}",
                "mute_success": "{user} has been muted | Duration: {duration} | Case: {case_id}",
                "forcemute_success": "{user.id} has been muted | Duration: {duration} | Case: {case_id}",
                "unmute_success": "{user} has been unmuted | Case: {case_id}",
                "forceunmute_success": "{user.id} has been unmuted | Case: {case_id}",
                "warn_success": "{user} has been warned | Case: {case_id}",
                "forcewarn_success": "{user.id} has been warned | Case: {case_id}",
                "purge_success": "{count} messages deleted",
                "slowmode_success": "Slowmode set to {count}s in {channel.mention}",
                "slowmode_off": "Slowmode removed in {channel.mention}",
                "nick_success": "{user}'s nickname updated",
                "lock_success": "{channel.mention} has been locked | Reason: {reason}",
                "unlock_success": "{channel.mention} has been unlocked",
                "watch_success": "{user} added to watchlist",
                "unwatch_success": "{user} removed from watchlist",
                "immune_success": "{user} is now immune to automod",
                "unimmune_success": "{user}'s automod immunity removed",
                "seen_never": "{user} has never been seen",
                "seen_result": "{user} was last seen {trigger} in {channel}",
                "cleanup_success": "Deleted {count} bot messages",
                "ban_dm": "You have been banned in {server} for the following reason: {reason} | Duration: {duration}",
                "kick_dm": "You have been kicked from {server} for the following reason: {reason}",
                "mute_dm": "You have been muted in {server} for the following reason: {reason} | Duration: {duration}",
                "unmute_dm": "You have been unmuted in {server}",
                "warn_dm": "You have been warned in {server} for the following reason: {reason}",
                "softban_dm": "You have been softbanned from {server} for the following reason: {reason}",
                "error_user_not_found": "User not found",
                "error_already_muted": "{user} is already muted",
                "error_not_muted": "{user} is not muted",
                "error_hierarchy": "You cannot {action} someone with a higher or equal role",
                "error_already_banned": "{user.id} is already banned",
                "error_not_banned": "{user} is not banned",
                "error_invalid_duration": "Invalid duration. Use: 10m, 1h, 1d, 1w, perm",
                "error_duration_capped": "Duration capped at 180 days",
                "banlist_empty": "No bans found",
                "mutelist_empty": "No users currently muted",
            }
        },
        "mass_actions": {
            "enabled": True, "max_targets": 20,
            "messages": {
                "masswarn_success": "{success_count}/{total} users warned | Failed: {fail_count}",
                "massmute_success": "{success_count}/{total} users muted | Failed: {fail_count}",
                "masskick_success": "{success_count}/{total} users kicked | Failed: {fail_count}",
                "massban_success": "{success_count}/{total} users banned | Failed: {fail_count}",
                "massunban_success": "{success_count}/{total} users unbanned | Failed: {fail_count}",
                "massunmute_success": "{success_count}/{total} users unmuted | Failed: {fail_count}",
                "error_too_many_targets": "Max {count} users per mass action",
                "error_no_targets": "No valid targets provided",
            }
        },
        "cases": {
            "enabled": True,
            "messages": {
                "case_not_found": "Case {trigger} not found",
                "no_cases": "No cases found for {user}",
                "no_server_cases": "No cases issued yet",
                "case_deleted": "Case {trigger} deleted",
                "case_edited": "Case {case_id} updated",
                "addcase_success": "{case_type} case added for {user} silently | Case: {case_id}",
                "note_success": "Note added for {user} | Case: {case_id}",
                "note_deleted": "Note {case_id} deleted",
                "casecount": "{user} has {count} total cases",
            }
        },
        "logging": {
            "enabled": False,
            "channel": None,
            "channels": {"moderation": None, "messages": None, "members": None, "voice": None, "server": None, "automod": None, "antinuke": None, "antiraid": None},
            "messages": {
                "message_delete": "Message deleted by {user} in {channel} | Content: {trigger}",
                "message_edit": "{user} edited a message in {channel} | Before: {trigger} | After: {reason}",
                "message_bulk_delete": "{count} messages deleted in {channel}",
                "member_join": "{user} joined | Account created: {user.created_at} | Members: {server.member_count}",
                "member_leave": "{user} left | Joined: {user.joined_at}",
                "member_ban": "{user} was banned",
                "member_unban": "{user} was unbanned",
                "role_added": "{user} was given {trigger}",
                "role_removed": "{user} lost {trigger}",
                "nickname_change": "{user} changed nickname | Before: {trigger} | After: {reason}",
                "voice_join": "{user} joined {channel}",
                "voice_leave": "{user} left {channel}",
                "voice_move": "{user} moved from {trigger} to {reason}",
                "channel_create": "{channel} was created",
                "channel_delete": "{trigger} was deleted",
                "channel_update": "{channel} was updated",
                "role_create": "{trigger} role was created",
                "role_delete": "{trigger} role was deleted",
                "role_update": "{trigger} role was updated",
                "server_update": "Server settings were updated",
                "mod_action": "{mod} {action}d {user} | Reason: {reason} | Duration: {duration} | Case: {case_id}",
            }
        },
        "automod": {"enabled": False},
        "escalation": {
            "enabled": True,
            "manual": {
                "enabled": True, "thresholds": [],
                "messages": {
                    "escalation_triggered": "{user} has been {action}d due to repeated infractions | Case: {case_id}",
                    "escalation_dm": "You have been {action}d in {server} for the following reason: {reason}",
                }
            },
            "automod": {
                "enabled": True, "reset_after_hours": 24, "rules": {},
                "messages": {
                    "escalation_triggered": "{user} has been {action}d for repeated {rule} violations | Case: {case_id}",
                    "escalation_dm": "You have been {action}d in {server} for the following reason: {reason}",
                }
            }
        },
        "antinuke": {
            "enabled": False,
            "whitelist_roles": [], "whitelist_users": [],
            "thresholds": {"channel_delete": 3, "channel_create": 5, "role_delete": 3, "role_create": 5, "ban": 5, "kick": 5, "webhook_create": 3, "role_everyone_update": 1},
            "interval_seconds": 10, "action": "ban", "quarantine_role": None,
            "messages": {"triggered": "{user} exceeded the {rule} threshold and was {action}d | Case: {case_id}"}
        },
        "antiraid": {
            "enabled": False,
            "join_threshold": 10, "join_interval_seconds": 10, "account_age_min_days": 7,
            "action": "kick", "lockdown_channels": [], "auto_unlock_minutes": 10,
            "messages": {
                "raid_detected": "Raid detected | {count} joins in {duration} | Action: {action} | Affected: {success_count}",
                "raid_ended": "Raid mode ended",
                "new_account_flagged": "New account joined | {user} ({user.id}) | Age: {trigger} days",
            }
        },
        "slowmode_auto": {
            "enabled": False, "ignore_channels": [], "ignore_roles": [], "rules": [],
            "messages": {
                "slowmode_applied": "Slowmode of {count}s applied in {channel.mention} due to high activity",
                "slowmode_removed": "Slowmode removed in {channel.mention}",
            }
        },
        "lockdown": {
            "enabled": True, "server_lockdown_channels": [], "presets": {},
            "messages": {
                "lockdown_start": "{channel.mention} has been locked | Reason: {reason}",
                "lockdown_end": "{channel.mention} has been unlocked",
                "lockdown_server_start": "Server lockdown activated | {count} channels locked | Reason: {reason}",
                "lockdown_server_end": "Server lockdown lifted | {count} channels unlocked",
                "lockdown_channel_notice": "This channel has been locked by {mod} | Reason: {reason}",
                "unlock_channel_notice": "This channel has been unlocked by {mod}",
                "already_locked": "{channel.mention} is already locked",
                "not_locked": "{channel.mention} is not locked",
            }
        },
        "modnick": {
            "enabled": False, "default_name": "Moderated Nickname", "random_names": [], "log_changes": True,
            "rules": {"hoist": True, "blank": True, "unreadable": True, "zalgo": True, "bad_words": True, "mass_mentions": False, "custom_patterns": []},
            "messages": {
                "nickname_changed": "{user}'s nickname was changed to {trigger} | Rule: {reason}",
                "nickname_changed_dm": "Your nickname in {server} has been changed to {trigger} because it violated our nickname rules",
            }
        },
        "history": {"enabled": True, "messages": {"history_empty": "No history found for {user}", "history_cleared": "History cleared for {user}"}},
        "duration_roles": {
            "enabled": False, "roles": [],
            "messages": {
                "role_expired": "{user}'s {trigger} role has expired and been removed",
                "role_expiry_warning_dm": "Your {trigger} role in {server} expires in {count} days",
                "role_expired_dm": "Your {trigger} role in {server} has expired and been removed",
            }
        },
        "utility": {"enabled": True, "custom_help_entries": [], "messages": {"help_not_found": "Command {trigger} not found", "inrole_empty": "No members have that role", "banner_none": "{user} has no banner set", "bansearch_not_found": "{trigger} is not banned"}},
        "timezones": {
            "enabled": True,
            "messages": {
                "timezone_set": "Your timezone has been set to {trigger}",
                "timezone_get": "{user}'s timezone is {trigger}",
                "timezone_cleared": "Your timezone has been cleared",
                "timezone_not_set": "{user} has not set a timezone",
                "timezone_invalid": "Invalid timezone. Use a valid tz identifier e.g. America/New_York",
                "time_result": "Current time for {user}: {trigger}",
                "timefor_result": "Current time in {trigger}: {reason}",
            }
        },
        "reminders": {
            "enabled": True,
            "messages": {
                "reminder_set": "Reminder set for {duration} | Message: {reminder_message}",
                "reminder_fired": "{user.mention} Reminder: {reminder_message} | Set: {reminder_set_at}",
                "reminder_not_found": "Reminder not found",
                "reminder_deleted": "Reminder deleted",
                "reminder_list_empty": "You have no active reminders",
            }
        },
        "roles": {
            "enabled": True, "dm_on_action": True,
            "messages": {
                "addrole_success": "{user} has been given {trigger} | Reason: {reason}",
                "removerole_success": "{trigger} has been removed from {user} | Reason: {reason}",
                "temprole_success": "{user} has been given {trigger} | Duration: {duration} | Expires: {expires_at}",
                "temprole_expired": "{user} temp role {trigger} has expired",
                "temprole_list_empty": "No active temp roles",
                "error_role_not_found": "Role not found",
                "error_role_hierarchy": "That role is above my highest role",
            }
        },
        "reaction_roles": {
            "enabled": True,
            "messages": {
                "rr_created": "Panel {trigger} created",
                "rr_entry_added": "Role {trigger} added to panel {reason}",
                "rr_posted": "Panel {trigger} posted in {channel.mention}",
                "rr_deleted": "Panel {trigger} deleted",
                "rr_not_found": "Panel {trigger} not found",
                "rr_list_empty": "No reaction role panels found",
                "rr_max_reached": "You have reached the maximum number of roles for this panel",
                "rr_role_given": "You have been given {trigger}",
                "rr_role_removed": "You no longer have {trigger}",
            }
        },
        "welcome": {
            "enabled": True,
            "welcome": {"enabled": False, "channel": None, "ping": False, "delete_after": None, "message": "Welcome to {server}, {user.mention}! You are member #{server.member_count}."},
            "goodbye": {"enabled": False, "channel": None, "delete_after": None, "message": "{user} has left {server}."},
            "join_dm": {"enabled": False, "message": "Welcome to {server}!"},
            "welcome_role": {"enabled": False, "role": None},
            "rejoin_restore_roles": {"enabled": False, "ignore_roles": []},
            "account_age_gate": {"enabled": False, "min_age_days": 7, "kick": True, "message": "Your account is too new."},
            "member_count_channel": {"enabled": False, "channel": None, "format": "Members: {server.member_count}", "update_on": "both"}
        },
        "starboard": {
            "enabled": False, "channel": None, "emoji": "⭐", "threshold": 3,
            "self_star": False, "remove_on_unstar": False, "ignore_channels": [],
            "ignore_roles": [], "ignored_users": [], "nsfw_allowed": False,
            "max_age_days": 7, "bots_allowed": False,
            "messages": {"starboard_empty": "No starred messages found", "stats_none": "No star data found for {user}"}
        },
        "tags": {"enabled": True, "messages": {"tag_not_found": "Tag {trigger} not found", "tag_list_empty": "No tags created yet"}},
        "autoreply": {
            "enabled": True, "replies": [],
            "messages": {
                "autoreply_added": "Auto reply added",
                "autoreply_removed": "Auto reply removed",
                "autoreply_enabled": "Auto reply enabled",
                "autoreply_disabled": "Auto reply disabled",
                "autoreply_not_found": "Auto reply not found",
                "autoreply_list_empty": "No auto replies set up",
            }
        },
        "autoreaction": {
            "enabled": True, "reactions": [],
            "messages": {
                "autoreaction_added": "Auto reaction added",
                "autoreaction_removed": "Auto reaction removed",
                "autoreaction_not_found": "Auto reaction not found",
                "autoreaction_list_empty": "No auto reactions set up",
            }
        },
        "autoclean": {
            "enabled": True, "channels": [],
            "messages": {
                "autoclean_added": "Autoclean added for {channel.mention} | Mode: {trigger}",
                "autoclean_removed": "Autoclean removed from {channel.mention}",
                "autoclean_enabled": "Autoclean enabled for {channel.mention}",
                "autoclean_disabled": "Autoclean disabled for {channel.mention}",
                "autoclean_not_found": "No autoclean rule found for {channel.mention}",
                "autoclean_list_empty": "No autoclean rules set up",
                "autoclean_ran": "Autoclean ran in {channel.mention} | Deleted: {count} messages",
            }
        },
        "tickets": {
            "enabled": True, "log_channel": None, "transcript_channel": None,
            "dm_transcript": True, "max_open_per_user": 1,
            "messages": {
                "ticket_opened": "Your ticket has been opened in {channel.mention}",
                "ticket_already_open": "You already have an open ticket at {channel.mention}",
                "ticket_blacklisted": "You are blacklisted from opening tickets | Reason: {reason}",
                "ticket_closed": "Ticket closed by {mod} | Reason: {reason}",
                "ticket_claimed": "Ticket claimed by {mod.mention}",
                "ticket_deleted": "Ticket deleted by {mod} | Reason: {reason}",
                "not_a_ticket": "This command can only be used inside a ticket channel",
                "blacklist_success": "{user} has been blacklisted from tickets | Reason: {reason}",
                "unblacklist_success": "{user} has been removed from the ticket blacklist",
            }
        },
        "command_aliases": {"config": {"aliases": {
            "b": "ban", "fb": "forceban", "ub": "unban", "k": "kick",
            "m": "mute", "fm": "forcemute", "um": "unmute", "w": "warn",
            "fw": "forcewarn", "p": "purge", "sm": "slowmode",
        }}},
        "preset_reasons": {"config": {"presets": {
            "spam": "Spamming in chat",
            "ads": "Advertising without permission",
            "toxic": "Toxic behavior towards members",
            "nsfw": "Posting NSFW content outside designated channels",
            "raid": "Raiding the server",
            "slurs": "Using slurs or hate speech",
            "threats": "Threatening other members",
            "evade": "Ban or mute evasion",
        }}}
    }
}


class ConfigLoader:
    def __init__(self, pool):
        self.pool = pool
        self._cache: dict = {}
        self._ttl = 60

    def _expired(self, guild_id):
        if guild_id not in self._cache:
            return True
        _, ts = self._cache[guild_id]
        return time.time() - ts > self._ttl

    async def get_config(self, guild_id: int) -> dict:
        if not self._expired(guild_id):
            return self._cache[guild_id][0]

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT config FROM guild_configs WHERE guild_id = $1", guild_id)

        if row and row["config"]:
            try:
                loaded = yaml.safe_load(row["config"])
                if not isinstance(loaded, dict):
                    loaded = {}
            except Exception:
                loaded = {}
        else:
            loaded = {}

        merged = _deep_merge(DEFAULT_CONFIG.copy(), loaded)
        self._cache[guild_id] = (merged, time.time())
        return merged

    async def set_config(self, guild_id: int, yaml_str: str) -> bool:
        try:
            parsed = yaml.safe_load(yaml_str)
            if not isinstance(parsed, dict):
                return False
        except Exception:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO guild_configs (guild_id, config) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET config = $2",
                guild_id, yaml_str
            )
        self.invalidate(guild_id)
        return True

    async def get_raw(self, guild_id: int) -> Optional[str]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT config FROM guild_configs WHERE guild_id = $1", guild_id)
        return row["config"] if row else None

    async def reset_config(self, guild_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM guild_configs WHERE guild_id = $1", guild_id)
        self.invalidate(guild_id)

    def invalidate(self, guild_id: int):
        self._cache.pop(guild_id, None)

    def resolve_preset(self, config: dict, reason: Optional[str]) -> Optional[str]:
        if not reason:
            return reason
        presets = config.get("plugins", {}).get("preset_reasons", {}).get("config", {}).get("presets", {})
        return presets.get(reason, reason)


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result
