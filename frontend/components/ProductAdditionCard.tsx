"use client";

import React, { useMemo, useState } from "react";
import { useChat } from "@/lib/chatStore";

export default function ProductAdditionCard() {
  const { sendMessage } = useChat();
  const [step, setStep] = useState(0);
  const [product, setProduct] = useState("");
  const [qty, setQty] = useState<string>("");
  const [price, setPrice] = useState<string>("");
  const [available, setAvailable] = useState<string>("");
  const [expiry, setExpiry] = useState<string>("");
  const [genImg, setGenImg] = useState<boolean | null>(null);

  const canNext = useMemo(() => {
    if (step === 0) return product.trim().length > 0;
    if (step === 1) return Number(qty) > 0;
    if (step === 2) return Number(price) > 0;
    if (step === 3) return !!available;
    if (step === 4) return true; // expiry optional
    if (step === 5) return genImg !== null; // require explicit choice
    return true;
  }, [step, product, qty, price, available, genImg]);

  const onConfirm = () => {
    const parts = [
      `I want to add inventory`,
      `${product}`,
      `${qty} kg`,
      `${price} ETB/kg`,
      `available ${available}`,
    ];
    if (expiry) parts.push(`expiry ${expiry}`);
    if (genImg) parts.push(`Yes, generate an image`);
    sendMessage(parts.join(", "));
  };

  const label = [
    "What product do you want to add?",
    "How many kilograms?",
    "What price per kilogram (ETB/kg)?",
    "When is it available?",
    "Optional: Does it have an expiry date?",
    "Should I generate a fresh image for this product?",
    "Review",
  ][step];

  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white/75 dark:bg-white/5 p-4">
      <div className="text-sm font-semibold mb-1">Add Inventory</div>
      <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">{label}</div>

      {step === 0 && (
        <input
          className="w-full rounded-xl border px-3 py-2 bg-white/70 dark:bg-white/5 text-sm"
          placeholder="e.g., Tomatoes"
          value={product}
          onChange={(e) => setProduct(e.target.value)}
        />
      )}
      {step === 1 && (
        <input
          type="number"
          className="w-full rounded-xl border px-3 py-2 bg-white/70 dark:bg-white/5 text-sm"
          placeholder="Quantity in kg"
          value={qty}
          onChange={(e) => setQty(e.target.value)}
        />
      )}
      {step === 2 && (
        <input
          type="number"
          className="w-full rounded-xl border px-3 py-2 bg-white/70 dark:bg-white/5 text-sm"
          placeholder="Price (ETB/kg)"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
      )}
      {step === 3 && (
        <input
          type="date"
          className="w-full rounded-xl border px-3 py-2 bg-white/70 dark:bg-white/5 text-sm"
          value={available}
          onChange={(e) => setAvailable(e.target.value)}
        />
      )}
      {step === 4 && (
        <div className="flex items-center gap-2">
          <input
            type="date"
            className="flex-1 rounded-xl border px-3 py-2 bg-white/70 dark:bg-white/5 text-sm"
            value={expiry}
            onChange={(e) => setExpiry(e.target.value)}
          />
          <button className="text-xs px-3 py-2 rounded-xl border" onClick={() => { setExpiry(""); setStep(5); }}>Skip</button>
        </div>
      )}
      {step === 5 && (
        <div className="flex gap-2">
          <button
            className={`rounded-xl px-3 py-2 text-sm border ${genImg === true ? 'bg-blue-600 text-white' : 'bg-white/60 dark:bg-white/5'}`}
            onClick={() => setGenImg(true)}
          >
            Yes, generate image
          </button>
          <button
            className={`rounded-xl px-3 py-2 text-sm border ${genImg === false ? 'bg-blue-600 text-white' : 'bg-white/60 dark:bg-white/5'}`}
            onClick={() => setGenImg(false)}
          >
            No, skip image
          </button>
        </div>
      )}
      {step === 6 && (
        <div className="rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/5 p-3 text-sm">
          <div><span className="text-gray-600 dark:text-gray-300">Product:</span> <span className="font-medium">{product}</span></div>
          <div><span className="text-gray-600 dark:text-gray-300">Quantity:</span> <span className="font-medium">{qty} kg</span></div>
          <div><span className="text-gray-600 dark:text-gray-300">Price:</span> <span className="font-medium">{price} ETB/kg</span></div>
          <div><span className="text-gray-600 dark:text-gray-300">Available:</span> <span className="font-medium">{available}</span></div>
          <div><span className="text-gray-600 dark:text-gray-300">Expiry:</span> <span className="font-medium">{expiry || '—'}</span></div>
          <div><span className="text-gray-600 dark:text-gray-300">Generate Image:</span> <span className="font-medium">{genImg ? 'Yes' : 'No'}</span></div>
        </div>
      )}

      <div className="flex justify-between mt-3">
        <button className="text-xs px-3 py-2 rounded-xl border" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>Back</button>
        {step < 6 ? (
          <button className="text-xs px-3 py-2 rounded-xl bg-blue-600 text-white btn-glow disabled:opacity-60" onClick={() => setStep((s) => s + 1)} disabled={!canNext}>Next</button>
        ) : (
          <button className="text-xs px-3 py-2 rounded-xl bg-blue-600 text-white btn-glow disabled:opacity-60" onClick={onConfirm}>Confirm</button>
        )}
      </div>
    </div>
  );
}
