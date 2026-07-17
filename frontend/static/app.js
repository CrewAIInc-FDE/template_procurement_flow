/* Procurement Portal — board polling, drawer, chat widget, persona + i18n.
   No frameworks: the whole portal is one polled JSON endpoint rendered here. */

"use strict";

/* ------------------------------------------------------------------ i18n */

const I18N = {
  en: {
    wordmark_em: "Portal",
    board_label: "LIVE PIPELINE",
    title: 'Purchase requests, <em>live</em>',
    subtitle: "Describe what you need in the chat. AI agents structure, screen and source every request — escalations wait for a human decision right here on the board.",
    col_new: "New", col_processing: "Processing", col_done: "Done",
    empty_new: "NO NEW REQUESTS", empty_processing: "NOTHING IN FLIGHT", empty_done: "NOTHING DECIDED YET",
    st_submitted: "Submitted", st_in_triage: "In triage", st_awaiting_review: "Awaiting review",
    st_approved: "Approved", st_rejected: "Rejected",
    phase_screening: "Screening", phase_sourcing: "Sourcing",
    alerts_n: "alerts", alert_1: "alert", sev_high: "High", sev_medium: "Medium",
    urgency_high: "Urgent",
    requested_by: "Requested by",
    sec_items: "Line items", sec_screening: "Screening", sec_sourcing: "Sourcing",
    sec_alerts: "Alerts", sec_document: "Document", sec_review: "Human review", sec_memo: "Approval memo",
    th_item: "Item", th_qty: "Qty", th_unit: "Unit", th_total: "Total",
    estimated_total: "Estimated total", intake_wait: "STRUCTURING REQUEST…",
    unmatched: "Not matched to the catalog:",
    verdict_pass: "Pass", verdict_flag: "Flagged", verdict_reject: "Reject",
    confidence: "confidence", runner_up: "Runner-up", risks: "Key risks",
    review_prompt: "This request exceeds auto-approval policy. Approve to generate the purchase order, or reject it.",
    approve: "Approve", reject: "Reject", decision_sent: "DECISION SENT — RESUMING FLOW…",
    confirm_reject: "Reject this purchase request?",
    chat_title: "Procurement assistant", chat_status: "online",
    chat_intro: "Hi, I'm your procurement assistant — describe what you need and why.",
    chat_ack: "Thanks! Your request was submitted and is being processed — watch the board.",
    chat_placeholder: "Describe what you need…",
    chat_onboard: "on the board",
    submit_error: "Could not submit the request — is the server up?",
    decide_error: "Could not deliver the decision. Try again.",
  },
  es: {
    wordmark_em: "Portal",
    board_label: "PIPELINE EN VIVO",
    title: 'Solicitudes de compra, <em>en vivo</em>',
    subtitle: "Describe lo que necesitas en el chat. Los agentes de IA estructuran, evalúan y cotizan cada solicitud — las escaladas esperan una decisión humana aquí mismo en el tablero.",
    col_new: "Nuevas", col_processing: "En proceso", col_done: "Resueltas",
    empty_new: "SIN SOLICITUDES NUEVAS", empty_processing: "NADA EN CURSO", empty_done: "NADA RESUELTO AÚN",
    st_submitted: "Enviada", st_in_triage: "En análisis", st_awaiting_review: "Esperando revisión",
    st_approved: "Aprobada", st_rejected: "Rechazada",
    phase_screening: "Evaluando", phase_sourcing: "Cotizando",
    alerts_n: "alertas", alert_1: "alerta", sev_high: "Alta", sev_medium: "Media",
    urgency_high: "Urgente",
    requested_by: "Solicitado por",
    sec_items: "Ítems", sec_screening: "Evaluación", sec_sourcing: "Cotización",
    sec_alerts: "Alertas", sec_document: "Documento", sec_review: "Revisión humana", sec_memo: "Memo de aprobación",
    th_item: "Ítem", th_qty: "Cant.", th_unit: "Unitario", th_total: "Total",
    estimated_total: "Total estimado", intake_wait: "ESTRUCTURANDO SOLICITUD…",
    unmatched: "Sin match en el catálogo:",
    verdict_pass: "Aprobada", verdict_flag: "Con alertas", verdict_reject: "Rechazada",
    confidence: "confianza", runner_up: "Alternativa", risks: "Riesgos clave",
    review_prompt: "Esta solicitud excede la política de aprobación automática. Aprueba para generar la orden de compra, o recházala.",
    approve: "Aprobar", reject: "Rechazar", decision_sent: "DECISIÓN ENVIADA — RETOMANDO FLUJO…",
    confirm_reject: "¿Rechazar esta solicitud de compra?",
    chat_title: "Asistente de compras", chat_status: "en línea",
    chat_intro: "¡Hola! Soy tu asistente de compras — cuéntame qué necesitas y para qué.",
    chat_ack: "¡Gracias! Tu solicitud fue enviada y está siendo procesada — sigue el tablero.",
    chat_placeholder: "Describe lo que necesitas…",
    chat_onboard: "en el tablero",
    submit_error: "No se pudo enviar la solicitud — ¿está activo el servidor?",
    decide_error: "No se pudo entregar la decisión. Intenta de nuevo.",
  },
  pt: {
    wordmark_em: "Portal",
    board_label: "PIPELINE AO VIVO",
    title: 'Pedidos de compra, <em>ao vivo</em>',
    subtitle: "Descreva o que você precisa no chat. Agentes de IA estruturam, avaliam e cotam cada pedido — escalações aguardam uma decisão humana aqui mesmo no quadro.",
    col_new: "Novos", col_processing: "Em andamento", col_done: "Concluídos",
    empty_new: "SEM PEDIDOS NOVOS", empty_processing: "NADA EM ANDAMENTO", empty_done: "NADA CONCLUÍDO AINDA",
    st_submitted: "Enviado", st_in_triage: "Em análise", st_awaiting_review: "Aguardando revisão",
    st_approved: "Aprovado", st_rejected: "Rejeitado",
    phase_screening: "Avaliando", phase_sourcing: "Cotando",
    alerts_n: "alertas", alert_1: "alerta", sev_high: "Alta", sev_medium: "Média",
    urgency_high: "Urgente",
    requested_by: "Solicitado por",
    sec_items: "Itens", sec_screening: "Avaliação", sec_sourcing: "Cotação",
    sec_alerts: "Alertas", sec_document: "Documento", sec_review: "Revisão humana", sec_memo: "Memo de aprovação",
    th_item: "Item", th_qty: "Qtd.", th_unit: "Unitário", th_total: "Total",
    estimated_total: "Total estimado", intake_wait: "ESTRUTURANDO PEDIDO…",
    unmatched: "Sem correspondência no catálogo:",
    verdict_pass: "Aprovado", verdict_flag: "Com alertas", verdict_reject: "Rejeitado",
    confidence: "confiança", runner_up: "Alternativa", risks: "Riscos-chave",
    review_prompt: "Este pedido excede a política de aprovação automática. Aprove para gerar a ordem de compra, ou rejeite.",
    approve: "Aprovar", reject: "Rejeitar", decision_sent: "DECISÃO ENVIADA — RETOMANDO FLUXO…",
    confirm_reject: "Rejeitar este pedido de compra?",
    chat_title: "Assistente de compras", chat_status: "online",
    chat_intro: "Olá! Sou seu assistente de compras — descreva o que você precisa e por quê.",
    chat_ack: "Obrigado! Seu pedido foi enviado e está sendo processado — acompanhe o quadro.",
    chat_placeholder: "Descreva o que você precisa…",
    chat_onboard: "no quadro",
    submit_error: "Não foi possível enviar o pedido — o servidor está no ar?",
    decide_error: "Não foi possível entregar a decisão. Tente de novo.",
  },
};

