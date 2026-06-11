"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Clock,
  FileText,
  Inbox,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  MonitorSmartphone,
  RefreshCcw,
  Tickets,
  UserCog,
} from "lucide-react";
import { ManagementView, OperationsManagement } from "@/components/operations-management";
import {
  AdminSession,
  AdminUnauthorizedError,
  AuditLog,
  HandoffStatus,
  HandoffTicket,
  MessageRecord,
  authenticateAdmin,
  listAuditLogs,
  listConversationMessages,
  listHandoffTickets,
  logoutAdmin,
  updateHandoffTicket,
} from "@/lib/api";

type StatusFilter = HandoffStatus | "all";
type AdminView = "tickets" | "audit" | ManagementView;

const sessionStorageKey = "football-gear-admin-session";
const statusFilters: Array<{ value: StatusFilter; label: string }> = [
  { value: "open", label: "待处理" },
  { value: "in_progress", label: "处理中" },
  { value: "resolved", label: "已解决" },
  { value: "all", label: "全部" },
];
const statusLabels: Record<HandoffStatus, string> = {
  open: "待处理",
  in_progress: "处理中",
  resolved: "已解决",
};
const actionLabels: Record<string, string> = {
  "operations.login": "登录后台",
  "operations.logout": "退出后台",
  "handoff.update": "更新工单",
  "operations.password_changed": "修改密码",
  "operations.password_reset": "重置密码",
  "operations.session_revoked": "撤销会话",
  "operations.user_created": "创建账号",
  "operations.user_updated": "更新账号",
};

