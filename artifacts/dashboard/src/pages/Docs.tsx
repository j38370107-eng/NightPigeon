import { useState } from "react";
import { useLocation } from "wouter";

const PLUGIN_CATEGORIES = [
  {
    category: "Moderation",
    icon: "🛡️",
    plugins: [
      {
        name: "moderation",
        label: "Moderation",
        description: "Core moderation commands: warn, kick, ban, mute, unmute, tempban.",
        config: `plugins:
  moderation:
    enabled: true
    mute_role: 123456789  # Role ID for muted users
    dm_on_action: true    # DM users when actioned
    log_channel: null     # Channel ID for mod logs`,
        commands: ["!warn <user> [reason]", "!kick <user> [reason]", "!ban <user> [duration] [reason]", "!mute <user> [duration] [reason]", "!unmute <user>", "!case <id>", "!history <user>"],
      },
      {
        name: "cases",
        label: "Cases",
        description: "Track all moderation cases per server with persistent case IDs.",
        config: `plugins:
  cases:
    enabled: true`,
        commands: ["!case <id>", "!cases [user]", "!case edit <id> <reason>", "!case delete <id>"],
      },
      {
        name: "modnick",
        label: "ModNick",
        description: "Force-rename users with inappropriate names and lock nicknames.",
        config: `plugins:
  modnick:
    enabled: true
    replacement_name: "Moderated User"`,
        commands: ["!modnick <user> [name]", "!clearnick <user>"],
      },
    ],
  },
  {
    category: "Automation",
    icon: "🤖",
    plugins: [
      {
        name: "automod",
        label: "AutoMod",
        description: "Automatically moderate messages based on configurable rules and triggers.",
        config: `plugins:
  automod:
    enabled: true
    rules:
      - name: no_invites
        triggers:
          - discord_invite
        actions:
          - delete_message
          - warn
        ignore_roles: []
        ignore_channels: []`,
        commands: [],
      },
      {
        name: "autoreply",
        label: "Auto Reply",
        description: "Automatically reply to messages matching patterns or keywords.",
        config: `plugins:
  autoreply:
    enabled: true
    rules:
      - trigger: "hello bot"
        response: "Hello {user}!"
        match_type: contains  # exact | contains | regex`,
        commands: ["!autoreply add <trigger> <response>", "!autoreply list", "!autoreply remove <id>"],
      },
      {
        name: "autoreaction",
        label: "Auto Reaction",
        description: "Automatically add reactions to messages in specified channels.",
        config: `plugins:
  autoreaction:
    enabled: true
    rules:
      - channel: 123456789
        reactions:
          - "👍"
          - "👎"`,
        commands: [],
      },
      {
        name: "autoclean",
        label: "Auto Clean",
        description: "Automatically delete messages in channels after a set duration.",
        config: `plugins:
  autoclean:
    enabled: true
    channels:
      - id: 123456789
        max_age: 3600  # seconds`,
        commands: [],
      },
    ],
  },
  {
    category: "Logging",
    icon: "📋",
    plugins: [
      {
        name: "logging",
        label: "Logging",
        description: "Comprehensive audit logging for mod actions, messages, and member events.",
        config: `plugins:
  logging:
    enabled: true
    channels:
      mod_actions: 123456789
      message_events: 123456790
      member_events: 123456791
      voice_events: null
    ignored_channels: []`,
        commands: [],
      },
      {
        name: "history",
        label: "History",
        description: "Track and display full moderation history for any user.",
        config: `plugins:
  history:
    enabled: true`,
        commands: ["!history <user>", "!history clear <user>"],
      },
    ],
  },
  {
    category: "Anti-Abuse",
    icon: "🔒",
    plugins: [
      {
        name: "antinuke",
        label: "Anti-Nuke",
        description: "Protect your server from mass bans, channel deletions, and role nukes.",
        config: `plugins:
  antinuke:
    enabled: true
    ban_threshold: 3      # actions before trigger
    kick_threshold: 5
    channel_threshold: 2
    role_threshold: 3
    action: ban           # ban | kick | strip_roles`,
        commands: ["!antinuke status", "!antinuke whitelist <user>"],
      },
      {
        name: "antiraid",
        label: "Anti-Raid",
        description: "Detect and handle raid attempts with automated lockdown.",
        config: `plugins:
  antiraid:
    enabled: true
    join_threshold: 10    # joins per interval
    interval: 10          # seconds
    action: kick          # kick | ban | lockdown`,
        commands: ["!antiraid status", "!lockdown", "!unlockdown"],
      },
      {
        name: "escalation",
        label: "Escalation",
        description: "Automatically escalate punishments when users accumulate infractions.",
        config: `plugins:
  escalation:
    enabled: true
    thresholds:
      - count: 3
        action: mute
        duration: 1h
      - count: 5
        action: ban
        duration: 1d`,
        commands: [],
      },
    ],
  },
  {
    category: "Community",
    icon: "✨",
    plugins: [
      {
        name: "levels",
        label: "Levels",
        description: "XP-based leveling system with role rewards and leaderboards.",
        config: `plugins:
  levels:
    enabled: true
    xp_per_message: 15
    xp_cooldown: 60       # seconds between XP gains
    announce_channel: null
    role_rewards:
      - level: 5
        role: 123456789
      - level: 10
        role: 123456790`,
        commands: ["!rank [user]", "!leaderboard", "!setxp <user> <amount>"],
      },
      {
        name: "welcome",
        label: "Welcome",
        description: "Send customizable welcome messages when users join the server.",
        config: `plugins:
  welcome:
    enabled: true
    channel: 123456789
    message: |
      Welcome {user} to **{server}**!
      You are member #{count}.
    dm_message: null
    send_dm: false`,
        commands: [],
      },
      {
        name: "starboard",
        label: "Starboard",
        description: "Pin popular messages to a starboard channel based on reaction count.",
        config: `plugins:
  starboard:
    enabled: true
    channel: 123456789
    threshold: 5
    emoji: "⭐"
    self_star: false`,
        commands: [],
      },
      {
        name: "tags",
        label: "Tags",
        description: "Create custom text commands (tags) for frequently used responses.",
        config: `plugins:
  tags:
    enabled: true`,
        commands: ["!tag <name>", "!tag create <name> <content>", "!tag edit <name> <content>", "!tag delete <name>", "!tags"],
      },
    ],
  },
  {
    category: "Tickets",
    icon: "🎫",
    plugins: [
      {
        name: "tickets",
        label: "Tickets",
        description: "Full-featured support ticket system with categories and transcripts.",
        config: `plugins:
  tickets:
    enabled: true
    category: 123456789   # Category ID for ticket channels
    support_role: null
    log_channel: null
    message: "Thank you for opening a ticket. Support will be with you shortly."`,
        commands: ["!ticket open [reason]", "!ticket close", "!ticket add <user>", "!ticket remove <user>"],
      },
    ],
  },
  {
    category: "Roles",
    icon: "🎭",
    plugins: [
      {
        name: "reaction_roles",
        label: "Reaction Roles",
        description: "Assign roles to users when they react to specific messages.",
        config: `plugins:
  reaction_roles:
    enabled: true`,
        commands: ["!rr add <message_id> <emoji> <role>", "!rr remove <message_id> <emoji>", "!rr list"],
      },
      {
        name: "roles",
        label: "Roles",
        description: "Self-assignable roles and role management utilities.",
        config: `plugins:
  roles:
    enabled: true
    assignable: []        # List of role IDs users can self-assign`,
        commands: ["!iam <role>", "!iamnot <role>", "!roles"],
      },
      {
        name: "duration_roles",
        label: "Duration Roles",
        description: "Temporarily assign roles that expire after a set duration.",
        config: `plugins:
  duration_roles:
    enabled: true`,
        commands: ["!giverole <user> <role> <duration>", "!removerole <user> <role>"],
      },
    ],
  },
  {
    category: "Utilities",
    icon: "🔧",
    plugins: [
      {
        name: "reminders",
        label: "Reminders",
        description: "Set personal reminders that the bot will DM you about.",
        config: `plugins:
  reminders:
    enabled: true`,
        commands: ["!remind me in <duration> <message>", "!reminders", "!delreminder <id>"],
      },
      {
        name: "timezones",
        label: "Timezones",
        description: "Let users set their timezone for time conversion commands.",
        config: `plugins:
  timezones:
    enabled: true`,
        commands: ["!timezone set <tz>", "!time [user]", "!time convert <time> <from_tz> <to_tz>"],
      },
      {
        name: "slowmode_auto",
        label: "Auto Slowmode",
        description: "Automatically adjust channel slowmode based on message rate.",
        config: `plugins:
  slowmode_auto:
    enabled: true
    channels:
      - id: 123456789
        min_slowmode: 0
        max_slowmode: 10`,
        commands: [],
      },
      {
        name: "lockdown",
        label: "Lockdown",
        description: "Lock channels or the entire server during emergencies.",
        config: `plugins:
  lockdown:
    enabled: true`,
        commands: ["!lockdown [channel]", "!lockdown server", "!unlock [channel]", "!unlock server"],
      },
    ],
  },
];

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
      <div className="absolute inset-0 bg-black/65 fixed" />

      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Navbar */}
        <nav className="border-b border-white/10 backdrop-blur-md bg-black/30">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
            <button
              onClick={() => setLocation("/")}
              className="flex items-center gap-2 text-white font-bold text-lg hover:text-indigo-300 transition-colors"
            >
              <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.955 11.955 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
              </svg>
              ZepBot
            </button>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setLocation("/dashboard")}
                className="text-sm text-white/60 hover:text-white transition-colors px-3 py-1.5"
              >
                Dashboard
              </button>
              <span className="text-sm text-indigo-300 border border-indigo-500/40 rounded px-2 py-1 text-xs">Documentation</span>
            </div>
          </div>
        </nav>

        <div className="flex flex-1 max-w-7xl mx-auto w-full px-4 py-6 gap-6">
          {/* Sidebar */}
          <div className="w-56 shrink-0">
            <div className="sticky top-6">
              <h2 className="text-xs font-semibold text-white/40 uppercase tracking-widest px-1 mb-3">Plugins</h2>
              <div className="flex flex-col gap-1">
                {PLUGIN_CATEGORIES.map((cat) => (
                  <div key={cat.category}>
                    <div className="flex items-center gap-1.5 px-2 py-1 text-xs text-white/40 uppercase tracking-wider mt-2 first:mt-0">
                      <span>{cat.icon}</span>
                      <span>{cat.category}</span>
                    </div>
                    {cat.plugins.map((plugin) => (
                      <button
                        key={plugin.name}
                        onClick={() => { setSelectedPlugin(plugin); setActiveSection("overview"); }}
                        className={`w-full text-left px-3 py-1.5 text-sm rounded transition-all ${
                          selectedPlugin.name === plugin.name
                            ? "bg-indigo-600/30 text-white border-l-2 border-indigo-400"
                            : "text-white/60 hover:text-white hover:bg-white/5"
                        }`}
                      >
                        {plugin.label}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="bg-white/5 border border-white/10 rounded-xl p-8 backdrop-blur-sm">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h1 className="text-2xl font-bold text-white">{selectedPlugin.label}</h1>
                  <p className="text-white/60 mt-1">{selectedPlugin.description}</p>
                </div>
                <span className="text-xs bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded px-2 py-1">Plugin</span>
              </div>

              <div className="flex gap-1 mb-6 border-b border-white/10 pb-1">
                {(["overview", "config", "commands"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => setActiveSection(s)}
                    className={`px-4 py-2 text-sm rounded-t transition-colors capitalize ${
                      activeSection === s
                        ? "text-white bg-white/10 border-b-2 border-indigo-400"
                        : "text-white/40 hover:text-white/70"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>

              {activeSection === "overview" && (
                <div className="space-y-4">
                  <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                    <h3 className="text-white font-medium mb-2">About</h3>
                    <p className="text-white/60 text-sm leading-relaxed">{selectedPlugin.description}</p>
                  </div>
                  <div className="bg-indigo-900/20 border border-indigo-500/20 rounded-lg p-4">
                    <h3 className="text-indigo-300 font-medium text-sm mb-2">📝 Quick Start</h3>
                    <p className="text-white/50 text-sm">
                      To enable this plugin, add it to your server config and set <code className="bg-black/30 px-1 rounded text-indigo-300">enabled: true</code>. Then use the YAML editor or the config commands to configure it.
                    </p>
                  </div>
                  {selectedPlugin.commands.length > 0 && (
                    <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                      <h3 className="text-white font-medium mb-3">Commands ({selectedPlugin.commands.length})</h3>
                      <div className="space-y-1">
                        {selectedPlugin.commands.map((cmd) => (
                          <div key={cmd} className="flex items-center gap-2">
                            <code className="bg-black/40 text-green-400 text-sm px-2 py-1 rounded font-mono">{cmd}</code>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeSection === "config" && (
                <div>
                  <p className="text-white/50 text-sm mb-4">Example configuration for <strong className="text-white">{selectedPlugin.label}</strong>:</p>
                  <pre className="bg-black/50 border border-white/10 rounded-lg p-4 overflow-x-auto">
                    <code className="text-green-300 text-sm font-mono leading-relaxed whitespace-pre">{selectedPlugin.config}</code>
                  </pre>
                  <p className="text-white/30 text-xs mt-3">Paste this into your server's YAML config in the Dashboard and adjust values as needed.</p>
                </div>
              )}

              {activeSection === "commands" && (
                <div>
                  {selectedPlugin.commands.length === 0 ? (
                    <div className="text-center py-8 text-white/30">
                      <p>This plugin has no user-facing commands — it works automatically.</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {selectedPlugin.commands.map((cmd) => {
                        const parts = cmd.split(" ");
                        return (
                          <div key={cmd} className="bg-white/5 border border-white/10 rounded-lg p-4">
                            <code className="text-white font-mono font-medium">{parts[0]}</code>
                            <code className="text-white/50 font-mono"> {parts.slice(1).join(" ")}</code>
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
