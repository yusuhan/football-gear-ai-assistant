export type ChatResponse = {
  conversation_id: string | null;
  answer: string;
  intent: string;
  confidence: number;
  route: string;
  needs_handoff: boolean;
  handoff: {
    ticket_id: string;
    reason: string;
    status: string;
  } | null;
  tool_calls: Array<{
    name: string;
    arguments: Record<string, unknown>;
    result: Record<string, unknown>;
  }>;
  sources: Array<{
    article_id: string;
    question: string;
    score: number;
  }>;
};

export type HandoffStatus = "open" | "in_progress" | "resolved";

export type HandoffTicket = {
  id: string;
  conversation_id: string;
  reason: string;
  status: HandoffStatus;
  assigned_to: string | null;
  resolution_note: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MessageRecord = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | string;
  content: string;
  intent: string | null;
  route: string | null;
  confidence: number | null;
  created_at: string;
};

export type Operator = {
  id: string;
  username: string;
  role: "admin" | "support";
};

export type AdminSession = {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  operator: Operator;
};

export type AuditLog = {
  id: string;
  actor_username: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

export type OperationsUser = {
  id: string;
  username: string;
  role: "admin" | "support";
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type OperationsSession = {
  id: string;
  user_id: string;
  username: string;
  role: "admin" | "support";
  expires_at: string;
  created_at: string;
  is_current: boolean;
};

export const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class AdminUnauthorizedError extends Error {}

function adminHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

async function requireOk(response: Response, message: string) {
  if (response.status === 401) {
    throw new AdminUnauthorizedError("后台访问令牌无效或已失效");
  }
  if (!response.ok) {
    throw new Error(`${message}: ${response.status}`);
  }
}

export async function sendChat(message: string, conversationId?: string | null): Promise<ChatResponse> {
  const response = await fetch(`${apiBaseUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`);
  }

  return response.json();
}

export async function streamChat(
  message: string,
  conversationId: string | null,
  onChunk: (chunk: string) => void,
): Promise<string | null> {
  const response = await fetch(`${apiBaseUrl}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Stream request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    onChunk(decoder.decode(value, { stream: true }));
  }
  return response.headers.get("X-Conversation-Id");
}

export async function authenticateAdmin(username: string, password: string): Promise<AdminSession> {
  const response = await fetch(`${apiBaseUrl}/admin/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  await requireOk(response, "Admin login failed");
  return response.json();
}

export async function logoutAdmin(token: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/admin/auth/logout`, {
    method: "POST",
    headers: adminHeaders(token),
  });
  await requireOk(response, "Admin logout failed");
}

export async function listAuditLogs(token: string): Promise<AuditLog[]> {
  const response = await fetch(`${apiBaseUrl}/admin/audit-logs`, { headers: adminHeaders(token) });
  await requireOk(response, "Audit log request failed");
  return response.json();
}

export async function changePassword(token: string, currentPassword: string, newPassword: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/admin/auth/change-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...adminHeaders(token) },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  await requireOk(response, "Password change failed");
}

export async function listOperationsUsers(token: string): Promise<OperationsUser[]> {
  const response = await fetch(`${apiBaseUrl}/admin/users`, { headers: adminHeaders(token) });
  await requireOk(response, "Operations users request failed");
  return response.json();
}

export async function createOperationsUser(
  token: string,
  payload: { username: string; password: string; role: "admin" | "support" },
): Promise<OperationsUser> {
  const response = await fetch(`${apiBaseUrl}/admin/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...adminHeaders(token) },
    body: JSON.stringify(payload),
  });
  await requireOk(response, "Operations user creation failed");
  return response.json();
}

export async function updateOperationsUser(
  token: string,
  userId: string,
  payload: { role: "admin" | "support"; is_active: boolean },
): Promise<OperationsUser> {
  const response = await fetch(`${apiBaseUrl}/admin/users/${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...adminHeaders(token) },
    body: JSON.stringify(payload),
  });
  await requireOk(response, "Operations user update failed");
  return response.json();
}

export async function resetOperationsPassword(token: string, userId: string, newPassword: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/admin/users/${userId}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...adminHeaders(token) },
    body: JSON.stringify({ new_password: newPassword }),
  });
  await requireOk(response, "Password reset failed");
}

export async function listOperationsSessions(token: string): Promise<OperationsSession[]> {
  const response = await fetch(`${apiBaseUrl}/admin/sessions`, { headers: adminHeaders(token) });
  await requireOk(response, "Operations sessions request failed");
  return response.json();
}

export async function revokeOperationsSession(token: string, sessionId: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/admin/sessions/${sessionId}`, {
    method: "DELETE",
    headers: adminHeaders(token),
  });
  await requireOk(response, "Operations session revoke failed");
}

export async function listHandoffTickets(token: string, status?: HandoffStatus | "all"): Promise<HandoffTicket[]> {
  const query = status && status !== "all" ? `?status=${status}` : "?status=";
  const response = await fetch(`${apiBaseUrl}/handoff-tickets${query}`, { headers: adminHeaders(token) });
  await requireOk(response, "Handoff ticket request failed");

  return response.json();
}

export async function listConversationMessages(token: string, conversationId: string): Promise<MessageRecord[]> {
  const response = await fetch(`${apiBaseUrl}/conversations/${conversationId}/messages`, {
    headers: adminHeaders(token),
  });
  await requireOk(response, "Conversation messages request failed");

  return response.json();
}

export async function updateHandoffTicket(
  token: string,
  ticketId: string,
  payload: {
    status: HandoffStatus;
    assigned_to?: string;
    resolution_note?: string;
  },
): Promise<HandoffTicket> {
  const response = await fetch(`${apiBaseUrl}/handoff-tickets/${ticketId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...adminHeaders(token) },
    body: JSON.stringify(payload),
  });

  await requireOk(response, "Handoff ticket update failed");

  return response.json();
}
