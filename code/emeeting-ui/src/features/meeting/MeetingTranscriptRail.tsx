import { useEffect, useMemo, useRef, useState } from "react";
import { MeetingChatSection, type ChatLine } from "./MeetingChatSection";
import {
  IconCamOff,
  IconCamOn,
  IconChat,
  IconMicOff,
  IconMicOn,
  IconPeople,
  IconTranscript,
} from "../../components/MeetingUiIcons";

export type TranscriptLine = {
  traceId: string;
  participantId: string;
  speakerLabel: string;
  text: string;
  final: boolean;
  at: string;
};

export type MeetingParticipantRow = {
  id: string;
  name: string;
  isSelf: boolean;
  micOn?: boolean;
  camOn?: boolean;
  emotionLabel?: string;
};

export type { ChatLine };

type MeetingTranscriptRailProps = {
  lines: TranscriptLine[];
  asrStatus: string;
  chatMessages: ChatLine[];
  currentParticipantId: string;
  onSendChat: (text: string) => void;
  chatConnected?: boolean;
  participants: MeetingParticipantRow[];
  verdictSummary?: string | null;
  verdictDetail?: string | null;
  verdictOpen?: boolean;
  onToggleVerdict?: () => void;
};

export function MeetingTranscriptRail({
  lines,
  asrStatus,
  chatMessages,
  currentParticipantId,
  onSendChat,
  chatConnected = true,
  participants,
  verdictSummary = null,
  verdictDetail = null,
  verdictOpen = false,
  onToggleVerdict,
}: MeetingTranscriptRailProps) {
  const [showTranscript, setShowTranscript] = useState(true);
  const [showChat, setShowChat] = useState(true);
  const [showPeople, setShowPeople] = useState(true);

  const scrollRef = useRef<HTMLDivElement>(null);
  const linesChrono = useMemo(() => [...lines], [lines]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lines]);

  return (
    <aside className="meeting-transcript-rail" aria-label="Панель встречи">
      <div className="meeting-rail-toolbar" role="toolbar" aria-label="Разделы панели">
        <button
          type="button"
          className={`meeting-rail-toolbtn ${showTranscript ? "meeting-rail-toolbtn--on" : ""}`}
          onClick={() => setShowTranscript((v) => !v)}
          aria-pressed={showTranscript}
          title={showTranscript ? "Скрыть транскрибацию" : "Показать транскрибацию"}
        >
          <IconTranscript size={22} title="Транскрибация" />
        </button>
        <button
          type="button"
          className={`meeting-rail-toolbtn ${showChat ? "meeting-rail-toolbtn--on" : ""}`}
          onClick={() => setShowChat((v) => !v)}
          aria-pressed={showChat}
          title={showChat ? "Скрыть чат" : "Показать чат"}
        >
          <IconChat size={22} title="Чат" />
        </button>
        <button
          type="button"
          className={`meeting-rail-toolbtn ${showPeople ? "meeting-rail-toolbtn--on" : ""}`}
          onClick={() => setShowPeople((v) => !v)}
          aria-pressed={showPeople}
          title={showPeople ? "Скрыть участников" : "Показать участников"}
        >
          <IconPeople size={22} title="Участники" />
        </button>
      </div>

      {showTranscript && (
        <div className="meeting-transcript-rail__section">
          <div className="meeting-transcript-rail__section-title-row">
            <div className="meeting-transcript-rail__section-title">Транскрибация</div>
            <span className="meeting-transcript-rail__asr-status">{asrStatus}</span>
          </div>
          <div
            ref={scrollRef}
            className="meeting-transcript-rail__scroll meeting-transcript-rail__scroll--chrono"
            role="log"
            aria-live="polite"
            aria-relevant="additions text"
          >
            {linesChrono.length === 0 ? (
              <p className="meeting-transcript-rail__muted">Здесь будет распознанная речь по мере поступления.</p>
            ) : (
              linesChrono.map((line, idx) => (
                <div
                  key={`${line.traceId}-${line.participantId}-${line.at}-${idx}`}
                  className={`meeting-transcript-rail__line ${line.final ? "" : "meeting-transcript-rail__line--draft"}`}
                >
                  <div className="meeting-transcript-rail__line-meta">
                    <span className="meeting-transcript-rail__speaker">{line.speakerLabel}</span>
                    <time className="meeting-transcript-rail__time" dateTime={line.at}>
                      {new Date(line.at).toLocaleTimeString(undefined, {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </time>
                    {line.final ? (
                      <span className="meeting-transcript-rail__badge meeting-transcript-rail__badge--final">готово</span>
                    ) : (
                      <span className="meeting-transcript-rail__badge">набирается…</span>
                    )}
                  </div>
                  <div className="meeting-transcript-rail__line-text">{line.text || "…"}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {showTranscript && (
        <div className="meeting-transcript-rail__section">
          <div className="meeting-transcript-rail__section-title-row">
            <div className="meeting-transcript-rail__section-title">Вердикт AI</div>
          </div>
          {verdictSummary ? (
            <>
              <button
                type="button"
                className="meeting-transcript-rail__verdict-btn"
                onClick={onToggleVerdict}
                aria-expanded={verdictOpen}
              >
                <span>{verdictSummary}</span>
                <span className="meeting-transcript-rail__chevron">{verdictOpen ? "▲" : "▼"}</span>
              </button>
              {verdictOpen && verdictDetail ? (
                <pre className="meeting-transcript-rail__verdict-detail">{verdictDetail}</pre>
              ) : null}
            </>
          ) : (
            <p className="meeting-transcript-rail__muted">
              Промежуточный вердикт появится после накопления данных анализа.
            </p>
          )}
        </div>
      )}

      {showChat && (
        <MeetingChatSection
          messages={chatMessages}
          currentParticipantId={currentParticipantId}
          onSend={onSendChat}
          canSend={chatConnected}
        />
      )}

      {showPeople && (
        <div className="meeting-transcript-rail__section meeting-transcript-rail__people">
          <div className="meeting-transcript-rail__section-title-row">
            <div className="meeting-transcript-rail__section-title">Участники</div>
            <span className="meeting-transcript-rail__people-count">{participants.length}</span>
          </div>
          <ul className="meeting-people-list">
            {participants.map((p) => (
              <li key={p.id} className="meeting-people-list__row">
                <div className="meeting-people-list__avatar" aria-hidden>
                  {p.name.trim().charAt(0).toUpperCase() || "?"}
                </div>
                <div className="meeting-people-list__main">
                  <div className="meeting-people-list__name">
                    {p.name}
                    {p.isSelf ? <span className="meeting-people-list__you"> вы</span> : null}
                  </div>
                  {p.emotionLabel ? (
                    <div className="meeting-people-list__meta">{p.emotionLabel}</div>
                  ) : null}
                </div>
                {p.isSelf && (
                  <div className="meeting-people-list__devices" aria-label="Ваши устройства">
                    <span
                      className={`meeting-people-list__dev ${p.micOn ? "meeting-people-list__dev--on" : "meeting-people-list__dev--off"}`}
                      title={p.micOn ? "Микрофон включён" : "Микрофон выключен"}
                    >
                      {p.micOn ? <IconMicOn size={18} /> : <IconMicOff size={18} />}
                    </span>
                    <span
                      className={`meeting-people-list__dev ${p.camOn ? "meeting-people-list__dev--on" : "meeting-people-list__dev--off"}`}
                      title={p.camOn ? "Камера включена" : "Камера выключена"}
                    >
                      {p.camOn ? <IconCamOn size={18} /> : <IconCamOff size={18} />}
                    </span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
