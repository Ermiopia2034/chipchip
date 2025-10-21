export type ParsedKind =
  | "text"
  | "image"
  | "prices"
  | "nudge"
  | "schedule"
  | "order_summary"
  | "inventory"
  | "list"
  | "status"
  | "registration_form"
  | "add_inventory_form";

export type ParsedMessage = {
  kind: ParsedKind;
  content: string;
  data?: unknown;
  actions?: { id: string; label: string }[];
  metadata?: unknown;
};

// Backend may attach structured order data alongside the confirmation text.
// This mirrors the shape returned by the order tool.
type ExplicitOrderItem = {
  product_id?: number;
  product_name?: string;
  quantity_kg?: number;
  price_per_unit?: number;
  label?: string;
};

function isExplicitOrderItem(x: unknown): x is ExplicitOrderItem {
  if (!x || typeof x !== "object") return false;
  // Light guard: allow partials; detailed type checks done on read.
  return true;
}

function parseImageFromContent(content: string): string | null {
  const m = content.match(/Image:\s*(\/static\/images\/\S+)/i);
  return m ? m[1] : null;
}

function parsePrices(content: string) {
  // Current market prices for X:\n- Farm/Local: N ETB/kg\n- Supermarket: N ETB/kg\n- Distribution Center: N ETB/kg\n\nHistorical selling price: N ETB/kg\n\nRecommendation: Set price at N ETB/kg ...
  const head = content.match(/^Current market prices for\s+(.+?):\s*/i);
  if (!head) return null;
  const product = head[1];
  const farm = content.match(/Farm\/Local:\s*(\d+(?:\.\d+)?)\s*ETB\/kg/i)?.[1];
  const superm = content.match(/Supermarket:\s*(\d+(?:\.\d+)?)\s*ETB\/kg/i)?.[1];
  const dist = content.match(/Distribution Center:\s*(\d+(?:\.\d+)?)\s*ETB\/kg/i)?.[1];
  const hist = content.match(/Historical selling price:\s*(\d+(?:\.\d+)?)\s*ETB\/kg/i)?.[1];
  const rec = content.match(/Recommendation:.*?\s(\d+(?:\.\d+)?)\s*ETB\/kg/i)?.[1];
  return {
    product,
    rows: [
      { label: "Farm/Local", value: farm ? Number(farm) : null },
      { label: "Supermarket", value: superm ? Number(superm) : null },
      { label: "Distribution Center", value: dist ? Number(dist) : null },
      { label: "Historical Avg", value: hist ? Number(hist) : null },
    ],
    recommended: rec ? Number(rec) : null,
  };
}

function parseNudge(content: string) {
  if (!/Expiring Inventory Alert/i.test(content)) return null;
  // Lines like: - Milk (10 kg): Expires in 2 days → Suggest 20% flash sale
  const lines = content.split("\n").filter(Boolean);
  const items = lines
    .slice(1)
    .map((l) => {
      const m = l.match(/-\s*(.+?)\s*\((.+?)\):\s*Expires in\s*(\d+)\s*days?\s*\u2192\s*Suggest\s*(\d+)%/i);
      if (m) {
        return { name: m[1], qty: m[2], days: Number(m[3]), discount: Number(m[4]) };
      }
      return null;
    })
    .filter(Boolean);
  return { title: "Expiring Inventory Alert", suggestions: items };
}

function parseSchedule(content: string) {
  if (!/^Your Delivery Schedule:/i.test(content)) return null;
  const lines = content.split("\n").slice(1);
  const entries = lines
    .map((l) => {
      const m = l.match(/^(.*?):\s*(\d+)\s*orders?\s*\((\d+)\s*ETB total\)/i);
      if (m) return { when: m[1], count: Number(m[2]), total: Number(m[3]) };
      return null;
    })
    .filter(Boolean);
  return { entries };
}

function parseOrderSummary(content: string) {
  if (!/^Order confirmed!/i.test(content)) return null;
  const id = content.match(/Order ID:\s*(\d+)/i)?.[1];
  const total = content.match(/Total:\s*(\d+(?:\.\d+)?)\s*ETB/i)?.[1];
  const delivery = content.match(/Delivery:\s*([^\n]+)/i)?.[1];
  const payment = /Payment:\s*(.*)/i.exec(content)?.[1];
  const itemsLine = content.match(/Items:\s*([^\n]+)/i)?.[1];
  let items: { label: string }[] = [];
  if (itemsLine) {
    items = itemsLine.split(/,\s*/).map((s) => ({ label: s.trim() }));
  }
  return { orderId: id, total: total ? Number(total) : null, delivery, payment, items };
}

