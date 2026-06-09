import { useState } from "react";
import { useLocation } from "wouter";

const PLUGIN_CATEGORIES = [
  {
    category: "General",
    plugins: [
      {
        name: "introduction",
        label: "Introduction",
        description: "ZepBot is a private moderation bot for Discord, inspired by Zeppelin. It uses a plugin-based architecture where every behavior is controlled through per-server YAML configuration stored in PostgreSQL.",
        config: `# Minimal working config
prefix: "!"

levels:
  users:
    "YOUR_USER_ID": 100   # Give yourself full access
  roles: {}
  commands: {}

plugins:
  moderation:
    enabled: true
    dm_on_action: true`,
        commands: [],
        configTitle: "Quick Start Config",
      },
      {
        name: "configuration",
        label: "Configuration Format",
        description: "The entire bot behavior is driven by YAML stored in PostgreSQL per server. Use !setconfig to update it. The config is deep-merged with defaults so you only need to specify values you want to change.",
        config: `# Config commands
!setconfig          # Paste YAML to update config
!getconfig          # Get current config (DM)
!resetconfig        # Reset to defaults
!configaccess add @user    # Grant config edit access
!configaccess remove @user # Revoke access
!configaccess list         # List users with access`,
        commands: ["!setconfig", "!getconfig", "!resetconfig", "!configaccess add @user", "!configaccess remove @user", "!configaccess list"],
        configTitle: "Config Commands",
      },
      {
        name: "permissions",
        label: "Permissions (Levels)",
        description: "Commands are gated by a numeric level system (0–100). Bot owner is always level 1000. Assign levels to users or roles. Each command has a default minimum level you can override.",
        config: `levels:
  users:
    "123456789": 100    # user_id: level
  roles:
    "987654321": 50     # role_id: level
  commands:
    ban: 50             # override default level
    kick: 25
    mute: 25
    warn: 15
    massban: 100`,
        commands: ["!level [@user]", "!levels", "!levelset [@user]"],
      },
    ],
  },
  {
    category: "Moderation",
    plugins: [
      {
        name: "moderation",
        label: "Moderation",
        description: "Core moderation commands. All messages (success, DMs, errors) are fully customizable via YAML.",
        config: `plugins:
  moderation:
    enabled: true
    mute_role: 123456789      # Role ID to use for muting
    dm_on_action: true         # DM users when actioned
    mute_remove_roles: false   # Strip all roles on mute
    ban_delete_message_days: 1 # Days of messages to delete on ban
    messages:
      ban_success: "{user} has been banned | Case: {case_id}"
      ban_dm: "You have been banned from {server} | Reason: {reason}"
      kick_dm: "You have been kicked from {server} | Reason: {reason}"
      mute_dm: "You have been muted in {server} | Duration: {duration}"
      warn_dm: "You have been warned in {server} | Reason: {reason}"`,
        commands: ["!ban @user [duration] [reason]", "!unban <id> [reason]", "!tempban @user <dur> [reason]", "!softban @user [reason]", "!kick @user [reason]", "!mute @user [dur] [reason]", "!unmute @user [reason]", "!warn @user [reason]", "!purge <n>", "!nick @user <name>", "!locknick @user", "!seen @user"],
      },
      {
        name: "cases",
        label: "Cases",
        description: "Every moderation action creates a tracked case with a unique ID. Cases can be edited, annotated, and searched.",
        config: `plugins:
  cases:
    enabled: true
    messages:
      case_not_found: "Case {trigger} not found"
      no_cases: "No cases found for {user}"`,
        commands: ["!case <id>", "!cases @user", "!servercases", "!reason <id> <reason>", "!editcase <id> reason/duration <value>", "!deletecase <id>", "!addcase @user <type> [reason]", "!note @user <text>", "!casecount @user"],
      },
      {
        name: "mass_actions",
        label: "Mass Actions",
        description: "Ban, mute, kick, or warn multiple users at once. Separate targets from reason using |.",
        config: `plugins:
  mass_actions:
    enabled: true
    max_targets: 20`,
        commands: ["!massban @u1 @u2 ... | [reason]", "!massmute @u1 @u2 ... [dur] | [reason]", "!masskick @u1 @u2 ... | [reason]", "!masswarn @u1 @u2 ... | [reason]", "!massunban <id1> <id2> ... | [reason]"],
      },
      {
        name: "modnick",
        label: "ModNick",
        description: "Automatically rename users with hoisting characters, zalgo text, blank names, or custom patterns. Lock specific nicknames.",
        config: `plugins:
  modnick:
    enabled: true
    default_name: "Moderated Nickname"
    rules:
      hoist: true           # Names starting with ! # etc
      blank: true           # Blank or invisible names
      zalgo: true           # Zalgo/combining characters
      bad_words: true       # Custom word list
      custom_patterns: []   # Regex patterns to block`,
        commands: ["!modnick @user [name]", "!clearnick @user", "!locknick @user", "!unlocknick @user"],
      },
      {
        name: "lockdown",
        label: "Lockdown",
        description: "Lock individual channels or the entire server. Create presets for common lockdown scenarios.",
        config: `plugins:
  lockdown:
    enabled: true
    server_lockdown_channels: []  # Channel IDs for server lockdown
    presets:
      emergency:
        channels: [123456789, 987654321]
        reason: "Emergency lockdown"`,
        commands: ["!lockdown [#channel] [reason]", "!lockdown -server [reason]", "!lockdown <preset> [reason]", "!lockdown list", "!unlock [#channel]", "!unlock -server"],
      },
    ],
  },
  {
    category: "Automation",
    plugins: [
      {
        name: "automod",
        label: "AutoMod",
        description: "15 configurable rules covering spam, bad words, invites, mentions, caps, links, zalgo, phishing, and more. Each rule has independent actions and escalation.",
        config: `plugins:
  automod:
    enabled: true
    spam:
      enabled: true
      max_messages: 5
      interval_seconds: 5
      action: mute            # delete | warn | mute | kick | ban
      mute_duration_minutes: 10
    bad_words:
      enabled: true
      words: ["word1", "word2"]
      action: delete
    invite_links:
      enabled: true
      action: delete
      whitelist_guilds: []
    mass_mentions:
      enabled: true
      max_mentions: 5
      action: mute
    caps_spam:
      enabled: true
      min_length: 10
      cap_percent: 70
      action: delete
    links:
      enabled: false
      mode: blacklist         # whitelist | blacklist
      domains: []
      action: delete
    phishing:
      enabled: true
      action: ban`,
        commands: ["!immune @user", "!unimmune @user", "!immunelist"],
      },
      {
        name: "escalation",
        label: "Escalation",
        description: "Automatically escalate punishments when users accumulate infractions. Two modes: manual (tracks warn/mute/kick) and automod (tracks rule violations).",
        config: `plugins:
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
        - tracked_type: "warn"
          count: 5
          action: ban
          duration: "perm"
          reason: "5 warnings — permanent ban"
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
              action: kick`,
        commands: [],
      },
      {
        name: "antinuke",
        label: "Anti-Nuke",
        description: "Detect and punish mass destructive actions (bans, channel deletes, role deletions) within a configurable time window.",
        config: `plugins:
  antinuke:
    enabled: true
    whitelist_roles: []
    whitelist_users: []
    thresholds:
      channel_delete: 3
      channel_create: 5
      role_delete: 3
      role_create: 5
      ban: 5
      kick: 5
      webhook_create: 3
    interval_seconds: 10
    action: ban               # ban | kick | strip_roles
    quarantine_role: null`,
        commands: [],
      },
      {
        name: "antiraid",
        label: "Anti-Raid",
        description: "Detect mass join events and automatically kick/ban new members or lock down channels. Account age gating included.",
        config: `plugins:
  antiraid:
    enabled: true
    join_threshold: 10
    join_interval_seconds: 10
    account_age_min_days: 7   # Flag accounts newer than this
    action: kick              # kick | ban | lockdown
    lockdown_channels: []
    auto_unlock_minutes: 10`,
        commands: ["!raidmode on/off"],
      },
      {
        name: "autoreply",
        label: "Auto Reply",
        description: "Reply automatically to messages matching triggers. Supports exact, contains, starts_with, ends_with, and regex match types.",
        config: `plugins:
  autoreply:
    enabled: true
    replies:
      - trigger: "hello bot"
        response: "Hello {user.mention}!"
        match_type: contains    # exact|contains|starts_with|ends_with|regex
        delete_trigger: false
        delete_after: null      # seconds`,
        commands: ["!autoreply add <type> <trigger> <response>", "!autoreply remove <id>", "!autoreply list", "!autoreply enable/disable <id>"],
      },
      {
        name: "autoreaction",
        label: "Auto Reaction",
        description: "Automatically add emoji reactions to messages matching triggers or in specific channels.",
        config: `plugins:
  autoreaction:
    enabled: true
    reactions:
      - trigger: "good job"
        emojis: ["👍", "🎉"]
        match_type: contains`,
        commands: ["!autoreaction add <type> <trigger> <emoji>", "!autoreaction remove <id>", "!autoreaction list"],
      },
      {
        name: "autoclean",
        label: "Auto Clean",
        description: "Automatically delete messages in channels on a schedule. Three modes: interval (every N seconds), keepx (keep last N messages), maxage (delete messages older than N seconds).",
        config: `plugins:
  autoclean:
    enabled: true
    channels:
      - id: 123456789
        mode: keepx           # interval | keepx | maxage
        keep_count: 10
        ignore_pinned: true
        ignore_bots: false`,
        commands: ["!autoclean add #channel <mode> <value>", "!autoclean remove #channel", "!autoclean list", "!autoclean now #channel"],
      },
      {
        name: "slowmode_auto",
        label: "Auto Slowmode",
        description: "Dynamically increase channel slowmode when message rate exceeds a threshold, then restore it when activity drops.",
        config: `plugins:
  slowmode_auto:
    enabled: true
    rules:
      - channel_id: 123456789
        msg_per_minute: 30    # Trigger threshold
        slowmode_seconds: 5   # Slowmode to apply
        restore_after: 60     # Seconds before restoring`,
        commands: [],
      },
    ],
  },
  {
    category: "Community",
    plugins: [
      {
        name: "welcome",
        label: "Welcome",
        description: "Welcome/goodbye messages, join DMs, auto-roles on join, account age gating, and role restoration on rejoin.",
        config: `plugins:
  welcome:
    enabled: true
    welcome:
      enabled: true
      channel: 123456789
      message: "Welcome {user.mention} to **{server}**! You are member #{server.member_count}."
      ping: false
      delete_after: null
    goodbye:
      enabled: true
      channel: 123456789
      message: "{user} left the server."
    join_dm:
      enabled: false
      message: "Welcome to {server}!"
    welcome_role:
      enabled: false
      role: null
    account_age_gate:
      enabled: false
      min_age_days: 7
      kick: true`,
        commands: ["!welcome_test"],
      },
      {
        name: "levels",
        label: "Levels (XP)",
        description: "XP-based leveling system with role rewards, leaderboards, and announce channels.",
        config: `plugins:
  levels:
    enabled: true
    xp_per_message: 15
    xp_cooldown: 60
    announce_channel: null
    role_rewards:
      - level: 5
        role: 123456789
      - level: 10
        role: 987654321`,
        commands: ["!rank [@user]", "!leaderboard", "!setxp @user <amount>"],
      },
      {
        name: "starboard",
        label: "Starboard",
        description: "Pin popular messages to a starboard channel when they hit a star threshold.",
        config: `plugins:
  starboard:
    enabled: true
    channel: 123456789
    emoji: "⭐"
    threshold: 5
    self_star: false
    remove_on_unstar: true
    max_age_days: 7
    bots_allowed: false`,
        commands: ["!starboard top [n]", "!starboard stats [@user]", "!starboard clear @user"],
      },
      {
        name: "tags",
        label: "Tags",
        description: "Define custom text commands (tags) in YAML or via bot commands for frequently used responses.",
        config: `# In YAML config:
tags:
  rules: "Please read the rules in #rules!"
  support: "Open a ticket in #support."

# Or via commands:
# !tag create rules Please read the rules!`,
        commands: ["!tag <name>", "!tag list", "!tag create <name> <content>", "!tag edit <name> <content>", "!tag delete <name>"],
      },
    ],
  },
  {
    category: "Tickets",
    plugins: [
      {
        name: "tickets",
        label: "Tickets",
        description: "Full-featured support ticket system with button/dropdown panels, multi-category support, claiming, transcripts, and blacklisting.",
        config: `plugins:
  tickets:
    enabled: true
    log_channel: null
    transcript_channel: null
    dm_transcript: true
    max_open_per_user: 1`,
        commands: ["!ticket panel create <name> <button|dropdown>", "!ticket panel post <name>", "!ticket close [reason]", "!ticket claim", "!ticket adduser @user", "!ticket removeuser @user", "!ticket blacklist [@user] [reason]"],
      },
    ],
  },
  {
    category: "Roles",
    plugins: [
      {
        name: "reaction_roles",
        label: "Reaction Roles",
        description: "Create button or dropdown panels to let users self-assign roles.",
        config: `plugins:
  reaction_roles:
    enabled: true`,
        commands: ["!rr create <name> <button|dropdown>", "!rr add <name> <@role> <emoji_or_label>", "!rr post <name>", "!rr delete <name>", "!rr list"],
      },
      {
        name: "roles",
        label: "Roles",
        description: "Add/remove roles with reason logging, and assign temporary roles that expire after a duration.",
        config: `plugins:
  roles:
    enabled: true
    dm_on_action: true`,
        commands: ["!addrole @user <@role> [reason]", "!removerole @user <@role> [reason]", "!temprole @user <@role> <duration> [reason]", "!temproles [@user]"],
      },
      {
        name: "duration_roles",
        label: "Duration Roles",
        description: "Configure roles that automatically expire. Send DM warnings before expiry.",
        config: `plugins:
  duration_roles:
    enabled: true
    roles:
      - role_id: 123456789
        warn_before_days: 3   # DM warning X days before expiry`,
        commands: ["!giverole @user <@role> <duration>"],
      },
    ],
  },
  {
    category: "Utilities",
    plugins: [
      {
        name: "utility",
        label: "Utility",
        description: "User info, server info, avatar, banner, permissions viewer, role info, and more.",
        config: `plugins:
  utility:
    enabled: true`,
        commands: ["!userinfo [@user]", "!serverinfo", "!avatar [@user]", "!banner [@user]", "!roleinfo <@role>", "!permissions [@user]", "!inrole <@role>", "!modstats [@mod]", "!help [command]"],
      },
      {
        name: "reminders",
        label: "Reminders",
        description: "Set personal reminders. The bot DMs you when the time comes.",
        config: `plugins:
  reminders:
    enabled: true`,
        commands: ["!remind <duration> <message>", "!reminders", "!delreminder <id>"],
      },
      {
        name: "timezones",
        label: "Timezones",
        description: "Users set their timezone once; use !time to see anyone's current time and convert between zones.",
        config: `plugins:
  timezones:
    enabled: true`,
        commands: ["!timezone set <tz>", "!timezone get [@user]", "!time [@user]", "!timefor <zone>", "!timeconvert <time> <from> <to>"],
      },
      {
        name: "logging",
        label: "Logging",
        description: "Comprehensive audit logging split across configurable channels: mod actions, messages, members, voice, server events, automod, antinuke, and antiraid.",
        config: `plugins:
  logging:
    enabled: true
    channels:
      moderation: 123456789   # Mod actions
      messages: 123456790     # Message edits/deletes
      members: 123456791      # Joins, leaves, bans
      voice: null             # Voice events
      server: null            # Channel/role changes
      automod: null           # Automod strikes
      antinuke: null
      antiraid: null`,
        commands: [],
      },
    ],
  },
];

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
        <nav style={{ borderBottom: "1px solid rgba(255,255,255,0.07)", backdropFilter: "blur(20px)", background: "rgba(8,10,24,0.55)" }}>
          <div className="max-w-7xl mx-auto px-5 h-14 flex items-center justify-between">
            <button
              onClick={() => setLocation("/")}
              className="flex items-center gap-2.5 text-white font-bold text-base hover:text-indigo-300 transition-colors"
            >
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "rgba(99,102,241,0.3)", border: "1px solid rgba(129,140,248,0.4)" }}>
                <svg className="w-4 h-4 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.955 11.955 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                </svg>
              </div>
              ZepBot
            </button>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setLocation("/dashboard")}
                className="text-sm px-3 py-1.5 transition-colors"
                style={{ color: "rgba(255,255,255,0.5)" }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.9)")}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.5)")}
              >
                Dashboard
              </button>
              <span className="text-xs px-2 py-1 rounded" style={{ background: "rgba(99,102,241,0.2)", color: "rgba(165,180,252,0.9)", border: "1px solid rgba(99,102,241,0.3)" }}>
                Documentation
              </span>
            </div>
          </div>
        </nav>

        <div className="flex flex-1 max-w-7xl mx-auto w-full px-5 py-5 gap-5">
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
                      className="w-full text-left px-3 py-1.5 text-sm rounded-md transition-all mb-0.5"
                      style={selectedPlugin.name === plugin.name
                        ? { background: "rgba(99,102,241,0.2)", color: "rgba(255,255,255,0.95)", borderLeft: "2px solid rgba(129,140,248,0.7)" }
                        : { color: "rgba(255,255,255,0.5)", paddingLeft: "14px" }}
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

          <div className="flex-1 min-w-0">
            <div className="rounded-xl p-7" style={GLASS}>
              <div className="flex items-start justify-between mb-5">
                <div>
                  <h1 className="text-2xl font-bold text-white">{selectedPlugin.label}</h1>
                  <p className="mt-1.5 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.55)" }}>{selectedPlugin.description}</p>
                </div>
                <span className="text-xs px-2 py-1 rounded shrink-0 ml-4 mt-1" style={{ background: "rgba(99,102,241,0.2)", color: "rgba(165,180,252,0.9)", border: "1px solid rgba(99,102,241,0.25)" }}>
                  Plugin
                </span>
              </div>

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
                    {s}
                  </button>
                ))}
              </div>

              {activeSection === "overview" && (
                <div className="space-y-4">
                  <div className="rounded-lg p-4" style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)" }}>
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-sm font-medium text-indigo-300">Quick Start</span>
                    </div>
                    <p className="text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>
                      Add <code className="px-1.5 py-0.5 rounded text-xs text-indigo-300" style={{ background: "rgba(0,0,0,0.35)" }}>enabled: true</code> under <code className="px-1.5 py-0.5 rounded text-xs text-indigo-300" style={{ background: "rgba(0,0,0,0.35)" }}>plugins: {selectedPlugin.name}:</code> in your server config to activate this plugin with defaults.
                    </p>
                  </div>
                  {selectedPlugin.commands.length > 0 && (
                    <div className="rounded-lg p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                      <h3 className="text-white font-medium text-sm mb-3">Commands ({selectedPlugin.commands.length})</h3>
                      <div className="space-y-1.5">
                        {selectedPlugin.commands.map((cmd) => {
                          const [name, ...rest] = cmd.split(" ");
                          return (
                            <div key={cmd} className="flex items-center gap-2 text-sm font-mono">
                              <span className="text-green-400">{name}</span>
                              <span style={{ color: "rgba(255,255,255,0.4)" }}>{rest.join(" ")}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeSection === "config" && (
                <div>
                  <p className="text-sm mb-3" style={{ color: "rgba(255,255,255,0.45)" }}>
                    {(selectedPlugin as typeof selectedPlugin & { configTitle?: string }).configTitle ?? `Example configuration for ${selectedPlugin.label}`}:
                  </p>
                  <div className="rounded-lg overflow-hidden" style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <div className="flex items-center gap-2 px-4 py-2.5" style={{ background: "rgba(255,255,255,0.04)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: "rgba(239,68,68,0.6)" }} />
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: "rgba(234,179,8,0.6)" }} />
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: "rgba(34,197,94,0.6)" }} />
                      <span className="text-xs ml-1" style={{ color: "rgba(255,255,255,0.25)" }}>config.yaml</span>
                    </div>
                    <pre className="p-4 overflow-x-auto">
                      <code className="text-sm font-mono leading-relaxed" style={{ color: "#86efac" }}>{selectedPlugin.config}</code>
                    </pre>
                  </div>
                  <p className="text-xs mt-3" style={{ color: "rgba(255,255,255,0.25)" }}>
                    Paste this into your server config using <code className="px-1 rounded text-indigo-400" style={{ background: "rgba(0,0,0,0.3)" }}>!setconfig</code> and adjust values as needed.
                  </p>
                </div>
              )}

              {activeSection === "commands" && (
                <div>
                  {selectedPlugin.commands.length === 0 ? (
                    <div className="py-10 text-center rounded-lg" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}>
                      <p className="text-sm" style={{ color: "rgba(255,255,255,0.3)" }}>This plugin has no user-facing commands — it operates automatically.</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {selectedPlugin.commands.map((cmd) => {
                        const parts = cmd.split(" ");
                        return (
                          <div key={cmd} className="flex items-start gap-3 rounded-lg p-3.5" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                            <code className="text-green-400 font-mono text-sm shrink-0">{parts[0]}</code>
                            <code className="font-mono text-sm" style={{ color: "rgba(255,255,255,0.45)" }}>{parts.slice(1).join(" ")}</code>
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
