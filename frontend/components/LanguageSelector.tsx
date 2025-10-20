"use client";

import React from "react";
import { useChat } from "@/lib/chatStore";

const options = [
  { label: "Auto", value: "auto" },
  { label: "English", value: "en" },
  { label: "አማርኛ", value: "am" },
  { label: "Amharic-Latin", value: "amglish" },
];

export default function LanguageSelector() {
  const { language, setLanguage } = useChat();
  return (
    <select
      className="rounded-xl border border-black/10 dark:border-white/10 glass p-2 text-sm"
      value={language}
      onChange={(e) => setLanguage(e.target.value)}
      aria-label="Language"
      title="Language"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}
