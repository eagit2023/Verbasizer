/*
 * Capa de acceso al motor.
 *
 * La aplicación corre dentro de una ventana de pywebview, que expone las
 * funciones Python de `desktop.Bridge` como `window.pywebview.api.<nombre>`.
 * Cada llamada devuelve una Promise; si Python lanza un error, la Promise se
 * rechaza con un Error cuyo `message` es el texto pensado para el usuario.
 *
 * `window.pywebview.api` no está garantizado en `window.onload`: hay que esperar
 * el evento `pywebviewready` (documentación de pywebview). Por eso toda llamada
 * pasa por `ready`.
 *
 * El resto de la interfaz solo conoce el objeto `API` de abajo. Si algún día el
 * transporte cambia, se cambia este archivo y nada más.
 */
(function (global) {
  "use strict";

  const ready = new Promise((resolve) => {
    if (global.pywebview && global.pywebview.api) {
      resolve();
      return;
    }
    global.addEventListener("pywebviewready", () => resolve(), { once: true });
  });

  function inApp() {
    return Boolean(global.pywebview && global.pywebview.api);
  }

  async function call(name, params) {
    await ready;
    const fn = global.pywebview.api[name];
    if (typeof fn !== "function") {
      throw new Error("El motor no expone la operación '" + name + "'.");
    }
    try {
      return await fn(params === undefined ? {} : params);
    } catch (err) {
      throw new Error((err && err.message) || String(err));
    }
  }

  global.API = {
    /** Espera a que el puente esté listo, con un tope para no colgar la interfaz. */
    async health(timeoutMs) {
      const limit = new Promise((resolve) => setTimeout(() => resolve(null), timeoutMs || 8000));
      try {
        return await Promise.race([call("health"), limit]);
      } catch (err) {
        return null;
      }
    },

    inApp: inApp,

    tag(text, source, lang, keepPunctuation) {
      return call("tag", {
        text: text,
        source: source,
        lang: lang || null,
        keep_punctuation: keepPunctuation !== false,
      });
    },

    distribute(tokens, options) {
      return call("distribute", {
        tokens: tokens,
        unit: options.unit || 1,
        mode: options.mode || "round_robin",
        columns: options.columns || 4,
        categories: options.categories || ["NOUN", "VERB", "ADJ"],
      });
    },

    generate(columns, options) {
      return call("generate", {
        columns: columns,
        rule: options.rule || null,
        lines: options.lines || 8,
        words_per_line: options.wordsPerLine || 6,
        seed: options.seed === undefined ? null : options.seed,
        avoid_repeats: options.avoidRepeats !== false,
      });
    },

    regenerate(columns, previous, locked, options) {
      return call("regenerate", {
        columns: columns,
        previous: previous,
        locked: locked,
        rule: options.rule || null,
        lines: options.lines || null,
        seed: options.seed === undefined ? null : options.seed,
        avoid_repeats: options.avoidRepeats !== false,
      });
    },

    /* Archivos: diálogos nativos del sistema. Devuelven null si se cancela. */

    openTextFile() {
      return call("open_text_file");
    },

    openSession() {
      return call("open_session");
    },

    saveSession(session) {
      return call("save_session", { session: session });
    },

    saveText(text, filename) {
      return call("save_text", { text: text, filename: filename });
    },
  };
})(window);
