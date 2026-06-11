"use client";

import { FormEvent, useEffect, useState } from "react";
import { KeyRound, LoaderCircle, MonitorSmartphone, RefreshCcw, UserPlus } from "lucide-react";
import {
  AdminSession,
  AdminUnauthorizedError,
  OperationsSession,
  OperationsUser,
  changePassword,
  createOperationsUser,
  listOperationsSessions,
  listOperationsUsers,
  resetOperationsPassword,
  revokeOperationsSession,
  updateOperationsUser,
} from "@/lib/api";

export type ManagementView = "users" | "sessions" | "security";

type Props = {
  session: AdminSession;
  view: ManagementView;
  onSessionInvalid: (message?: string) => void;
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function OperationsManagement({ session, view, onSessionInvalid }: Props) {
  const [users, setUsers] = useState<OperationsUser[]>([]);
  const [sessions, setSessions] = useState<OperationsSession[]>([]);
  const [username, setUsername] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserRole, setNewUserRole] = useState<"admin" | "support">("support");
  const [resetUserId, setResetUserId] = useState<string | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleError(requestError: unknown, fallback: string) {
    if (requestError instanceof AdminUnauthorizedError) {
      onSessionInvalid(requestError.message);
      return;
    }
    setError(requestError instanceof Error ? requestError.message : fallback);
  }

  async function loadCurrentView() {
    setIsLoading(true);
    setError(null);
    try {
      if (view === "users") setUsers(await listOperationsUsers(session.access_token));
      if (view === "sessions") setSessions(await listOperationsSessions(session.access_token));
    } catch (requestError) {
      handleError(requestError, "数据加载失败");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadCurrentView();
  }, [view, session.access_token]);

  async function handleCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const user = await createOperationsUser(session.access_token, {
        username: username.trim(),
        password: newUserPassword,
        role: newUserRole,
      });
      setUsers((current) => [...current, user]);
      setUsername("");
      setNewUserPassword("");
      setNewUserRole("support");
      setMessage("账号已创建");
    } catch (requestError) {
      handleError(requestError, "账号创建失败");
    }
  }

  async function handleUserUpdate(user: OperationsUser, changes: Partial<Pick<OperationsUser, "role" | "is_active">>) {
    setError(null);
    try {
      const updated = await updateOperationsUser(session.access_token, user.id, {
        role: changes.role ?? user.role,
        is_active: changes.is_active ?? user.is_active,
      });
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (requestError) {
      handleError(requestError, "账号更新失败");
    }
  }

  async function handlePasswordReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!resetUserId) return;
    setError(null);
    try {
      await resetOperationsPassword(session.access_token, resetUserId, resetPassword);
      setResetUserId(null);
      setResetPassword("");
      setMessage("密码已重置，目标账号的会话已撤销");
    } catch (requestError) {
      handleError(requestError, "密码重置失败");
    }
  }

  async function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await changePassword(session.access_token, currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setMessage("密码已修改，其他登录会话已退出");
    } catch (requestError) {
      handleError(requestError, "密码修改失败");
    }
  }

  async function handleSessionRevoke(item: OperationsSession) {
    setError(null);
    try {
      await revokeOperationsSession(session.access_token, item.id);
      if (item.is_current) {
        onSessionInvalid("当前会话已退出");
        return;
      }
      setSessions((current) => current.filter((sessionItem) => sessionItem.id !== item.id));
      setMessage("会话已撤销");
    } catch (requestError) {
      handleError(requestError, "会话撤销失败");
    }
  }

  if (view === "security") {
    return (
      <section className="mx-auto w-full max-w-6xl px-4 py-5">
        <div className="max-w-lg rounded-md border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2"><KeyRound size={18} className="text-pitch" /><h2 className="font-semibold">修改我的密码</h2></div>
          <form onSubmit={handlePasswordChange} className="space-y-3">
            <label className="block text-sm font-medium text-zinc-700" htmlFor="current-password">当前密码</label>
            <input id="current-password" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} className="h-11 w-full rounded-md border border-zinc-200 px-3 text-sm outline-none focus:border-pitch" />
            <label className="block text-sm font-medium text-zinc-700" htmlFor="new-password">新密码</label>
            <input id="new-password" type="password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} className="h-11 w-full rounded-md border border-zinc-200 px-3 text-sm outline-none focus:border-pitch" />
            <button type="submit" disabled={!currentPassword || newPassword.length < 8} className="h-11 rounded-md bg-pitch px-4 text-sm font-medium text-white disabled:bg-zinc-300">修改密码</button>
          </form>
          {message ? <p className="mt-3 text-sm text-pitch">{message}</p> : null}
          {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
        </div>
      </section>
    );
  }

  if (view === "sessions") {
    return (
      <section className="mx-auto w-full max-w-6xl px-4 py-5">
        <div className="overflow-hidden rounded-md border border-zinc-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3"><div className="flex items-center gap-2"><MonitorSmartphone size={18} className="text-pitch" /><h2 className="font-semibold">在线会话</h2></div><button type="button" onClick={loadCurrentView} className="flex h-9 w-9 items-center justify-center rounded-md border border-zinc-200" title="刷新" aria-label="刷新会话"><RefreshCcw size={16} /></button></div>
          {isLoading ? <p className="p-4 text-sm text-zinc-500">正在加载会话</p> : <div className="divide-y divide-zinc-100">{sessions.map((item) => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"><div><p className="text-sm font-medium">{item.username} · {item.role}{item.is_current ? " · 当前会话" : ""}</p><p className="mt-1 text-xs text-zinc-500">登录：{formatTime(item.created_at)} · 过期：{formatTime(item.expires_at)}</p></div><button type="button" onClick={() => handleSessionRevoke(item)} className="rounded-md border border-zinc-200 px-3 py-2 text-sm text-red-700 hover:border-red-300">撤销</button></div>)}</div>}
        </div>
        {message ? <p className="mt-3 text-sm text-pitch">{message}</p> : null}
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      </section>
    );
  }

  return (
    <section className="mx-auto grid w-full max-w-6xl gap-4 px-4 py-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="overflow-hidden rounded-md border border-zinc-200 bg-white shadow-sm">
        <div className="border-b border-zinc-200 px-4 py-3"><h2 className="font-semibold">运营账号</h2></div>
        {isLoading ? <p className="p-4 text-sm text-zinc-500">正在加载账号</p> : <div className="divide-y divide-zinc-100">{users.map((user) => <div key={user.id} className="grid gap-3 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_130px_100px_100px] sm:items-center"><div><p className="text-sm font-medium">{user.username}</p><p className="text-xs text-zinc-500">创建：{formatTime(user.created_at)}</p></div><select value={user.role} onChange={(event) => handleUserUpdate(user, { role: event.target.value as "admin" | "support" })} disabled={user.id === session.operator.id} className="h-9 rounded-md border border-zinc-200 px-2 text-sm"><option value="support">support</option><option value="admin">admin</option></select><button type="button" onClick={() => handleUserUpdate(user, { is_active: !user.is_active })} disabled={user.id === session.operator.id} className="h-9 rounded-md border border-zinc-200 px-2 text-sm disabled:text-zinc-400">{user.is_active ? "停用" : "启用"}</button><button type="button" onClick={() => { setResetUserId(user.id); setResetPassword(""); }} disabled={user.id === session.operator.id} className="h-9 rounded-md border border-zinc-200 px-2 text-sm disabled:text-zinc-400">重置密码</button></div>)}</div>}
      </div>

      <div className="space-y-4">
        <form onSubmit={handleCreateUser} className="rounded-md border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center gap-2"><UserPlus size={18} className="text-pitch" /><h2 className="font-semibold">创建账号</h2></div>
          <div className="space-y-3"><input value={username} onChange={(event) => setUsername(event.target.value)} placeholder="用户名" minLength={3} className="h-10 w-full rounded-md border border-zinc-200 px-3 text-sm" /><input type="password" value={newUserPassword} onChange={(event) => setNewUserPassword(event.target.value)} placeholder="初始密码（至少8位）" minLength={8} className="h-10 w-full rounded-md border border-zinc-200 px-3 text-sm" /><select value={newUserRole} onChange={(event) => setNewUserRole(event.target.value as "admin" | "support")} className="h-10 w-full rounded-md border border-zinc-200 px-3 text-sm"><option value="support">support</option><option value="admin">admin</option></select><button type="submit" disabled={username.trim().length < 3 || newUserPassword.length < 8} className="h-10 w-full rounded-md bg-pitch text-sm font-medium text-white disabled:bg-zinc-300">创建</button></div>
        </form>

        {resetUserId ? <form onSubmit={handlePasswordReset} className="rounded-md border border-zinc-200 bg-white p-4 shadow-sm"><h2 className="mb-3 font-semibold">重置密码</h2><input type="password" value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} placeholder="新密码（至少8位）" minLength={8} className="h-10 w-full rounded-md border border-zinc-200 px-3 text-sm" /><div className="mt-3 flex gap-2"><button type="submit" disabled={resetPassword.length < 8} className="h-10 flex-1 rounded-md bg-pitch text-sm text-white disabled:bg-zinc-300">确认重置</button><button type="button" onClick={() => setResetUserId(null)} className="h-10 rounded-md border border-zinc-200 px-3 text-sm">取消</button></div></form> : null}
        {message ? <p className="text-sm text-pitch">{message}</p> : null}
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
      </div>
    </section>
  );
}