function formatTime(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function readStoredSession(): AdminSession | null {
  const rawSession = sessionStorage.getItem(sessionStorageKey);
  if (!rawSession) return null;
  try {
    const session = JSON.parse(rawSession) as AdminSession;
    if (new Date(session.expires_at) <= new Date()) {
      sessionStorage.removeItem(sessionStorageKey);
      return null;
    }
    return session;
  } catch {
    sessionStorage.removeItem(sessionStorageKey);
    return null;
  }
}

export function HandoffDashboard() {
  const [session, setSession] = useState<AdminSession | null>(null);
  const [isAuthReady, setIsAuthReady] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [view, setView] = useState<AdminView>("tickets");
  const [status, setStatus] = useState<StatusFilter>("open");
  const [tickets, setTickets] = useState<HandoffTicket[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageRecord[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [resolutionNote, setResolutionNote] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedTicket = useMemo(
    () => tickets.find((ticket) => ticket.id === selectedTicketId) ?? null,
    [selectedTicketId, tickets],
  );

  function clearSession(message?: string) {
    sessionStorage.removeItem(sessionStorageKey);
    setSession(null);
    setTickets([]);
    setMessages([]);
    setAuditLogs([]);
    setSelectedTicketId(null);
    setError(message ?? null);
  }

  function handleRequestError(requestError: unknown, fallbackMessage: string) {
    if (requestError instanceof AdminUnauthorizedError) {
      clearSession(requestError.message);
      return;
    }
    setError(requestError instanceof Error ? requestError.message : fallbackMessage);
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim() || !password || isAuthenticating) return;

    setIsAuthenticating(true);
    setError(null);
    try {
      const nextSession = await authenticateAdmin(username.trim(), password);
      sessionStorage.setItem(sessionStorageKey, JSON.stringify(nextSession));
      setSession(nextSession);
      setPassword("");
    } catch (requestError) {
      handleRequestError(requestError, "后台登录失败");
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function handleLogout() {
    if (!session) return;
    try {
      await logoutAdmin(session.access_token);
    } catch (requestError) {
      if (!(requestError instanceof AdminUnauthorizedError)) {
        setError("退出请求失败，本地会话已清除");
      }
    } finally {
      clearSession();
    }
  }

  async function loadTickets(nextStatus = status) {
    if (!session) return;
    setIsLoading(true);
    setError(null);
    try {
      const nextTickets = await listHandoffTickets(session.access_token, nextStatus);
      setTickets(nextTickets);
      setSelectedTicketId((currentId) =>
        currentId && nextTickets.some((ticket) => ticket.id === currentId)
          ? currentId
          : nextTickets[0]?.id ?? null,
      );
    } catch (requestError) {
      handleRequestError(requestError, "工单加载失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function loadMessages(ticket: HandoffTicket | null) {
    if (!ticket || !session) {
      setMessages([]);
      return;
    }
    try {
      setMessages(await listConversationMessages(session.access_token, ticket.conversation_id));
      setResolutionNote(ticket.resolution_note ?? "");
    } catch (requestError) {
      handleRequestError(requestError, "会话记录加载失败");
    }
  }

  async function loadAuditLogs() {
    if (!session || session.operator.role !== "admin") return;
    setIsLoading(true);
    setError(null);
    try {
      setAuditLogs(await listAuditLogs(session.access_token));
    } catch (requestError) {
      handleRequestError(requestError, "审计日志加载失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function changeTicketStatus(nextStatus: HandoffStatus) {
    if (!selectedTicket || !session) return;
    setIsUpdating(true);
    setError(null);
    try {
      const updatedTicket = await updateHandoffTicket(session.access_token, selectedTicket.id, {
        status: nextStatus,
        resolution_note: nextStatus === "resolved" ? resolutionNote : selectedTicket.resolution_note ?? undefined,
      });
      setTickets((current) => current.map((ticket) => (ticket.id === updatedTicket.id ? updatedTicket : ticket)));
      setResolutionNote(updatedTicket.resolution_note ?? "");
    } catch (requestError) {
      handleRequestError(requestError, "工单更新失败");
    } finally {
      setIsUpdating(false);
    }
  }

  useEffect(() => {
    setSession(readStoredSession());
    setIsAuthReady(true);
  }, []);

  useEffect(() => {
    if (session && view === "tickets") loadTickets(status);
    if (session && view === "audit") loadAuditLogs();
  }, [session, status, view]);

  useEffect(() => {
    if (view === "tickets") loadMessages(selectedTicket);
  }, [session, view, selectedTicket?.id]);

  if (!isAuthReady) return <main className="min-h-screen bg-[#f6f8f5]" />;

  if (!session) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f6f8f5] px-4">
        <section className="w-full max-w-sm rounded-md border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-md bg-pitch text-white">
            <LockKeyhole size={19} aria-hidden="true" />
          </div>
          <h1 className="text-lg font-semibold text-zinc-950">运营后台登录</h1>
          <p className="mt-1 text-sm leading-6 text-zinc-500">使用运营账号登录后处理人工接管工单。</p>
          <form onSubmit={handleLogin} className="mt-5 space-y-3">
            <label className="block text-sm font-medium text-zinc-700" htmlFor="username">用户名</label>
            <input
              id="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              className="h-11 w-full rounded-md border border-zinc-200 px-3 text-sm outline-none focus:border-pitch"
            />
            <label className="block text-sm font-medium text-zinc-700" htmlFor="password">密码</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              className="h-11 w-full rounded-md border border-zinc-200 px-3 text-sm outline-none focus:border-pitch"
            />
            <button
              type="submit"
              disabled={!username.trim() || !password || isAuthenticating}
              className="h-11 w-full rounded-md bg-pitch text-sm font-medium text-white hover:bg-[#125438] disabled:bg-zinc-300"
            >
              {isAuthenticating ? "正在登录" : "登录"}
            </button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
          <a className="mt-5 inline-block text-sm text-zinc-500 hover:text-pitch" href="/">返回聊天</a>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f6f8f5]">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div>
            <h1 className="text-lg font-semibold text-zinc-950">运营工作台</h1>
            <p className="text-sm text-zinc-500">{session.operator.username} · {session.operator.role}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setView("tickets")}
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm ${view === "tickets" ? "bg-pitch text-white" : "border border-zinc-200 text-zinc-700"}`}
            >
              <Tickets size={16} aria-hidden="true" />工单
            </button>
            {session.operator.role === "admin" ? (
              <>
                <button
                  type="button"
                  onClick={() => setView("users")}
                  className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm ${view === "users" ? "bg-pitch text-white" : "border border-zinc-200 text-zinc-700"}`}
                >
                  <UserCog size={16} aria-hidden="true" />账号
                </button>
                <button
                  type="button"
                  onClick={() => setView("audit")}
                  className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm ${view === "audit" ? "bg-pitch text-white" : "border border-zinc-200 text-zinc-700"}`}
                >
                  <FileText size={16} aria-hidden="true" />审计
                </button>
              </>
            ) : null}
            <button type="button" onClick={() => setView("sessions")} className={`flex h-10 w-10 items-center justify-center rounded-md border ${view === "sessions" ? "border-pitch text-pitch" : "border-zinc-200 text-zinc-700"}`} aria-label="在线会话" title="在线会话"><MonitorSmartphone size={17} /></button>
            <button type="button" onClick={() => setView("security")} className={`flex h-10 w-10 items-center justify-center rounded-md border ${view === "security" ? "border-pitch text-pitch" : "border-zinc-200 text-zinc-700"}`} aria-label="修改密码" title="修改密码"><KeyRound size={17} /></button>
            {view === "tickets" || view === "audit" ? <button
              type="button"
              onClick={() => (view === "tickets" ? loadTickets(status) : loadAuditLogs())}
              className="flex h-10 w-10 items-center justify-center rounded-md border border-zinc-200 text-zinc-700"
              aria-label="刷新" title="刷新"
            ><RefreshCcw size={17} aria-hidden="true" /></button> : null}
            <button
              type="button"
              onClick={handleLogout}
              className="flex h-10 w-10 items-center justify-center rounded-md border border-zinc-200 text-zinc-700 hover:text-red-700"
              aria-label="退出后台" title="退出后台"
            ><LogOut size={17} aria-hidden="true" /></button>
          </div>
        </div>
      </header>

      {view === "users" || view === "sessions" || view === "security" ? (
        <OperationsManagement session={session} view={view} onSessionInvalid={clearSession} />
      ) : view === "audit" ? (
        <section className="mx-auto w-full max-w-6xl px-4 py-5">
          <div className="overflow-hidden rounded-md border border-zinc-200 bg-white shadow-sm">
            <div className="border-b border-zinc-200 px-4 py-3"><h2 className="font-semibold text-zinc-950">最近操作</h2></div>
            {isLoading ? <p className="p-4 text-sm text-zinc-500">正在加载审计日志</p> : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="bg-zinc-50 text-zinc-500"><tr><th className="px-4 py-3">时间</th><th className="px-4 py-3">账号</th><th className="px-4 py-3">角色</th><th className="px-4 py-3">操作</th><th className="px-4 py-3">资源</th><th className="px-4 py-3">详情</th></tr></thead>
                  <tbody className="divide-y divide-zinc-100">
                    {auditLogs.map((log) => <tr key={log.id}><td className="whitespace-nowrap px-4 py-3 text-zinc-500">{formatTime(log.created_at)}</td><td className="px-4 py-3 font-medium">{log.actor_username}</td><td className="px-4 py-3">{log.actor_role}</td><td className="px-4 py-3">{actionLabels[log.action] ?? log.action}</td><td className="px-4 py-3 text-zinc-500">{log.resource_id ?? log.resource_type}</td><td className="max-w-[320px] truncate px-4 py-3 text-zinc-500">{JSON.stringify(log.details)}</td></tr>)}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
        </section>
      ) : (
        <section className="mx-auto grid w-full max-w-6xl gap-4 px-4 py-5 lg:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="rounded-md border border-zinc-200 bg-white shadow-sm">
            <div className="grid grid-cols-4 gap-2 border-b border-zinc-200 p-3">
              {statusFilters.map((filter) => <button key={filter.value} type="button" onClick={() => setStatus(filter.value)} className={`rounded-md px-2 py-2 text-sm ${status === filter.value ? "bg-pitch text-white" : "bg-zinc-50 text-zinc-700"}`}>{filter.label}</button>)}
            </div>
            <div className="max-h-[calc(100vh-174px)] overflow-y-auto p-3">
              {isLoading ? <p className="flex items-center gap-2 p-3 text-sm text-zinc-500"><LoaderCircle size={16} className="animate-spin" />正在加载工单</p> : tickets.length === 0 ? <p className="flex items-center gap-2 p-3 text-sm text-zinc-500"><Inbox size={16} />当前没有工单</p> : <div className="space-y-2">{tickets.map((ticket) => <button key={ticket.id} type="button" onClick={() => setSelectedTicketId(ticket.id)} className={`w-full rounded-md border p-3 text-left ${ticket.id === selectedTicketId ? "border-pitch bg-[#eef7f0]" : "border-zinc-200"}`}><div className="mb-2 flex justify-between gap-2"><span className="truncate text-sm font-medium">{ticket.reason}</span><span className="shrink-0 text-xs text-zinc-500">{statusLabels[ticket.status]}</span></div><p className="truncate text-xs text-zinc-500">会话：{ticket.conversation_id}</p><p className="mt-1 text-xs text-zinc-400">{formatTime(ticket.created_at)}</p></button>)}</div>}
            </div>
          </aside>

          <section className="rounded-md border border-zinc-200 bg-white shadow-sm">
            {selectedTicket ? <><div className="border-b border-zinc-200 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="mb-2 flex items-center gap-2">{selectedTicket.status === "resolved" ? <CheckCircle2 size={18} className="text-pitch" /> : <Clock size={18} className="text-amber-600" />}<h2 className="font-semibold">{selectedTicket.reason}</h2></div><p className="text-sm text-zinc-500">会话 ID：{selectedTicket.conversation_id}</p><p className="mt-1 text-sm text-zinc-500">处理人：{selectedTicket.assigned_to ?? "未分配"} · 更新时间：{formatTime(selectedTicket.updated_at)}</p></div>{selectedTicket.status === "open" ? <button type="button" onClick={() => changeTicketStatus("in_progress")} disabled={isUpdating} className="rounded-md bg-pitch px-3 py-2 text-sm text-white disabled:bg-zinc-300">标记处理中</button> : null}</div></div>
              <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_320px]"><div className="min-h-[420px] space-y-3 rounded-md border border-zinc-200 bg-zinc-50 p-4">{messages.map((message) => <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}><div className={`max-w-[82%] whitespace-pre-wrap rounded-md px-3 py-2 text-sm leading-6 ${message.role === "user" ? "bg-pitch text-white" : "border border-zinc-200 bg-white"}`}><div className="mb-1 text-xs opacity-70">{message.role === "user" ? "客户" : "AI"} · {formatTime(message.created_at)}</div>{message.content}</div></div>)}</div><div className="space-y-3"><div className="rounded-md border border-zinc-200 p-3"><h3 className="mb-2 text-sm font-semibold">处理备注</h3><textarea value={resolutionNote} onChange={(event) => setResolutionNote(event.target.value)} placeholder="记录人工客服处理结果" rows={8} className="w-full resize-none rounded-md border border-zinc-200 p-3 text-sm outline-none focus:border-pitch" /></div><button type="button" onClick={() => changeTicketStatus("resolved")} disabled={isUpdating || selectedTicket.status === "resolved"} className="w-full rounded-md bg-pitch px-3 py-3 text-sm font-medium text-white disabled:bg-zinc-300">{selectedTicket.status === "resolved" ? "已解决" : "标记已解决"}</button></div></div></> : <div className="flex min-h-[520px] items-center justify-center text-sm text-zinc-500">请选择一个工单</div>}
            {error ? <div className="border-t border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
          </section>
        </section>
      )}
    </main>
  );
}
