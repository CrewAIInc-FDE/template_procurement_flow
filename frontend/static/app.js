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
    manage: "Manage", manage_title: "Manage portal",
    tab_people: "People", tab_policy: "Policy", tab_products: "Products", tab_suppliers: "Suppliers",
    people_help: "The people who submit requests. Each approval limit is sent to the AI, which flags requests above it.",
    add_person: "Add person", edit: "Edit", del: "Delete", save: "Save", cancel: "Cancel", saved: "Saved",
    f_name: "Name", f_email: "Email", f_role: "Role", f_department: "Department", f_limit: "Approval limit (USD)",
    th_person: "Person", th_role: "Role", th_limit: "Limit", th_product: "Product", th_category: "Category",
    th_price: "Unit price", th_supplier: "Supplier", th_location: "Location", th_ontime: "On-time", th_categories: "Categories",
    policy_help: "Requests whose sourced total exceeds this threshold require human review — even from an approver within their own limit.",
    limit_label: "Auto-approve threshold (USD)",
    readonly_note: "Backend-controlled — managed in the deployment",
    products_help: "Catalog the AI matches requests against.",
    suppliers_help: "Vendors the AI sources from.",
    confirm_del_person: "Remove this person?",
    del_person_error: "Couldn't remove — this persona has requests on the board.",
    save_error: "Couldn't save. Check the fields and try again.",
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
    manage: "Gestionar", manage_title: "Gestionar portal",
    tab_people: "Personas", tab_policy: "Política", tab_products: "Productos", tab_suppliers: "Proveedores",
    people_help: "Las personas que envían solicitudes. Cada límite de aprobación se envía a la IA, que marca las solicitudes que lo superan.",
    add_person: "Agregar persona", edit: "Editar", del: "Eliminar", save: "Guardar", cancel: "Cancelar", saved: "Guardado",
    f_name: "Nombre", f_email: "Correo", f_role: "Cargo", f_department: "Departamento", f_limit: "Límite de aprobación (USD)",
    th_person: "Persona", th_role: "Cargo", th_limit: "Límite", th_product: "Producto", th_category: "Categoría",
    th_price: "Precio unit.", th_supplier: "Proveedor", th_location: "Ubicación", th_ontime: "A tiempo", th_categories: "Categorías",
    policy_help: "Las solicitudes cuyo total cotizado supera este umbral requieren revisión humana — incluso de un aprobador dentro de su propio límite.",
    limit_label: "Umbral de auto-aprobación (USD)",
    readonly_note: "Controlado por el backend — se gestiona en el deployment",
    products_help: "Catálogo con el que la IA compara las solicitudes.",
    suppliers_help: "Proveedores desde los que cotiza la IA.",
    confirm_del_person: "¿Eliminar esta persona?",
    del_person_error: "No se pudo eliminar — esta persona tiene solicitudes en el tablero.",
    save_error: "No se pudo guardar. Revisa los campos e intenta de nuevo.",
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
    manage: "Gerenciar", manage_title: "Gerenciar portal",
    tab_people: "Pessoas", tab_policy: "Política", tab_products: "Produtos", tab_suppliers: "Fornecedores",
    people_help: "As pessoas que enviam pedidos. Cada limite de aprovação é enviado à IA, que sinaliza pedidos acima dele.",
    add_person: "Adicionar pessoa", edit: "Editar", del: "Excluir", save: "Salvar", cancel: "Cancelar", saved: "Salvo",
    f_name: "Nome", f_email: "E-mail", f_role: "Cargo", f_department: "Departamento", f_limit: "Limite de aprovação (USD)",
    th_person: "Pessoa", th_role: "Cargo", th_limit: "Limite", th_product: "Produto", th_category: "Categoria",
    th_price: "Preço unit.", th_supplier: "Fornecedor", th_location: "Local", th_ontime: "No prazo", th_categories: "Categorias",
    policy_help: "Pedidos cujo total cotado excede este limite exigem revisão humana — mesmo de um aprovador dentro do próprio limite.",
    limit_label: "Limite de auto-aprovação (USD)",
    readonly_note: "Controlado pelo backend — gerenciado no deployment",
    products_help: "Catálogo com o qual a IA compara os pedidos.",
    suppliers_help: "Fornecedores dos quais a IA cota.",
    confirm_del_person: "Remover esta pessoa?",
    del_person_error: "Não foi possível remover — esta pessoa tem pedidos no quadro.",
    save_error: "Não foi possível salvar. Verifique os campos e tente de novo.",
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

let employees = (window.EMPLOYEES || []).slice();
let personaId = localStorage.getItem("crewai_persona");
if (!employees.some((e) => e.id === personaId)) personaId = employees[0]?.id;