function parseInventoryList(content: string) {
  if (!/^Your Current Inventory:/i.test(content)) return null;
  const lines = content.split("\n").slice(1);
  return { lines };
}

function parseGenericList(content: string) {
  // Found N products:\n- A\n- B
  if (!/^Found\s+\d+\s+products:/i.test(content)) return null;
  const lines = content.split("\n").slice(1);
  return { lines };
}

export function parseAssistantPayload(payload: unknown): ParsedMessage {
  const p = (payload ?? {}) as Record<string, unknown>;
  const content = String((p["content"] as string | undefined) ?? (p["message"] as string | undefined) ?? "");

  // If backend ever adds a type/data, keep them
  const explicitType = typeof p["type"] === "string" ? (p["type"] as string) : undefined;
  const explicit = (p["data"] ?? {}) as Record<string, unknown>;
  const metadata = p["metadata"];

  if (explicitType === "image" && typeof explicit["url"] === "string") {
    return { kind: "image", content, data: { url: explicit["url"] }, metadata };
  }

  // Do not auto-open guided forms based on backend types; forms are opened via UI actions only.

  const imageUrl = parseImageFromContent(content);
  if (imageUrl) return { kind: "image", content, data: { url: imageUrl }, metadata };

  // No content-based fallbacks for forms.

  const prices = parsePrices(content);
  if (prices) {
    return {
      kind: "prices",
      content,
      data: prices,
      actions: [
        { id: "use_recommended", label: prices.recommended ? `Use ${prices.recommended} ETB/kg` : "Use recommended" },
        { id: "set_custom", label: "Set custom price…" },
      ],
      metadata,
    };
  }

  const nudge = parseNudge(content);
  if (nudge) {
    return {
      kind: "nudge",
      content,
      data: nudge,
      actions: [{ id: "run_flash_sale", label: "Run suggested flash sale" }],
      metadata,
    };
  }

  const schedule = parseSchedule(content);
  if (schedule) return { kind: "schedule", content, data: schedule, metadata };

  const order = parseOrderSummary(content);
  if (order) {
    // If backend included structured data, prefer/merge it for accuracy
    if (explicit && typeof explicit === "object") {
      const items = Array.isArray(explicit["items"]) ? (explicit["items"] as unknown[]).filter(isExplicitOrderItem) : null;
      const total = typeof explicit["total"] === "number" ? (explicit["total"] as number) : null;
      const deliveryDate = typeof explicit["delivery_date"] === "string" ? (explicit["delivery_date"] as string) : null;
      const deliveryLoc = typeof explicit["delivery_location"] === "string" ? (explicit["delivery_location"] as string) : null;
      const payment = typeof explicit["payment"] === "string" ? (explicit["payment"] as string) : null;
      const oid = typeof explicit["order_id"] === "string" ? (explicit["order_id"] as string) : null;
      if (oid) order.orderId = oid;
      if (payment) order.payment = payment;
      if (total !== null) order.total = total;
      if (deliveryDate || deliveryLoc) {
        order.delivery = `${deliveryDate ?? ""}${deliveryLoc ? ` to ${deliveryLoc}` : ""}`.trim();
      }
      if (items) {
        order.items = items.map((it) => ({
          label: it?.product_name ?? it?.label ?? `#${it?.product_id ?? ""}`,
          product_name: it?.product_name,
          quantity_kg: typeof it?.quantity_kg === "number" ? it.quantity_kg : null,
          price_per_unit: typeof it?.price_per_unit === "number" ? it.price_per_unit : null,
        }));
      }
    }
    return { kind: "order_summary", content, data: order, metadata };
  }

  const inv = parseInventoryList(content);
  if (inv) return { kind: "inventory", content, data: inv, metadata };

  const list = parseGenericList(content);
  if (list) return { kind: "list", content, data: list, metadata };

  return { kind: "text", content, metadata };
}

export function shouldSimulateCOD(content: string): boolean {
  return /Payment is Cash on Delivery\.\s*Confirming order/i.test(content);
}
