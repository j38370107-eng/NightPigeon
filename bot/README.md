# Discord Moderation Bot

A feature-rich, plugin-based Discord moderation bot inspired by Zeppelin and Hepboat. All responses, DMs, and messages are fully customizable per-server via YAML configuration stored in PostgreSQL.

---

## Setup

### 1. Install Requirements

```bash
cd bot
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the `bot/` folder:

```env
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=your_postgresql_url_here
BOT_OWNER_ID=your_discord_user_id_here
```

### 3. Set Up PostgreSQL

Run all the CREATE TABLE statements from the `database.sql` file:

```bash
psql $DATABASE_URL < database.sql
```

Or run them manually in your PostgreSQL client.

### 4. Run the Bot

```bash
cd bot
python main.py
```

---

## Whitelisting Servers

Only whitelisted servers can use the bot. To whitelist a server:

```
!whitelist <server_id> <owner_user_id> [notes]
```

This command is only available to the `BOT_OWNER_ID`.

The bot will automatically leave any non-whitelisted server it joins.

---

## Setting Server Config

### Commands

| Command | Description | Access |
|---------|-------------|--------|
| `!setconfig` | Set server config (paste YAML in code block) | Server owner + config access users |
| `!getconfig` | DMs you the current raw YAML | Server owner + config access users |
| `!resetconfig` | Resets config to defaults | Server owner |
| `!configaccess add @user` | Grant config access | Server owner only |
| `!configaccess remove @user` | Remove config access | Server owner only |
| `!configaccess list` | List config access users | Server owner only |

### How to Set Config

```
!setconfig
\```yaml
levels:
  roles:
    "1234567890": 50
plugins:
  moderation:
    enabled: true
    mute_role: "9876543210"
\```
```

---

## Levels System

Levels control who can use which commands. Range: 0–100. Bot owner is always 1000.

```yaml
levels:
  users:
    "123456789": 100    # This user has level 100
  roles:
    "987654321": 50     # Members with this role have level 50
  commands:
    ban: 50             # Override default command level
    kick: 25
```

**Default levels:** ban=50, kick=25, mute=25, warn=25, massban=100, etc.

Commands below user level are silently ignored.

---

## Alias System

Define short aliases for commands:

```yaml
plugins:
  command_aliases:
    config:
      aliases:
        "b": "ban"
        "k": "kick"
        "m": "mute"
        "w": "warn"
        "p": "purge"
```

---

## Preset Reasons

Map short keys to full reason text:

```yaml
plugins:
  preset_reasons:
    config:
      presets:
        "spam": "Spamming in chat"
        "ads": "Advertising without permission"
        "toxic": "Toxic behavior towards members"
```

Usage: `!ban @user spam` → reason becomes "Spamming in chat"

---

## Tags

Define tags in YAML:

```yaml
tags:
  rules: "Please read the rules in #rules!"
  support: "Open a ticket in #support."
  faq: "Check our FAQ at https://example.com/faq"
```

Usage: `!tag rules`

---

## All Commands by Plugin

