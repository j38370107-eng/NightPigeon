import { useState } from "react";
import { useLocation } from "wouter";
import YamlEditor from "@/components/YamlEditor";

const DEFAULT_CONFIG = `# ZepBot Server Configuration
# Visit /docs for full plugin documentation

prefix: "!"

plugins:
  moderation:
    enabled: true
    mute_role: null
    dm_on_action: true
    log_channel: null

  automod:
    enabled: false
    rules:
      - name: no_invites
        triggers:
          - discord_invite
        actions:
          - delete_message
          - warn

  welcome:
    enabled: false
    channel: null
    message: "Welcome {user} to {server}!"

  levels:
    enabled: false
    xp_per_message: 15
    xp_cooldown: 60
    announce_channel: null

  logging:
    enabled: false
    channels:
      mod_actions: null
      message_events: null
      member_events: null
`;

interface Guild {
  id: string;
  name: string;
  icon: string | null;
  memberCount?: number;
}

const MOCK_GUILDS: Guild[] = [
  { id: "1", name: "My Server", icon: null, memberCount: 342 },
  { id: "2", name: "Dev Community", icon: null, memberCount: 1204 },
  { id: "3", name: "Gaming Hub", icon: null, memberCount: 89 },
];

function GuildIcon({ guild }: { guild: Guild }) {
  if (guild.icon) {
    return (
      <img
        src={`https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png`}
        className="w-10 h-10 rounded-full"
        alt={guild.name}
      />
    );
  }
  const initials = guild.name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <div className="w-10 h-10 rounded-full bg-indigo-600/50 border border-indigo-500/40 flex items-center justify-center text-sm font-bold text-indigo-200">
      {initials}
    </div>
  );
}

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const [selectedGuild, setSelectedGuild] = useState<Guild | null>(null);
  const [yamlValue, setYamlValue] = useState(DEFAULT_CONFIG);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<"editor" | "settings">("editor");

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 600));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
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
      <div className="absolute inset-0 bg-black/60 fixed" />

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
                onClick={() => setLocation("/docs")}
                className="text-sm text-white/60 hover:text-white transition-colors px-3 py-1.5"
              >
                Docs
              </button>
              <button className="flex items-center gap-2 text-sm text-white/80 hover:text-white transition-colors border border-white/20 rounded-md px-3 py-1.5 bg-white/5">
                <div className="w-5 h-5 rounded-full bg-indigo-500/40 border border-indigo-400/50 flex items-center justify-center text-xs">A</div>
                Admin
              </button>
            </div>
          </div>
        </nav>

        <div className="flex flex-1 max-w-7xl mx-auto w-full px-4 py-6 gap-6">
          {/* Sidebar */}
          <div className="w-64 shrink-0 flex flex-col gap-3">
            <h2 className="text-xs font-semibold text-white/40 uppercase tracking-widest px-1">Your Servers</h2>
            <div className="flex flex-col gap-2">
              {MOCK_GUILDS.map((guild) => (
                <button
                  key={guild.id}
                  onClick={() => { setSelectedGuild(guild); setYamlValue(DEFAULT_CONFIG); }}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-left transition-all duration-150 ${
                    selectedGuild?.id === guild.id
                      ? "bg-indigo-600/30 border border-indigo-500/50 text-white"
                      : "bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  <GuildIcon guild={guild} />
                  <div className="min-w-0">
                    <div className="font-medium text-sm truncate">{guild.name}</div>
                    <div className="text-xs text-white/40">{guild.memberCount?.toLocaleString()} members</div>
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-auto pt-4 border-t border-white/10">
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-white/50 hover:text-white/80 transition-colors rounded-md hover:bg-white/5">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add Bot to Server
              </button>
            </div>
          </div>

          {/* Main content */}
          <div className="flex-1 flex flex-col min-h-0">
            {!selectedGuild ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </div>
                  <p className="text-white/40 text-sm">Select a server to edit its configuration</p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col flex-1 min-h-0 gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <GuildIcon guild={selectedGuild} />
                    <div>
                      <h1 className="text-white font-semibold">{selectedGuild.name}</h1>
                      <p className="text-xs text-white/40">Configuration Editor</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex bg-white/5 border border-white/10 rounded-md overflow-hidden text-sm">
                      <button
                        onClick={() => setActiveTab("editor")}
                        className={`px-4 py-1.5 transition-colors ${activeTab === "editor" ? "bg-indigo-600/50 text-white" : "text-white/50 hover:text-white"}`}
                      >
                        YAML Editor
                      </button>
                      <button
                        onClick={() => setActiveTab("settings")}
                        className={`px-4 py-1.5 transition-colors ${activeTab === "settings" ? "bg-indigo-600/50 text-white" : "text-white/50 hover:text-white"}`}
                      >
                        Quick Settings
                      </button>
                    </div>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                        saved
                          ? "bg-green-600/70 text-white border border-green-500/50"
                          : "bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500/50"
                      }`}
                    >
                      {saving ? "Saving..." : saved ? "✓ Saved" : "Save Config"}
                    </button>
                  </div>
                </div>

                {activeTab === "editor" ? (
                  <div
                    className="flex-1 rounded-lg overflow-hidden border border-white/10"
                    style={{ minHeight: 0, height: "calc(100vh - 220px)" }}
                  >
                    <YamlEditor value={yamlValue} onChange={setYamlValue} />
                  </div>
                ) : (
                  <QuickSettings yamlValue={yamlValue} onYamlChange={setYamlValue} />
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function QuickSettings({ yamlValue, onYamlChange }: { yamlValue: string; onYamlChange: (v: string) => void }) {
  return (
    <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-4 content-start">
      {[
        { name: "moderation", label: "Moderation", desc: "Kicks, bans, mutes, warns", icon: "🛡️" },
        { name: "automod", label: "AutoMod", desc: "Spam, invite, word filters", icon: "🤖" },
        { name: "logging", label: "Logging", desc: "Audit log for all actions", icon: "📋" },
        { name: "welcome", label: "Welcome", desc: "Welcome messages & DMs", icon: "👋" },
        { name: "levels", label: "Levels", desc: "XP and rank system", icon: "⭐" },
        { name: "tickets", label: "Tickets", desc: "Support ticket system", icon: "🎫" },
        { name: "starboard", label: "Starboard", desc: "Pin popular messages", icon: "⭐" },
        { name: "antinuke", label: "Anti-Nuke", desc: "Protect from mass actions", icon: "🔒" },
      ].map((plugin) => (
        <div key={plugin.name} className="bg-white/5 border border-white/10 rounded-lg p-4 hover:bg-white/8 transition-colors">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl">{plugin.icon}</span>
              <div>
                <div className="text-white font-medium text-sm">{plugin.label}</div>
                <div className="text-white/40 text-xs">{plugin.desc}</div>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer mt-0.5">
              <input type="checkbox" className="sr-only peer" defaultChecked={plugin.name === "moderation"} />
              <div className="w-9 h-5 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-4 after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600" />
            </label>
          </div>
        </div>
      ))}
    </div>
  );
}
