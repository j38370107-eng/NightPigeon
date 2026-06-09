import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import YamlEditor from "@/components/YamlEditor";

const API = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "") || "/api";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw Object.assign(new Error(err.error ?? res.statusText), { status: res.status });
  }
  return res.json();
}

interface User {
  id: string;
  username: string;
  avatar: string | null;
  discriminator: string;
}

interface Guild {
  id: string;
  name: string;
  icon: string | null;
  hasConfig: boolean;
}

interface Case {
  id: number;
  userId: string;
  moderatorId: string;
  action: string;
  reason: string | null;
  duration: string | null;
  expiresAt: string | null;
  createdAt: string;
}

interface CasesResponse {
  cases: Case[];
  total: number;
  limit: number;
  offset: number;
}

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

const ACTION_STYLES: Record<string, { bg: string; color: string; border: string }> = {
  ban:       { bg: "rgba(239,68,68,0.18)",   color: "rgba(252,165,165,0.95)",  border: "rgba(239,68,68,0.3)" },
  forceban:  { bg: "rgba(239,68,68,0.18)",   color: "rgba(252,165,165,0.95)",  border: "rgba(239,68,68,0.3)" },
  tempban:   { bg: "rgba(239,68,68,0.14)",   color: "rgba(252,165,165,0.85)",  border: "rgba(239,68,68,0.25)" },
  kick:      { bg: "rgba(249,115,22,0.18)",  color: "rgba(253,186,116,0.95)",  border: "rgba(249,115,22,0.3)" },
  mute:      { bg: "rgba(234,179,8,0.15)",   color: "rgba(253,224,71,0.95)",   border: "rgba(234,179,8,0.3)" },
  warn:      { bg: "rgba(99,102,241,0.18)",  color: "rgba(165,180,252,0.95)",  border: "rgba(99,102,241,0.3)" },
  unban:     { bg: "rgba(34,197,94,0.14)",   color: "rgba(134,239,172,0.95)",  border: "rgba(34,197,94,0.25)" },
  unmute:    { bg: "rgba(34,197,94,0.14)",   color: "rgba(134,239,172,0.95)",  border: "rgba(34,197,94,0.25)" },
  note:      { bg: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.55)",  border: "rgba(255,255,255,0.12)" },
  softban:   { bg: "rgba(239,68,68,0.12)",   color: "rgba(252,165,165,0.8)",   border: "rgba(239,68,68,0.2)" },
};

