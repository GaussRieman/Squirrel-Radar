"use client";

import { ReactNode } from "react";

type AgentContextButtonProps = {
  context: Record<string, unknown>;
  children: ReactNode;
  className?: string;
};

export function AgentContextButton({ context, children, className }: AgentContextButtonProps) {
  return (
    <button
      type="button"
      className={className || "context-link"}
      onClick={() => {
        window.dispatchEvent(new CustomEvent("agent-context-selected", { detail: context }));
      }}
    >
      {children}
    </button>
  );
}