### Moderation
- `!ban @user [duration] [reason]` — Ban a user
- `!forceban <user_id> [duration] [reason]` — Ban by ID
- `!unban <user_id> [reason]` — Unban a user
- `!tempban @user <duration> [reason]` — Temporary ban
- `!softban @user [reason]` — Ban then immediately unban (clears messages)
- `!banlist` — List recent bans
- `!baninfo <user_id>` — Ban info for user ID
- `!kick @user [reason]` — Kick a user
- `!mute @user [duration] [reason]` — Mute a user
- `!forcemute <user_id> [duration] [reason]` — Mute by ID
- `!unmute @user [reason]` — Unmute a user
- `!forceunmute <user_id> [reason]` — Unmute by ID
- `!mutelist` — List muted users
- `!warn @user [reason]` — Warn a user
- `!forcewarn <user_id> [reason]` — Warn by ID
- `!purge <amount>` — Purge messages
- `!purge bots/embeds/images/links/contains <text> <amount>`
- `!slowmode <seconds> [#channel]` — Set slowmode
- `!slowmode off [#channel]` — Remove slowmode
- `!nick @user <nickname>` — Set nickname
- `!resetnick @user` — Reset nickname
- `!locknick @user` — Lock nickname (prevents changes)
- `!unlocknick @user` — Unlock nickname
- `!lock [#channel] [reason]` — Lock channel
- `!unlock [#channel]` — Unlock channel
- `!hide [#channel]` — Hide channel
- `!unhide [#channel]` — Unhide channel
- `!nuke [#channel]` — Clone+delete channel
- `!watch @user [reason]` — Add to watchlist
- `!unwatch @user` — Remove from watchlist
- `!watchlist` — View watchlist
- `!immune @user` — Automod immune
- `!unimmune @user` — Remove immunity
- `!immunelist` — List immune users
- `!roleban @user <@role> [reason]` — Ban user from role
- `!unroleban @user <@role>` — Remove role ban
- `!rolebanned @user` — View user's role bans
- `!seen @user` — When was user last seen
- `!cleanup <amount>` — Delete bot messages

### Cases
- `!case <id>` — View case
- `!cases @user` — View user's cases
- `!servercases` — Recent server cases
- `!deletecase <id>` — Delete case
- `!reason <id> <reason>` — Update case reason
- `!editcase <id> reason/duration <value>` — Edit case
- `!addcase @user <type> [reason]` — Add case silently
- `!casecount @user` — Count cases
- `!note @user <text>` — Add note
- `!viewnote <id>` — View note
- `!viewnotes @user` — View all notes
- `!deletenote <id>` — Delete note
- `!notesearch <keyword>` — Search notes
- `!editnote <id> <text>` — Edit note

### Mass Actions
- `!masswarn @user1 @user2 ... | [reason]`
- `!massmute @user1 @user2 ... [duration] | [reason]`
- `!masskick @user1 @user2 ... | [reason]`
- `!massban @user1 @user2 ... [duration] | [reason]`
- `!massunban <id1> <id2> ... | [reason]`
- `!massunmute @user1 @user2 ... | [reason]`

### Utility
- `!userinfo [@user]` — User information
- `!avatar [@user]` — User avatar
- `!banner [@user]` — User banner
- `!serverinfo` — Server information
- `!roleinfo <@role>` — Role information
- `!channelinfo [#channel]` — Channel information
- `!membercount` — Member count
- `!roles [@user]` — User's roles
- `!joined [@user]` — When user joined
- `!snowflake <id>` — Snowflake timestamp
- `!permissions [@user] [#channel]` — View permissions
- `!inrole <@role>` — Members with role
- `!charcount <text>` — Character count
- `!warncount [@user]` — Warning count
- `!modstats [@mod]` — Moderator stats
- `!bansearch <user_id>` — Check if user is banned
- `!casesearch <keyword>` — Search cases
- `!embed <json>` — Post embed from JSON
- `!help [command]` — Help menu

### Levels
- `!level [@user]` — View level
- `!levels` — List all level assignments
- `!levelset [@user]` — Show effective level

### Lockdown
- `!lockdown [#channel] [reason]` — Lock a channel
- `!lockdown <preset> [reason]` — Apply lockdown preset
- `!lockdown -server` — Lock all channels
- `!lockdown list` — List locked channels
- `!unlock [#channel]` — Unlock channel
- `!unlock -server` — Unlock all channels

### Raid Mode
- `!raidmode on/off` — Toggle raid mode

### Tags
- `!tag <name>` — Use a tag
- `!tag list` — List all tags

### Reminders
- `!remind <duration> <message>` — Set reminder
- `!reminders` — List your reminders
- `!delreminder <id>` — Delete reminder

