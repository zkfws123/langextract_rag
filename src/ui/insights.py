from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional


@dataclass(frozen=True)
class HighlightSpan:
    entity_id: str
    start: int
    end: int
    label: str
    extraction_class: str


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def build_highlight_spans(markdown_text: str, extractions: Iterable[Any]) -> List[HighlightSpan]:
  spans: List[HighlightSpan] = []
  max_spans = 500

  for idx, ext in enumerate(extractions):
    extraction_class = getattr(ext, "extraction_class", "") or ""
    label = getattr(ext, "extraction_text", "") or ""
    if not label:
      continue

    interval = getattr(ext, "char_interval", None) or {}
    start = _safe_int(interval.get("start_pos"))
    end = _safe_int(interval.get("end_pos"))

    # Prefer provided char_interval; otherwise try substring search (best-effort)
    if start is None or end is None or start < 0 or end <= start or end > len(markdown_text):
      found = markdown_text.find(label)
      if found < 0:
        continue
      start = found
      end = found + len(label)

    if start < 0 or end <= start or end > len(markdown_text):
      continue

    entity_id = f"e{idx}"
    spans.append(
      HighlightSpan(
        entity_id=entity_id,
        start=start,
        end=end,
        label=label,
        extraction_class=extraction_class,
      )
    )

    if len(spans) >= max_spans:
      break

  # Important: insert tags from right to left
  spans.sort(key=lambda s: (s.start, s.end), reverse=True)
  return spans


def _apply_spans(markdown_text: str, spans: List[HighlightSpan]) -> str:
    text = markdown_text
    for span in spans:
        raw = text[span.start : span.end]
        escaped = html.escape(raw)
        badge = "metric" if span.extraction_class == "数据指标" else "entity"
        wrapped = (
            f"<span class=\"hl {badge}\" data-eid=\"{span.entity_id}\" "
            f"title=\"{html.escape(span.label)}\">{escaped}</span>"
        )
        text = text[: span.start] + wrapped + text[span.end :]
    # Escape remaining text that isn't part of spans
    # Note: span inserts already escaped; now escape the rest by escaping and then un-escaping inserted spans is hard.
    # Instead, we escaped each wrapped raw but not other parts; do a safe global escape first.
    # We handle this by escaping first, then applying spans over the escaped text using mapping.
    return text


