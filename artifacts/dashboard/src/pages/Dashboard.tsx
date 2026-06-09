import { useState } from "react";
import { useLocation } from "wouter";
import YamlEditor from "@/components/YamlEditor";

const DEFAULT_CONFIG = `# Night Pigeon Server Configuration
# Visit /docs (Wikipedia) for the full plugin reference

prefix: "!"

# ── Permission Levels ──────────────────────────────────────────
# Range: 0–100. Bot owner is always 1000.
# Assign levels to users (by ID) or roles (by ID).
# Each command has a default minimum level you can override.
levels:
  users:
    "YOUR_USER_ID": 100    # Give yourself full access
  roles:
    "STAFF_ROLE_ID": 50    # Staff can use mod commands
    "MOD_ROLE_ID": 75      # Mods get higher access
  commands:
    ban: 50
    kick: 25
    mute: 25
    warn: 15
    massban: 100
    antinuke: 75

# ── Tags ───────────────────────────────────────────────────────
# Quick-reply shortcuts usable with !tag <name>
tags:
  rules: "Please read the rules in #rules!"
  support: "Please open a ticket in #support."

# ── Plugins ────────────────────────────────────────────────────
plugins:

  moderation:
    enabled: true
    mute_role: null              # Role ID for mute (required for mute commands)
    dm_on_action: true           # DM users when they are actioned
    mute_remove_roles: false     # Strip all roles when muting
    ban_delete_message_days: 1   # How many days of messages to purge on ban
    messages:
      ban_success: "{user} has been banned | Case: {case_id}"
      kick_success: "{user} has been kicked | Case: {case_id}"
      mute_success: "{user} has been muted | Duration: {duration} | Case: {case_id}"
      warn_success: "{user} has been warned | Case: {case_id}"
      ban_dm: "You have been banned from {server} | Reason: {reason}"
      kick_dm: "You have been kicked from {server} | Reason: {reason}"
      mute_dm: "You have been muted in {server} | Duration: {duration} | Reason: {reason}"
      warn_dm: "You have been warned in {server} | Reason: {reason}"

  logging:
    enabled: false
    channels:
      moderation: null    # Mod actions (ban, kick, mute, warn)
      messages: null      # Message edits and deletes
      members: null       # Joins, leaves, role changes
      voice: null         # Voice channel events
      server: null        # Channel and role changes
      automod: null       # Automod strikes
      antinuke: null      # Anti-nuke triggers
      antiraid: null      # Anti-raid triggers

  automod:
    enabled: false
    spam:
      enabled: false
      max_messages: 5
      interval_seconds: 5
      action: mute

  welcome:
    enabled: false
    welcome:
      enabled: false
      channel: null
      message: "Welcome {user.mention} to **{server}**! You are member #{server.member_count}."

  escalation:
    enabled: true
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
          duration: "perm"
          reason: "5 warnings — permanent ban"

  preset_reasons:
    config:
      presets:
        spam: "Spamming in chat"
        ads: "Advertising without permission"
        toxic: "Toxic behavior towards members"
        nsfw: "Posting NSFW content outside designated channels"
        raid: "Raiding the server"
        evade: "Ban or mute evasion"

  command_aliases:
    config:
      aliases:
        b: ban
        fb: forceban
        ub: unban
        k: kick
        m: mute
        fm: forcemute
        um: unmute
        w: warn
        fw: forcewarn
        p: purge
        sm: slowmode
`;

interface Guild {
  id: string;
  name: string;
  icon: string | null;
  memberCount?: number;
  online?: number;
  cases?: number;
}

const MOCK_GUILDS: Guild[] = [
  { id: "1", name: "My Server", icon: null, memberCount: 342, online: 89, cases: 14 },
  { id: "2", name: "Dev Community", icon: null, memberCount: 1204, online: 312, cases: 57 },
  { id: "3", name: "Gaming Hub", icon: null, memberCount: 89, online: 23, cases: 3 },
];

function GuildIcon({ guild }: { guild: Guild }) {
  if (guild.icon) {
    return <img src={`https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png`} className="w-10 h-10 rounded-full" alt={guild.name} />;
  }
  const initials = guild.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="w-10 h-10 rounded-full bg-indigo-600/50 border border-indigo-500/40 flex items-center justify-center text-sm font-bold text-indigo-200">
      {initials}
    </div>
  );
}

