"use client";

import React, { useState } from "react";
import { useChat } from "@/lib/chatStore";

export default function RegistrationCard() {
  const { sendMessage } = useChat();
  const [role, setRole] = useState<"customer" | "supplier">("customer");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("");
  const [step, setStep] = useState(0);

  const steps = [
    { key: "role", label: "Are you a customer or a supplier?", render: () => (
      <div className="flex gap-2">
        <button className={`rounded-xl px-3 py-2 text-sm border ${role === 'customer' ? 'bg-blue-600 text-white' : 'bg-white/60 dark:bg-white/5'}`} onClick={() => setRole("customer")}>Customer</button>
        <button className={`rounded-xl px-3 py-2 text-sm border ${role === 'supplier' ? 'bg-blue-600 text-white' : 'bg-white/60 dark:bg-white/5'}`} onClick={() => setRole("supplier")}>Supplier</button>
      </div>
    )},
    { key: "name", label: "What’s your name?", render: () => (
      <input className="w-full rounded-xl border px-3 py-2 bg-white/70 dark:bg-white/5" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
    )},
    { key: "phone", label: "What’s your phone number?", render: () => (
      <input className="w-full rounded-xl border px-3 py-2 bg-white/70 dark:bg-white/5" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="09XXXXXXXX or +2519XXXXXXXX" />
    )},
    { key: "location", label: "What’s your default delivery location?", render: () => (
      <input className="w-full rounded-xl border px-3 py-2 bg-white/70 dark:bg-white/5" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g., Addis Ababa (Bole)" />
    )},
  ];

  const canNext = () => {
    if (step === 1) return name.trim().length > 0;
    if (step === 2) return /^(\+?251)?\s*-?0?9\d{8}$/g.test(phone.replace(/\s|-/g, '')) || phone.trim().length >= 9;
    if (step === 3) return location.trim().length > 0;
    return true;
  };

  const onConfirm = () => {
    const text = `I want to register as a ${role}. My name is ${name}. My phone is ${phone}. My default location is ${location}.`;
    sendMessage(text);
  };

  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white/75 dark:bg-white/5 p-4">
      <div className="text-sm font-semibold mb-2">Let’s get you registered</div>
      <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">{steps[step].label}</div>
      <div>{steps[step].render()}</div>
      <div className="flex justify-between mt-3">
        <button className="text-xs px-3 py-2 rounded-xl border" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>Back</button>
        {step < steps.length - 1 ? (
          <button className="text-xs px-3 py-2 rounded-xl bg-blue-600 text-white btn-glow disabled:opacity-60" onClick={() => setStep((s) => s + 1)} disabled={!canNext()}>Next</button>
        ) : (
          <button className="text-xs px-3 py-2 rounded-xl bg-blue-600 text-white btn-glow disabled:opacity-60" onClick={onConfirm} disabled={!canNext()}>Confirm</button>
        )}
      </div>
    </div>
  );
}

