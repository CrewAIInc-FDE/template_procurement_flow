/* Procurement Portal — board polling, drawer, chat widget, persona + i18n.
   No frameworks: the whole portal is one polled JSON endpoint rendered here. */

"use strict";

/* ------------------------------------------------------------------ i18n */

const I18N = {
  en: {
    wordmark_em: "Portal",
    board_label: "LIVE PIPELINE",
    title: 'Purchase requests, <em>live</em>',
    subtitle: "Open a request in chat, collect supplier quotes by email, then review and adjust the proposed awards before purchase orders are generated.",
    col_awaiting: "Awaiting Quotes", col_review: "Quote Review", col_complete: "Complete",
    empty_awaiting: "NO REQUESTS AWAITING QUOTES", empty_review: "NOTHING TO REVIEW", empty_complete: "NOTHING COMPLETED YET",
    st_submitted: "Structuring", st_awaiting_quotes: "Awaiting quotes", st_reviewing_quotes: "Reviewing quotes", st_awaiting_review: "Awaiting review",
    st_approved: "Approved", st_rejected: "Rejected",
    phase_screening: "Screening", phase_gmail: "Scanning Gmail", phase_approval: "Applying decision",
    alerts_n: "alerts", alert_1: "alert", sev_high: "High", sev_medium: "Medium",
    urgency_high: "Urgent",
    requested_by: "Requested by",
    sec_items: "Line items", sec_screening: "Screening", sec_quotes: "Quote proposal",
    sec_alerts: "Alerts", sec_documents: "Purchase orders", sec_review: "Human review", sec_warnings: "Quote warnings",
    th_item: "Item", th_qty: "Qty", th_unit: "Unit", th_total: "Total",
    estimated_total: "Estimated total", intake_wait: "STRUCTURING REQUEST…",
    unmatched: "Not matched to the catalog:",
    verdict_pass: "Pass", verdict_flag: "Flagged", verdict_reject: "Reject",
    confidence: "confidence", runner_up: "Runner-up", risks: "Risks",
    review_prompt: "Review the suggested supplier for each covered item. You can change any selection before approving.",
    approve: "Approve", reject: "Reject", decision_sent: "DECISION SENT — RESUMING FLOW…",
    review_quotes: "Review quotes", review_started: "SCANNING THE INBOX FOR THIS PR…",
    th_supplier_choice: "Supplier / quote", th_price_score: "Price", th_delivery: "Delivery", th_delivery_score: "Speed", th_score: "Score",
    cheapest: "Least price", fastest: "Fastest", days: "days", no_risks: "No recorded risks", outstanding: "Still awaiting quotes",
    confirm_reject: "Reject this purchase request?",
    chat_title: "Procurement assistant", chat_status: "online",
    chat_intro: "Hi, I'm your procurement assistant — describe what you need and why.",
    chat_ack: "{pr} opened and awaiting quotes.",
    chat_placeholder: "Describe what you need…",
    chat_onboard: "Open request",
    submit_error: "Could not submit the request — is the server up?",
    decide_error: "Could not deliver the decision. Try again.",
    manage: "Manage", manage_title: "Manage portal",
    tab_people: "People", tab_policy: "Policy", tab_products: "Products", tab_suppliers: "Suppliers",
    people_help: "The people who submit requests. Each approval limit is sent to the AI, which flags requests above it.",
    add_person: "Add person", edit: "Edit", del: "Delete", save: "Save", cancel: "Cancel", saved: "Saved",
    f_name: "Name", f_email: "Email", f_role: "Role", f_department: "Department", f_limit: "Approval limit (USD)",
    th_person: "Person", th_role: "Role", th_limit: "Limit", th_product: "Product", th_category: "Category",
    th_price: "Unit price", th_supplier: "Supplier", th_location: "Location", th_ontime: "On-time", th_categories: "Categories",
    policy_help: "Required conversion rate used to compare CLP and USD quote lines. Quote scoring stays fixed at 50% price and 50% delivery.",
    limit_label: "CLP per USD",
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
    subtitle: "Abre una solicitud en el chat, recibe cotizaciones por correo y luego revisa y ajusta la propuesta antes de generar las órdenes de compra.",
    col_awaiting: "Esperando cotizaciones", col_review: "Revisión de cotizaciones", col_complete: "Completas",
    empty_awaiting: "SIN SOLICITUDES ESPERANDO COTIZACIÓN", empty_review: "NADA PARA REVISAR", empty_complete: "NADA COMPLETADO AÚN",
    st_submitted: "Estructurando", st_awaiting_quotes: "Esperando cotizaciones", st_reviewing_quotes: "Revisando cotizaciones", st_awaiting_review: "Esperando revisión",
    st_approved: "Aprobada", st_rejected: "Rechazada",
    phase_screening: "Evaluando", phase_gmail: "Revisando Gmail", phase_approval: "Aplicando decisión",
    alerts_n: "alertas", alert_1: "alerta", sev_high: "Alta", sev_medium: "Media",
    urgency_high: "Urgente",
    requested_by: "Solicitado por",
    sec_items: "Ítems", sec_screening: "Evaluación", sec_quotes: "Propuesta de compra",
    sec_alerts: "Alertas", sec_documents: "Órdenes de compra", sec_review: "Revisión humana", sec_warnings: "Alertas de cotización",
    th_item: "Ítem", th_qty: "Cant.", th_unit: "Unitario", th_total: "Total",
    estimated_total: "Total estimado", intake_wait: "ESTRUCTURANDO SOLICITUD…",
    unmatched: "Sin match en el catálogo:",
    verdict_pass: "Aprobada", verdict_flag: "Con alertas", verdict_reject: "Rechazada",
    confidence: "confianza", runner_up: "Alternativa", risks: "Riesgos",
    review_prompt: "Revisa el proveedor sugerido para cada ítem cubierto. Puedes cambiar cualquier selección antes de aprobar.",
    approve: "Aprobar", reject: "Rechazar", decision_sent: "DECISIÓN ENVIADA — RETOMANDO FLUJO…",
    review_quotes: "Revisar cotizaciones", review_started: "REVISANDO EL BUZÓN PARA ESTA PR…",
    th_supplier_choice: "Proveedor / cotización", th_price_score: "Precio", th_delivery: "Entrega", th_delivery_score: "Rapidez", th_score: "Puntaje",
    cheapest: "Menor precio", fastest: "Más rápida", days: "días", no_risks: "Sin riesgos registrados", outstanding: "Aún esperando cotizaciones",
    confirm_reject: "¿Rechazar esta solicitud de compra?",
    chat_title: "Asistente de compras", chat_status: "en línea",
    chat_intro: "¡Hola! Soy tu asistente de compras — cuéntame qué necesitas y para qué.",
    chat_ack: "{pr} fue abierta y está esperando cotizaciones.",
    chat_placeholder: "Describe lo que necesitas…",
    chat_onboard: "Abrir solicitud",
    submit_error: "No se pudo enviar la solicitud — ¿está activo el servidor?",
    decide_error: "No se pudo entregar la decisión. Intenta de nuevo.",
    manage: "Gestionar", manage_title: "Gestionar portal",
    tab_people: "Personas", tab_policy: "Política", tab_products: "Productos", tab_suppliers: "Proveedores",
    people_help: "Las personas que envían solicitudes. Cada límite de aprobación se envía a la IA, que marca las solicitudes que lo superan.",
    add_person: "Agregar persona", edit: "Editar", del: "Eliminar", save: "Guardar", cancel: "Cancelar", saved: "Guardado",
    f_name: "Nombre", f_email: "Correo", f_role: "Cargo", f_department: "Departamento", f_limit: "Límite de aprobación (USD)",
    th_person: "Persona", th_role: "Cargo", th_limit: "Límite", th_product: "Producto", th_category: "Categoría",
    th_price: "Precio unit.", th_supplier: "Proveedor", th_location: "Ubicación", th_ontime: "A tiempo", th_categories: "Categorías",
    policy_help: "Tipo de cambio obligatorio para comparar cotizaciones en CLP y USD. El puntaje queda fijo en 50% precio y 50% entrega.",
    limit_label: "CLP por USD",
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
    subtitle: "Abra um pedido no chat, receba cotações por e-mail e depois revise e ajuste a proposta antes de gerar as ordens de compra.",
    col_awaiting: "Aguardando cotações", col_review: "Revisão de cotações", col_complete: "Concluídos",
    empty_awaiting: "SEM PEDIDOS AGUARDANDO COTAÇÃO", empty_review: "NADA PARA REVISAR", empty_complete: "NADA CONCLUÍDO AINDA",
    st_submitted: "Estruturando", st_awaiting_quotes: "Aguardando cotações", st_reviewing_quotes: "Revisando cotações", st_awaiting_review: "Aguardando revisão",
    st_approved: "Aprovado", st_rejected: "Rejeitado",
    phase_screening: "Avaliando", phase_gmail: "Lendo Gmail", phase_approval: "Aplicando decisão",
    alerts_n: "alertas", alert_1: "alerta", sev_high: "Alta", sev_medium: "Média",
    urgency_high: "Urgente",
    requested_by: "Solicitado por",
    sec_items: "Itens", sec_screening: "Avaliação", sec_quotes: "Proposta de compra",
    sec_alerts: "Alertas", sec_documents: "Ordens de compra", sec_review: "Revisão humana", sec_warnings: "Alertas de cotação",
    th_item: "Item", th_qty: "Qtd.", th_unit: "Unitário", th_total: "Total",
    estimated_total: "Total estimado", intake_wait: "ESTRUTURANDO PEDIDO…",
    unmatched: "Sem correspondência no catálogo:",
    verdict_pass: "Aprovado", verdict_flag: "Com alertas", verdict_reject: "Rejeitado",
    confidence: "confiança", runner_up: "Alternativa", risks: "Riscos",
    review_prompt: "Revise o fornecedor sugerido para cada item coberto. Você pode alterar qualquer seleção antes de aprovar.",
    approve: "Aprovar", reject: "Rejeitar", decision_sent: "DECISÃO ENVIADA — RETOMANDO FLUXO…",
    review_quotes: "Revisar cotações", review_started: "LENDO A CAIXA DE ENTRADA PARA ESTA PR…",
    th_supplier_choice: "Fornecedor / cotação", th_price_score: "Preço", th_delivery: "Entrega", th_delivery_score: "Rapidez", th_score: "Pontuação",
    cheapest: "Menor preço", fastest: "Mais rápida", days: "dias", no_risks: "Sem riscos registrados", outstanding: "Ainda aguardando cotações",
    confirm_reject: "Rejeitar este pedido de compra?",
    chat_title: "Assistente de compras", chat_status: "online",
    chat_intro: "Olá! Sou seu assistente de compras — descreva o que você precisa e por quê.",
    chat_ack: "{pr} foi aberto e está aguardando cotações.",
    chat_placeholder: "Descreva o que você precisa…",
    chat_onboard: "Abrir pedido",
    submit_error: "Não foi possível enviar o pedido — o servidor está no ar?",
    decide_error: "Não foi possível entregar a decisão. Tente de novo.",
    manage: "Gerenciar", manage_title: "Gerenciar portal",
    tab_people: "Pessoas", tab_policy: "Política", tab_products: "Produtos", tab_suppliers: "Fornecedores",
    people_help: "As pessoas que enviam pedidos. Cada limite de aprovação é enviado à IA, que sinaliza pedidos acima dele.",
    add_person: "Adicionar pessoa", edit: "Editar", del: "Excluir", save: "Salvar", cancel: "Cancelar", saved: "Salvo",
    f_name: "Nome", f_email: "E-mail", f_role: "Cargo", f_department: "Departamento", f_limit: "Limite de aprovação (USD)",
    th_person: "Pessoa", th_role: "Cargo", th_limit: "Limite", th_product: "Produto", th_category: "Categoria",
    th_price: "Preço unit.", th_supplier: "Fornecedor", th_location: "Local", th_ontime: "No prazo", th_categories: "Categorias",
    policy_help: "Câmbio obrigatório para comparar cotações em CLP e USD. A pontuação permanece fixa em 50% preço e 50% entrega.",
    limit_label: "CLP por USD",
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

const fmtMoney = (n, currency) => n == null ? "" :
  new Intl.NumberFormat(lang === "en" ? "en-US" : lang === "es" ? "es-CL" : "pt-BR",
    { style: "currency", currency, maximumFractionDigits: currency === "CLP" ? 0 : 2 }).format(n);

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
  if (!res.ok) {
    let message = `${res.status}`;
    try { message = (await res.json()).error || message; } catch { /* non-JSON error */ }
    throw new Error(message);
  }
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

const COLS = {
  submitted: "awaiting", awaiting_quotes: "awaiting",
  reviewing_quotes: "review", awaiting_review: "review",
  approved: "complete", rejected: "complete",
};
let lastBoardJson = "";
let board = [];
const prevStatus = {};
const decisionSent = {};

function chipStatus(r) {
  const dot = (r.status === "submitted" || r.status === "reviewing_quotes")
    ? '<span class="blink-dot" aria-hidden="true"></span>' : "";
  return `<span class="chip chip-status-${r.status}">${dot}${esc(t("st_" + r.status))}</span>`;
}

function cardHtml(r) {
  const summary = r.justification || r.raw_message || "";
  const badges = [];
  if (r.status === "reviewing_quotes" && r.phase)
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
  const byCol = { awaiting: [], review: [], complete: [] };
  for (const r of board) (byCol[COLS[r.status]] || byCol.awaiting).push(r);
  for (const col of ["awaiting", "review", "complete"]) {
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

function quoteBadges(option) {
  return [
    option.is_cheapest ? `<span class="quote-marker">${esc(t("cheapest"))}</span>` : "",
    option.is_fastest ? `<span class="quote-marker">${esc(t("fastest"))}</span>` : "",
  ].join("");
}

function quoteReviewHtml(review, actionable) {
  if (!review?.lines?.length) return "";
  const rows = review.lines.map((line) => {
    const selected = line.options.find((o) => o.quote_id === line.suggested_quote_id) || line.options[0];
    const options = line.options.map((o) => `<option value="${esc(o.quote_id)}"${o.quote_id === selected.quote_id ? " selected" : ""}>
      ${esc(o.supplier_name)} · ${esc(o.quote_id)} · ${esc(o.total_score.toFixed(1))}
    </option>`).join("");
    const risks = selected.risk_notes?.length ? selected.risk_notes.join(" · ") : t("no_risks");
    return `<tr class="quote-main" data-quote-row="${line.request_item_id}">
      <td><strong>${esc(line.item_name)}</strong><span class="items-sku">${esc(line.sku || line.catalog_item_id)} · ${line.quantity}</span></td>
      <td><select class="quote-select" data-award-item="${line.request_item_id}" ${actionable ? "" : "disabled"}>${options}</select></td>
      <td class="num" data-metric="price">${esc(fmtMoney(selected.line_total, selected.currency))}<span class="items-sku">${esc(fmtUSD(selected.line_total_usd))}</span></td>
      <td class="num" data-metric="price-score">${esc(selected.price_score.toFixed(1))}</td>
      <td class="num" data-metric="delivery">${selected.delivery_days} ${esc(t("days"))}</td>
      <td class="num" data-metric="delivery-score">${esc(selected.delivery_score.toFixed(1))}</td>
      <td class="num quote-score" data-metric="score">${esc(selected.total_score.toFixed(1))}</td>
    </tr>
    <tr class="quote-context" data-quote-context="${line.request_item_id}"><td colspan="7">
      <span data-metric="markers">${quoteBadges(selected)}</span>
      <span class="quote-risks" data-metric="risks">${esc(risks)}</span>
    </td></tr>`;
  }).join("");
  return `<div class="quote-table-wrap"><table class="quote-table">
    <thead><tr><th>${esc(t("th_item"))}</th><th>${esc(t("th_supplier_choice"))}</th><th class="num">${esc(t("th_total"))}</th><th class="num">${esc(t("th_price_score"))}</th><th class="num">${esc(t("th_delivery"))}</th><th class="num">${esc(t("th_delivery_score"))}</th><th class="num">${esc(t("th_score"))}</th></tr></thead>
    <tbody>${rows}</tbody>
  </table></div>`;
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

  if (d.status === "awaiting_quotes") {
    parts.push(`<div class="section">${sectionHead(t("sec_review"))}<div class="review-box">
      <p>${d.outstanding_items?.length} ${esc(t("outstanding"))}</p>
      <button class="btn btn-approve" data-review-quotes>${esc(t("review_quotes"))}</button>
    </div></div>`);
  } else if (d.status === "reviewing_quotes") {
    parts.push(`<div class="section">${sectionHead(t("sec_review"))}<div class="review-box">
      <div class="decision-note"><span class="spinner" aria-hidden="true"></span>${esc(t("review_started"))}</div>
    </div></div>`);
  }

  if (d.status === "awaiting_review") {
    parts.push(`<div class="section">${sectionHead(t("sec_review"))}
      <div class="review-box">`);
    if (d.pending_review && !decisionSent[d.pr_number]) {
      parts.push(`<p>${esc(t("review_prompt"))}</p>${quoteReviewHtml(d.quote_review, true)}
        <div class="review-actions">
          <button class="btn btn-approve" data-decide="approve">${esc(t("approve"))}</button>
          <button class="btn btn-reject" data-decide="reject">${esc(t("reject"))}</button>
        </div>`);
    } else {
      parts.push(`<div class="decision-note"><span class="spinner" aria-hidden="true"></span>${esc(t("decision_sent"))}</div>`);
    }
    parts.push(`</div></div>`);
  }

  parts.push(`<div class="section">${sectionHead(t("sec_items"))}`);
  if (d.items?.length) {
    const rows = d.items.map((it) => `
      <tr><td>${esc(it.name)}<span class="items-sku">${esc(it.catalog_item_id || "")}${it.sku ? " · " + esc(it.sku) : ""}${it.po_number ? " · " + esc(it.po_number) : ""}</span></td>
      <td class="num">${it.quantity}</td>
      <td class="num">${esc(fmtUSD(it.unit_price_usd))}</td>
      <td class="num">${esc(fmtUSD(it.line_total_usd))}${it.awarded_supplier ? `<span class="items-sku">${esc(it.awarded_supplier)}</span>` : ""}</td></tr>`).join("");
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

  if (d.screening) {
    const s = d.screening;
    parts.push(`<div class="section">${sectionHead(t("sec_screening"))}<div class="panel">
      <div class="verdict-row">${verdictChip(s.verdict)}</div>
      <p class="reasoning">${esc(s.reasoning || "")}</p>`);
    if (s.violations?.length) parts.push(`<ul class="fact-list bad">${s.violations.map((v) => `<li>${esc(v)}</li>`).join("")}</ul>`);
    if (s.anomalies?.length) parts.push(`<ul class="fact-list">${s.anomalies.map((v) => `<li>${esc(v)}</li>`).join("")}</ul>`);
    parts.push(`</div></div>`);
  }

  if (d.quote_review?.lines?.length && d.status !== "awaiting_review") {
    parts.push(`<div class="section">${sectionHead(t("sec_quotes"))}<div class="panel">${quoteReviewHtml(d.quote_review, false)}</div></div>`);
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

  if (d.purchase_orders?.length) {
    parts.push(`<div class="section">${sectionHead(t("sec_documents"))}${d.purchase_orders.map((po) =>
      `<div class="doc po-doc"><div class="po-meta">${esc(po.po_number)} · ${esc(po.supplier_name)}</div>${po.html}</div>`).join("")}</div>`);
  }
  if (d.status === "rejected" && d.rejection_note_html) {
    parts.push(`<div class="section">${sectionHead(t("sec_documents"))}<div class="doc">${d.rejection_note_html}</div></div>`);
  }

  return parts.join("");
}

function bindDrawer(d) {
  $("#drawer-close")?.addEventListener("click", closeDrawer);
  document.querySelectorAll("[data-award-item]").forEach((select) =>
    select.addEventListener("change", () => {
      const itemId = Number(select.dataset.awardItem);
      const line = d.quote_review?.lines?.find((candidate) => candidate.request_item_id === itemId);
      const option = line?.options?.find((candidate) => candidate.quote_id === select.value);
      const row = document.querySelector(`[data-quote-row="${itemId}"]`);
      const context = document.querySelector(`[data-quote-context="${itemId}"]`);
      if (!option || !row || !context) return;
      row.querySelector('[data-metric="price"]').innerHTML = `${esc(fmtMoney(option.line_total, option.currency))}<span class="items-sku">${esc(fmtUSD(option.line_total_usd))}</span>`;
      row.querySelector('[data-metric="price-score"]').textContent = option.price_score.toFixed(1);
      row.querySelector('[data-metric="delivery"]').textContent = `${option.delivery_days} ${t("days")}`;
      row.querySelector('[data-metric="delivery-score"]').textContent = option.delivery_score.toFixed(1);
      row.querySelector('[data-metric="score"]').textContent = option.total_score.toFixed(1);
      context.querySelector('[data-metric="markers"]').innerHTML = quoteBadges(option);
      context.querySelector('[data-metric="risks"]').textContent = option.risk_notes?.length ? option.risk_notes.join(" · ") : t("no_risks");
    }));
  $("[data-review-quotes]")?.addEventListener("click", async (ev) => {
    ev.currentTarget.disabled = true;
    try {
      await api(`/api/requests/${d.pr_number}/review-quotes`, { method: "POST" });
      lastDetailJson = "";
      await pollBoard();
      await refreshDetail();
    } catch (error) {
      ev.currentTarget.disabled = false;
      toast(error.message || t("decide_error"), true);
    }
  });
  document.querySelectorAll("[data-decide]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const action = btn.dataset.decide;
      if (action === "reject" && !window.confirm(t("confirm_reject"))) return;
      decisionSent[d.pr_number] = true;
      lastDetailJson = "";
      refreshDetail();
      try {
        const opts = { method: "POST", headers: { "Content-Type": "application/json" } };
        if (action === "approve") {
          opts.body = JSON.stringify({ awards: Array.from(document.querySelectorAll("[data-award-item]")).map((select) => ({
            request_item_id: Number(select.dataset.awardItem), quote_id: select.value,
          })) });
        } else {
          opts.body = "{}";
        }
        await api(`/api/requests/${d.pr_number}/${action}`, opts);
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

    api("/api/requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ employee_id: personaId, message }),
    }).then((res) => {
      typing.remove();
      msgEl("msg-bot", esc(t("chat_ack").replace("{pr}", res.pr_number)));
      const el = msgEl("msg-sys", `<span class="pr-link">${esc(res.pr_number)}</span> · ${esc(t("chat_onboard"))}`);
      el.querySelector(".pr-link").addEventListener("click", () => openDrawer(res.pr_number));
      pollBoard();
    }).catch(() => { typing.remove(); toast(t("submit_error"), true); });
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
  const v = settingsCache ? settingsCache.clp_per_usd ?? "" : "";
  return `<p class="admin-help">${esc(t("policy_help"))}</p>
    <form class="admin-form settings-form" id="settings-form">
      <div class="field">
        <label for="sf-limit">${esc(t("limit_label"))}</label>
        <input id="sf-limit" type="number" inputmode="decimal" min="0.01" step="0.01" required value="${esc(v)}">
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
    settingsCache = await api("/api/settings", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clp_per_usd: val }) });
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
