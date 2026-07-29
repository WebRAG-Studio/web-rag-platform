const state = {
  sites: [],
  active: null,
  view: "dashboard",
  session: crypto.randomUUID(),
  poller: null,
  speakAnswers: false,
};
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json", ...(options.headers || {})},
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({detail: "Request failed"}));
    throw new Error(typeof detail.detail === "string" ? detail.detail : "Request failed");
  }
  return response.status === 204 ? null : response.json();
}

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = String(value ?? "");
  return node.innerHTML;
}

function safeHttpUrl(value) {
  try {
    const url = new URL(String(value || ""), window.location.origin);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

function languageDirection(value) {
  return /[\u0600-\u06ff]/.test(String(value || "")) ? "rtl" : "ltr";
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "Not available";
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes} min ${Math.round(seconds % 60)} sec`;
}

function progressLabel(progress = {}) {
  if (progress.status === "complete") return "Completed";
  if (progress.status === "running") return progress.stage || "Crawling";
  if (progress.status === "indexing") return "Building index";
  return progress.status || "Queued";
}

function announce(message) {
  $("#announcer").textContent = message;
}

function renderSites() {
  const list = $("#site-list");
  if (!state.sites.length) {
    list.innerHTML = '<p class="empty-list">No assistants yet.</p>';
    return;
  }
  list.innerHTML = state.sites.map(site => `
    <button class="site-button ${site.site_id === state.active ? "active" : ""}" data-site="${escapeHtml(site.site_id)}">
      ${escapeHtml(site.site_name)}
      <small>${escapeHtml(progressLabel(site.progress))}</small>
    </button>`).join("");
}

function renderLanding() {
  state.active = null;
  state.view = "dashboard";
  stopPolling();
  document.documentElement.style.setProperty("--brand", "#0f766e");
  $("#workspace").innerHTML = `
    <div class="landing">
      <span class="eyebrow">SITEMIND LABS</span>
      <h1>Turn websites into intelligent, source-grounded assistants.</h1>
      <p class="lede">Turn public websites and documents into multilingual, citation-grounded AI assistants.</p>
      <p>Create an assistant by entering a website name and public website URL.</p>
      <button class="primary" data-open-setup>Create Website Assistant</button>
      <section class="existing-section"><h2>Existing website assistants</h2>
        ${state.sites.length ? `<p>Select an assistant from the sidebar to view its dashboard.</p>` : "<p>No assistants have been created in this local workspace.</p>"}
      </section>
      <div class="landing-band"><strong>Independent project</strong><p>SiteMind is not affiliated with websites used in examples. Only crawl and index content you are permitted to use.</p></div>
    </div>`;
}

function siteLogo(site) {
  const logo = safeHttpUrl(site.logo_url);
  return logo ? `<img class="site-logo" src="${escapeHtml(logo)}" alt="">` : '<span class="site-logo fallback" aria-hidden="true">S</span>';
}

function viewTabs(siteId) {
  return `<nav class="tabs" aria-label="Site views">
    ${["dashboard", "progress", "chat", "settings"].map(view =>
      `<button class="${state.view === view ? "active" : ""}" data-view="${view}" data-site="${escapeHtml(siteId)}">${view[0].toUpperCase() + view.slice(1)}</button>`
    ).join("")}
  </nav>`;
}

function siteHeader(site) {
  return `<div class="dashboard-head">
    <div class="site-identity">${siteLogo(site)}<div><span class="eyebrow">WEBSITE ASSISTANT</span><h1>${escapeHtml(site.site_name)}</h1><p>${escapeHtml(site.website_url)}</p></div></div>
    <span class="status-pill">${escapeHtml(progressLabel(site.progress))}</span>
  </div>${viewTabs(site.site_id)}`;
}

function metric(label, value) {
  return `<div class="metric"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value ?? 0)}</strong></div>`;
}

function renderDashboard(site) {
  const progress = site.progress || {};
  $("#workspace").innerHTML = `<div class="dashboard">${siteHeader(site)}
    <div class="metrics metrics-wide">
      ${metric("Pages discovered", progress.pages_discovered)}
      ${metric("Documents discovered", progress.documents_discovered)}
      ${metric("Documents processed", progress.documents_processed)}
      ${metric("OCR pages", progress.ocr_pages)}
      ${metric("Chunks indexed", progress.chunks_indexed)}
      ${metric("Failures", progress.failed)}
    </div>
    <div class="command-bar">
      <button class="primary" data-view="chat" data-site="${escapeHtml(site.site_id)}">Open Chat</button>
      <button class="secondary" data-view="progress" data-site="${escapeHtml(site.site_id)}">View Progress</button>
      <button class="secondary" data-action="resume">Resume</button>
      <button class="secondary" data-action="recrawl">Recrawl</button>
      <button class="secondary" data-view="settings" data-site="${escapeHtml(site.site_id)}">Settings</button>
    </div>
    <section class="detail-band">
      <div><small>Assistant</small><strong>${escapeHtml(site.assistant_name)}</strong></div>
      <div><small>Base URL</small><strong>${escapeHtml(site.website_url)}</strong></div>
      <div><small>Last crawl</small><strong>${escapeHtml(progress.completed_at || "Not completed")}</strong></div>
    </section>
  </div>`;
}

function renderProgress(site) {
  const progress = site.progress || {};
  const percentage = Number.isFinite(Number(progress.percentage)) ? Math.max(0, Math.min(100, Number(progress.percentage))) : null;
  $("#workspace").innerHTML = `<div class="dashboard">${siteHeader(site)}
    <section class="progress-panel" aria-live="polite">
      <div class="progress-head"><div><span class="eyebrow">LIVE CRAWL STATUS</span><h2>${escapeHtml(progress.stage || "Queued")}</h2></div><strong>${percentage === null ? "Calculating" : `${percentage}%`}</strong></div>
      ${percentage === null ? "" : `<progress max="100" value="${percentage}">${percentage}%</progress>`}
      <dl class="progress-grid">
        <div><dt>Completed</dt><dd>${escapeHtml(progress.successes || progress.processed || 0)}</dd></div>
        <div><dt>Total discovered</dt><dd>${escapeHtml(progress.discovered ?? "Unknown")}</dd></div>
        <div><dt>Current item</dt><dd class="wrap">${escapeHtml(progress.current_url || "None")}</dd></div>
        <div><dt>Elapsed</dt><dd>${escapeHtml(formatDuration(progress.elapsed_seconds))}</dd></div>
        <div><dt>Rate</dt><dd>${escapeHtml(progress.rate_per_second || 0)} items/sec</dd></div>
        <div><dt>ETA</dt><dd>${escapeHtml(formatDuration(progress.eta_seconds))}</dd></div>
        <div><dt>Successes</dt><dd>${escapeHtml(progress.successes || 0)}</dd></div>
        <div><dt>Skipped</dt><dd>${escapeHtml(progress.skipped || 0)}</dd></div>
        <div><dt>Failures</dt><dd>${escapeHtml(progress.failed || 0)}</dd></div>
      </dl>
      <div class="command-bar"><button class="secondary" data-action="stop">Stop safely</button><button class="secondary" data-action="resume">Resume</button><button class="secondary" data-action="recrawl">Recrawl</button></div>
    </section>
  </div>`;
}

function renderChat(site) {
  $("#workspace").innerHTML = `<div class="dashboard">${siteHeader(site)}
    <section class="chat" aria-label="${escapeHtml(site.assistant_name)} chat">
      <div class="chat-head">${siteLogo(site)}<div><strong>${escapeHtml(site.assistant_name)}</strong><small>${escapeHtml(site.site_name)}</small></div>
        <div class="chat-tools"><button class="icon-text voice-toggle" type="button" aria-pressed="${state.speakAnswers}">Voice playback: ${state.speakAnswers ? "on" : "off"}</button><button class="icon-text" data-action="reset">Reset conversation</button></div>
      </div>
      <div class="messages" aria-live="polite">
        <div class="message" dir="auto">Hello! Ask me about the information available on this website and its indexed documents.</div>
        <div class="suggestions">
          ${["What information is available on this website?", "Summarize the main services.", "Which documents are indexed?", "Show the source for your answer."].map(question => `<button data-suggestion="${escapeHtml(question)}">${escapeHtml(question)}</button>`).join("")}
        </div>
      </div>
      <form class="chat-form"><label class="sr-only" for="chat-question">Question</label><input id="chat-question" name="question" maxlength="4000" required placeholder="Ask a source-grounded question"><button type="button" class="voice-button" title="Ask by voice" aria-label="Ask by voice">Mic</button><button class="primary">Ask</button></form>
    </section>
  </div>`;
}

function renderSettings(site) {
  $("#workspace").innerHTML = `<div class="dashboard">${siteHeader(site)}
    <section class="settings-panel"><span class="eyebrow">SITE SETTINGS</span><h2>Branding and languages</h2>
      <form id="settings-form" class="form-grid">
        <label>Assistant Name<input name="assistant_name" required maxlength="100" value="${escapeHtml(site.assistant_name)}"></label>
        <label>Languages<input name="languages" value="${escapeHtml((site.languages || ["en"]).join(", "))}"></label>
        <label>Optional Logo URL<input name="logo_url" type="url" value="${escapeHtml(site.logo_url || "")}"></label>
        <label>Accent Color<input name="accent_color" type="color" value="${escapeHtml(site.accent_color || "#0f766e")}"></label>
        <div class="form-span"><button class="primary" type="submit">Save Settings</button><span id="settings-status" role="status"></span></div>
      </form>
      <div class="danger-zone"><h3>Delete generated site data</h3><p>Remove this site's local crawl, documents, conversations, and index.</p><button class="danger" data-action="delete">Delete Site Data</button></div>
    </section>
  </div>`;
}

function renderActive() {
  const site = state.sites.find(item => item.site_id === state.active);
  if (!site) return renderLanding();
  document.documentElement.style.setProperty("--brand", site.accent_color || "#0f766e");
  if (state.view === "progress") renderProgress(site);
  else if (state.view === "chat") renderChat(site);
  else if (state.view === "settings") renderSettings(site);
  else renderDashboard(site);
}

async function selectSite(id, view = "dashboard") {
  state.active = id;
  state.view = view;
  const result = await api(`/api/sites/${encodeURIComponent(id)}`);
  const site = {...result.config, progress: {...result.progress, ...await api(`/api/sites/${encodeURIComponent(id)}/progress`)}};
  const index = state.sites.findIndex(item => item.site_id === id);
  if (index >= 0) state.sites[index] = site; else state.sites.push(site);
  renderSites();
  renderActive();
  startPolling();
}

function startPolling() {
  stopPolling();
  if (!state.active) return;
  state.poller = setInterval(refreshProgress, 2000);
}

function stopPolling() {
  if (state.poller) clearInterval(state.poller);
  state.poller = null;
}

async function refreshProgress() {
  if (!state.active) return;
  try {
    const progress = await api(`/api/sites/${encodeURIComponent(state.active)}/progress`);
    const site = state.sites.find(item => item.site_id === state.active);
    if (!site) return;
    site.progress = progress;
    renderSites();
    if (state.view === "progress" || state.view === "dashboard") renderActive();
    if (progress.status === "complete" || progress.status === "stopped") stopPolling();
  } catch {
    stopPolling();
  }
}

async function askQuestion(event) {
  event.preventDefault();
  const input = event.currentTarget.question;
  const question = input.value.trim();
  if (!question || !state.active) return;
  const messages = $(".messages");
  messages.insertAdjacentHTML("beforeend", `<div class="message user" dir="${languageDirection(question)}">${escapeHtml(question)}</div><div class="message pending">Searching verified sources...</div>`);
  input.value = "";
  try {
    const result = await api(`/api/sites/${encodeURIComponent(state.active)}/chat`, {
      method: "POST",
      body: JSON.stringify({question, session_id: state.session}),
    });
    const sourceCards = (result.sources || []).map(source => {
      const page = source.page ? `Page ${source.page}` : source.type;
      const href = safeHttpUrl(source.local_url || source.url);
      return `<article class="source-card"><strong>${escapeHtml(source.title)}</strong><small>${escapeHtml(page || "Source")}</small>${source.highlight ? `<mark>${escapeHtml(source.highlight)}</mark>` : ""}${href ? `<a href="${escapeHtml(href)}${source.page ? `#page=${Number(source.page)}` : ""}" target="_blank" rel="noopener">Open source</a>` : ""}</article>`;
    }).join("");
    $(".pending").outerHTML = `<div class="message" dir="${languageDirection(result.answer)}">${escapeHtml(result.answer)}${sourceCards ? `<div class="source-panel"><h3>Sources</h3>${sourceCards}</div>` : ""}</div>`;
    if (state.speakAnswers && window.speechSynthesis) {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(result.answer);
      utterance.lang = languageDirection(result.answer) === "rtl" ? "ur-PK" : "en-US";
      speechSynthesis.speak(utterance);
    }
  } catch (error) {
    $(".pending").textContent = `Unable to answer: ${error.message}`;
  }
  messages.scrollTop = messages.scrollHeight;
}