let lang = localStorage.getItem("crewai_lang") || "en";
const t = (key) => (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;

/* ------------------------------------------------------------- utilities */

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const fmtUSD = (n) => n == null ? "" :
  new Intl.NumberFormat(lang === "en" ? "en-US" : lang === "es" ? "es-CL" : "pt-BR",
    { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

const rel = (iso) => {
  if (!iso) return "";
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  return m < 1 ? "now" : m < 60 ? `${m}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`;
};

const ALERT_SVG = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><path d="M12 9v4M12 17h.01"/></svg>';

function toast(msg, isError) {
  const el = document.createElement("div");
  el.className = "toast" + (isError ? " toast-error" : "");
  el.textContent = msg;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.status === 204 ? null : res.json();
}

/* -------------------------------------------------------------- persona */

const EMPLOYEES = window.EMPLOYEES || [];
let personaId = localStorage.getItem("crewai_persona");
if (!EMPLOYEES.some((e) => e.id === personaId)) personaId = EMPLOYEES[0]?.id;

const initials = (name) => name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();

function renderPersona() {
  const emp = EMPLOYEES.find((e) => e.id === personaId);
  if (!emp) return;
  $("#persona-avatar").textContent = initials(emp.name);
  $("#persona-name").textContent = emp.name;
  $("#persona-role").textContent = `${emp.role} · ${emp.department}`;
  $("#persona-menu").innerHTML = EMPLOYEES.map((e) => `
    <li><button class="persona-opt" role="option" data-id="${esc(e.id)}" aria-selected="${e.id === personaId}">
      <span class="avatar">${esc(initials(e.name))}</span>
      <span class="persona-id">
        <span class="persona-name">${esc(e.name)}</span>
        <span class="persona-role">${esc(e.role)}</span>
      </span>
      <span class="persona-limit">${fmtUSD(e.approval_limit_usd)}</span>
    </button></li>`).join("");
}

function setupPersona() {
  const btn = $("#persona-btn"), menu = $("#persona-menu");
  btn.addEventListener("click", () => {
    const open = menu.hidden;
    menu.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
  });
  menu.addEventListener("click", (ev) => {
    const opt = ev.target.closest(".persona-opt");
    if (!opt) return;
    personaId = opt.dataset.id;
    localStorage.setItem("crewai_persona", personaId);
    renderPersona();
    menu.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  });
  document.addEventListener("click", (ev) => {
    if (!$("#persona").contains(ev.target)) { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); }
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); }
  });
}