function ActionBadge({ action }: { action: string }) {
  const s = ACTION_STYLES[action] ?? { bg: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.55)", border: "rgba(255,255,255,0.12)" };
  return (
    <span className="text-xs px-2 py-0.5 rounded font-medium" style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}` }}>
      {action}
    </span>
  );
}

function truncateId(id: string) {
  return id.length > 8 ? `…${id.slice(-6)}` : id;
}

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

const PAGE_SIZE = 25;
const ACTION_FILTERS = ["all", "ban", "forceban", "tempban", "kick", "mute", "warn", "unban", "unmute", "softban", "note"];

function CasesView({ guild }: { guild: Guild }) {
  const [actionFilter, setActionFilter] = useState("all");
  const [userIdSearch, setUserIdSearch] = useState("");
  const [page, setPage] = useState(0);

  const offset = page * PAGE_SIZE;

  const { data, isLoading, isError } = useQuery<CasesResponse>({
    queryKey: ["cases", guild.id, actionFilter, userIdSearch, offset],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
        action: actionFilter,
      });
      if (userIdSearch.trim()) params.set("user_id", userIdSearch.trim());
      return apiFetch<CasesResponse>(`/guilds/${guild.id}/cases?${params}`);
    },
    retry: false,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleSearchChange = (val: string) => {
    setUserIdSearch(val);
    setPage(0);
  };

  const handleFilterChange = (val: string) => {
    setActionFilter(val);
    setPage(0);
  };

  return (
    <div className="flex flex-col gap-4 flex-1 min-h-0">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-40">
          <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 pointer-events-none" style={{ color: "rgba(255,255,255,0.3)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
          </svg>
          <input
            type="text"
            placeholder="Filter by user ID…"
            value={userIdSearch}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg text-sm outline-none"
            style={{ ...GLASS, color: "rgba(255,255,255,0.75)", caretColor: "rgba(129,140,248,0.9)" }}
          />
        </div>
        <div className="flex gap-1 flex-wrap">
          {ACTION_FILTERS.map((a) => (
            <button
              key={a}
              onClick={() => handleFilterChange(a)}
              className="px-2.5 py-1 rounded text-xs font-medium transition-colors capitalize"
              style={actionFilter === a
                ? { background: "rgba(99,102,241,0.35)", color: "rgba(165,180,252,0.95)", border: "1px solid rgba(129,140,248,0.4)" }
                : { ...GLASS, color: "rgba(255,255,255,0.4)" }}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.08)", minHeight: 0 }}>
        <div className="h-full overflow-y-auto" style={{ background: "rgba(8,10,24,0.6)" }}>
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-5 h-5 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />
            </div>
          ) : isError ? (
            <div className="flex items-center justify-center py-20">
              <p className="text-sm" style={{ color: "rgba(252,165,165,0.8)" }}>Failed to load cases.</p>
            </div>
          ) : !data || data.cases.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-2">
              <svg className="w-8 h-8" style={{ color: "rgba(255,255,255,0.15)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-sm" style={{ color: "rgba(255,255,255,0.3)" }}>No cases found</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  {["#", "Action", "User", "Moderator", "Reason", "Duration", "Date"].map((h) => (
                    <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold uppercase tracking-wider" style={{ color: "rgba(255,255,255,0.3)" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.cases.map((c, i) => (
                  <tr
                    key={c.id}
                    style={{
                      borderBottom: i < data.cases.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.03)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  >
                    <td className="px-4 py-2.5 font-mono text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
                      {c.id}
                    </td>
                    <td className="px-4 py-2.5">
                      <ActionBadge action={c.action} />
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs" style={{ color: "rgba(165,180,252,0.8)" }} title={c.userId}>
                      {truncateId(c.userId)}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs" style={{ color: "rgba(255,255,255,0.4)" }} title={c.moderatorId}>
                      {truncateId(c.moderatorId)}
                    </td>
                    <td className="px-4 py-2.5 max-w-xs">
                      <span className="truncate block text-xs" style={{ color: "rgba(255,255,255,0.6)" }} title={c.reason ?? ""}>
                        {c.reason ?? <span style={{ color: "rgba(255,255,255,0.2)" }}>—</span>}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
                      {c.duration ?? <span style={{ color: "rgba(255,255,255,0.2)" }}>—</span>}
                    </td>
                    <td className="px-4 py-2.5 text-xs whitespace-nowrap" style={{ color: "rgba(255,255,255,0.35)" }}>
                      {formatDate(c.createdAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {data && totalPages > 1 && (
        <div className="flex items-center justify-between text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
          <span>{data.total.toLocaleString()} cases total</span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2.5 py-1 rounded transition-colors"
              style={page === 0 ? { ...GLASS, color: "rgba(255,255,255,0.2)", cursor: "not-allowed" } : { ...GLASS, color: "rgba(255,255,255,0.6)" }}
            >
              ←
            </button>
            <span style={{ color: "rgba(255,255,255,0.5)" }}>
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-2.5 py-1 rounded transition-colors"
              style={page >= totalPages - 1 ? { ...GLASS, color: "rgba(255,255,255,0.2)", cursor: "not-allowed" } : { ...GLASS, color: "rgba(255,255,255,0.6)" }}
            >
              →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const [selectedGuild, setSelectedGuild] = useState<Guild | null>(null);
  const [yamlValue, setYamlValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"editor" | "cases">("editor");
  const queryClient = useQueryClient();

  const { data: user, isLoading: authLoading, error: authError } = useQuery<User>({
    queryKey: ["me"],
    queryFn: () => apiFetch<User>("/auth/me"),
    retry: false,
  });

  const { data: guilds, isLoading: guildsLoading } = useQuery<Guild[]>({
    queryKey: ["guilds"],
    queryFn: () => apiFetch<Guild[]>("/guilds"),
    enabled: !!user,
    retry: false,
  });

  const { data: configData, isLoading: configLoading } = useQuery<{ yaml: string }>({
    queryKey: ["config", selectedGuild?.id],
    queryFn: () => apiFetch<{ yaml: string }>(`/guilds/${selectedGuild!.id}/config`),
    enabled: !!selectedGuild,
    retry: false,
  });

  useEffect(() => {
    if (configData?.yaml != null) setYamlValue(configData.yaml);
  }, [configData]);

  const handleSave = async () => {
    if (!selectedGuild) return;
    setSaving(true);
    setSaveError(null);
    try {
      await apiFetch(`/guilds/${selectedGuild.id}/config`, {
        method: "PUT",
        body: JSON.stringify({ yaml: yamlValue }),
      });
      queryClient.invalidateQueries({ queryKey: ["config", selectedGuild.id] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err: any) {
      setSaveError(err.message ?? "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => {
    await fetch(`${API}/auth/logout`, { method: "POST", credentials: "include", headers: {} });
    queryClient.clear();
    setLocation("/");
  };

  const selectGuild = (guild: Guild) => {
    setSelectedGuild(guild);
    setYamlValue("");
    setSaveError(null);
    setActiveTab("editor");
  };

  const isAuthError = (authError as any)?.status === 401 || authError != null;

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "rgb(8,10,22)" }}>
        <div className="w-6 h-6 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />
      </div>
    );
  }

  if (isAuthError || !user) {
    return (
      <div
        className="min-h-screen w-full flex flex-col items-center justify-center"
        style={{
          backgroundImage: `url(${import.meta.env.BASE_URL}nightsky.png)`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, rgba(6,8,20,0.75) 0%, rgba(10,12,28,0.82) 100%)" }} />
        <div className="relative z-10 flex flex-col items-center gap-6 text-center px-6">
          <div className="w-16 h-16 rounded-2xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.15)" }}>
            <img src={`${import.meta.env.BASE_URL}pigeon.jpeg`} alt="Night Pigeon" className="w-full h-full object-cover" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Sign in to continue</h1>
            <p className="text-sm mt-1.5" style={{ color: "rgba(255,255,255,0.45)" }}>
              You need to authenticate with Discord to access the dashboard.
            </p>
          </div>
          <a
            href={`${API}/auth/discord`}
            className="flex items-center gap-2.5 px-6 py-2.5 rounded-lg font-semibold text-white text-sm transition-all hover:scale-[1.02] active:scale-[0.98]"
            style={{ background: "rgba(88,101,242,0.9)", border: "1px solid rgba(129,140,248,0.5)", boxShadow: "0 4px 20px rgba(99,102,241,0.3)" }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.002.022.015.043.031.053a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z" />
            </svg>
            Sign in with Discord
          </a>
          <button onClick={() => setLocation("/")} className="text-xs transition-colors" style={{ color: "rgba(255,255,255,0.3)" }}
            onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.6)")}
            onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.3)")}>
            ← Back to home
          </button>
        </div>
      </div>
    );
  }

  const avatarUrl = user.avatar
    ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png?size=64`
    : null;

  const noServers = !guildsLoading && guilds != null && guilds.length === 0;

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
              <div className="flex items-center gap-2 text-sm rounded-md px-3 py-1.5" style={{ ...GLASS, color: "rgba(255,255,255,0.7)" }}>
                {avatarUrl ? (
                  <img src={avatarUrl} className="w-5 h-5 rounded-full" alt={user.username} />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-indigo-500/50 border border-indigo-400/40 flex items-center justify-center text-xs font-bold text-indigo-200">
                    {user.username[0].toUpperCase()}
                  </div>
                )}
                <span>{user.username}</span>
              </div>
              <button
                onClick={handleLogout}
                className="text-sm px-3 py-1.5 rounded-md transition-colors"
                style={{ color: "rgba(255,255,255,0.4)" }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.75)")}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.4)")}
              >
                Sign out
              </button>
            </div>
          </div>
        </nav>

        <div className="flex flex-1 max-w-7xl mx-auto w-full px-5 py-5 gap-5">
          <div className="w-60 shrink-0 flex flex-col gap-3">
            <p className="text-xs font-semibold uppercase tracking-widest px-1" style={{ color: "rgba(255,255,255,0.3)" }}>Your Servers</p>

            {guildsLoading ? (
              <div className="flex flex-col gap-1.5">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 rounded-lg animate-pulse" style={{ background: "rgba(255,255,255,0.04)" }} />
                ))}
              </div>
            ) : noServers ? (
              <div className="rounded-xl px-4 py-5 text-center" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}>
                <div className="text-2xl mb-2">🔒</div>
                <p className="text-sm font-medium" style={{ color: "rgba(252,165,165,0.9)" }}>No access</p>
                <p className="text-xs mt-1.5 leading-relaxed" style={{ color: "rgba(255,255,255,0.35)" }}>
                  You don't have any whitelisted servers. Contact your server admin to get access.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-1.5">
                {(guilds ?? []).map((guild) => (
                  <button
                    key={guild.id}
                    onClick={() => selectGuild(guild)}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-150"
                    style={selectedGuild?.id === guild.id
                      ? { background: "rgba(99,102,241,0.2)", border: "1px solid rgba(129,140,248,0.35)", color: "rgba(255,255,255,0.95)" }
                      : { ...GLASS, color: "rgba(255,255,255,0.65)" }}
                  >
                    <GuildIcon guild={guild} />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-sm truncate">{guild.name}</div>
                      <div className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>
                        {guild.hasConfig ? "Config set" : "No config"}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex-1 flex flex-col min-h-0 gap-4">
            {!selectedGuild ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-20 h-20 rounded-2xl overflow-hidden mx-auto mb-4 opacity-40" style={{ border: "1px solid rgba(255,255,255,0.1)" }}>
                    <img src={`${import.meta.env.BASE_URL}pigeon.jpeg`} alt="Night Pigeon" className="w-full h-full object-cover" />
                  </div>
                  <p className="text-sm" style={{ color: "rgba(255,255,255,0.35)" }}>
                    {noServers ? "No accessible servers" : "Select a server to manage its configuration"}
                  </p>
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
                        {activeTab === "editor" ? "YAML Configuration" : "Moderation Cases"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex rounded-lg overflow-hidden text-sm" style={{ ...GLASS }}>
                      {(["editor", "cases"] as const).map((t) => (
                        <button
                          key={t}
                          onClick={() => setActiveTab(t)}
                          className="px-4 py-1.5 transition-colors"
                          style={activeTab === t
                            ? { background: "rgba(99,102,241,0.4)", color: "rgba(255,255,255,0.95)" }
                            : { color: "rgba(255,255,255,0.45)" }}
                        >
                          {t === "editor" ? "YAML" : "Cases"}
                        </button>
                      ))}
                    </div>
                    {activeTab === "editor" && (
                      <>
                        {saveError && (
                          <span className="text-xs px-2 py-1 rounded" style={{ background: "rgba(239,68,68,0.15)", color: "rgba(252,165,165,0.9)", border: "1px solid rgba(239,68,68,0.25)" }}>
                            {saveError}
                          </span>
                        )}
                        <button
                          onClick={handleSave}
                          disabled={saving || configLoading}
                          className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
                          style={saved
                            ? { background: "rgba(34,197,94,0.25)", color: "rgba(134,239,172,0.95)", border: "1px solid rgba(34,197,94,0.3)" }
                            : { background: "rgba(99,102,241,0.4)", color: "rgba(255,255,255,0.95)", border: "1px solid rgba(129,140,248,0.35)" }}
                        >
                          {saving ? "Saving…" : saved ? "✓ Saved" : "Save Config"}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {activeTab === "editor" ? (
                  <div className="flex-1 rounded-xl overflow-hidden" style={{ minHeight: 0, height: "calc(100vh - 220px)", border: "1px solid rgba(255,255,255,0.08)" }}>
                    {configLoading ? (
                      <div className="h-full flex items-center justify-center" style={{ background: "rgb(19,21,36)" }}>
                        <div className="w-5 h-5 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />
                      </div>
                    ) : (
                      <YamlEditor value={yamlValue} onChange={setYamlValue} />
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col flex-1 min-h-0" style={{ height: "calc(100vh - 220px)" }}>
                    <CasesView guild={selectedGuild} />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
