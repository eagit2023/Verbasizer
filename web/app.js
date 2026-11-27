/*
 * Interfaz del Verbasizer.
 *
 * Todo el estado de la sesión vive acá. El motor (Python, del otro lado del
 * puente de pywebview) etiqueta y genera, y no guarda nada. Las sesiones se
 * guardan como archivo con diálogos del sistema.
 */
(function () {
  "use strict";

  // ------------------------------------------------------------- estado --

  const state = {
    sources: [],      // { name, text, lang, tokens, color }
    columns: [],      // formato del motor + weight/pos_filter
    generation: null, // última tirada
    locked: new Set(),// "linea:posicion"
    history: [],      // tiradas anteriores
    tray: [],         // líneas guardadas
    usefulPos: ["NOUN", "VERB", "ADJ", "ADV", "PROPN", "PRON", "NUM", "INTJ"],
  };

  const SOURCE_COLORS = [
    "var(--src-1)", "var(--src-2)", "var(--src-3)",
    "var(--src-4)", "var(--src-5)", "var(--src-6)",
  ];

  const $ = (id) => document.getElementById(id);

  // ------------------------------------------------------------ helpers --

  let toastTimer = null;
  function toast(message, isError) {
    const el = $("toast");
    el.textContent = message;
    el.className = "toast" + (isError ? " error" : "");
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, isError ? 6000 : 2800);
  }

  function colorFor(sourceName) {
    const index = state.sources.findIndex((s) => s.name === sourceName);
    return index === -1 ? "var(--src-fallback)" : SOURCE_COLORS[index % SOURCE_COLORS.length];
  }

  function parseRule(raw) {
    if (!raw || !raw.trim()) return null;
    const numbers = raw.split(",")
      .map((n) => parseInt(n.trim(), 10))
      .filter((n) => Number.isInteger(n) && n > 0);
    return numbers.length ? numbers : null;
  }

  function uniqueName(base) {
    let name = base || "fuente";
    let n = 2;
    while (state.sources.some((s) => s.name === name)) {
      name = base + "-" + n;
      n += 1;
    }
    return name;
  }

  // ------------------------------------------------------------ fuentes --

  async function addSource() {
    const text = $("source-text").value.trim();
    if (!text) { toast("No hay texto para agregar.", true); return; }

    const name = uniqueName(($("source-name").value || "").trim() || "fuente");
    const lang = $("source-lang").value;
    const button = $("btn-add-source");
    button.disabled = true;
    button.textContent = lang ? "Etiquetando…" : "Procesando…";

    try {
      const result = await API.tag(text, name, lang, true);
      state.sources.push({
        name: name,
        text: text,
        lang: lang || null,
        tokens: result.tokens,
      });
      $("source-text").value = "";
      $("source-name").value = "";
      renderSources();
      toast(`"${name}": ${result.tokens.length} palabras.`);
    } catch (err) {
      toast(err.message, true);
    } finally {
      button.disabled = false;
      button.textContent = "Agregar fuente";
    }
  }

  function removeSource(name) {
    state.sources = state.sources.filter((s) => s.name !== name);
    renderSources();
  }

  function renderSources() {
    const list = $("sources-list");
    list.innerHTML = "";

    state.sources.forEach((source) => {
      const li = document.createElement("li");
      li.className = "source";
      li.style.setProperty("--source-color", colorFor(source.name));

      const tagged = source.tokens.some((t) => t.pos);
      li.innerHTML = `
        <span class="swatch"></span>
        <span class="source-name"></span>
        <span class="source-meta"></span>
        <button class="ghost small" title="Quitar">×</button>`;
      li.querySelector(".source-name").textContent = source.name;
      li.querySelector(".source-meta").textContent =
        source.tokens.length + " palabras" + (tagged ? " · etiquetada" : "");
      li.querySelector("button").addEventListener("click", () => removeSource(source.name));
      list.appendChild(li);
    });

    const hasTagged = state.sources.some((s) => s.tokens.some((t) => t.pos));
    $("mode").querySelector('option[value="by_pos"]').disabled = !hasTagged;
  }

  // ----------------------------------------------------------- columnas --

  async function distribute() {
    if (!state.sources.length) { toast("Cargá al menos una fuente.", true); return; }

    const tokens = state.sources.flatMap((s) => s.tokens);
    const mode = $("mode").value;
    const options = {
      unit: parseInt($("unit").value, 10) || 1,
      mode: mode,
      columns: parseInt($("column-count").value, 10) || 4,
      categories: $("categories").value.split(",").map((c) => c.trim().toUpperCase()).filter(Boolean),
    };

    try {
      const result = await API.distribute(tokens, options);
      // Conservar pesos si los nombres coinciden con el reparto anterior.
      const previousWeights = {};
      state.columns.forEach((c) => { previousWeights[c.name] = c.weight; });
      state.columns = result.columns.map((c) => ({
        ...c,
        weight: previousWeights[c.name] !== undefined ? previousWeights[c.name] : 1,
      }));
      renderColumns();
      const vacias = state.columns.filter((c) => !c.fragments.length).map((c) => c.name);
      toast(vacias.length
        ? `Repartido. Sin material para: ${vacias.join(", ")}.`
        : `Repartido en ${state.columns.length} columnas.`);
    } catch (err) {
      toast(err.message, true);
    }
  }

  function renderColumns() {
    const container = $("columns-list");
    container.innerHTML = "";

    if (!state.columns.length) {
      container.innerHTML = '<p class="empty">Todavía no repartiste nada.</p>';
      return;
    }

    state.columns.forEach((column, index) => {
      const card = document.createElement("div");
      card.className = "column-card" + (column.fragments.length ? "" : " empty-column");

      const posOptions = ['<option value="">cualquiera</option>']
        .concat(state.usefulPos.map((p) =>
          `<option value="${p}"${column.pos_filter === p ? " selected" : ""}>${p}</option>`))
        .join("");

      card.innerHTML = `
        <div class="column-head">
          <strong class="column-name"></strong>
          <span class="column-count"></span>
        </div>
        <label class="weight">
          <span>peso <b class="weight-value">${column.weight}</b></span>
          <input type="range" min="0" max="10" step="0.5" value="${column.weight}">
        </label>
        <label class="pos">
          <span>categoría</span>
          <select>${posOptions}</select>
        </label>
        <div class="peek"></div>`;

      card.querySelector(".column-name").textContent = column.name;
      card.querySelector(".column-count").textContent =
        column.fragments.length + (column.fragments.length === 1 ? " frag." : " frags.");

      const peek = column.fragments.slice(0, 6)
        .map((f) => f.map((t) => t.text).join(" "))
        .join(" · ");
      card.querySelector(".peek").textContent = peek;

      const range = card.querySelector('input[type="range"]');
      range.addEventListener("input", () => {
        const value = parseFloat(range.value);
        state.columns[index].weight = value;
        card.querySelector(".weight-value").textContent = value;
        card.classList.toggle("muted", value === 0);
      });
      card.classList.toggle("muted", column.weight === 0);

      card.querySelector("select").addEventListener("change", (event) => {
        state.columns[index].pos_filter = event.target.value || null;
      });

      container.appendChild(card);
    });
  }

  // ----------------------------------------------------------- generar ---

  function generateOptions() {
    const rawSeed = $("seed").value.trim();
    const seed = rawSeed === "" ? undefined : parseInt(rawSeed, 10);
    return {
      rule: parseRule($("rule").value),
      lines: parseInt($("lines").value, 10) || 8,
      wordsPerLine: parseInt($("length").value, 10) || 6,
      seed: Number.isInteger(seed) ? seed : undefined,
      avoidRepeats: $("avoid-repeats").checked,
    };
  }

  async function doGenerate() {
    if (!state.columns.length) { toast("Primero repartí en columnas.", true); return; }
    try {
      const result = await API.generate(state.columns, generateOptions());
      pushHistory(result);
      state.generation = result;
      state.locked.clear();
      showSeed(result.seed);
      renderOutput();
    } catch (err) {
      toast(err.message, true);
    }
  }

  /* La semilla usada se muestra, pero NO se escribe en el campo: si quedara ahí,
     el siguiente "Generar" repetiría la tirada anterior en vez de hacer una nueva.
     El campo es un pedido explícito; esto es el registro de lo que salió. */
  function showSeed(seed) {
    const label = $("seed-last");
    label.innerHTML = "";
    const text = document.createElement("span");
    text.textContent = "última: " + seed + " · ";
    const reuse = document.createElement("a");
    reuse.href = "#";
    reuse.textContent = "reusar";
    reuse.addEventListener("click", (event) => {
      event.preventDefault();
      $("seed").value = seed;
    });
    label.appendChild(text);
    label.appendChild(reuse);
  }

  async function doRegenerate() {
    if (!state.generation) return;
    const locked = Array.from(state.locked).map((key) => key.split(":").map(Number));
    const options = generateOptions();
    options.seed = undefined; // una tirada nueva para lo no fijado
    try {
      const result = await API.regenerate(state.columns, state.generation, locked, options);
      pushHistory(result);
      state.generation = result;
      showSeed(result.seed);
      renderOutput();
    } catch (err) {
      toast(err.message, true);
    }
  }

  function pushHistory(generation) {
    state.history.unshift(generation);
    if (state.history.length > 30) state.history.pop();
    renderHistory();
  }

  function toggleLock(lineIndex, position) {
    const key = lineIndex + ":" + position;
    if (state.locked.has(key)) state.locked.delete(key);
    else state.locked.add(key);
    renderOutput();
  }

  function renderOutput() {
    const container = $("output");
    container.innerHTML = "";

    const generation = state.generation;
    $("btn-regenerate").disabled = !generation;
    $("btn-clear-locks").disabled = !state.locked.size;

    if (!generation) {
      container.innerHTML = '<p class="empty">Nada generado todavía.</p>';
      return;
    }

    generation.lines.forEach((line, lineIndex) => {
      const row = document.createElement("div");
      row.className = "line";

      const keep = document.createElement("button");
      keep.className = "keep";
      keep.title = "Mandar a la bandeja";
      keep.textContent = "→";
      keep.addEventListener("click", () => {
        addToTray(line.text);
      });
      row.appendChild(keep);

      const chips = document.createElement("div");
      chips.className = "chips";

      line.placements.forEach((placement, position) => {
        const key = lineIndex + ":" + position;
        const chip = document.createElement("button");
        chip.className = "chip" + (state.locked.has(key) ? " locked" : "");
        chip.textContent = placement.text;
        chip.style.setProperty("--source-color", colorFor(placement.source));
        chip.title = `${placement.column} · ${placement.source}`;
        chip.addEventListener("click", () => toggleLock(lineIndex, position));
        chips.appendChild(chip);
      });

      row.appendChild(chips);
      container.appendChild(row);
    });
  }

  // ----------------------------------------------------------- bandeja ---

  function addToTray(text) {
    if (!text || state.tray.includes(text)) { toast("Ya está en la bandeja."); return; }
    state.tray.push(text);
    renderTray();
  }

  function renderTray() {
    const list = $("tray");
    list.innerHTML = "";
    if (!state.tray.length) {
      list.innerHTML = '<li class="empty">Vacía.</li>';
      return;
    }
    state.tray.forEach((text, index) => {
      const li = document.createElement("li");
      li.innerHTML = '<span class="tray-text"></span><button class="ghost small">×</button>';
      li.querySelector(".tray-text").textContent = text;
      li.querySelector("button").addEventListener("click", () => {
        state.tray.splice(index, 1);
        renderTray();
      });
      list.appendChild(li);
    });
  }

  function feedTrayBack() {
    if (!state.tray.length) { toast("La bandeja está vacía.", true); return; }
    $("source-text").value = state.tray.join("\n");
    $("source-name").value = uniqueName("bandeja");
    $("source-text").scrollIntoView({ behavior: "smooth", block: "center" });
    toast("Listo para agregarlo como fuente nueva.");
  }

  // ---------------------------------------------------------- historial --

  function renderHistory() {
    const list = $("history");
    list.innerHTML = "";
    if (!state.history.length) {
      list.innerHTML = '<li class="empty">Sin tiradas todavía.</li>';
      return;
    }
    state.history.forEach((generation) => {
      const li = document.createElement("li");
      li.innerHTML = '<button class="ghost history-item"><b></b><span></span></button>';
      li.querySelector("b").textContent = "#" + generation.seed;
      li.querySelector("span").textContent =
        (generation.lines[0] ? generation.lines[0].text : "").slice(0, 60);
      li.querySelector("button").addEventListener("click", () => {
        state.generation = generation;
        state.locked.clear();
        showSeed(generation.seed);
        renderOutput();
      });
      list.appendChild(li);
    });
  }

  // ------------------------------------------------------------ sesión ---

  function sessionData() {
    return {
      format: 1,
      name: state.sources.map((s) => s.name).join(", ") || "sin título",
      unit: parseInt($("unit").value, 10) || 1,
      keep_punctuation: true,
      sources: state.sources.map((s) => ({
        name: s.name, text: s.text, lang: s.lang, tokens: s.tokens,
      })),
      columns: state.columns,
      generations: state.history.slice().reverse(),
      saved: state.tray,
    };
  }

  /* En la ventana de escritorio las descargas del navegador están apagadas, así
     que guardar y abrir pasan por diálogos nativos (ver desktop.Bridge). */
  async function exportSession() {
    try {
      const path = await API.saveSession(sessionData());
      if (path) toast("Sesión guardada.");
    } catch (err) {
      toast(err.message, true);
    }
  }

  async function importSession() {
    let data;
    try {
      data = await API.openSession();
    } catch (err) {
      toast(err.message, true);
      return;
    }
    if (!data) return; // cancelado
    loadSession(data);
  }

  function loadSession(data) {
    try {
      if (data.format !== 1) throw new Error("Formato de sesión desconocido.");
      state.sources = (data.sources || []).map((s) => ({
        name: s.name, text: s.text, lang: s.lang || null, tokens: s.tokens || [],
      }));
      state.columns = data.columns || [];
      state.history = (data.generations || []).slice().reverse();
      state.generation = state.history[0] || null;
      state.tray = data.saved || [];
      state.locked.clear();
      if (data.unit) $("unit").value = data.unit;
      renderSources(); renderColumns(); renderOutput(); renderTray(); renderHistory();
      toast("Sesión cargada.");
    } catch (err) {
      toast("No pude leer la sesión: " + err.message, true);
    }
  }

  async function openSourceFile() {
    try {
      const file = await API.openTextFile();
      if (!file) return; // cancelado
      $("source-text").value = file.text;
      if (!$("source-name").value) $("source-name").value = file.name;
    } catch (err) {
      toast(err.message, true);
    }
  }

  /* El portapapeles moderno puede estar bloqueado dentro de una ventana
     embebida; si falla, se usa el método clásico. */
  function copyText(text) {
    const fallback = () => {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
      document.body.removeChild(area);
      return ok;
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(() => true, () => fallback());
    }
    return Promise.resolve(fallback());
  }

  /* Confirmación en dos clics, sin diálogos del navegador: dentro de una
     ventana embebida confirm() no siempre está disponible. */
  function confirmTwice(button, label, action) {
    if (button.dataset.armed === "1") {
      clearTimeout(button._disarm);
      button.dataset.armed = "";
      button.textContent = label;
      action();
      return;
    }
    button.dataset.armed = "1";
    button.textContent = "¿Seguro? clic de nuevo";
    button._disarm = setTimeout(() => {
      button.dataset.armed = "";
      button.textContent = label;
    }, 3000);
  }

  // ------------------------------------------------------------- arranque -

  async function checkServer() {
    const health = await API.health();
    const el = $("server-status");
    if (!health) {
      el.textContent = "sin motor";
      el.className = "status bad";
      el.title = API.inApp()
        ? "El motor no respondió."
        : "Esta interfaz tiene que abrirse desde la aplicación Verbasizer.";
      return;
    }
    if (health.useful_pos) state.usefulPos = health.useful_pos;
    const langs = Object.entries(health.languages)
      .filter(([, ok]) => ok).map(([lang]) => lang);
    el.textContent = langs.length ? "motor · " + langs.join(" ") : "motor · sin modelos";
    el.className = "status ok";
    el.title = langs.length
      ? "Idiomas con modelo instalado: " + langs.join(", ")
      : "Sin modelos de idioma: no vas a poder usar categorías gramaticales.";

    const select = $("source-lang");
    Array.from(select.options).forEach((option) => {
      if (option.value && !langs.includes(option.value)) {
        option.disabled = true;
        option.textContent += " (falta el modelo)";
      }
    });
    if (select.selectedOptions[0] && select.selectedOptions[0].disabled) select.value = "";
  }

  function wire() {
    $("btn-add-source").addEventListener("click", addSource);
    $("btn-distribute").addEventListener("click", distribute);
    $("btn-generate").addEventListener("click", doGenerate);
    $("btn-regenerate").addEventListener("click", doRegenerate);
    $("btn-clear-locks").addEventListener("click", () => {
      state.locked.clear();
      renderOutput();
    });

    $("mode").addEventListener("change", (event) => {
      const byPos = event.target.value === "by_pos";
      $("label-count").hidden = byPos;
      $("label-categories").hidden = !byPos;
    });

    $("btn-file-source").addEventListener("click", openSourceFile);

    $("btn-tray-copy").addEventListener("click", () => {
      if (!state.tray.length) { toast("La bandeja está vacía.", true); return; }
      copyText(state.tray.join("\n")).then((ok) => {
        toast(ok ? "Copiado." : "No se pudo copiar. Probá Guardar .txt.", !ok);
      });
    });
    $("btn-tray-save").addEventListener("click", async () => {
      if (!state.tray.length) { toast("La bandeja está vacía.", true); return; }
      try {
        const path = await API.saveText(state.tray.join("\n") + "\n", "bandeja.txt");
        if (path) toast("Bandeja guardada.");
      } catch (err) {
        toast(err.message, true);
      }
    });
    $("btn-tray-feed").addEventListener("click", feedTrayBack);
    $("btn-tray-clear").addEventListener("click", (event) => {
      if (!state.tray.length) return;
      confirmTwice(event.currentTarget, "Vaciar", () => {
        state.tray = [];
        renderTray();
      });
    });

    $("btn-export").addEventListener("click", exportSession);
    $("btn-import").addEventListener("click", importSession);

    document.addEventListener("keydown", (event) => {
      if (event.target.matches("input, textarea, select")) return;
      if (event.key === "g") { event.preventDefault(); doGenerate(); }
      if (event.key === "r") { event.preventDefault(); doRegenerate(); }
    });
  }

  wire();
  renderSources();
  renderColumns();
  renderOutput();
  renderTray();
  renderHistory();
  checkServer();
})();
