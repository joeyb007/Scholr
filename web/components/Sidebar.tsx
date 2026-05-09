"use client";

import { useState } from "react";
import { useSession, signOut } from "next-auth/react";
import type { Conversation } from "@/types/scholr";

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

function TrashIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M1.5 3h9M4.5 3V2a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v1M2.5 3l.5 7a.5.5 0 0 0 .5.5h5a.5.5 0 0 0 .5-.5l.5-7" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

interface ConfirmModalProps {
  title: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmModal({ title, onConfirm, onCancel }: ConfirmModalProps) {
  const [closing, setClosing] = useState(false);

  function dismiss(cb: () => void) {
    setClosing(true);
    setTimeout(cb, 140);
  }

  return (
    <div className={`confirm-overlay${closing ? " confirm-overlay--out" : ""}`} onClick={() => dismiss(onCancel)}>
      <div className="confirm-box" onClick={e => e.stopPropagation()}>
        <div className="confirm-title">Delete inquiry?</div>
        <div className="confirm-body">
          &ldquo;{title}&rdquo; and all its messages will be permanently deleted.
        </div>
        <div className="confirm-actions">
          <button className="confirm-cancel" onClick={() => dismiss(onCancel)}>Cancel</button>
          <button className="confirm-delete" onClick={() => dismiss(onConfirm)}>Delete</button>
        </div>
      </div>
    </div>
  );
}

export function Sidebar({ conversations, activeId, onSelect, onNew, onDelete }: SidebarProps) {
  const [pendingDelete, setPendingDelete] = useState<Conversation | null>(null);
  const { status } = useSession();

  function handleDeleteClick(e: React.MouseEvent, conv: Conversation) {
    e.stopPropagation();
    setPendingDelete(conv);
  }

  function handleConfirm() {
    if (pendingDelete) {
      onDelete(pendingDelete.id);
      setPendingDelete(null);
    }
  }

  return (
    <>
      {pendingDelete && (
        <ConfirmModal
          title={pendingDelete.title}
          onConfirm={handleConfirm}
          onCancel={() => setPendingDelete(null)}
        />
      )}

      <div className="sidebar">
        <div className="sidebar__brand">
          <div className="sidebar__brand-row">
            <div className="sidebar__logo">S</div>
            <span className="sidebar__wordmark">scholr</span>
            <span className="sidebar__version">0.4.2</span>
          </div>
          <button className="sidebar__new" onClick={onNew}>
            + new inquiry
          </button>
        </div>

        <div className="sidebar__nav">
          <div className="sidebar__section">Recent</div>
          {conversations.map(conv => (
            <button
              key={conv.id}
              className={`sidebar__item${conv.id === activeId ? " sidebar__item--active" : ""}`}
              onClick={() => onSelect(conv.id)}
            >
              <div className="sidebar__item-row">
                <div className="sidebar__item-content">
                  <div className="sidebar__item-title">{conv.title}</div>
                  <div className="sidebar__item-meta">
                    D{conv.depthReached} · {timeAgo(conv.createdAt).toUpperCase()}
                  </div>
                </div>
                <span
                  className="sidebar__item-delete"
                  onClick={e => handleDeleteClick(e, conv)}
                  role="button"
                  aria-label="Delete"
                >
                  <TrashIcon />
                </span>
              </div>
            </button>
          ))}
        </div>

        <div className="sidebar__footer">
          <div className="sidebar__dot" />
          <span className="sidebar__status">OPENALEX</span>
          {status === "authenticated" && (
            <button className="sidebar__logout" onClick={() => signOut()}>sign out</button>
          )}
        </div>
      </div>
    </>
  );
}