/* ---------------------------------------------------------------- board */

const COLS = { submitted: "new", in_triage: "processing", awaiting_review: "processing", approved: "done", rejected: "done" };
let lastBoardJson = "";
let board = [];
const prevStatus = {};
const decisionSent = {};

function chipStatus(r) {
  const dot = (r.status === "submitted" || r.status === "in_triage")
    ? '<span class="blink-dot" aria-hidden="true"></span>' : "";
  return `<span class="chip chip-status-${r.status}">${dot}${esc(t("st_" + r.status))}</span>`;
}

function cardHtml(r) {
  const summary = r.justification || r.raw_message || "";
  const badges = [];
  if (r.status === "in_triage" && r.phase)
    badges.push(`<span class="chip chip-phase"><span class="blink-dot"></span>${esc(t("phase_" + r.phase))}…</span>`);
  if (r.alerts_count > 0)
    badges.push(`<span class="chip chip-alerts">${ALERT_SVG}${r.alerts_count} ${esc(r.alerts_count === 1 ? t("alert_1") : t("alerts_n"))}</span>`);
  if (r.urgency === "high") badges.push(`<span class="chip chip-urgency-high">${esc(t("urgency_high"))}</span>`);
  if (r.detected_language) badges.push(`<span class="chip chip-lang">${esc(r.detected_language)}</span>`);
  return `
  <button class="card${r.status === "awaiting_review" ? " review" : ""}" data-pr="${esc(r.pr_number)}"
          aria-label="${esc(r.pr_number)} — ${esc(t("st_" + r.status))}">
    <div class="card-top">
      <span class="pr-mono">${esc(r.pr_number)}</span>
      ${chipStatus(r)}
      <span class="pr-mono" style="margin-left:auto">${esc(rel(r.created_at))}</span>
    </div>
    <p class="card-summary">${esc(summary)}</p>
    <div class="card-who">${esc(r.employee_name)} · ${esc(r.employee_role)}</div>
    <div class="card-foot">
      ${r.estimated_total_usd != null ? `<span class="card-total">${esc(fmtUSD(r.estimated_total_usd))}</span>` : ""}
      ${badges.join("")}
    </div>
  </button>`;
}