function startVoiceInput() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) return announce("Voice input is not available in this browser.");
  const recognition = new Recognition();
  const site = state.sites.find(item => item.site_id === state.active);
  recognition.lang = (site?.languages || ["en"])[0] === "ur" ? "ur-PK" : "en-US";
  recognition.interimResults = false;
  const button = $(".voice-button");
  button.classList.add("listening");
  announce("Listening");
  recognition.onend = () => button.classList.remove("listening");
  recognition.onerror = () => { button.classList.remove("listening"); announce("Voice input failed."); };
  recognition.onresult = result => {
    const input = $("#chat-question");
    input.value = result.results[0][0].transcript;
    input.focus();
  };
  recognition.start();
}

async function siteAction(action) {
  if (!state.active) return;
  if (action === "delete") {
    $("#delete-site-id").textContent = state.active;
    $("#delete-form").reset();
    $("#delete-dialog").showModal();
    return;
  }
  if (action === "reset") {
    await api(`/api/sites/${encodeURIComponent(state.active)}/conversation/reset`, {
      method: "POST", body: JSON.stringify({session_id: state.session}),
    });
    state.session = crypto.randomUUID();
    renderActive();
    announce("Conversation reset.");
    return;
  }
  const endpoint = action === "stop" ? "stop" : action;
  await api(`/api/sites/${encodeURIComponent(state.active)}/${endpoint}`, {method: "POST"});
  announce(`${action} requested.`);
  startPolling();
  refreshProgress();
}

