"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
import { Send, ShieldCheck, Sparkles } from "lucide-react";
import { sendChat, streamChat } from "@/lib/api";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

const examples = ["推荐护腿板", "Mercurial 16 Elite有43码吗", "多久发货", "你是谁"];

export function ChatShell() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "你好，我是接入商家工作流的足球装备智能客服。可以帮你推荐装备、查库存尺码、回答售后政策，并在订单异常或投诉退款时转接人工。",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const canSend = input.trim().length > 0 && !isLoading;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = input.trim();
    if (!message || isLoading) {
      return;
    }

    setInput("");
    setIsLoading(true);
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: message },
      { id: assistantId, role: "assistant", content: "" },
    ]);

    try {
      const nextConversationId = await streamChat(message, conversationId, (chunk) => {
        setMessages((current) =>
          current.map((item) => (item.id === assistantId ? { ...item, content: item.content + chunk } : item)),
        );
      });
      setConversationId(nextConversationId ?? conversationId);
    } catch {
      const response = await sendChat(message, conversationId);
      setConversationId(response.conversation_id);
      setMessages((current) =>
        current.map((item) => (item.id === assistantId ? { ...item, content: response.answer } : item)),
      );
    } finally {
      setIsLoading(false);
    }
  }

  function useExample(example: string) {
    setInput(example);
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <main className="flex min-h-screen flex-col bg-[#f6f8f5]">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-pitch text-white">
              <Sparkles size={20} aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-zinc-950">Football Gear AI Assistant</h1>
              <p className="text-sm text-zinc-500">嵌入商家工作流的智能客服</p>
            </div>
          </div>
          <div className="hidden items-center gap-3 text-sm text-zinc-600 sm:flex">
            <a className="rounded-md border border-zinc-200 px-3 py-2 hover:border-pitch hover:text-pitch" href="/admin/handoffs">
              工单后台
            </a>
            <div className="flex items-center gap-2">
              <ShieldCheck size={18} className="text-pitch" aria-hidden="true" />
              Production MVP
            </div>
          </div>
        </div>
      </header>

      <section className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-5">
        <div className="mb-4 flex flex-wrap gap-2">
          {examples.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => useExample(example)}
              className="rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700 shadow-sm transition hover:border-pitch hover:text-pitch"
            >
              {example}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto rounded-md border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[82%] whitespace-pre-wrap rounded-md px-4 py-3 text-sm leading-6 ${
                    message.role === "user"
                      ? "bg-pitch text-white"
                      : "border border-zinc-200 bg-zinc-50 text-zinc-900"
                  }`}
                >
                  {message.content || "正在思考..."}
                </div>
              </div>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 flex gap-3 rounded-md border border-zinc-200 bg-white p-3 shadow-sm">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder="咨询装备、库存、尺码、物流或售后；Enter 发送，Shift+Enter 换行"
            rows={2}
            className="min-h-12 flex-1 resize-none border-0 bg-transparent text-sm leading-6 outline-none placeholder:text-zinc-400"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-pitch text-white transition hover:bg-[#125438] disabled:cursor-not-allowed disabled:bg-zinc-300"
            aria-label="发送"
            title="发送"
          >
            <Send size={18} aria-hidden="true" />
          </button>
        </form>
      </section>
    </main>
  );
}