function renderBoard() {
  const byCol = { new: [], processing: [], done: [] };
  for (const r of board) (byCol[COLS[r.status]] || byCol.new).push(r);
  for (const col of ["new", "processing", "done"]) {
    const rows = byCol[col];
    $(`#count-${col}`).textContent = rows.length;
    $(`#col-${col}`).innerHTML = rows.length
      ? rows.map(cardHtml).join("")
      : `<div class="col-empty">${esc(t("empty_" + col))}</div>`;
  }
  for (const r of board) {
    if (prevStatus[r.pr_number] && prevStatus[r.pr_number] !== r.status) {
      const el = document.querySelector(`.card[data-pr="${r.pr_number}"]`);
      if (el) el.classList.add("flash");
      if (["approved", "rejected"].includes(r.status)) delete decisionSent[r.pr_number];
    }
    prevStatus[r.pr_number] = r.status;
  }
}

async function pollBoard() {
  try {
    const data = await api("/api/requests");
    const json = JSON.stringify(data);
    board = data;
    if (json !== lastBoardJson) {
      lastBoardJson = json;
      renderBoard();
    }
    if (openPr) refreshDetail();
  } catch { /* transient — next poll retries */ }
}

/* --------------------------------------------------------------- drawer */

let openPr = null;
let lastDetailJson = "";

function sectionHead(label) {
  return `<div class="section-head"><span class="section-pill"></span><span class="section-label">${esc(label)}</span></div>`;
}

function verdictChip(v) {
  const cls = { pass: "approved", flag: "awaiting_review", reject: "rejected" }[v] || "submitted";
  const label = { pass: t("verdict_pass"), flag: t("verdict_flag"), reject: t("verdict_reject") }[v] || v;
  return `<span class="chip chip-status-${cls}">${esc(label)}</span>`;
}

