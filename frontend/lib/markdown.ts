// Minimal, safe-ish Markdown to HTML conversion without external deps.
// 1) Escape HTML
// 2) Apply limited markdown patterns

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function sanitizeUrl(url: string): string | null {
  try {
    if (url.startsWith("/")) return url; // relative ok
    const u = new URL(url);
    if (u.protocol === "http:" || u.protocol === "https:") return url;
    return null;
  } catch {
    return null;
  }
}

export function markdownToHtml(input: string): string {
  if (!input) return "";
  // Normalize newlines
  let text = input.replace(/\r\n?/g, "\n");

  // Code blocks ```
  text = text.replace(/```([\s\S]*?)```/g, (_m, code) => {
    return `<pre class="md-code"><code>${escapeHtml(String(code))}</code></pre>`;
  });

  // Escape remaining HTML
  text = escapeHtml(text);

  // Headings #, ##, ### at line start
  text = text.replace(/^###\s*(.+)$/gm, '<h3 class="md-h">$1</h3>');
  text = text.replace(/^##\s*(.+)$/gm, '<h2 class="md-h">$1</h2>');
  text = text.replace(/^#\s*(.+)$/gm, '<h1 class="md-h">$1</h1>');

  // Bold **text** and italics *text*
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/(^|\W)\*(?!\s)([^*]+?)\*(?=\W|$)/g, '$1<em>$2</em>');

  // Inline code `code`
  text = text.replace(/`([^`]+?)`/g, '<code class="md-inline">$1</code>');

  // Links [text](url)
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, label, url) => {
    const safe = sanitizeUrl(String(url).trim());
    const t = escapeHtml(String(label));
    return safe ? `<a href="${safe}" target="_blank" rel="noopener noreferrer" class="md-link">${t}</a>` : t;
  });

  // Lists: convert blocks of lines starting with - or * into <ul>
  const lines = text.split("\n");
  const out: string[] = [];
  let ul: string[] | null = null;
  let ol: string[] | null = null;
  for (const line of lines) {
    let m;
    if ((m = line.match(/^\s*[-*]\s+(.*)$/))) {
      if (!ul) ul = [];
      ul.push(`<li>${m[1]}</li>`);
      continue;
    }
    if ((m = line.match(/^\s*(\d+)\.\s+(.*)$/))) {
      if (!ol) ol = [];
      ol.push(`<li>${m[2]}</li>`);
      continue;
    }
    if (ul) {
      out.push(`<ul class="md-list">${ul.join("")}</ul>`);
      ul = null;
    }
    if (ol) {
      out.push(`<ol class="md-list">${ol.join("")}</ol>`);
      ol = null;
    }
    out.push(line.length ? `<p>${line}</p>` : "");
  }
  if (ul) out.push(`<ul class="md-list">${ul.join("")}</ul>`);
  if (ol) out.push(`<ol class="md-list">${ol.join("")}</ol>`);

  return out.join("\n");
}