def build_insights_html(markdown_text: str, extractions: Iterable[Any], max_chars: int = 120000) -> str:
    """Return a self-contained HTML page: left source text w/ highlights, right entity cards.

    Clicking a card scrolls to the first matched highlight and draws a line.
    """

    source = markdown_text[:max_chars]
    spans = build_highlight_spans(source, extractions)

    # Build right-side cards data
    cards = []
    for s in spans:
        cards.append(
            {
                "id": s.entity_id,
                "label": s.label,
                "class": s.extraction_class,
                "start": s.start,
                "end": s.end,
            }
        )

    # Escape full text first, then re-inject highlight spans based on original indices.
    # To keep indices correct, we apply spans on the original string but wrap with <pre> and escape non-span parts.
    # Implementation: build pieces.
    pieces: List[str] = []
    last = 0
    spans_lr = sorted(spans, key=lambda s: (s.start, s.end))
    for s in spans_lr:
        if s.start < last:
            continue
        pieces.append(html.escape(source[last : s.start]))
        raw = source[s.start : s.end]
        escaped_raw = html.escape(raw)
        badge = "metric" if s.extraction_class == "数据指标" else "entity"
        pieces.append(
            f"<span class=\"hl {badge}\" data-eid=\"{s.entity_id}\" title=\"{html.escape(s.label)}\">{escaped_raw}</span>"
        )
        last = s.end
    pieces.append(html.escape(source[last:]))
    left_html = "".join(pieces)

    cards_json = json.dumps(cards, ensure_ascii=False)

    return f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    :root {{
      --bg: #ffffff;
      --panel: #f7f7f9;
      --border: #e5e7eb;
      --text: #111827;
      --muted: #6b7280;
      --hl-entity: #dbeafe;
      --hl-metric: #fee2e2;
      --hl-active: #fde68a;
      --line: #ef4444;
    }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, 'Apple Color Emoji','Segoe UI Emoji'; color: var(--text); background: var(--bg); }}
    .wrap {{ display: grid; grid-template-columns: 1fr 380px; gap: 12px; height: 100vh; padding: 12px; box-sizing: border-box; }}
    .left {{ position: relative; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }}
    .right {{ border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: var(--panel); }}
    .hdr {{ padding: 10px 12px; border-bottom: 1px solid var(--border); background: var(--bg); font-weight: 600; }}
    .sub {{ color: var(--muted); font-weight: 500; font-size: 12px; margin-left: 8px; }}
    .content {{ height: calc(100vh - 52px); overflow: auto; position: relative; }}
    pre {{ margin: 0; padding: 14px; white-space: pre-wrap; word-break: break-word; line-height: 1.55; font-size: 13px; }}

    .hl {{ padding: 1px 2px; border-radius: 4px; border: 1px solid rgba(0,0,0,0.06); cursor: pointer; }}
    .hl.entity {{ background: var(--hl-entity); }}
    .hl.metric {{ background: var(--hl-metric); }}
    .hl.active {{ background: var(--hl-active) !important; }}

    .cards {{ padding: 10px; display: grid; gap: 10px; }}
    .card {{ background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 10px 10px; cursor: pointer; }}
    .card:hover {{ border-color: #cbd5e1; }}
    .tag {{ display: inline-block; padding: 2px 6px; font-size: 12px; border-radius: 999px; border: 1px solid var(--border); color: var(--muted); margin-left: 6px; }}
    .card-title {{ font-weight: 650; }}
    .card-meta {{ margin-top: 6px; color: var(--muted); font-size: 12px; }}

    svg.overlay {{ position: absolute; left: 0; top: 0; width: 100%; height: 100%; pointer-events: none; }}
  </style>
</head>
<body>
  <div class=\"wrap\" id=\"wrap\">
    <div class=\"left\" id=\"leftPanel\">
      <div class=\"hdr\">源文档 <span class=\"sub\">点击右侧实体，自动定位并连线</span></div>
      <div class=\"content\" id=\"leftScroll\">
        <svg class=\"overlay\" id=\"overlay\"></svg>
        <pre id=\"source\">{left_html}</pre>
      </div>
    </div>

    <div class=\"right\" id=\"rightPanel\">
      <div class=\"hdr\">提取洞察 <span class=\"sub\">共 {len(cards)} 条高亮</span></div>
      <div class=\"content\" id=\"rightScroll\">
        <div class=\"cards\" id=\"cards\"></div>
      </div>
    </div>
  </div>

<script>
  const cards = {cards_json};

  const cardsEl = document.getElementById('cards');
  const leftScroll = document.getElementById('leftScroll');
  const overlay = document.getElementById('overlay');

  function clearActive() {{
    document.querySelectorAll('.hl.active').forEach(el => el.classList.remove('active'));
  }}

  function clearLine() {{
    while (overlay.firstChild) overlay.removeChild(overlay.firstChild);
  }}

  function drawLine(fromEl, toEl) {{
    clearLine();
    const wrap = document.getElementById('wrap');
    const wrapRect = wrap.getBoundingClientRect();

    const a = fromEl.getBoundingClientRect();
    const b = toEl.getBoundingClientRect();

    const x1 = a.left - wrapRect.left;
    const y1 = a.top - wrapRect.top + a.height / 2;
    const x2 = b.left - wrapRect.left;
    const y2 = b.top - wrapRect.top + b.height / 2;

    const svgNS = 'http://www.w3.org/2000/svg';
    const line = document.createElementNS(svgNS, 'line');
    line.setAttribute('x1', x1);
    line.setAttribute('y1', y1);
    line.setAttribute('x2', x2);
    line.setAttribute('y2', y2);
    line.setAttribute('stroke', getComputedStyle(document.documentElement).getPropertyValue('--line').trim() || '#ef4444');
    line.setAttribute('stroke-width', '2');
    line.setAttribute('stroke-linecap', 'round');

    const dot1 = document.createElementNS(svgNS, 'circle');
    dot1.setAttribute('cx', x1);
    dot1.setAttribute('cy', y1);
    dot1.setAttribute('r', '4');
    dot1.setAttribute('fill', '#ef4444');

    const dot2 = document.createElementNS(svgNS, 'circle');
    dot2.setAttribute('cx', x2);
    dot2.setAttribute('cy', y2);
    dot2.setAttribute('r', '4');
    dot2.setAttribute('fill', '#ef4444');

    overlay.appendChild(line);
    overlay.appendChild(dot1);
    overlay.appendChild(dot2);
  }}

  function focusEntity(entityId, cardEl) {{
    const target = document.querySelector(`.hl[data-eid="${{entityId}}"]`);
    if (!target) return;

    clearActive();
    target.classList.add('active');

    // scroll to center
    const containerRect = leftScroll.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const delta = (targetRect.top - containerRect.top) - (containerRect.height / 2 - targetRect.height / 2);
    leftScroll.scrollTop += delta;

    // after scroll, draw line
    window.requestAnimationFrame(() => drawLine(cardEl, target));
  }}

  function cardTemplate(item) {{
    const div = document.createElement('div');
    div.className = 'card';
    div.id = `card-${{item.id}}`;

    const clsTag = item.class || '';
    div.innerHTML = `
      <div class="card-title">${{escapeHtml(item.label)}}<span class="tag">${{escapeHtml(clsTag)}}</span></div>
      <div class="card-meta">字符区间: ${{item.start}} - ${{item.end}}</div>
    `;

    div.addEventListener('click', () => focusEntity(item.id, div));
    return div;
  }}

  function escapeHtml(s) {{
    return String(s)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }}

  // render cards
  cards.forEach(item => cardsEl.appendChild(cardTemplate(item)));

  // click highlight also focuses the corresponding card
  document.querySelectorAll('.hl').forEach(hl => {{
    hl.addEventListener('click', () => {{
      const eid = hl.getAttribute('data-eid');
      const cardEl = document.getElementById(`card-${{eid}}`);
      if (cardEl) focusEntity(eid, cardEl);
    }});
  }});

  // re-draw line on window resize
  window.addEventListener('resize', clearLine);
</script>
</body>
</html>
"""