const GLASS = {
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  backdropFilter: "blur(12px)",
};

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const [selectedGuild, setSelectedGuild] = useState<Guild | null>(null);
  const [yamlValue, setYamlValue] = useState(DEFAULT_CONFIG);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<"editor" | "plugins">("editor");

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 600));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

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
              <div className="w-7 h-7 rounded-lg overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.2)" }}>
                <img src={`${import.meta.env.BASE_URL}pigeon.jpeg`} alt="Night Pigeon" className="w-full h-full object-cover" />
              </div>
              Night Pigeon
            </button>
            <div className="flex items-center gap-2">
              <button onClick={() => setLocation("/docs")} className="text-sm px-3 py-1.5 rounded-md transition-colors" style={{ color: "rgba(255,255,255,0.5)" }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.85)")}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.5)")}>
                Wikipedia
              </button>
              <div className="flex items-center gap-2 text-sm rounded-md px-3 py-1.5 cursor-pointer" style={{ ...GLASS, color: "rgba(255,255,255,0.7)" }}>
                <div className="w-5 h-5 rounded-full bg-indigo-500/50 border border-indigo-400/40 flex items-center justify-center text-xs font-bold text-indigo-200">A</div>
                <span>Admin</span>
              </div>
            </div>
          </div>
        </nav>

        <div className="flex flex-1 max-w-7xl mx-auto w-full px-5 py-5 gap-5">
          <div className="w-60 shrink-0 flex flex-col gap-3">
            <p className="text-xs font-semibold uppercase tracking-widest px-1" style={{ color: "rgba(255,255,255,0.3)" }}>Your Servers</p>
            <div className="flex flex-col gap-1.5">
              {MOCK_GUILDS.map((guild) => (
                <button
                  key={guild.id}
                  onClick={() => { setSelectedGuild(guild); setYamlValue(DEFAULT_CONFIG); }}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-150"
                  style={selectedGuild?.id === guild.id
                    ? { background: "rgba(99,102,241,0.2)", border: "1px solid rgba(129,140,248,0.35)", color: "rgba(255,255,255,0.95)" }
                    : { ...GLASS, color: "rgba(255,255,255,0.65)" }}
                >
                  <GuildIcon guild={guild} />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-sm truncate">{guild.name}</div>
                    <div className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>{guild.memberCount?.toLocaleString()} members</div>
                  </div>
                  {guild.cases ? (
                    <span className="text-xs px-1.5 py-0.5 rounded shrink-0" style={{ background: "rgba(239,68,68,0.2)", color: "rgba(252,165,165,0.9)", border: "1px solid rgba(239,68,68,0.25)" }}>
                      {guild.cases}
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
            <div className="mt-1">
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors" style={{ color: "rgba(255,255,255,0.4)" }}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add Bot to Server
              </button>
            </div>
          </div>

          <div className="flex-1 flex flex-col min-h-0 gap-4">
            {!selectedGuild ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-20 h-20 rounded-2xl overflow-hidden mx-auto mb-4 opacity-40" style={{ border: "1px solid rgba(255,255,255,0.1)" }}>
                    <img src={`${import.meta.env.BASE_URL}pigeon.jpeg`} alt="Night Pigeon" className="w-full h-full object-cover" />
                  </div>
                  <p className="text-sm" style={{ color: "rgba(255,255,255,0.35)" }}>Select a server to manage its configuration</p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col flex-1 min-h-0 gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <GuildIcon guild={selectedGuild} />
                    <div>
                      <h1 className="text-white font-semibold text-base">{selectedGuild.name}</h1>
                      <p className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>
                        {selectedGuild.memberCount?.toLocaleString()} members · {selectedGuild.online} online
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex rounded-lg overflow-hidden text-sm" style={{ ...GLASS }}>
                      {(["editor", "plugins"] as const).map((t) => (
                        <button
                          key={t}
                          onClick={() => setActiveTab(t)}
                          className="px-4 py-1.5 transition-colors capitalize"
                          style={activeTab === t
                            ? { background: "rgba(99,102,241,0.4)", color: "rgba(255,255,255,0.95)" }
                            : { color: "rgba(255,255,255,0.45)" }}
                        >
                          {t === "editor" ? "YAML Editor" : "Plugins"}
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
                      style={saved
                        ? { background: "rgba(34,197,94,0.25)", color: "rgba(134,239,172,0.95)", border: "1px solid rgba(34,197,94,0.3)" }
                        : { background: "rgba(99,102,241,0.4)", color: "rgba(255,255,255,0.95)", border: "1px solid rgba(129,140,248,0.35)" }}
                    >
                      {saving ? "Saving…" : saved ? "✓ Saved" : "Save Config"}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: "Total Cases", value: selectedGuild.cases?.toString() ?? "0", icon: "⚖️", bg: "rgba(239,68,68,0.12)", bd: "rgba(239,68,68,0.2)" },
                    { label: "Members", value: selectedGuild.memberCount?.toLocaleString() ?? "—", icon: "👥", bg: "rgba(59,130,246,0.1)", bd: "rgba(59,130,246,0.2)" },
                    { label: "Online", value: selectedGuild.online?.toString() ?? "—", icon: "🟢", bg: "rgba(34,197,94,0.08)", bd: "rgba(34,197,94,0.2)" },
                  ].map((s) => (
                    <div key={s.label} className="rounded-xl px-4 py-3" style={{ background: s.bg, border: `1px solid ${s.bd}`, backdropFilter: "blur(8px)" }}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm">{s.icon}</span>
                        <span className="text-xs" style={{ color: "rgba(255,255,255,0.45)" }}>{s.label}</span>
                      </div>
                      <div className="text-xl font-bold text-white">{s.value}</div>
                    </div>
                  ))}
                </div>

                {activeTab === "editor" ? (
                  <div className="flex-1 rounded-xl overflow-hidden" style={{ minHeight: 0, height: "calc(100vh - 310px)", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <YamlEditor value={yamlValue} onChange={setYamlValue} />
                  </div>
                ) : (
                  <PluginGrid />
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const PLUGINS = [
  { name: "moderation", label: "Moderation", desc: "Kicks, bans, mutes, warns", icon: "🛡️", enabled: true },
  { name: "automod", label: "AutoMod", desc: "Spam, invite, word filters", icon: "🤖", enabled: false },
  { name: "logging", label: "Logging", desc: "Audit log for all actions", icon: "📋", enabled: false },
  { name: "welcome", label: "Welcome", desc: "Welcome & goodbye messages", icon: "👋", enabled: false },
  { name: "tickets", label: "Tickets", desc: "Support ticket system", icon: "🎫", enabled: true },
  { name: "starboard", label: "Starboard", desc: "Pin popular messages", icon: "✨", enabled: false },
  { name: "antinuke", label: "Anti-Nuke", desc: "Protect from mass actions", icon: "🔒", enabled: false },
  { name: "antiraid", label: "Anti-Raid", desc: "Raid detection & lockdown", icon: "🚨", enabled: false },
  { name: "escalation", label: "Escalation", desc: "Auto-escalate infractions", icon: "📈", enabled: true },
  { name: "reaction_roles", label: "Reaction Roles", desc: "Role assignment panels", icon: "🎭", enabled: false },
  { name: "reminders", label: "Reminders", desc: "Personal reminders via DM", icon: "⏰", enabled: true },
  { name: "tags", label: "Tags", desc: "Custom text commands", icon: "🏷️", enabled: true },
];

function PluginGrid() {
  const [states, setStates] = useState<Record<string, boolean>>(
    Object.fromEntries(PLUGINS.map((p) => [p.name, p.enabled]))
  );

  return (
    <div className="flex-1 overflow-y-auto grid grid-cols-2 xl:grid-cols-3 gap-3 content-start">
      {PLUGINS.map((p) => {
        const on = states[p.name];
        return (
          <div key={p.name} className="rounded-xl p-4 transition-all duration-150" style={on
            ? { background: "rgba(99,102,241,0.12)", border: "1px solid rgba(129,140,248,0.25)", backdropFilter: "blur(8px)" }
            : { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", backdropFilter: "blur(12px)" }}>
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2.5">
                <span className="text-xl mt-0.5">{p.icon}</span>
                <div>
                  <div className="text-white font-medium text-sm">{p.label}</div>
                  <div className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>{p.desc}</div>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-0.5" onClick={() => setStates(s => ({ ...s, [p.name]: !s[p.name] }))}>
                <div className="w-9 h-5 rounded-full transition-colors" style={{ background: on ? "rgb(99,102,241)" : "rgba(255,255,255,0.15)" }}>
                  <div className="absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all" style={{ left: on ? "20px" : "2px" }} />
                </div>
              </label>
            </div>
          </div>
        );
      })}
    </div>
  );
}
