import { useState } from "react";
import { useLocation } from "wouter";

/* ──────────────────────────────────────────────────────────────
   PLUGIN DATA — every plugin, every command, full config docs
────────────────────────────────────────────────────────────── */

const PLUGIN_CATEGORIES = [
  // ── GENERAL ───────────────────────────────────────────────────
  {
    category: "General",
    plugins: [
      {
        name: "introduction",
        label: "Introduction",
        description:
          "Night Pigeon is a private, plugin-based Discord moderation bot. Every plugin is independently toggleable. All bot messages, embeds, and DMs are fully customizable per server through YAML configuration stored in PostgreSQL. The bot will leave any server that has not been whitelisted by the bot owner.",
        configTitle: "Minimal Working Config",
        config: `# Paste this into !setconfig to get started immediately.
prefix: "!"

levels:
  users:
    "YOUR_USER_ID": 100   # Give yourself owner-level access (0–100)
  roles: {}
  commands: {}

plugins:
  moderation:
    enabled: true
    mute_role: null        # Set this to your mute role ID
    dm_on_action: true`,
        commands: [],
      },
      {
        name: "config_format",
        label: "Config Format",
        description:
          "All server configuration is written in YAML and stored per-server in PostgreSQL. The config is deep-merged with built-in defaults — you only need to specify keys you want to override. All plugin messages support template variables like {user}, {mod}, {reason}, {duration}, {case_id}, {server}, {channel}.",
        configTitle: "How Config Works",
        config: `# Config is deep-merged with defaults.
# You only need the keys you want to change.

# ── Top-level structure ──────────────────────────────
prefix: "!"          # Command prefix (default: !)

levels:              # Permission system (see Levels page)
  users: {}
  roles: {}
  commands: {}

tags: {}             # Quick-reply shortcuts

plugins:             # One entry per plugin
  moderation:
    enabled: true
    # ...

# ── Template Variables ───────────────────────────────
# {user}           → User's display name
# {user.mention}   → @mention
# {user.id}        → User ID
# {user.name}      → Username
# {user.created_at}→ Account creation date
# {user.joined_at} → Server join date
# {mod}            → Moderator name
# {mod.mention}    → Moderator @mention
# {server}         → Server name
# {server.id}      → Server ID
# {server.member_count} → Member count
# {reason}         → Action reason
# {duration}       → Duration string (e.g. "1h", "permanent")
# {case_id}        → Moderation case number
# {channel}        → Channel name
# {channel.mention}→ #channel mention
# {count}          → Generic count
# {trigger}        → Automod trigger string
# {rule}           → Automod rule name
# {expires_at}     → Expiry timestamp

# ── Message format (string or embed) ────────────────
# String:
#   ban_success: "{user} banned | Case: {case_id}"
#
# Embed:
#   ban_success:
#     content: "Action taken"
#     embed:
#       color: "#FF0000"
#       title: "User Banned"
#       description: "{user} was banned | Reason: {reason}"
#       footer: "Case #{case_id}"
#       fields:
#         - name: "Duration"
#           value: "{duration}"
#           inline: true`,
        commands: [
          "!setconfig — paste YAML block to update config",
          "!getconfig — DMs you the current raw YAML",
          "!resetconfig — reset all config to defaults",
          "!configaccess add @user",
          "!configaccess remove @user",
          "!configaccess list",
        ],
      },
      {
        name: "levels",
        label: "Permissions (Levels)",
        description:
          "Night Pigeon uses a numeric permission level system. Each user has an effective level from 0–100 (bot owner is always 1000). Levels are resolved from user overrides first, then the highest matching role. Commands have default minimum levels that you can override per-server.",
        configTitle: "Level Configuration",
        config: `# Default command levels (override as needed):
# ban=50, forceban=50, unban=50, kick=25, mute=25, forcemute=25
# unmute=25, warn=15, forcewarn=15, purge=50, slowmode=25
# lock=50, unlock=50, nick=25, locknick=50, watch=50
# massban=100, massmute=75, masskick=75, masswarn=50
# antinuke=75, raidmode=75, addrole=50, temprole=50
# ticket panel=75, rr create=75

levels:
  users:
    "123456789012345678": 100   # User ID → level (0–100)
    "987654321098765432": 50
  roles:
    "111222333444555666": 75    # Role ID → level
    "999888777666555444": 25
  commands:
    ban: 50        # Override default level for !ban
    kick: 25       # Override default level for !kick
    warn: 10       # Anyone with level 10+ can warn
    massban: 100   # Only level 100 can massban`,
        commands: [
          "!level [@user] — show user's effective level",
          "!levels — list all level assignments in config",
          "!levelset [@user] — show how their level is resolved",
        ],
      },
      {
        name: "aliases",
        label: "Aliases",
        description:
          "Map short command aliases to full commands. Aliases are resolved before the command is dispatched so they work with all arguments, flags, and reason presets.",
        configTitle: "Alias Configuration",
        config: `plugins:
  command_aliases:
    config:
      aliases:
        b:  ban
        fb: forceban
        ub: unban
        k:  kick
        m:  mute
        fm: forcemute
        um: unmute
        u:  unmute
        w:  warn
        fw: forcewarn
        p:  purge
        sm: slowmode
        l:  lock
        ul: unlock
        h:  history

# Usage: !b @user 1d spam   →   !ban @user 1d spam`,
        commands: [],
      },
      {
        name: "preset_reasons",
        label: "Preset Reasons",
        description:
          "Map short keyword reasons to full reason text. When you use !ban @user spam, the reason stored and shown is the full preset text.",
        configTitle: "Preset Reasons Config",
        config: `plugins:
  preset_reasons:
    config:
      presets:
        spam:    "Spamming in chat"
        ads:     "Advertising without permission"
        toxic:   "Toxic behavior towards members"
        nsfw:    "Posting NSFW content outside designated channels"
        raid:    "Raiding the server"
        slurs:   "Using slurs or hate speech"
        threats: "Threatening other members"
        evade:   "Ban or mute evasion"
        dox:     "Sharing personal information without consent"

# Usage: !ban @user evade
# Stored reason: "Ban or mute evasion"`,
        commands: [],
      },
      {
        name: "duration_syntax",
        label: "Duration Syntax",
        description:
          "Durations are used in ban, mute, temprole, temprole, reminders, and more. Maximum duration is 180 days. Longer values are automatically capped. Use 'perm' or 'permanent' for indefinite actions.",
        configTitle: "Duration Examples",
        config: `# Duration format:
#   <number><unit>  — combine freely
#   s = seconds
#   m = minutes
#   h = hours
#   d = days
#   w = weeks

# Examples:
#   30s     → 30 seconds
#   10m     → 10 minutes
#   1h      → 1 hour
#   12h     → 12 hours
#   1d      → 1 day
#   3d12h   → 3 days and 12 hours
#   1w      → 1 week
#   2w3d    → 2 weeks and 3 days
#   perm    → permanent (no expiry)
#   permanent → same as perm

# Max: 180d (longer is auto-capped and flagged in response)`,
        commands: [],
      },
    ],
  },

  // ── MODERATION ────────────────────────────────────────────────
  {
    category: "Moderation",
    plugins: [
      {
        name: "moderation",
        label: "Moderation",
        description:
          "Core moderation commands. Every response message, DM, and error message is independently customizable via YAML. Supports role hierarchy enforcement, preset reasons, and optional DM notifications on every action.",
        configTitle: "Moderation Config",
        config: `plugins:
  moderation:
    enabled: true
    mute_role: 123456789012345678    # Role ID given to muted users (required)
    dm_on_action: true               # DM the user when they are actioned
    mute_remove_roles: false         # Strip ALL roles when muting (restores on unmute)
    mute_dm_time_updates: false      # DM user when their mute duration is edited
    ban_delete_message_days: 1       # Days of messages purged when banning (0–7)

    messages:
      # ── Success messages ─────────────────────────
      ban_success:     "{user} has been banned | Case: {case_id}"
      forceban_success:"{user.id} has been force-banned | Case: {case_id}"
      unban_success:   "{user.id} has been unbanned | Case: {case_id}"
      tempban_success: "{user} temp-banned | Duration: {duration} | Case: {case_id}"
      softban_success: "{user} has been softbanned | Case: {case_id}"
      kick_success:    "{user} has been kicked | Case: {case_id}"
      mute_success:    "{user} muted | Duration: {duration} | Case: {case_id}"
      forcemute_success: "{user.id} muted | Duration: {duration} | Case: {case_id}"
      unmute_success:  "{user} has been unmuted | Case: {case_id}"
      warn_success:    "{user} has been warned | Case: {case_id}"
      forcewarn_success: "{user.id} warned | Case: {case_id}"
      purge_success:   "{count} messages deleted"
      slowmode_success:"Slowmode set to {count}s in {channel.mention}"
      slowmode_off:    "Slowmode removed in {channel.mention}"
      nick_success:    "{user}'s nickname updated to {trigger}"
      lock_success:    "{channel.mention} locked | Reason: {reason}"
      unlock_success:  "{channel.mention} unlocked"
      watch_success:   "{user} added to watchlist | Reason: {reason}"
      unwatch_success: "{user} removed from watchlist"
      immune_success:  "{user} is now immune to automod"
      unimmune_success:"{user}'s automod immunity removed"
      seen_never:      "{user} has never been seen"
      seen_result:     "{user} last seen {trigger} in {channel}"
      cleanup_success: "Deleted {count} bot messages"

      # ── DMs sent to actioned user ─────────────────
      ban_dm:    "You have been banned from **{server}** | Reason: {reason} | Duration: {duration}"
      kick_dm:   "You have been kicked from **{server}** | Reason: {reason}"
      mute_dm:   "You have been muted in **{server}** | Duration: {duration} | Reason: {reason}"
      unmute_dm: "You have been unmuted in **{server}**"
      warn_dm:   "You have been warned in **{server}** | Reason: {reason}"
      softban_dm:"You have been softbanned from **{server}** | Reason: {reason}"

      # ── Error messages ────────────────────────────
      error_user_not_found:   "User not found"
      error_already_muted:    "{user} is already muted"
      error_not_muted:        "{user} is not muted"
      error_hierarchy:        "You cannot {action} someone with a higher or equal role"
      error_already_banned:   "{user.id} is already banned"
      error_not_banned:       "{user} is not banned"
      error_invalid_duration: "Invalid duration. Use: 10m, 1h, 1d, 1w, perm"
      error_duration_capped:  "Duration capped at 180 days"
      banlist_empty:          "No bans found"
      mutelist_empty:         "No users currently muted"`,
        commands: [
          "!ban @user [duration] [reason] — ban a user",
          "!forceban <user_id> [duration] [reason] — ban by ID (not in server)",
          "!unban <user_id> [reason] — unban",
          "!tempban @user <duration> [reason] — ban with automatic expiry",
          "!softban @user [reason] — ban then immediately unban (clears recent messages)",
          "!banlist — list recent bans",
          "!baninfo <user_id> — ban info for a user ID",
          "!kick @user [reason] — kick from server",
          "!mute @user [duration] [reason] — apply mute role",
          "!forcemute <user_id> [duration] [reason] — mute user by ID",
          "!unmute @user [reason] — remove mute role",
          "!forceunmute <user_id> [reason] — unmute by ID",
          "!mutelist — list currently muted users",
          "!warn @user [reason] — issue a warning",
          "!forcewarn <user_id> [reason] — warn by ID",
          "!purge <n> — delete last N messages",
          "!purge bots <n> — delete last N bot messages",
          "!purge embeds <n> — delete last N messages with embeds",
          "!purge images <n> — delete last N messages with images",
          "!purge links <n> — delete last N messages with links",
          "!purge contains <text> <n> — delete messages containing text",
          "!purge @user <n> — delete last N messages from a specific user",
          "!slowmode <seconds> [#channel] — set channel slowmode",
          "!slowmode off [#channel] — remove slowmode",
          "!nick @user <nickname> — set a user's nickname",
          "!resetnick @user — reset to default nickname",
          "!locknick @user — lock nickname (prevents self-changes)",
          "!unlocknick @user — unlock nickname",
          "!lock [#channel] [reason] — lock channel (deny @everyone Send Messages)",
          "!unlock [#channel] — unlock channel",
          "!hide [#channel] — hide channel from @everyone",
          "!unhide [#channel] — restore channel visibility",
          "!nuke [#channel] — clone channel and delete original",
          "!watch @user [reason] — add to watchlist",
          "!unwatch @user — remove from watchlist",
          "!watchlist — view current watchlist",
          "!immune @user — mark as automod-immune",
          "!unimmune @user — remove automod immunity",
          "!immunelist — list immune users",
          "!roleban @user <@role> [reason] — ban user from getting a specific role",
          "!unroleban @user <@role> — remove role ban",
          "!rolebanned @user — list active role bans",
          "!seen @user — when was this user last active",
          "!cleanup <n> — delete last N bot messages in channel",
        ],
      },
      {
        name: "cases",
        label: "Cases",
        description:
          "Every moderation action automatically creates a numbered case. Cases track the action type, moderator, user, reason, duration, and timestamp. Cases can be edited, annotated with notes, and deleted.",
        configTitle: "Cases Config",
        config: `plugins:
  cases:
    enabled: true
    messages:
      case_not_found:    "Case #{trigger} not found"
      no_cases:          "No cases found for {user}"
      no_server_cases:   "No cases issued yet in this server"
      case_deleted:      "Case #{trigger} deleted"
      case_edited:       "Case #{case_id} updated"
      addcase_success:   "Silent {case_type} case added for {user} | Case: #{case_id}"
      note_success:      "Note added for {user} | Note: #{case_id}"
      note_deleted:      "Note #{case_id} deleted"
      casecount:         "{user} has {count} total cases"`,
        commands: [
          "!case <id> — view a specific case",
          "!cases @user — view all cases for a user",
          "!servercases — view recent server-wide cases",
          "!servercases <page> — paginate cases",
          "!deletecase <id> — permanently delete a case",
          "!reason <id> <new_reason> — update case reason",
          "!editcase <id> reason <text> — edit case reason",
          "!editcase <id> duration <value> — edit case duration",
          "!addcase @user <type> [reason] — add a case silently (no action taken)",
          "!casecount @user — count cases by type",
          "!note @user <text> — add a private moderator note",
          "!viewnote <id> — view a specific note",
          "!viewnotes @user — view all notes for a user",
          "!deletenote <id> — delete a note",
          "!editnote <id> <new_text> — edit a note",
          "!notesearch <keyword> — search notes by keyword",
        ],
      },
      {
        name: "mass_actions",
        label: "Mass Actions",
        description:
          "Apply a moderation action to multiple users at once. Separate targets from the reason with |. Targets can be @mentions or raw user IDs. Each action still creates individual cases.",
        configTitle: "Mass Actions Config",
        config: `plugins:
  mass_actions:
    enabled: true
    max_targets: 20    # Max users per mass action call
    messages:
      masswarn_success:  "{success_count}/{total} users warned | Failed: {fail_count}"
      massmute_success:  "{success_count}/{total} users muted | Failed: {fail_count}"
      masskick_success:  "{success_count}/{total} users kicked | Failed: {fail_count}"
      massban_success:   "{success_count}/{total} users banned | Failed: {fail_count}"
      massunban_success: "{success_count}/{total} users unbanned | Failed: {fail_count}"
      massunmute_success:"{success_count}/{total} users unmuted | Failed: {fail_count}"
      error_too_many_targets: "Max {count} users per mass action"
      error_no_targets:       "No valid targets provided"`,
        commands: [
          "!masswarn @u1 @u2 ... | [reason]",
          "!massmute @u1 @u2 ... [duration] | [reason]",
          "!masskick @u1 @u2 ... | [reason]",
          "!massban @u1 @u2 ... [duration] | [reason]",
          "!massunban <id1> <id2> ... | [reason]",
          "!massunmute @u1 @u2 ... | [reason]",
        ],
      },
      {
        name: "modnick",
        label: "ModNick",
        description:
          "Automatically detects and replaces inappropriate nicknames on message send or join. Supports hoisting characters, zalgo text, blank names, bad words, and custom regex patterns. Nicknames can also be manually locked.",
        configTitle: "ModNick Config",
        config: `plugins:
  modnick:
    enabled: true
    default_name: "Moderated Nickname"   # Replacement name used
    random_names: []                      # Random pool instead of fixed name
    log_changes: true                     # Log to mod channel
    rules:
      hoist: true            # Names starting with ! # @ etc (show at top of list)
      blank: true            # Blank, invisible, or whitespace-only names
      unreadable: true       # Names with no readable ASCII characters
      zalgo: true            # Excessive combining/zalgo characters
      bad_words: true        # Words from the bad_words automod list
      mass_mentions: false   # Names containing @everyone / @here
      custom_patterns:       # Additional regex patterns to block
        - "(?i)admin"
        - "(?i)mod(?!erate)"
    messages:
      nickname_changed: "{user}'s nickname changed to {trigger} | Rule: {reason}"
      nickname_changed_dm: "Your nickname in {server} was changed to {trigger} because it violated nickname rules: {reason}"`,
        commands: [
          "!modnick @user [name] — manually force a new nickname (uses default_name if omitted)",
          "!clearnick @user — remove forced nickname",
          "!locknick @user — lock nickname (user cannot change it)",
          "!unlocknick @user — allow user to change nickname again",
        ],
      },
      {
        name: "lockdown",
        label: "Lockdown",
        description:
          "Lock individual channels or the entire server with one command. Create named presets for common scenarios (raid lockdown, emergency, etc.) so you can activate complex lockdowns instantly.",
        configTitle: "Lockdown Config",
        config: `plugins:
  lockdown:
    enabled: true
    server_lockdown_channels: []    # Channel IDs locked in server lockdown (empty = all)
    presets:
      raid:
        channels: [123456789, 987654321]
        reason: "Raid lockdown — please stand by"
      emergency:
        channels: [111222333, 444555666]
        reason: "Emergency lockdown"
    messages:
      lockdown_start:         "{channel.mention} has been locked | Reason: {reason}"
      lockdown_end:           "{channel.mention} has been unlocked"
      lockdown_server_start:  "Server lockdown activated | {count} channels locked | Reason: {reason}"
      lockdown_server_end:    "Server lockdown lifted | {count} channels unlocked"
      lockdown_channel_notice:"This channel has been locked by {mod} | Reason: {reason}"
      unlock_channel_notice:  "This channel has been unlocked by {mod}"
      already_locked:         "{channel.mention} is already locked"
      not_locked:             "{channel.mention} is not locked"`,
        commands: [
          "!lockdown [#channel] [reason] — lock a single channel",
          "!lockdown -server [reason] — lock all channels",
          "!lockdown <preset_name> [reason] — activate a named preset",
          "!lockdown list — list currently locked channels",
          "!unlock [#channel] — unlock a channel",
          "!unlock -server — unlock all channels",
        ],
      },
      {
        name: "history",
        label: "History",
        description:
          "Track a full timeline of events for any user: bans, kicks, mutes, warnings, role changes, joins, and leaves. Filter by type. History persists even after cases are deleted.",
        configTitle: "History Config",
        config: `plugins:
  history:
    enabled: true
    messages:
      history_empty:   "No history found for {user}"
      history_cleared: "History cleared for {user}"`,
        commands: [
          "!history @user — full event history",
          "!history @user cases — moderation cases only",
          "!history @user notes — notes only",
          "!history @user joins — server join/leave events",
          "!history @user roles — role change events",
          "!history clear @user — delete all history events for a user",
        ],
      },
    ],
  },

  // ── AUTOMATION ────────────────────────────────────────────────
  {
    category: "Automation",
    plugins: [
      {
        name: "automod",
        label: "AutoMod",
        description:
          "15 independent automod rules covering every common abuse vector. Each rule has its own action, ignore lists, channel overrides, and escalation configuration. Checks automod_immune and ignored_users tables before firing.",
        configTitle: "AutoMod — All 15 Rules",
        config: `plugins:
  automod:
    enabled: true

    # ── 1. Spam — rate limiting per user ─────────────────────────
    spam:
      enabled: true
      max_messages: 5         # Max messages in the interval
      interval_seconds: 5     # Rolling window in seconds
      action: mute            # delete | warn | mute | kick | ban
      mute_duration_minutes: 10
      ignore_roles: []        # Role IDs to skip
      ignore_channels: []     # Channel IDs to skip
      messages:
        triggered: "{user} was muted for spam | Rule: spam"

    # ── 2. Bad Words ─────────────────────────────────────────────
    bad_words:
      enabled: true
      words: ["word1", "word2"]    # Exact words (case-insensitive)
      action: delete
      dm_user: false
      ignore_roles: []
      ignore_channels: []
      messages:
        triggered: "Message from {user} deleted | Rule: bad_words"

    # ── 3. Discord Invite Links ──────────────────────────────────
    invite_links:
      enabled: true
      action: delete
      whitelist_guilds: []    # Guild IDs whose invites are allowed
      ignore_roles: []
      ignore_channels: []

    # ── 4. Mass Mentions ─────────────────────────────────────────
    mass_mentions:
      enabled: true
      max_mentions: 5         # @user mentions per message
      action: mute
      mute_duration_minutes: 15
      ignore_roles: []

    # ── 5. Caps Spam ─────────────────────────────────────────────
    caps_spam:
      enabled: true
      min_length: 10          # Only check messages longer than this
      cap_percent: 70         # % of uppercase characters required
      action: delete
      ignore_roles: []

    # ── 6. Link Spam — too many links per message ────────────────
    link_spam:
      enabled: true
      max_links: 3            # Links per message
      action: delete
      ignore_roles: []

    # ── 7. Repeated Text — duplicate/similar messages ────────────
    repeated_text:
      enabled: true
      threshold: 3            # Same/similar messages in window
      interval_seconds: 10
      similarity_ratio: 0.85  # 0.0–1.0 (1.0 = exact duplicate)
      action: mute
      mute_duration_minutes: 5

    # ── 8. Mass Emojis ───────────────────────────────────────────
    mass_emojis:
      enabled: true
      max_emojis: 10
      action: delete

    # ── 9. Zalgo Text ────────────────────────────────────────────
    zalgo:
      enabled: true
      action: delete

    # ── 10. Newline Spam ─────────────────────────────────────────
    newline_spam:
      enabled: true
      max_newlines: 8
      action: delete

    # ── 11. Mention Spam — ghost pings ───────────────────────────
    mentionspam:
      enabled: true
      max_mentions: 8         # Total mentions including roles
      action: warn

    # ── 12. Links — domain whitelist/blacklist ───────────────────
    links:
      enabled: false
      mode: blacklist         # whitelist | blacklist
      domains:               # Domain list (matches subdomains)
        - "example-bad.com"
      action: delete
      ignore_roles: []
      only_channels: []       # Only apply in these channel IDs

    # ── 13. Word Filter — advanced patterns ──────────────────────
    wordfilter:
      enabled: false
      patterns: []            # Supports * wildcard and regex
      normalize_leet: true    # Convert l33tspeak before matching
      action: delete
      ignore_roles: []

    # ── 14. Alts — account age gate ──────────────────────────────
    alts:
      enabled: false
      min_age_days: 7
      action: kick            # kick | ban | mute
      dm_user: true

    # ── 15. Phishing ─────────────────────────────────────────────
    phishing:
      enabled: true
      check_fake_nitro: true          # Free Nitro patterns
      check_lookalike_domains: true   # discordapp.gifts etc.
      check_ip_grabbers: true         # Known IP grabber domains
      action: ban`,
        commands: [
          "!immune @user — exempt user from all automod rules",
          "!unimmune @user — remove automod exemption",
          "!immunelist — list all automod-immune users",
        ],
      },
      {
        name: "escalation",
        label: "Escalation",
        description:
          "Automatically escalates punishments when users accumulate infractions. Two independent modes: manual escalation (counts warn/mute/kick actions) and automod escalation (counts automod rule violations per-rule per-user).",
        configTitle: "Escalation Config",
        config: `plugins:
  escalation:
    enabled: true

    # ── Manual Escalation ────────────────────────────────────────
    # Fires after warn, mute, kick actions.
    # tracked_type: "warn" | "mute" | "kick" | "any"
    manual:
      enabled: true
      thresholds:
        - tracked_type: "warn"
          count: 3
          action: mute
          duration: "1h"
          reason: "3 warnings — auto-muted"
        - tracked_type: "warn"
          count: 5
          action: ban
          duration: "1d"
          reason: "5 warnings — 1 day ban"
        - tracked_type: "warn"
          count: 7
          action: ban
          duration: "perm"
          reason: "7 warnings — permanent ban"
      messages:
        escalation_triggered: "{user} escalated to {action} after {count} {tracked_type}(s) | Case: {case_id}"
        escalation_dm:        "You have been {action}d in {server} | Reason: {reason}"

    # ── Automod Escalation ───────────────────────────────────────
    # Counts per-rule violations, resets after reset_after_hours.
    automod:
      enabled: true
      reset_after_hours: 24
      rules:
        spam:
          thresholds:
            - count: 1
              action: mute
              duration: "10m"
            - count: 3
              action: kick
            - count: 5
              action: ban
              duration: "1d"
        invite_links:
          thresholds:
            - count: 2
              action: mute
              duration: "30m"
            - count: 4
              action: ban
              duration: "perm"
      messages:
        escalation_triggered: "{user} escalated for repeated {rule} violations | Case: {case_id}"`,
        commands: [],
      },
      {
        name: "antinuke",
        label: "Anti-Nuke",
        description:
          "Detects mass destructive actions (channel deletes, role deletes, mass bans) within a configurable time window and immediately punishes the actor. Supports whitelists for trusted admins.",
        configTitle: "Anti-Nuke Config",
        config: `plugins:
  antinuke:
    enabled: true
    whitelist_roles: []        # Role IDs exempt from anti-nuke
    whitelist_users: []        # User IDs exempt from anti-nuke
    thresholds:
      channel_delete: 3        # Max channel deletes in interval
      channel_create: 5        # Max channel creates
      role_delete:    3        # Max role deletes
      role_create:    5        # Max role creates
      ban:            5        # Max bans
      kick:           5        # Max kicks
      webhook_create: 3        # Max webhook creates
      role_everyone_update: 1  # @everyone permission changes
    interval_seconds: 10       # Tracking window in seconds
    action: ban                # ban | kick | strip_roles
    quarantine_role: null      # Optional role to apply instead of action
    messages:
      triggered: "{user} exceeded {rule} threshold ({count}) and was {action}d | Case: {case_id}"`,
        commands: [],
      },
      {
        name: "antiraid",
        label: "Anti-Raid",
        description:
          "Detects mass join events (raids) and automatically kicks/bans the new members or triggers a channel lockdown. Also detects suspiciously new accounts (alt detection on join).",
        configTitle: "Anti-Raid Config",
        config: `plugins:
  antiraid:
    enabled: true
    join_threshold: 10          # Joins within interval to trigger
    join_interval_seconds: 10   # Detection window
    account_age_min_days: 7     # Flag accounts newer than this
    action: kick                # kick | ban | lockdown
    lockdown_channels: []       # Channels to lock on raid trigger (empty = all)
    auto_unlock_minutes: 10     # Auto-unlock after this many minutes (0 = manual)
    messages:
      raid_detected:      "Raid detected | {count} joins in {duration} | Action: {action} | Affected: {success_count}"
      raid_ended:         "Raid mode ended"
      new_account_flagged:"New account joined | {user} ({user.id}) | Age: {trigger} days"`,
        commands: ["!raidmode on — manually activate raid mode", "!raidmode off — deactivate raid mode"],
      },
      {
        name: "autoreply",
        label: "Auto Reply",
        description:
          "Automatically reply to messages matching triggers. Supports five match types: exact, contains, starts_with, ends_with, regex. Replies can be plain text or embeds. Supports per-channel and per-role overrides.",
        configTitle: "Auto Reply Config",
        config: `plugins:
  autoreply:
    enabled: true
    replies:
      - trigger: "hello bot"
        response: "Hello {user.mention}! How can I help?"
        match_type: contains       # exact|contains|starts_with|ends_with|regex
        match_case: false
        delete_trigger: false      # Delete the original message
        delete_after: null         # Auto-delete bot reply after N seconds
        only_channels: []          # Only apply in these channel IDs
        ignore_channels: []        # Never apply in these channels
        only_roles: []             # Only for users with these roles
        ignore_roles: []           # Never for users with these roles
        cooldown_seconds: 30       # Per-user cooldown

      - trigger: "^!rules$"
        response:
          embed:
            color: "#5865F2"
            title: "Server Rules"
            description: "Please read all rules carefully."
        match_type: regex`,
        commands: [
          "!autoreply add <type> <trigger> <response> — add a new auto-reply",
          "!autoreply remove <id> — remove auto-reply",
          "!autoreply list — list all auto-replies",
          "!autoreply enable <id> — enable a disabled reply",
          "!autoreply disable <id> — disable a reply without deleting",
        ],
      },
      {
        name: "autoreaction",
        label: "Auto Reaction",
        description:
          "Automatically react to messages with emojis based on triggers or channels. Supports the same match types as Auto Reply.",
        configTitle: "Auto Reaction Config",
        config: `plugins:
  autoreaction:
    enabled: true
    reactions:
      - trigger: "good job"
        emojis: ["👍", "🎉", "⭐"]
        match_type: contains
        only_channels: []
        ignore_channels: []
        ignore_roles: []
        cooldown_seconds: 0`,
        commands: [
          "!autoreaction add <type> <trigger> <emoji1> [emoji2...] — add reaction rule",
          "!autoreaction remove <id> — remove reaction rule",
          "!autoreaction list — list all reaction rules",
        ],
      },
      {
        name: "autoclean",
        label: "Auto Clean",
        description:
          "Automatically delete messages in channels on a schedule. Three modes: interval (purge every N seconds), keepx (keep last N messages), maxage (delete messages older than N seconds).",
        configTitle: "Auto Clean Config",
        config: `plugins:
  autoclean:
    enabled: true
    channels:
      - id: 123456789012345678      # Channel ID
        mode: keepx                  # interval | keepx | maxage
        keep_count: 10               # (keepx) how many messages to keep
        # interval_seconds: 300      # (interval) how often to clean
        # max_age_seconds: 3600      # (maxage) delete messages older than this
        delay_seconds: 0             # Delay between individual deletes
        ignore_pinned: true          # Skip pinned messages
        ignore_bots: false           # Skip bot messages
        ignore_roles: []             # Skip messages from users with these roles`,
        commands: [
          "!autoclean add #channel keepx <n> — keep last N messages",
          "!autoclean add #channel interval <seconds> — clean every N seconds",
          "!autoclean add #channel maxage <seconds> — delete messages older than N seconds",
          "!autoclean remove #channel — remove autoclean for channel",
          "!autoclean list — list all autoclean rules",
          "!autoclean enable #channel — re-enable a disabled rule",
          "!autoclean disable #channel — pause autoclean for channel",
          "!autoclean now #channel — run autoclean immediately",
        ],
      },
      {
        name: "slowmode_auto",
        label: "Auto Slowmode",
        description:
          "Dynamically increase channel slowmode when the message rate exceeds a threshold, then automatically restore it when activity drops back down.",
        configTitle: "Auto Slowmode Config",
        config: `plugins:
  slowmode_auto:
    enabled: true
    ignore_channels: []   # Never apply to these channels
    ignore_roles: []      # Messages from these roles don't count
    rules:
      - channel_id: 123456789012345678
        msg_per_minute: 30         # Trigger when rate exceeds this
        slowmode_seconds: 5        # Slowmode to apply
        restore_after: 60          # Seconds of calm before restoring
    messages:
      slowmode_applied: "Slowmode of {count}s applied in {channel.mention} (high activity)"
      slowmode_removed: "Slowmode removed in {channel.mention}"`,
        commands: [],
      },
    ],
  },

  // ── LOGGING ───────────────────────────────────────────────────
  {
    category: "Logging",
    plugins: [
      {
        name: "logging",
        label: "Logging",
        description:
          "Comprehensive audit logging split across up to 8 independent channels. Every log message is independently customizable via the messages block. Ignored channels are never logged.",
        configTitle: "Logging Config",
        config: `plugins:
  logging:
    enabled: true
    channel: null               # Fallback if a specific channel is null
    ignored_channels: []        # Never log events from these channels
    ignored_users: []           # Never log events involving these users
    channels:
      moderation: 123456789     # Ban, kick, mute, warn, case actions
      messages:   123456790     # Message edits, deletes, bulk deletes
      members:    123456791     # Joins, leaves, role changes, nickname changes
      voice:      null          # Voice channel join/leave/move
      server:     null          # Channel/role/server setting changes
      automod:    null          # Automod strikes and deleted messages
      antinuke:   null          # Anti-nuke trigger events
      antiraid:   null          # Anti-raid trigger events
    messages:
      message_delete:       "Message deleted by {user} in {channel} | Content: {trigger}"
      message_edit:         "{user} edited in {channel} | Before: {trigger} | After: {reason}"
      message_bulk_delete:  "{count} messages deleted in {channel}"
      member_join:          "{user} joined | Created: {user.created_at} | Members: {server.member_count}"
      member_leave:         "{user} left | Joined: {user.joined_at}"
      member_ban:           "{user} was banned"
      member_unban:         "{user} was unbanned"
      role_added:           "{user} received {trigger}"
      role_removed:         "{user} lost {trigger}"
      nickname_change:      "{user} changed nickname | Before: {trigger} | After: {reason}"
      voice_join:           "{user} joined {channel}"
      voice_leave:          "{user} left {channel}"
      voice_move:           "{user} moved from {trigger} to {reason}"
      channel_create:       "{channel} was created"
      channel_delete:       "{trigger} was deleted"
      channel_update:       "{channel} was updated"
      role_create:          "{trigger} role was created"
      role_delete:          "{trigger} role was deleted"
      role_update:          "{trigger} role was updated"
      server_update:        "Server settings were updated"
      mod_action:           "{mod} {action}d {user} | Reason: {reason} | Duration: {duration} | Case: #{case_id}"`,
        commands: [],
      },
    ],
  },

  // ── COMMUNITY ─────────────────────────────────────────────────
  {
    category: "Community",
    plugins: [
      {
        name: "welcome",
        label: "Welcome",
        description:
          "Welcome/goodbye messages, join DMs, auto-roles on join, account age gating, role restoration on rejoin, and member count channel auto-update.",
        configTitle: "Welcome Config",
        config: `plugins:
  welcome:
    enabled: true

    # ── Welcome message ───────────────────────────────────────────
    welcome:
      enabled: true
      channel: 123456789012345678
      ping: false                   # Ping the user in the welcome message
      delete_after: null            # Auto-delete welcome after N seconds
      message: "Welcome {user.mention} to **{server}**! You are member #{server.member_count}."

    # ── Goodbye message ───────────────────────────────────────────
    goodbye:
      enabled: true
      channel: 123456789012345678
      delete_after: null
      message: "{user} has left the server."

    # ── DM on join ────────────────────────────────────────────────
    join_dm:
      enabled: false
      message: "Welcome to **{server}**! Please read the rules."

    # ── Auto-role on join ─────────────────────────────────────────
    welcome_role:
      enabled: false
      role: null                    # Role ID to give on join

    # ── Account age gate ─────────────────────────────────────────
    account_age_gate:
      enabled: false
      min_age_days: 7               # Minimum account age in days
      kick: true                    # Kick if account is too new
      message: "Your account must be at least 7 days old to join this server."

    # ── Role restoration on rejoin ────────────────────────────────
    rejoin_restore_roles:
      enabled: false
      ignore_roles: []              # Role IDs to never restore

    # ── Member count channel ──────────────────────────────────────
    member_count_channel:
      enabled: false
      channel: null                 # Voice channel ID used as counter
      format: "Members: {server.member_count}"
      update_on: "both"             # join | leave | both`,
        commands: ["!welcome_test — post a test welcome message for yourself"],
      },
      {
        name: "starboard",
        label: "Starboard",
        description:
          "Pin popular messages to a dedicated starboard channel when they accumulate enough star reactions. Configurable emoji, threshold, age limit, and self-star rules.",
        configTitle: "Starboard Config",
        config: `plugins:
  starboard:
    enabled: true
    channel: 123456789012345678     # Where starred messages appear
    emoji: "⭐"                      # Reaction emoji to count
    threshold: 5                    # Stars needed to post
    self_star: false                # Can users star their own messages?
    remove_on_unstar: true          # Remove from starboard if stars drop below threshold
    ignore_channels: []             # Channels whose messages can't be starred
    ignore_roles: []                # Users with these roles can't be starred
    ignored_users: []               # Specific users excluded
    nsfw_allowed: false             # Allow starboard posts from NSFW channels
    max_age_days: 7                 # Only star messages newer than this (0 = no limit)
    bots_allowed: false             # Allow bot messages on starboard
    messages:
      starboard_empty: "No starred messages found"
      stats_none:      "No star data found for {user}"`,
        commands: [
          "!starboard top [n] — top N starred messages (default 10)",
          "!starboard stats [@user] — star statistics for a user",
          "!starboard clear @user — remove all of a user's starred messages",
        ],
      },
      {
        name: "tags",
        label: "Tags",
        description:
          "Create reusable text or embed responses triggered by !tag <name>. Tags can be defined in YAML config or created via commands.",
        configTitle: "Tags Config",
        config: `# In YAML config (top-level, not under plugins):
tags:
  rules:   "Please read the rules in #rules!"
  support: "Please open a ticket in #support."
  faq:     "Check our FAQ at https://example.com/faq"
  staff:   "Our staff team consists of @Admins and @Mods."

# Or create them dynamically via commands:
# !tag create rules Please read the rules in #rules!

plugins:
  tags:
    enabled: true
    messages:
      tag_not_found:   "Tag {trigger} not found"
      tag_list_empty:  "No tags created yet"`,
        commands: [
          "!tag <name> — use a tag",
          "!tag list — list all available tags",
          "!tag create <name> <content> — create a new tag",
          "!tag edit <name> <new_content> — edit an existing tag",
          "!tag delete <name> — delete a tag",
          "!tag info <name> — view tag details",
        ],
      },
    ],
  },

  // ── TICKETS ───────────────────────────────────────────────────
  {
    category: "Tickets",
    plugins: [
      {
        name: "tickets",
        label: "Tickets",
        description:
          "Full-featured support ticket system. Create button or dropdown panels with multiple categories. Supports claiming, user management, transcripts, and per-user blacklisting.",
        configTitle: "Tickets Config",
        config: `plugins:
  tickets:
    enabled: true
    log_channel: null          # Channel for open/close events
    transcript_channel: null   # Channel for transcript posts
    dm_transcript: true        # DM transcript to user on close
    max_open_per_user: 1       # Max open tickets per user (0 = unlimited)
    messages:
      ticket_opened:         "Your ticket has been opened in {channel.mention}"
      ticket_already_open:   "You already have an open ticket at {channel.mention}"
      ticket_blacklisted:    "You are blacklisted from opening tickets | Reason: {reason}"
      ticket_closed:         "Ticket closed by {mod} | Reason: {reason}"
      ticket_claimed:        "Ticket claimed by {mod.mention}"
      ticket_deleted:        "Ticket deleted by {mod} | Reason: {reason}"
      not_a_ticket:          "This command can only be used inside a ticket channel"
      blacklist_success:     "{user} blacklisted from tickets | Reason: {reason}"
      unblacklist_success:   "{user} removed from ticket blacklist"`,
        commands: [
          "!ticket panel create <name> <button|dropdown> [#channel] — create a new panel",
          "!ticket panel post <name> — post the panel in its channel",
          "!ticket panel delete <name> — delete a panel",
          "!ticket panel list — list all panels",
          "!ticket close [reason] — close ticket (inside ticket channel)",
          "!ticket delete [reason] — delete ticket channel entirely",
          "!ticket claim — claim this ticket",
          "!ticket unclaim — release claim",
          "!ticket adduser @user — add a user to the ticket",
          "!ticket removeuser @user — remove a user from ticket",
          "!ticket rename <new_name> — rename ticket channel",
          "!ticket blacklist [@user] [reason] — blacklist user / list blacklist",
          "!ticket unblacklist @user — unblacklist user",
        ],
      },
    ],
  },

  // ── ROLES ─────────────────────────────────────────────────────
  {
    category: "Roles",
    plugins: [
      {
        name: "reaction_roles",
        label: "Reaction Roles",
        description:
          "Create button or dropdown panels that let users self-assign roles. Supports max-role limits, required roles to interact, and remove-on-reselect.",
        configTitle: "Reaction Roles Config",
        config: `plugins:
  reaction_roles:
    enabled: true
    messages:
      rr_created:      "Panel {trigger} created"
      rr_entry_added:  "Role {trigger} added to panel {reason}"
      rr_posted:       "Panel {trigger} posted in {channel.mention}"
      rr_deleted:      "Panel {trigger} deleted"
      rr_not_found:    "Panel {trigger} not found"
      rr_list_empty:   "No reaction role panels found"
      rr_max_reached:  "You've reached the maximum number of roles for this panel"
      rr_role_given:   "You have been given {trigger}"
      rr_role_removed: "You no longer have {trigger}"`,
        commands: [
          "!rr create <name> <button|dropdown> — create a new panel",
          "!rr add <panel_name> <@role> <emoji_or_label> [description] — add a role to panel",
          "!rr remove <panel_name> <@role> — remove a role from panel",
          "!rr post <panel_name> — post the panel (sends message with buttons/dropdown)",
          "!rr delete <panel_name> — delete a panel",
          "!rr list — list all panels",
          "!rr info <panel_name> — view panel details",
        ],
      },
      {
        name: "roles",
        label: "Roles",
        description:
          "Manually add/remove roles with reason logging and DM notifications. Add temporary roles that expire automatically.",
        configTitle: "Roles Config",
        config: `plugins:
  roles:
    enabled: true
    dm_on_action: true     # DM users when roles are added/removed
    messages:
      addrole_success:    "{user} has been given {trigger} | Reason: {reason}"
      removerole_success: "{trigger} removed from {user} | Reason: {reason}"
      temprole_success:   "{user} given {trigger} | Duration: {duration} | Expires: {expires_at}"
      temprole_expired:   "{user}'s {trigger} role has expired"
      temprole_list_empty:"No active temp roles"
      error_role_not_found:    "Role not found"
      error_role_hierarchy:    "That role is above my highest role"`,
        commands: [
          "!addrole @user <@role> [reason] — give a role to a user",
          "!removerole @user <@role> [reason] — remove a role from a user",
          "!temprole @user <@role> <duration> [reason] — give a role that expires",
          "!temproles [@user] — list active temporary roles",
        ],
      },
      {
        name: "duration_roles",
        label: "Duration Roles",
        description:
          "Configure roles with built-in expiry. Optionally send DM warnings N days before expiry.",
        configTitle: "Duration Roles Config",
        config: `plugins:
  duration_roles:
    enabled: true
    roles:
      - role_id: 123456789012345678
        warn_before_days: 3     # DM warning X days before expiry
    messages:
      role_expired:            "{user}'s {trigger} role has expired"
      role_expiry_warning_dm:  "Your {trigger} role in {server} expires in {count} days"
      role_expired_dm:         "Your {trigger} role in {server} has expired and been removed"`,
        commands: ["!giverole @user <@role> <duration> [reason] — assign a duration role"],
      },
    ],
  },

  // ── UTILITIES ─────────────────────────────────────────────────
  {
    category: "Utilities",
    plugins: [
      {
        name: "utility",
        label: "Utility",
        description:
          "General-purpose lookup and display commands: user info, server info, avatar, banner, permissions viewer, role listing, snowflake decoder, and moderator statistics.",
        configTitle: "Utility Config",
        config: `plugins:
  utility:
    enabled: true
    custom_help_entries: []    # Extra entries shown in !help
    messages:
      help_not_found:    "Command {trigger} not found"
      inrole_empty:      "No members have that role"
      banner_none:       "{user} has no banner set"
      bansearch_not_found: "{trigger} is not banned in this server"`,
        commands: [
          "!userinfo [@user] — full user info (join date, roles, ID, creation date)",
          "!avatar [@user] — show user's avatar",
          "!banner [@user] — show user's profile banner",
          "!serverinfo — server details (channels, roles, member count, boost level)",
          "!roleinfo <@role> — role details (color, ID, members, permissions)",
          "!channelinfo [#channel] — channel details",
          "!membercount — current server member count",
          "!roles [@user] — list user's roles",
          "!joined [@user] — when user joined the server",
          "!snowflake <id> — decode Discord snowflake to timestamp",
          "!permissions [@user] [#channel] — view effective permissions",
          "!inrole <@role> — list all members with a specific role",
          "!charcount <text> — count characters in text",
          "!warncount [@user] — count warnings",
          "!modstats [@mod] — moderator action statistics",
          "!bansearch <user_id> — check if user is banned",
          "!casesearch <keyword> — search cases by reason keyword",
          "!embed <json> — post a custom embed from JSON",
          "!help [command] — help menu or command-specific help",
        ],
      },
      {
        name: "reminders",
        label: "Reminders",
        description:
          "Set personal reminders. The bot will DM you when the reminder fires.",
        configTitle: "Reminders Config",
        config: `plugins:
  reminders:
    enabled: true
    messages:
      reminder_set:        "Reminder set for {duration} | Message: {reminder_message}"
      reminder_fired:      "{user.mention} Reminder: {reminder_message} | Set {reminder_set_at}"
      reminder_not_found:  "Reminder not found"
      reminder_deleted:    "Reminder deleted"
      reminder_list_empty: "You have no active reminders"`,
        commands: [
          "!remind <duration> <message> — set a reminder",
          "!reminders — list your active reminders",
          "!delreminder <id> — delete a specific reminder",
        ],
      },
      {
        name: "timezones",
        label: "Timezones",
        description:
          "Users set their timezone once. Then anyone can look up someone's current time or convert between zones.",
        configTitle: "Timezones Config",
        config: `plugins:
  timezones:
    enabled: true
    messages:
      timezone_set:      "Your timezone has been set to {trigger}"
      timezone_get:      "{user}'s timezone is {trigger}"
      timezone_cleared:  "Your timezone has been cleared"
      timezone_not_set:  "{user} has not set a timezone"
      timezone_invalid:  "Invalid timezone. Example: America/New_York"
      time_result:       "Current time for {user}: {trigger}"
      timefor_result:    "Current time in {trigger}: {reason}"`,
        commands: [
          "!timezone set <tz> — set your timezone (e.g. America/New_York, Europe/London)",
          "!timezone get [@user] — see a user's timezone",
          "!timezone clear — clear your timezone",
          "!timezone list — list all members with timezones set",
          "!time [@user] — current time for a user",
          "!timefor <timezone> — current time in any timezone",
          "!timeconvert <time> <from_tz> <to_tz> — convert time between zones",
        ],
      },
      {
        name: "dev",
        label: "Dev / Owner",
        description:
          "Bot owner–only commands for managing whitelisted servers, evaluating code, reloading plugins, and inspecting bot state.",
        configTitle: "Owner-Only Commands",
        config: `# These commands are only available to BOT_OWNER_ID.
# They cannot be delegated via the levels system.

# Whitelist a server:
# !whitelist <guild_id> <owner_user_id> [notes]

# Unwhitelist a server (bot will leave):
# !unwhitelist <guild_id>

# No YAML configuration — owner commands are hardcoded.`,
        commands: [
          "!whitelist <guild_id> <owner_id> [notes] — whitelist a server",
          "!unwhitelist <guild_id> — remove server from whitelist (bot leaves)",
          "!whitelistlist — list all whitelisted servers",
          "!whitelistinfo <guild_id> — details about a whitelisted server",
          "!devleave <guild_id> — force-leave a server",
          "!devservers — list all servers the bot is in",
          "!deveval <code> — evaluate Python code",
          "!devreload <plugin_name> — hot-reload a plugin",
          "!devreloadall — reload all plugins",
          "!devstats — bot statistics (latency, memory, uptime)",
        ],
      },
    ],
  },
];