const initials = (name) => (name || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();

async function refreshEmployees() {
  try {
    employees = await api("/api/employees");
    if (!employees.some((e) => e.id === personaId)) {
      personaId = employees[0]?.id;
      if (personaId) localStorage.setItem("crewai_persona", personaId);
    }
    renderPersona();
  } catch { /* keep current list */ }
}

function renderPersona() {
  const emp = employees.find((e) => e.id === personaId);
  if (!emp) return;
  $("#persona-avatar").textContent = initials(emp.name);
  $("#persona-name").textContent = emp.name;
  $("#persona-role").textContent = `${emp.role} · ${emp.department}`;
  $("#persona-menu").innerHTML = employees.map((e) => `
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

/* --------------------------------------------------------------- manage */

let manageTab = "people";
let manageOpen = false;
let empForm = undefined;      // undefined = hidden, null = adding, id = editing
let settingsCache = null;
let catalogCache = null;
let suppliersCache = null;

function fieldRow(name, key, val, type) {
  const attr = type === "num" ? 'inputmode="numeric" step="1" min="0" type="number"' : 'type="text"';
  return `<div class="field${key === "name" || key === "email" ? " wide" : ""}">
    <label for="ef-${key}">${esc(t(name))}</label>
    <input id="ef-${key}" data-ef="${key}" ${attr} value="${esc(val ?? "")}">
  </div>`;
}

function peopleSection() {
  const rows = employees.map((e) => `
    <tr>
      <td><strong>${esc(e.name)}</strong><span class="sub">${esc(e.email || "")}</span></td>
      <td>${esc(e.role || "")}<span class="sub">${esc(e.department || "")}</span></td>
      <td class="num"><span class="limit-badge">${esc(fmtUSD(e.approval_limit_usd))}</span></td>
      <td><div class="row-actions">
        <button class="icon-btn" data-emp-edit="${esc(e.id)}" aria-label="${esc(t("edit"))}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
        </button>
        <button class="icon-btn danger" data-emp-del="${esc(e.id)}" aria-label="${esc(t("del"))}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/></svg>
        </button>
      </div></td>
    </tr>`).join("");

  let form = "";
  if (empForm !== undefined) {
    const e = empForm ? employees.find((x) => x.id === empForm) || {} : {};
    form = `<form class="admin-form" id="emp-form">
      ${fieldRow("f_name", "name", e.name)}
      ${fieldRow("f_email", "email", e.email)}
      ${fieldRow("f_role", "role", e.role)}
      ${fieldRow("f_department", "department", e.department)}
      ${fieldRow("f_limit", "approval_limit_usd", e.approval_limit_usd ?? 0, "num")}
      <div class="form-actions">
        <button type="submit" class="btn btn-approve btn-small">${esc(t("save"))}</button>
        <button type="button" class="btn btn-ghost btn-small" id="emp-cancel">${esc(t("cancel"))}</button>
      </div>
    </form>`;
  }

  return `<p class="admin-help">${esc(t("people_help"))}</p>
    <table class="admin-table">
      <thead><tr><th>${esc(t("th_person"))}</th><th>${esc(t("th_role"))}</th><th class="num">${esc(t("th_limit"))}</th><th></th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    ${empForm === undefined ? `<div class="form-actions"><button class="btn btn-approve btn-small" id="emp-add">+ ${esc(t("add_person"))}</button></div>` : form}`;
}

function policySection() {
  const v = settingsCache ? settingsCache.auto_approve_limit_usd : "";
  return `<p class="admin-help">${esc(t("policy_help"))}</p>
    <form class="admin-form settings-form" id="settings-form">
      <div class="field">
        <label for="sf-limit">${esc(t("limit_label"))}</label>
        <input id="sf-limit" type="number" inputmode="numeric" min="0" step="1000" value="${esc(v)}">
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-approve btn-small">${esc(t("save"))}</button>
        <span class="field-hint" id="settings-saved" hidden>${esc(t("saved"))} ✓</span>
      </div>
    </form>`;
}

function productsSection() {
  if (!catalogCache) return `<p class="admin-help">…</p>`;
  const rows = catalogCache.map((c) => `
    <tr><td><strong>${esc(c.name)}</strong><span class="sub">${esc(c.sku || "")}</span></td>
    <td>${esc(c.category || "")}</td>
    <td class="num">${esc(fmtUSD(c.unit_price_usd))}</td></tr>`).join("");
  return `<span class="readonly-note">${esc(t("readonly_note"))}</span>
    <p class="admin-help">${esc(t("products_help"))}</p>
    <table class="admin-table">
      <thead><tr><th>${esc(t("th_product"))}</th><th>${esc(t("th_category"))}</th><th class="num">${esc(t("th_price"))}</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
}

function suppliersSection() {
  if (!suppliersCache) return `<p class="admin-help">…</p>`;
  const rows = suppliersCache.map((s) => {
    const rate = s.on_time_delivery_rate != null
      ? `${Math.round(s.on_time_delivery_rate * (s.on_time_delivery_rate <= 1 ? 100 : 1))}%` : "";
    return `<tr><td><strong>${esc(s.name)}</strong></td>
      <td>${esc((s.categories || []).join(", "))}</td>
      <td>${esc(s.location || "")}</td>
      <td class="num">${esc(rate)}</td></tr>`;
  }).join("");
  return `<span class="readonly-note">${esc(t("readonly_note"))}</span>
    <p class="admin-help">${esc(t("suppliers_help"))}</p>
    <table class="admin-table">
      <thead><tr><th>${esc(t("th_supplier"))}</th><th>${esc(t("th_categories"))}</th><th>${esc(t("th_location"))}</th><th class="num">${esc(t("th_ontime"))}</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
}

function renderManage() {
  const tabs = [["people", "tab_people"], ["policy", "tab_policy"], ["products", "tab_products"], ["suppliers", "tab_suppliers"]];
  const body = { people: peopleSection, policy: policySection, products: productsSection, suppliers: suppliersSection }[manageTab]();
  $("#manage-inner").innerHTML = `
    <div class="drawer-top">
      <span class="pr-mono" id="manage-title">${esc(t("manage_title").toUpperCase())}</span>
      <button class="drawer-close" id="manage-close" aria-label="${esc(t("cancel"))}">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>
    </div>
    <div class="admin-tabs">${tabs.map(([id, key]) =>
      `<button class="admin-tab${id === manageTab ? " active" : ""}" data-tab="${id}">${esc(t(key))}</button>`).join("")}</div>
    <div id="manage-body">${body}</div>`;
  bindManage();
}

function bindManage() {
  $("#manage-close").addEventListener("click", closeManage);
  document.querySelectorAll("[data-tab]").forEach((b) =>
    b.addEventListener("click", () => { manageTab = b.dataset.tab; empForm = undefined; loadTab(); }));

  document.querySelectorAll("[data-emp-edit]").forEach((b) =>
    b.addEventListener("click", () => { empForm = b.dataset.empEdit; renderManage(); }));
  document.querySelectorAll("[data-emp-del]").forEach((b) =>
    b.addEventListener("click", () => deletePerson(b.dataset.empDel)));
  $("#emp-add")?.addEventListener("click", () => { empForm = null; renderManage(); });
  $("#emp-cancel")?.addEventListener("click", () => { empForm = undefined; renderManage(); });
  $("#emp-form")?.addEventListener("submit", savePerson);
  $("#settings-form")?.addEventListener("submit", saveSettings);
}

function readEmpForm() {
  const out = {};
  document.querySelectorAll("#emp-form [data-ef]").forEach((i) => { out[i.dataset.ef] = i.value.trim(); });
  return out;
}

async function savePerson(ev) {
  ev.preventDefault();
  const data = readEmpForm();
  if (!data.name) return toast(t("save_error"), true);
  const editing = empForm;  // id or null
  try {
    if (editing) await api(`/api/employees/${editing}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    else await api("/api/employees", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    empForm = undefined;
    await refreshEmployees();
    renderManage();
  } catch { toast(t("save_error"), true); }
}

async function deletePerson(id) {
  if (!window.confirm(t("confirm_del_person"))) return;
  try {
    await api(`/api/employees/${id}`, { method: "DELETE" });
    await refreshEmployees();
    renderManage();
  } catch { toast(t("del_person_error"), true); }
}

async function saveSettings(ev) {
  ev.preventDefault();
  const val = $("#sf-limit").value;
  try {
    settingsCache = await api("/api/settings", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ auto_approve_limit_usd: val }) });
    const s = $("#settings-saved"); if (s) { s.hidden = false; setTimeout(() => { s.hidden = true; }, 2500); }
  } catch { toast(t("save_error"), true); }
}