function detailHtml(d) {
  const summary = d.justification || d.raw_message || "";
  const parts = [];

  parts.push(`
    <div class="drawer-top">
      <span class="pr-mono" id="drawer-pr">${esc(d.pr_number)}</span>
      ${chipStatus(d)}
      <button class="drawer-close" id="drawer-close" aria-label="Close">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>
    </div>
    <h2 class="drawer-title">${esc(summary.length > 120 ? summary.slice(0, 117) + "…" : summary)}</h2>
    <p class="drawer-meta">${esc(t("requested_by"))} <strong>${esc(d.employee?.name || "")}</strong>
      <span class="sep">·</span>${esc(d.employee?.role || "")}
      <span class="sep">·</span><span class="mono">${esc(rel(d.created_at))}</span></p>`);

  /* review actions — the demo money shot goes first */
  if (d.status === "awaiting_review") {
    parts.push(`<div class="section">${sectionHead(t("sec_review"))}
      <div class="review-box">`);
    if (d.pending_review && !decisionSent[d.pr_number]) {
      parts.push(`<p>${esc(t("review_prompt"))}</p>
        <div class="review-actions">
          <button class="btn btn-approve" data-decide="approve">${esc(t("approve"))}</button>
          <button class="btn btn-reject" data-decide="reject">${esc(t("reject"))}</button>
        </div>`);
    } else {
      parts.push(`<div class="decision-note"><span class="spinner" aria-hidden="true"></span>${esc(t("decision_sent"))}</div>`);
    }
    parts.push(`</div></div>`);
  }

  /* line items */
  parts.push(`<div class="section">${sectionHead(t("sec_items"))}`);
  if (d.items?.length) {
    const rows = d.items.map((it) => `
      <tr><td>${esc(it.name)}<span class="items-sku">${esc(it.catalog_item_id || "")}${it.sku ? " · " + esc(it.sku) : ""}</span></td>
      <td class="num">${it.quantity}</td>
      <td class="num">${esc(fmtUSD(it.unit_price_usd))}</td>
      <td class="num">${esc(fmtUSD(it.line_total_usd))}</td></tr>`).join("");
    parts.push(`<div class="panel"><table class="items-table">
      <thead><tr><th>${esc(t("th_item"))}</th><th class="num">${esc(t("th_qty"))}</th><th class="num">${esc(t("th_unit"))}</th><th class="num">${esc(t("th_total"))}</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td colspan="3">${esc(t("estimated_total"))}</td><td class="num">${esc(fmtUSD(d.estimated_total_usd))}</td></tr></tfoot>
    </table>`);
    if (d.unmatched?.length)
      parts.push(`<div class="unmatched">${esc(t("unmatched"))}<ul>${d.unmatched.map((u) => `<li>${esc(u)}</li>`).join("")}</ul></div>`);
    parts.push(`</div>`);
  } else {
    parts.push(`<div class="panel panel-grey"><div class="decision-note"><span class="spinner" aria-hidden="true"></span>${esc(t("intake_wait"))}</div></div>`);
  }
  parts.push(`</div>`);

  /* screening */
  if (d.screening) {
    const s = d.screening;
    parts.push(`<div class="section">${sectionHead(t("sec_screening"))}<div class="panel">
      <div class="verdict-row">${verdictChip(s.verdict)}</div>
      <p class="reasoning">${esc(s.reasoning || "")}</p>`);
    if (s.violations?.length) parts.push(`<ul class="fact-list bad">${s.violations.map((v) => `<li>${esc(v)}</li>`).join("")}</ul>`);
    if (s.anomalies?.length) parts.push(`<ul class="fact-list">${s.anomalies.map((v) => `<li>${esc(v)}</li>`).join("")}</ul>`);
    parts.push(`</div></div>`);
  }

  /* sourcing */
  if (d.sourcing) {
    const s = d.sourcing;
    parts.push(`<div class="section">${sectionHead(t("sec_sourcing"))}<div class="panel">
      <div class="supplier-row">
        <span class="supplier-name">${esc(s.recommended_supplier)}</span>
        <span class="supplier-total">${esc(fmtUSD(s.total_cost_usd))}</span>
      </div>
      <div class="verdict-row"><span class="chip chip-lang">${esc(s.confidence)} ${esc(t("confidence"))}</span></div>
      ${s.runner_up ? `<p class="runner-up">${esc(t("runner_up"))}: ${esc(s.runner_up)}</p>` : ""}
      <p class="reasoning">${esc(s.rationale || "")}</p>
      ${s.key_risks?.length ? `<ul class="fact-list">${s.key_risks.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>` : ""}
    </div></div>`);
  }

  /* alerts */
  if (d.alerts?.length) {
    parts.push(`<div class="section">${sectionHead(t("sec_alerts"))}<div class="panel">
      ${d.alerts.map((a) => `<div class="alert-item">
        <span class="chip alert-sev ${a.severity === "high" ? "chip-status-rejected" : "chip-urgency-high"}"
          style="${a.severity !== "high" ? "background:var(--amber-soft);color:var(--amber)" : ""}">${esc(a.severity === "high" ? t("sev_high") : t("sev_medium"))}</span>
        <span>${esc(a.message)}</span></div>`).join("")}
    </div></div>`);
  }

  /* documents */
  const doc =
    d.status === "approved" && d.purchase_order_html ? d.purchase_order_html :
    d.status === "rejected" && d.rejection_note_html ? d.rejection_note_html :
    d.status === "awaiting_review" && d.escalation_memo_html ? d.escalation_memo_html : null;
  if (doc) {
    const label = d.status === "awaiting_review" ? t("sec_memo") : t("sec_document");
    parts.push(`<div class="section">${sectionHead(label)}<div class="doc">${doc}</div></div>`);
  }

  return parts.join("");
}

function bindDrawer(d) {
  $("#drawer-close")?.addEventListener("click", closeDrawer);
  document.querySelectorAll("[data-decide]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const action = btn.dataset.decide;
      if (action === "reject" && !window.confirm(t("confirm_reject"))) return;
      decisionSent[d.pr_number] = true;
      lastDetailJson = "";
      refreshDetail();
      try {
        await api(`/api/requests/${d.pr_number}/${action}`, { method: "POST" });
      } catch {
        delete decisionSent[d.pr_number];
        lastDetailJson = "";
        refreshDetail();
        toast(t("decide_error"), true);
      }
    }));
}