async function loadSites() {
  state.sites = await api("/api/sites");
  renderSites();
  renderLanding();
}

const setupDialog = $("#setup-dialog");
const deleteDialog = $("#delete-dialog");
document.addEventListener("click", event => {
  if (event.target.closest("#new-site, [data-open-setup]")) setupDialog.showModal();
  if (event.target.closest("[data-close]")) setupDialog.close();
  if (event.target.closest("[data-close-delete]")) deleteDialog.close();
  const siteButton = event.target.closest("[data-site].site-button");
  if (siteButton) selectSite(siteButton.dataset.site);
  const viewButton = event.target.closest("[data-view]");
  if (viewButton && state.active) { state.view = viewButton.dataset.view; renderActive(); }
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action) siteAction(action).catch(error => announce(error.message));
  const suggestion = event.target.closest("[data-suggestion]")?.dataset.suggestion;
  if (suggestion && $("#chat-question")) { $("#chat-question").value = suggestion; $("#chat-question").focus(); }
  if (event.target.closest(".voice-button")) startVoiceInput();
  if (event.target.closest(".voice-toggle")) {
    state.speakAnswers = !state.speakAnswers;
    renderActive();
  }
});

document.addEventListener("submit", async event => {
  if (event.target.matches(".chat-form")) return askQuestion(event);
  event.preventDefault();
  if (event.target.id === "setup-form") {
    const form = new FormData(event.target);
    const languages = String(form.get("languages") || "en").split(",").map(value => value.trim()).filter(Boolean);
    const payload = {
      site_name: form.get("site_name"),
      website_url: form.get("website_url"),
      assistant_name: form.get("assistant_name"),
      crawl_mode: form.get("crawl_mode"),
      max_pages: Number(form.get("max_pages")),
      max_depth: Number(form.get("max_depth")),
      languages,
      logo_url: form.get("logo_url") || null,
      accent_color: form.get("accent_color"),
      include_html: Boolean(form.get("include_html")),
      include_pdf: Boolean(form.get("include_pdf")),
      enable_ocr: Boolean(form.get("enable_ocr")),
    };
    try {
      const site = await api("/api/sites", {method: "POST", body: JSON.stringify(payload)});
      setupDialog.close();
      state.sites.push({...site, progress: {status: "queued", stage: "Validating website"}});
      selectSite(site.site_id, "progress");
    } catch (error) {
      $("#form-error").textContent = error.message;
    }
  } else if (event.target.id === "settings-form") {
    const form = new FormData(event.target);
    try {
      const updated = await api(`/api/sites/${encodeURIComponent(state.active)}`, {
        method: "PATCH",
        body: JSON.stringify({
          assistant_name: form.get("assistant_name"),
          languages: String(form.get("languages") || "en").split(",").map(value => value.trim()).filter(Boolean),
          logo_url: form.get("logo_url") || null,
          accent_color: form.get("accent_color"),
        }),
      });
      const site = state.sites.find(item => item.site_id === state.active);
      Object.assign(site, updated);
      $("#settings-status").textContent = "Settings saved.";
      renderSites();
    } catch (error) {
      $("#settings-status").textContent = error.message;
    }
  } else if (event.target.id === "delete-form") {
    const confirmation = new FormData(event.target).get("confirm_site_id");
    try {
      await api(`/api/sites/${encodeURIComponent(state.active)}`, {
        method: "DELETE", body: JSON.stringify({confirm_site_id: confirmation}),
      });
      state.sites = state.sites.filter(site => site.site_id !== state.active);
      deleteDialog.close();
      renderSites();
      renderLanding();
    } catch (error) {
      $("#delete-error").textContent = error.message;
    }
  }
});

loadSites().catch(error => {
  $("#workspace").textContent = `SiteMind could not start: ${error.message}`;
});