### Roles
- `!addrole @user <@role> [reason]` — Add role
- `!removerole @user <@role> [reason]` — Remove role
- `!temprole @user <@role> <duration> [reason]` — Temp role
- `!temproles [@user]` — List temp roles

### Reaction Roles
- `!rr create <name> <button|dropdown|emoji> [#channel]`
- `!rr add <name> <@role> <emoji_or_label>`
- `!rr post <name>` — Post the panel
- `!rr delete <name>` — Delete panel
- `!rr list` — List all panels

### Tickets
- `!ticket panel create <name> <button|dropdown> [#channel]`
- `!ticket panel post <name>` — Post ticket panel
- `!ticket close [reason]` — Close ticket (in ticket channel)
- `!ticket claim` — Claim ticket
- `!ticket adduser @user` — Add user to ticket
- `!ticket removeuser @user` — Remove user from ticket
- `!ticket rename <name>` — Rename ticket channel
- `!ticket blacklist [@user] [reason]` — Blacklist user / list blacklist
- `!ticket unblacklist @user` — Unblacklist user

### Welcome
- `!welcome_test` — Test welcome message

### Starboard
- `!starboard top [count]` — Top starred messages
- `!starboard stats [@user]` — Star stats
- `!starboard clear @user` — Clear user's stars

### History
- `!history @user` — Full history
- `!history @user cases/notes/joins/roles` — Filtered history
- `!history clear @user` — Clear history events

### Auto Replies
- `!autoreply add <type> <trigger> <response>`
- `!autoreply remove <id>`
- `!autoreply list`
- `!autoreply enable/disable <id>`

### Auto Reactions
- `!autoreaction add <type> <trigger> <emoji1> [emoji2]...`
- `!autoreaction remove <id>`
- `!autoreaction list`

### Auto Clean
- `!autoclean add <#channel> <mode> <value>` — mode: interval/keepx/maxage
- `!autoclean remove <#channel>`
- `!autoclean list`
- `!autoclean now <#channel>` — Run immediately

### Timezones
- `!timezone set <tz>` — Set your timezone (e.g. America/New_York)
- `!timezone get [@user]` — Get timezone
- `!timezone clear` — Clear timezone
- `!timezone list` — List all member timezones
- `!time [@user]` — Current time for user
- `!timefor <timezone>` — Current time in timezone
- `!timeconvert <time> <from_tz> <to_tz>` — Convert time

### Config
- `!setconfig` — Set server YAML config
- `!getconfig` — Get current YAML config (DM)
- `!resetconfig` — Reset to defaults
- `!configaccess add/remove/list @user`

### Dev (Owner Only)
- `!whitelist <server_id> <owner_id> [notes]`
- `!unwhitelist <server_id>`
- `!whitelistlist`
- `!whitelistinfo <server_id>`
- `!devleave <server_id>`
- `!devservers`
- `!deveval <code>`
- `!devreload <plugin>`
- `!devreloadall`
- `!devstats`

---

## Automod Rules

Enable any rule in your YAML config. All rules check `automod_immune` and `ignored_users` tables before firing.

1. **spam** — Rate limiting per user
2. **bad_words** — Word list matching
3. **invite_links** — Discord invite detection
4. **mass_mentions** — Too many @mentions
5. **caps_spam** — Excessive CAPS
6. **link_spam** — Too many links
7. **repeated_text** — Duplicate/similar messages
8. **mass_emojis** — Too many emojis
9. **zalgo** — Zalgo text detection
10. **newline_spam** — Too many line breaks
11. **mentionspam** — Ghost ping tracking
12. **links** — Domain whitelist/blacklist/phishing
13. **wordfilter** — Wildcards, regex, l33tspeak normalization
14. **alts** — Account age gate on join
15. **phishing** — Fake Nitro, IP links, lookalike domains

---

## Escalation System

### Manual Escalation

Fires after warn/mute/kick. Configure thresholds:

```yaml
plugins:
  escalation:
    manual:
      enabled: true
      thresholds:
        - tracked_type: "warn"
          count: 3
          action: mute
          duration: "1h"
          reason: "3 warnings"
        - tracked_type: "warn"
          count: 5
          action: ban
          duration: "perm"
          reason: "5 warnings"
```

### Automod Escalation

Counts automod violations per rule per user:

```yaml
plugins:
  escalation:
    automod:
      reset_after_hours: 24
      rules:
        spam:
          thresholds:
            - count: 1
              action: mute
              duration: "10m"
            - count: 3
              action: kick
```

---

## Duration Syntax

| Format | Meaning |
|--------|---------|
| `10m` | 10 minutes |
| `1h` | 1 hour |
| `1d` | 1 day |
| `1w` | 1 week |
| `2d12h` | 2 days 12 hours |
| `perm` | Permanent |

Maximum: 180 days. Longer durations are automatically capped.

---

## YAML Config Reference

```yaml
# ─── Levels ───────────────────────────────────────
levels:
  users:
    "USER_ID": 100        # Direct user level assignment
  roles:
    "ROLE_ID": 50         # Role-based level
  commands:
    ban: 50               # Override default command level

# ─── Tags ─────────────────────────────────────────
tags:
  rules: "Read #rules!"
  support: "Open a ticket in #support"

# ─── Plugins ──────────────────────────────────────
plugins:

  # Moderation
  moderation:
    enabled: true
    mute_role: null                 # Role ID for mute
    dm_on_action: true              # DM users when actioned
    mute_remove_roles: false        # Remove all roles on mute
    ban_delete_message_days: 1      # Days of messages to delete on ban
    messages:
      ban_success: "{user} has been banned | Case: {case_id}"
      # ... customize any message

  # Logging
  logging:
    enabled: false
    channel: null                   # Default log channel ID
    channels:
      moderation: null
      messages: null
      members: null
      voice: null
      server: null
      automod: null
      antinuke: null
      antiraid: null

  # Automod
  automod:
    enabled: false
    spam:
      enabled: false
      max_messages: 5
      interval_seconds: 5
      action: mute                  # delete/mute/kick/ban/warn
      mute_duration_minutes: 10
    bad_words:
      enabled: false
      words: ["word1", "word2"]
      action: delete
    # ... (see full spec for all 15 rules)

  # Escalation
  escalation:
    enabled: true
    manual:
      enabled: true
      thresholds:
        - tracked_type: "warn"
          count: 3
          action: mute
          duration: "1h"
          reason: "3 warnings"

  # Anti-Nuke
  antinuke:
    enabled: false
    whitelist_roles: []
    whitelist_users: []
    thresholds:
      channel_delete: 3
      ban: 5
    interval_seconds: 10
    action: ban

  # Anti-Raid
  antiraid:
    enabled: false
    join_threshold: 10
    join_interval_seconds: 10
    account_age_min_days: 7
    action: kick
    lockdown_channels: []
    auto_unlock_minutes: 10

  # Welcome
  welcome:
    enabled: true
    welcome:
      enabled: false
      channel: null
      message: "Welcome {user.mention} to {server}!"
    goodbye:
      enabled: false
      channel: null
      message: "{user} left."
    welcome_role:
      enabled: false
      role: null

  # Tickets
  tickets:
    enabled: true
    log_channel: null
    transcript_channel: null
    dm_transcript: true
    max_open_per_user: 1

  # Starboard
  starboard:
    enabled: false
    channel: null
    emoji: "⭐"
    threshold: 3
    self_star: false

  # Aliases
  command_aliases:
    config:
      aliases:
        b: ban
        k: kick
        m: mute
        w: warn
        p: purge

  # Preset Reasons
  preset_reasons:
    config:
      presets:
        spam: "Spamming in chat"
        ads: "Advertising without permission"
```