async function refreshDetail() {
  if (!openPr) return;
  try {
    const d = await api(`/api/requests/${openPr}`);
    const json = JSON.stringify(d);
    if (json === lastDetailJson) return;
    lastDetailJson = json;
    $("#drawer-inner").innerHTML = detailHtml(d);
    bindDrawer(d);
  } catch { /* transient */ }
}

function openDrawer(pr) {
  openPr = pr;
  lastDetailJson = "";
  $("#drawer").hidden = false;
  $("#drawer-scrim").hidden = false;
  refreshDetail().then(() => $("#drawer-close")?.focus());
}

function closeDrawer() {
  openPr = null;
  $("#drawer").hidden = true;
  $("#drawer-scrim").hidden = true;
}

/* ----------------------------------------------------------------- chat */

let chatStarted = false;

function msgEl(cls, html) {
  const el = document.createElement("div");
  el.className = `msg ${cls}`;
  el.innerHTML = html;
  $("#chat-body").appendChild(el);
  $("#chat-body").scrollTop = $("#chat-body").scrollHeight;
  return el;
}

function openChat() {
  $("#chat").hidden = false;
  $("#chat-fab").classList.add("hidden");
  if (!chatStarted) {
    chatStarted = true;
    msgEl("msg-bot", esc(t("chat_intro")));
  }
  $("#chat-text").focus();
}

function closeChat() {
  $("#chat").hidden = true;
  $("#chat-fab").classList.remove("hidden");
}

function setupChat() {
  $("#chat-fab").addEventListener("click", openChat);
  $("#chat-close").addEventListener("click", closeChat);
  const textarea = $("#chat-text");
  textarea.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); $("#chat-form").requestSubmit(); }
  });
  $("#chat-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const message = textarea.value.trim();
    if (!message) return;
    textarea.value = "";
    msgEl("msg-user", esc(message));
    const typing = msgEl("msg-bot", '<span class="typing"><i></i><i></i><i></i></span>');

    // The ack is canned and NEVER waits on the AI backend (see frontend-plan.md).
    setTimeout(() => { typing.remove(); msgEl("msg-bot", esc(t("chat_ack"))); }, 900);

    api("/api/requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ employee_id: personaId, message }),
    }).then((res) => setTimeout(() => {  // after the canned ack, never before
      const el = msgEl("msg-sys", `<span class="pr-link">${esc(res.pr_number)}</span> · ${esc(t("chat_onboard"))}`);
      el.querySelector(".pr-link").addEventListener("click", () => openDrawer(res.pr_number));
      pollBoard();
    }, 1000)).catch(() => toast(t("submit_error"), true));
  });
}

/* ---------------------------------------------------------------- setup */

function applyLang() {
  document.documentElement.lang = lang;
  localStorage.setItem("crewai_lang", lang);
  document.querySelectorAll(".lang-btn").forEach((b) => b.classList.toggle("active", b.dataset.lang === lang));
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("#board-title").innerHTML = t("title");
  $("#chat-text").placeholder = t("chat_placeholder");
  renderPersona();
  renderBoard();
  lastDetailJson = "";
  if (openPr) refreshDetail();
}

document.addEventListener("click", (ev) => {
  const card = ev.target.closest(".card[data-pr]");
  if (card) openDrawer(card.dataset.pr);
});
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && openPr) closeDrawer();
});
$("#drawer-scrim").addEventListener("click", closeDrawer);
$("#lang-switch").addEventListener("click", (ev) => {
  const btn = ev.target.closest(".lang-btn");
  if (btn) { lang = btn.dataset.lang; applyLang(); }
});

setupPersona();
setupChat();
applyLang();
fetch("/api/wakeup", { method: "POST" }).catch(() => {});
pollBoard();
setInterval(pollBoard, 3000);
