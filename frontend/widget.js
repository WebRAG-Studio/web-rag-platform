(function () {
  const loader = document.currentScript;

  function validSiteId(value) {
    return /^[a-z0-9][a-z0-9-]{2,63}$/.test(String(value || ""));
  }

  class SiteMindWidget extends HTMLElement {
    async connectedCallback() {
      const siteId = this.getAttribute("site-id");
      if (!validSiteId(siteId)) {
        this.textContent = "SiteMind widget requires a valid site-id.";
        return;
      }
      const sessionId = crypto.randomUUID();
      const shadow = this.attachShadow({mode: "open"});
      shadow.innerHTML = `
        <style>
          :host{font-family:system-ui,sans-serif;color:#172025}button:focus-visible,input:focus-visible{outline:3px solid #8fd5cf;outline-offset:2px}
          .toggle{position:fixed;right:20px;bottom:20px;border:0;border-radius:50%;width:56px;height:56px;background:var(--widget-accent,#0f766e);color:white;font-weight:800;box-shadow:0 8px 22px #10202740}
          section{display:none;position:fixed;right:20px;bottom:88px;width:min(380px,calc(100vw - 32px));height:min(520px,calc(100vh - 120px));background:white;border:1px solid #dce3e5;box-shadow:0 18px 50px #10202740}
          section.open{display:grid;grid-template-rows:auto 1fr auto}header{padding:13px;border-bottom:1px solid #dce3e5;display:flex;align-items:center;gap:8px}header span{display:grid}header small{color:#607078}
          main{padding:14px;overflow:auto;white-space:pre-wrap;line-height:1.5}.source{display:grid;gap:4px;border-top:1px solid #dce3e5;padding-top:8px;margin-top:8px}.source a{color:var(--widget-accent,#0f766e)}
          form{display:grid;grid-template-columns:1fr auto auto;padding:10px;border-top:1px solid #dce3e5;gap:6px}input{min-width:0;padding:10px;border:1px solid #bcc8cc}form button,.reset{position:static;width:auto;height:auto;border:1px solid #bcc8cc;border-radius:3px;padding:8px;background:white}.ask{background:var(--widget-accent,#0f766e);color:white;border-color:var(--widget-accent,#0f766e)}
          [dir=rtl]{text-align:right;font-family:"Noto Sans Arabic","Segoe UI",sans-serif}
        </style>
        <button class="toggle" aria-label="Open website assistant" aria-expanded="false">AI</button>
        <section aria-label="Website assistant">
          <header><span><strong class="assistant-name">SiteMind Assistant</strong><small class="site-name">Website assistant</small></span><button class="reset" type="button">Reset</button></header>
          <main aria-live="polite" dir="auto">Hello! Ask me about the information available on this website and its indexed documents.</main>
          <form><label hidden for="widget-question">Question</label><input id="widget-question" required maxlength="4000"><button class="mic" type="button" aria-label="Ask by voice">Mic</button><button class="ask">Ask</button></form>
        </section>`;

      const toggle = shadow.querySelector(".toggle");
      const panel = shadow.querySelector("section");
      const output = shadow.querySelector("main");
      let currentSession = sessionId;

      toggle.onclick = () => {
        const open = panel.classList.toggle("open");
        toggle.setAttribute("aria-expanded", String(open));
        if (open) shadow.querySelector("input").focus();
      };

      try {
        const response = await fetch(`/api/sites/${encodeURIComponent(siteId)}`);
        if (!response.ok) throw new Error("Site configuration unavailable");
        const payload = await response.json();
        const config = payload.config || {};
        shadow.querySelector(".assistant-name").textContent = config.assistant_name || "SiteMind Assistant";
        shadow.querySelector(".site-name").textContent = config.site_name || "Website assistant";
        this.style.setProperty("--widget-accent", /^#[0-9a-f]{6}$/i.test(config.accent_color || "") ? config.accent_color : "#0f766e");
      } catch {
        output.textContent = "This website assistant is currently unavailable.";
      }

      shadow.querySelector(".reset").onclick = async () => {
        await fetch(`/api/sites/${encodeURIComponent(siteId)}/conversation/reset`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({session_id: currentSession}),
        }).catch(() => null);
        currentSession = crypto.randomUUID();
        output.textContent = "Conversation reset. Ask a new question.";
      };

      shadow.querySelector(".mic").onclick = () => {
        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!Recognition) {
          output.textContent = "Voice input is not available in this browser.";
          return;
        }
        const recognition = new Recognition();
        recognition.onresult = event => {
          shadow.querySelector("input").value = event.results[0][0].transcript;
        };
        recognition.start();
      };

      shadow.querySelector("form").onsubmit = async event => {
        event.preventDefault();
        const input = shadow.querySelector("input");
        const question = input.value.trim();
        if (!question) return;
        output.textContent = "Searching verified sources...";
        input.value = "";
        try {
          const response = await fetch(`/api/sites/${encodeURIComponent(siteId)}/chat`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({question, session_id: currentSession}),
          });
          const result = await response.json();
          if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Request failed");
          output.textContent = result.answer;
          for (const source of result.sources || []) {
            const card = document.createElement("div");
            card.className = "source";
            const title = document.createElement("strong");
            title.textContent = source.title || "Source";
            card.append(title);
            const href = source.local_url || source.url;
            if (href) {
              const link = document.createElement("a");
              link.textContent = source.page ? `Open source, page ${source.page}` : "Open source";
              link.href = href + (source.page ? `#page=${Number(source.page)}` : "");
              link.target = "_blank";
              link.rel = "noopener";
              card.append(link);
            }
            output.append(card);
          }
        } catch (error) {
          output.textContent = `Assistant unavailable: ${error.message}`;
        }
      };
    }
  }

  if (!customElements.get("sitemind-widget")) {
    customElements.define("sitemind-widget", SiteMindWidget);
  }

  const configuredSiteId = loader?.dataset.siteId;
  if (configuredSiteId && !document.querySelector("sitemind-widget")) {
    const widget = document.createElement("sitemind-widget");
    widget.setAttribute("site-id", configuredSiteId);
    document.body.append(widget);
  }
})();