/* ──────────────────────────────────────────────────────────────
   COMPONENT
────────────────────────────────────────────────────────────── */

const GLASS = {
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  backdropFilter: "blur(12px)",
};

export default function Docs() {
  const [, setLocation] = useLocation();
  const [selectedPlugin, setSelectedPlugin] = useState(PLUGIN_CATEGORIES[0].plugins[0]);
  const [activeSection, setActiveSection] = useState<"overview" | "config" | "commands">("overview");

  return (
    <div
      className="min-h-screen w-full flex flex-col"
      style={{
        backgroundImage: `url(${import.meta.env.BASE_URL}nightsky.png)`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
      }}
    >
      <div className="absolute inset-0 fixed" style={{ background: "linear-gradient(180deg, rgba(6,8,20,0.72) 0%, rgba(10,12,28,0.78) 100%)" }} />

      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Nav */}
        <nav style={{ borderBottom: "1px solid rgba(255,255,255,0.07)", backdropFilter: "blur(20px)", background: "rgba(8,10,24,0.55)" }}>
          <div className="max-w-7xl mx-auto px-5 h-14 flex items-center justify-between">
            <button onClick={() => setLocation("/")} className="flex items-center gap-2.5 text-white font-bold text-base hover:text-indigo-300 transition-colors">
              <div className="w-7 h-7 rounded-lg overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.2)" }}>
                <img src={`${import.meta.env.BASE_URL}pigeon.jpeg`} alt="Night Pigeon" className="w-full h-full object-cover" />
              </div>
              Night Pigeon
            </button>
            <div className="flex items-center gap-3">
              <button onClick={() => setLocation("/dashboard")} className="text-sm px-3 py-1.5 transition-colors" style={{ color: "rgba(255,255,255,0.5)" }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.9)")}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.5)")}>
                Dashboard
              </button>
              <span className="text-xs px-2 py-1 rounded" style={{ background: "rgba(99,102,241,0.2)", color: "rgba(165,180,252,0.9)", border: "1px solid rgba(99,102,241,0.3)" }}>
                Wikipedia
              </span>
            </div>
          </div>
        </nav>

        <div className="flex flex-1 max-w-7xl mx-auto w-full px-5 py-5 gap-5">
          {/* Sidebar */}
          <div className="w-52 shrink-0">
            <div className="sticky top-5 max-h-[calc(100vh-6rem)] overflow-y-auto pr-1" style={{ scrollbarWidth: "thin", scrollbarColor: "rgba(255,255,255,0.1) transparent" }}>
              {PLUGIN_CATEGORIES.map((cat) => (
                <div key={cat.category} className="mb-4">
                  <div className="text-xs font-semibold uppercase tracking-widest px-2 py-1 mb-1" style={{ color: "rgba(255,255,255,0.35)" }}>
                    {cat.category}
                  </div>
                  {cat.plugins.map((plugin) => (
                    <button
                      key={plugin.name}
                      onClick={() => { setSelectedPlugin(plugin); setActiveSection("overview"); }}
                      className="w-full text-left py-1.5 text-sm rounded-md transition-all mb-0.5"
                      style={selectedPlugin.name === plugin.name
                        ? { background: "rgba(99,102,241,0.2)", color: "rgba(255,255,255,0.95)", borderLeft: "2px solid rgba(129,140,248,0.7)", paddingLeft: "10px" }
                        : { color: "rgba(255,255,255,0.5)", paddingLeft: "12px" }}
                      onMouseEnter={e => { if (selectedPlugin.name !== plugin.name) (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.85)"; }}
                      onMouseLeave={e => { if (selectedPlugin.name !== plugin.name) (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.5)"; }}
                    >
                      {plugin.label}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            <div className="rounded-xl p-7" style={GLASS}>
              <div className="flex items-start justify-between mb-5">
                <div>
                  <h1 className="text-2xl font-bold text-white">{selectedPlugin.label}</h1>
                  <p className="mt-1.5 text-sm leading-relaxed max-w-2xl" style={{ color: "rgba(255,255,255,0.55)" }}>{selectedPlugin.description}</p>
                </div>
                <span className="text-xs px-2 py-1 rounded shrink-0 ml-4 mt-1" style={{ background: "rgba(99,102,241,0.2)", color: "rgba(165,180,252,0.9)", border: "1px solid rgba(99,102,241,0.25)" }}>
                  Plugin
                </span>
              </div>

              {/* Tabs */}
              <div className="flex gap-0.5 mb-6" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                {(["overview", "config", "commands"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => setActiveSection(s)}
                    className="px-4 py-2 text-sm capitalize transition-colors"
                    style={activeSection === s
                      ? { color: "rgba(255,255,255,0.95)", borderBottom: "2px solid rgba(129,140,248,0.8)", marginBottom: "-1px" }
                      : { color: "rgba(255,255,255,0.4)" }}
                    onMouseEnter={e => { if (activeSection !== s) (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.7)"; }}
                    onMouseLeave={e => { if (activeSection !== s) (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.4)"; }}
                  >
                    {s === "commands" ? `Commands (${selectedPlugin.commands.length})` : s}
                  </button>
                ))}
              </div>

              {/* Overview */}
              {activeSection === "overview" && (
                <div className="space-y-4">
                  <div className="rounded-lg p-4" style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)" }}>
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-sm font-medium text-indigo-300">Quick Enable</span>
                    </div>
                    <p className="text-sm font-mono" style={{ color: "rgba(255,255,255,0.65)" }}>
                      Add <code className="px-1.5 py-0.5 rounded text-xs" style={{ background: "rgba(0,0,0,0.4)", color: "#86efac" }}>enabled: true</code> under <code className="px-1.5 py-0.5 rounded text-xs" style={{ background: "rgba(0,0,0,0.4)", color: "#93c5fd" }}>plugins: {selectedPlugin.name}:</code> to activate with defaults.
                    </p>
                  </div>
                  {selectedPlugin.commands.length > 0 && (
                    <div className="rounded-lg p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                      <h3 className="text-white font-medium text-sm mb-3">All Commands</h3>
                      <div className="space-y-2">
                        {selectedPlugin.commands.map((cmd) => {
                          const dIdx = cmd.indexOf(" — ");
                          const sig = dIdx > -1 ? cmd.slice(0, dIdx) : cmd;
                          const desc = dIdx > -1 ? cmd.slice(dIdx + 3) : "";
                          const parts = sig.split(" ");
                          return (
                            <div key={cmd} className="flex items-start gap-3">
                              <div className="flex-1 min-w-0">
                                <span className="font-mono text-sm text-green-400">{parts[0]}</span>
                                {parts.length > 1 && <span className="font-mono text-sm" style={{ color: "rgba(255,255,255,0.4)" }}> {parts.slice(1).join(" ")}</span>}
                              </div>
                              {desc && <span className="text-xs shrink-0 text-right" style={{ color: "rgba(255,255,255,0.35)", maxWidth: "45%" }}>{desc}</span>}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Config */}
              {activeSection === "config" && (
                <div>
                  <p className="text-sm mb-3" style={{ color: "rgba(255,255,255,0.45)" }}>
                    {(selectedPlugin as typeof selectedPlugin & { configTitle?: string }).configTitle ?? `${selectedPlugin.label} configuration`}:
                  </p>
                  <div className="rounded-lg overflow-hidden" style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <div className="flex items-center gap-2 px-4 py-2.5" style={{ background: "rgba(255,255,255,0.04)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: "rgba(239,68,68,0.6)" }} />
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: "rgba(234,179,8,0.6)" }} />
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: "rgba(34,197,94,0.6)" }} />
                      <span className="text-xs ml-1" style={{ color: "rgba(255,255,255,0.25)" }}>config.yaml</span>
                    </div>
                    <pre className="p-4 overflow-x-auto max-h-[60vh] overflow-y-auto">
                      <code className="text-sm font-mono leading-relaxed" style={{ color: "#86efac" }}>{selectedPlugin.config}</code>
                    </pre>
                  </div>
                  <p className="text-xs mt-3" style={{ color: "rgba(255,255,255,0.25)" }}>
                    Use <code className="px-1 rounded text-indigo-400" style={{ background: "rgba(0,0,0,0.3)" }}>!setconfig</code> to apply changes. Only include keys you want to override — defaults are preserved.
                  </p>
                </div>
              )}

              {/* Commands */}
              {activeSection === "commands" && (
                <div>
                  {selectedPlugin.commands.length === 0 ? (
                    <div className="py-10 text-center rounded-lg" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}>
                      <p className="text-sm" style={{ color: "rgba(255,255,255,0.3)" }}>This plugin has no user-facing commands — it operates automatically.</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {selectedPlugin.commands.map((cmd) => {
                        const dIdx = cmd.indexOf(" — ");
                        const sig = dIdx > -1 ? cmd.slice(0, dIdx) : cmd;
                        const desc = dIdx > -1 ? cmd.slice(dIdx + 3) : "";
                        const parts = sig.split(" ");
                        return (
                          <div key={cmd} className="rounded-lg px-4 py-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <code className="font-mono text-sm text-green-400">{parts[0]}</code>
                                {parts.length > 1 && <code className="font-mono text-sm" style={{ color: "rgba(255,255,255,0.4)" }}> {parts.slice(1).join(" ")}</code>}
                              </div>
                              {desc && <span className="text-xs text-right shrink-0" style={{ color: "rgba(255,255,255,0.4)", maxWidth: "55%" }}>{desc}</span>}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