async function loadTab() {
  renderManage();  // paint immediately (may show placeholder)
  try {
    if (manageTab === "policy" && !settingsCache) settingsCache = await api("/api/settings");
    else if (manageTab === "products" && !catalogCache) catalogCache = await api("/api/catalog");
    else if (manageTab === "suppliers" && !suppliersCache) suppliersCache = await api("/api/suppliers");
    else return;
    renderManage();
  } catch { /* leave placeholder */ }
}

function openManage() {
  manageOpen = true;
  $("#manage-drawer").hidden = false;
  $("#manage-scrim").hidden = false;
  refreshEmployees().then(loadTab).then(() => $("#manage-close")?.focus());
}

function closeManage() {
  manageOpen = false;
  $("#manage-drawer").hidden = true;
  $("#manage-scrim").hidden = true;
}

/* ---------------------------------------------------------------- setup */

function applyLang() {
  document.documentElement.lang = lang;
  localStorage.setItem("crewai_lang", lang);
  document.querySelectorAll(".lang-btn").forEach((b) => b.classList.toggle("active", b.dataset.lang === lang));
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = t(el.dataset.i18nTitle); });
  $("#board-title").innerHTML = t("title");
  $("#chat-text").placeholder = t("chat_placeholder");
  renderPersona();
  renderBoard();
  lastDetailJson = "";
  if (openPr) refreshDetail();
  if (manageOpen) renderManage();
}

document.addEventListener("click", (ev) => {
  const card = ev.target.closest(".card[data-pr]");
  if (card) openDrawer(card.dataset.pr);
});
document.addEventListener("keydown", (ev) => {
  if (ev.key !== "Escape") return;
  if (manageOpen) closeManage();
  else if (openPr) closeDrawer();
});
$("#drawer-scrim").addEventListener("click", closeDrawer);
$("#manage-scrim").addEventListener("click", closeManage);
$("#manage-btn").addEventListener("click", openManage);
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
