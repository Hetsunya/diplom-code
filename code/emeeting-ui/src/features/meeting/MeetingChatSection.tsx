import { useEffect, useRef, useState } from "react";

export type ChatLine = {
  id: string;
  participantId: string;
  name: string;
  text: string;
  at: string;
};

type MeetingChatSectionProps = {
  messages: ChatLine[];
  currentParticipantId: string;
  onSend: (text: string) => void;
  canSend?: boolean;
};

const MAX_LEN = 2000;

export function MeetingChatSection({
  messages,
  currentParticipantId,
  onSend,
  canSend = true,
}: MeetingChatSectionProps) {
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  const submit = () => {
    const t = draft.trim();
    if (!t || !canSend) return;
    if (t.length > MAX_LEN) {
      onSend(t.slice(0, MAX_LEN));
    } else {
      onSend(t);
    }
    setDraft("");
  };

  return (
    <div className="meeting-transcript-rail__section meeting-transcript-rail__chat">
      <div className="meeting-transcript-rail__section-title-row">
        <div className="meeting-transcript-rail__section-title">Чат</div>
      </div>
      <div
        ref={scrollRef}
        className="meeting-transcript-rail__chat-scroll"
        role="log"
        aria-label="Сообщения чата"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <p className="meeting-transcript-rail__muted meeting-transcript-rail__chat-empty">
            Напишите сообщение участникам встречи.
          </p>
        ) : (
          messages.map((m) => {
            const mine = m.participantId === currentParticipantId;
            return (
              <div
                key={m.id}
                className={`meeting-chat-msg ${mine ? "meeting-chat-msg--mine" : "meeting-chat-msg--other"}`}
              >
                <div className="meeting-chat-msg__meta">
                  <span className="meeting-chat-msg__name">{mine ? "Вы" : m.name}</span>
                  <time className="meeting-chat-msg__time" dateTime={m.at}>
                    {new Date(m.at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                  </time>
                </div>
                <div className="meeting-chat-msg__bubble">{m.text}</div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
      <div className="meeting-transcript-rail__chat-input-row">
        <label className="meeting-transcript-rail__chat-label" htmlFor="meeting-chat-input">
          Сообщение
        </label>
        <textarea
          id="meeting-chat-input"
          className="meeting-transcript-rail__chat-input"
          rows={2}
          maxLength={MAX_LEN}
          placeholder={canSend ? "Текст для участников…" : "Подключение…"}
          value={draft}
          disabled={!canSend}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <button
          type="button"
          className="meeting-transcript-rail__chat-send"
          disabled={!canSend || !draft.trim()}
          onClick={submit}
        >
          Отправить
        </button>
      </div>
    </div>
  );
}
