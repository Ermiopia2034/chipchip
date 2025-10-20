"use client";

import React from "react";
import { ChatMessage as Msg } from "@/lib/chatStore";
import { User, Sprout } from "lucide-react";
import ImageMessage from "@/components/ImageMessage";
import PriceSuggestionCard from "@/components/PriceSuggestionCard";
import NudgeCard from "@/components/NudgeCard";
import ScheduleCard from "@/components/ScheduleCard";
import StatusRow from "@/components/StatusRow";
import OrderCard from "@/components/OrderCard";
import MarkdownContent from "@/components/MarkdownContent";
import RegistrationCard from "@/components/RegistrationCard";
import ProductAdditionCard from "@/components/ProductAdditionCard";

export default function ChatMessage({ message }: { message: Msg }) {
  const isUser = message.role === "user";
  return (
    <div className={`w-full flex ${isUser ? "justify-end" : "justify-start"} my-2 message-in`}>
      <div className={`flex items-end gap-2 max-w-[85%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        <div className={`h-8 w-8 rounded-full shrink-0 grid place-items-center ${isUser ? "bg-gradient-to-tr from-blue-600 via-fuchsia-500 to-amber-400 text-white" : "bg-gray-200 text-gray-700 dark:bg-gray-800 dark:text-gray-200"}`}>
          {isUser ? <User className="h-4 w-4" /> : <Sprout className="h-4 w-4" />}
        </div>
        {/* Bubble */}
        {(() => {
          if (isUser) {
            return (
              <div className={`px-3 py-2 rounded-2xl text-[0.92rem] leading-relaxed whitespace-pre-wrap shadow-sm border bg-gradient-to-tr from-blue-600 via-indigo-600 to-fuchsia-600 text-white border-white/10`}>
                {message.content}
                <div className={`text-[10px] mt-1 opacity-70 text-blue-100`}>
                  {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            );
          }

          // Assistant rendering by kind
          switch (message.kind) {
            case "image":
              return (
                <div className="space-y-2">
                  <ImageMessage url={message.data?.url} caption={message.content} />
                  <div className="text-[10px] mt-1 opacity-70 text-gray-500">
                    {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>
              );
            case "prices":
              return (
                <div className="space-y-2">
                  <PriceSuggestionCard
                    product={message.data?.product}
                    rows={message.data?.rows || []}
                    recommended={message.data?.recommended ?? null}
                    onAction={(id) => {
                      // Send a natural language follow-up via event bubbling; the store is not directly available here.
                      const evt = new CustomEvent("cc-action", { detail: { id, message } });
                      window.dispatchEvent(evt);
                    }}
                  />
                  <div className="text-[10px] mt-1 opacity-70 text-gray-500">
                    {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>
              );
            case "nudge":
              return (
                <div className="space-y-2">
                  <NudgeCard
                    title={message.data?.title || "Suggestion"}
                    suggestions={message.data?.suggestions || []}
                    onAction={(id) => {
                      const evt = new CustomEvent("cc-action", { detail: { id, message } });
                      window.dispatchEvent(evt);
                    }}
                  />
                  <div className="text-[10px] mt-1 opacity-70 text-gray-500">
                    {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>
              );
            case "schedule":
              return (
                <div className="space-y-2">
                  <ScheduleCard entries={message.data?.entries || []} />
                  <div className="text-[10px] mt-1 opacity-70 text-gray-500">
                    {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>
              );
            case "order_summary":
              return (
                <div className="space-y-2">
                  {/* Map parsed data into existing OrderCard shape loosely */}
                  <OrderCard
                    order={{
                      items: (message.data?.items || []).map((it: any) => ({
                        product_name: it.label || it.product_name,
                        quantity_kg: it.quantity_kg || 0,
                        price_per_unit: it.price_per_unit || 0,
                      })),
                      total: message.data?.total || 0,
                      delivery_date: message.data?.delivery || "",
                      delivery_location: (message.data?.delivery || "").split(" to ")[1] || "",
                    }}
                  />
                  <div className="text-[10px] mt-1 opacity-70 text-gray-500">
                    {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>
              );
            case "status":
              return <StatusRow text={message.content} />;
            case "registration_form":
              return (
                <div className="w-full">
                  <RegistrationCard />
                </div>
              );
            case "add_inventory_form":
              return (
                <div className="w-full">
                  <ProductAdditionCard />
                </div>
              );
            case "inventory":
            case "list":
            case "text":
            default:
              return (
                <div className={`px-3 py-2 rounded-2xl text-[0.92rem] leading-relaxed shadow-sm border bg-white/75 dark:bg-white/5 text-gray-900 dark:text-gray-100 border-black/10 dark:border-white/10`}>
                  <MarkdownContent text={message.content} />
                  <div className={`text-[10px] mt-1 opacity-70 text-gray-500`}>
                    {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>
              );
          }
        })()}
      </div>
    </div>
  );
}
