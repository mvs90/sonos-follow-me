/* Sonos Follow Me — bundled, dependency-free Home Assistant dashboard card. */
const words = {
  de: {
    rooms: "Räume",
    occupied: "Belegt",
    clear: "Frei",
    unavailable: "Nicht verfügbar",
    playing: "Wiedergabe",
    paused: "Pausiert",
    idle: "Bereit",
    on: "An",
    off: "Aus",
    empty: "Keine Follow-Me-Räume gefunden. Zuerst die Integration einrichten.",
    settings: "Einstellungen & Sensoren",
    remembered: "Letzte Lautstärke",
    default_volume: "Standardlautstärke",
    volume_cooldown: "Abkühlzeit",
    off_delay: "Ausschaltverzögerung",
    fade_seconds: "Überblenddauer",
    volume_reset: "Standardlautstärke verwenden",
    mode: "Sensorlogik",
    primary: "PIR startet, weitere halten",
    equal: "Alle gleichberechtigt",
    sources: "Musikquellen",
    sensors: "Sensoren",
    speaker: "Lautsprecher",
    error: "Änderung fehlgeschlagen",
    title: "Titel",
    choose: "Räume (ohne Auswahl: alle)",
    cooldown: "Abkühlzeit läuft",
    ready: "Standardlautstärke beim nächsten Besuch",
    minute: "min",
    resetHint: "0 Minuten = Standardlautstärke beim nächsten Besuch.",
    missing: "Raum nicht verfügbar",
    edit: "Raumzuordnung bearbeiten",
  },
  en: {
    rooms: "Rooms",
    occupied: "Occupied",
    clear: "Clear",
    unavailable: "Unavailable",
    playing: "Playing",
    paused: "Paused",
    idle: "Idle",
    on: "On",
    off: "Off",
    empty: "No Follow Me rooms found. Set up the integration first.",
    settings: "Settings & sensors",
    remembered: "Remembered volume",
    default_volume: "Default volume",
    volume_cooldown: "Volume cooldown",
    off_delay: "Clear delay",
    fade_seconds: "Fade duration",
    volume_reset: "Use default volume",
    mode: "Sensor mode",
    primary: "PIR starts, others hold",
    equal: "All sensors equal",
    sources: "Music sources",
    sensors: "Sensors",
    speaker: "Speaker",
    error: "Change failed",
    title: "Title",
    choose: "Rooms (empty selection: all)",
    cooldown: "Cooldown running",
    ready: "Default volume on next visit",
    minute: "min",
    resetHint: "0 minutes = default volume on the next visit.",
    missing: "Room unavailable",
    edit: "Edit room assignment",
  },
};
const node = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};
const valid = (state) =>
  state && !["unknown", "unavailable"].includes(state.state);
const roomSwitches = (hass) =>
  Object.values(hass?.states || {}).filter(
    (s) =>
      s.entity_id.startsWith("switch.") &&
      s.attributes.sonos_follow_me_room &&
      s.attributes.setting === "enabled",
  );
const lang = (hass) => words[hass?.language?.startsWith("de") ? "de" : "en"];
const css = `
:host{display:block;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,system-ui)}
ha-card{display:block;overflow:hidden;background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:var(--ha-card-border-radius,16px);border:1px solid var(--divider-color,#ddd)}
.brand{display:flex;align-items:center;gap:10px;min-width:0}.logo{width:48px;height:48px;object-fit:contain;flex-shrink:0}.count{white-space:nowrap;flex-shrink:0}header{gap:12px;padding:20px 20px 12px;display:flex;justify-content:space-between;align-items:center}h2{overflow-wrap:anywhere;font-size:21px;margin:0;font-weight:600}.count,.muted{color:var(--secondary-text-color,#666);font-size:13px}.rooms{padding:0 12px 12px;display:grid;gap:10px}.room{border:1px solid var(--divider-color,#ddd);border-radius:12px;padding:16px;min-width:0}.heading{display:flex;align-items:center;gap:10px;justify-content:space-between}.name{font-size:17px;font-weight:600;overflow-wrap:anywhere}.badge{display:inline-block;border-radius:20px;padding:4px 9px;font-size:12px;background:var(--secondary-background-color,#f3f4f5);margin-top:8px}.occupied{color:var(--primary-color,#007c83);background:color-mix(in srgb,var(--primary-color,#007c83) 12%,transparent)}.summary{white-space:pre-line;margin:12px 0;font-size:13px;line-height:1.7;overflow-wrap:anywhere}.row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:12px 0;font-size:14px}input,select,button{font:inherit;color:inherit}input[type=checkbox]{width:22px;height:22px;accent-color:var(--primary-color,#007c83);cursor:pointer;flex-shrink:0}input[type=number],select{background:var(--secondary-background-color,#f6f7f8);border:1px solid var(--divider-color,#ccc);border-radius:8px;padding:9px;box-sizing:border-box;max-width:100%;min-width:0}input[type=number]{width:100%}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px}.field{display:grid;gap:6px;font-size:12px;color:var(--secondary-text-color,#666)}.field input{color:var(--primary-text-color)}details{border-top:1px solid var(--divider-color,#ddd);margin-top:14px;padding-top:12px}summary{cursor:pointer;font-size:14px;font-weight:500;padding:4px 0}select{width:100%;margin-top:6px}ul{padding-left:18px;font-size:13px;line-height:1.7;overflow-wrap:anywhere}.error{padding:12px;color:var(--error-color,#b00020);overflow-wrap:anywhere}.empty{padding:20px}.hint{font-size:12px;line-height:1.5;color:var(--secondary-text-color,#666);margin-top:12px}a{color:var(--primary-color,#007c83);font-size:13px}input:focus-visible,select:focus-visible,summary:focus-visible{outline:2px solid var(--primary-color,#007c83);outline-offset:3px}:disabled{opacity:.5;cursor:not-allowed}
`;

class SonosFollowMeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._expanded = new Set();
    this._busy = new Set();
    this.shadowRoot.addEventListener("focusout", () =>
      setTimeout(() => this._render(), 0),
    );
  }
  setConfig(config) {
    if (
      config.entities !== undefined &&
      (!Array.isArray(config.entities) ||
        config.entities.some(
          (e) => typeof e !== "string" || !e.startsWith("switch."),
        ))
    )
      throw new Error("entities must be a list of Follow Me switch entity IDs");
    this._config = { ...config };
    this._render();
  }
  set hass(hass) {
    this._hass = hass;
    this._render();
  }
  connectedCallback() {
    if (!this._interval)
      this._interval = setInterval(() => this._render(), 30000);
  }
  disconnectedCallback() {
    clearInterval(this._interval);
    this._interval = null;
  }
  static getStubConfig() {
    return { type: "custom:sonos-follow-me-card", title: "Sonos Follow Me" };
  }
  static getConfigElement() {
    return document.createElement("sonos-follow-me-card-editor");
  }
  getCardSize() {
    return (
      2 +
      6 *
        (this._config?.entities?.length || roomSwitches(this._hass).length || 1)
    );
  }
  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }
  async _call(state, action, data = {}) {
    if (!state || this._busy.has(state.entity_id)) return;
    const id = state.entity_id;
    this._busy.add(id);
    this._error = "";
    this._render(true);
    try {
      await this._hass.callService(id.split(".")[0], action, {
        entity_id: id,
        ...data,
      });
    } catch (error) {
      this._error = `${lang(this._hass).error}: ${error.message || error}`;
    } finally {
      this._busy.delete(id);
      this._render(true);
    }
  }
  _toggle(state, text, parent) {
    const label = node("label", undefined, "row");
    label.append(node("span", text));
    const input = node("input");
    input.type = "checkbox";
    input.checked = state?.state === "on";
    input.setAttribute("aria-label", text);
    input.disabled = !valid(state) || this._busy.has(state.entity_id);
    input.addEventListener("change", () =>
      this._call(state, input.checked ? "turn_on" : "turn_off"),
    );
    label.append(input);
    parent.append(label);
  }
  _number(state, key, parent, t) {
    if (!state) return;
    const label = node("label", undefined, "field");
    const unit = state.attributes.unit_of_measurement || "";
    label.append(node("span", `${t[key]} (${unit})`));
    const input = node("input");
    input.type = "number";
    input.value = valid(state) ? state.state : "";
    input.min = state.attributes.min;
    input.max = state.attributes.max;
    input.step = state.attributes.step;
    input.setAttribute("aria-label", t[key]);
    input.disabled = !valid(state) || this._busy.has(state.entity_id);
    input.addEventListener("change", () => {
      if (input.value !== "" && input.reportValidity())
        this._call(state, "set_value", { value: Number(input.value) });
    });
    label.append(input);
    parent.append(label);
  }
  _render(force = false) {
    if (
      !this._hass ||
      !this._config ||
      (!force && this.shadowRoot.activeElement)
    )
      return;
    const hass = this._hass,
      t = lang(hass),
      states = Object.values(hass.states);
    const switches = this._config.entities?.length
      ? this._config.entities.map((id) => hass.states[id])
      : roomSwitches(hass).sort((a, b) =>
          (a.attributes.room_name || "").localeCompare(
            b.attributes.room_name || "",
          ),
        );
    const style = node("style", css),
      card = node("ha-card"),
      header = node("header");
    const brand = node("div", undefined, "brand");
    const logo = node("img", undefined, "logo");
    logo.src = "/sonos_follow_me/follow-me-logo.png?v=0.3.1";
    logo.alt = "";
    logo.width = 48;
    logo.height = 48;
    brand.append(logo, node("h2", this._config.title || "Sonos Follow Me"));
    header.append(
      brand,
      node("span", `${switches.length} ${t.rooms}`, "count"),
    );
    card.append(header);
    if (this._error) {
      const error = node("div", this._error, "error");
      error.setAttribute("role", "alert");
      card.append(error);
    }
    const container = node("div", undefined, "rooms");
    card.append(container);
    if (!switches.length) container.append(node("div", t.empty, "empty"));
    for (const enabled of switches) {
      if (
        !enabled?.attributes.sonos_follow_me_room ||
        enabled.attributes.setting !== "enabled"
      ) {
        container.append(node("div", t.missing, "empty"));
        continue;
      }
      const a = enabled.attributes,
        id = a.sonos_follow_me_room;
      const settings = Object.fromEntries(
        states
          .filter((s) => s.attributes.sonos_follow_me_room === id)
          .map((s) => [s.attributes.setting, s]),
      );
      const room = node("section", undefined, "room");
      room.dataset.room = id;
      const heading = node("div", undefined, "heading");
      heading.append(
        node("div", a.room_name || enabled.attributes.friendly_name, "name"),
      );
      this._toggle(enabled, "Follow Me", heading);
      room.append(heading);
      const occupancy = settings.occupancy;
      room.append(
        node(
          "span",
          !valid(occupancy)
            ? t.unavailable
            : occupancy.state === "on"
              ? t.occupied
              : t.clear,
          `badge ${occupancy?.state === "on" ? "occupied" : ""}`,
        ),
      );
      const player = hass.states[a.player];
      const friendly = (entity) =>
        hass.states[entity]?.attributes.friendly_name || entity;
      room.append(
        node(
          "div",
          `${t.speaker}: ${friendly(a.player)} · ${t[player?.state] || player?.state || t.unavailable}\n${t.remembered}: ${Math.round((a.remembered_volume || 0) * 100)} %`,
          "summary",
        ),
      );
      this._toggle(settings.volume_reset, t.volume_reset, room);
      const grid = node("div", undefined, "grid");
      for (const key of ["default_volume", "volume_cooldown"])
        this._number(settings[key], key, grid, t);
      room.append(grid);
      if (
        settings.volume_reset?.state === "on" &&
        a.vacant_since != null &&
        valid(settings.volume_cooldown)
      ) {
        const left = Math.max(
          0,
          Math.ceil(
            (Number(a.vacant_since) +
              Number(settings.volume_cooldown.state) * 60 -
              Date.now() / 1000) /
              60,
          ),
        );
        room.append(
          node(
            "div",
            left ? `${t.cooldown}: ${left} ${t.minute}` : t.ready,
            "hint",
          ),
        );
      } else room.append(node("div", t.resetHint, "hint"));
      const details = node("details");
      details.open = this._expanded.has(id);
      details.append(node("summary", t.settings));
      details.addEventListener("toggle", () => {
        if (details.open) this._expanded.add(id);
        else this._expanded.delete(id);
      });
      const more = node("div", undefined, "grid");
      for (const key of ["off_delay", "fade_seconds"])
        this._number(settings[key], key, more, t);
      details.append(more);
      const mode = settings.mode;
      if (mode) {
        const label = node("label", t.mode, "field");
        const select = node("select");
        select.setAttribute("aria-label", t.mode);
        for (const option of ["primary", "equal"]) {
          const el = node("option", t[option]);
          el.value = option;
          select.append(el);
        }
        select.value = mode.state;
        select.disabled = !valid(mode) || this._busy.has(mode.entity_id);
        select.addEventListener("change", () =>
          this._call(mode, "select_option", { option: select.value }),
        );
        label.append(select);
        details.append(label);
      }
      details.append(node("p", t.sensors, "muted"));
      const sensors = node("ul");
      for (const entity of [a.primary, ...(a.secondary || [])].filter(
        Boolean,
      )) {
        const s = hass.states[entity];
        sensors.append(
          node(
            "li",
            `${friendly(entity)}: ${valid(s) ? (s.state === "on" ? t.occupied : t.clear) : t.unavailable}`,
          ),
        );
      }
      details.append(sensors);
      details.append(node("p", t.sources, "muted"));
      const sources = node("ol");
      sources.className = "muted";
      for (const source of a.sources || [])
        sources.append(node("li", friendly(source)));
      details.append(sources);
      const link = node("a", t.edit);
      link.href = "/config/integrations/integration/sonos_follow_me";
      details.append(link);
      room.append(details);
      container.append(room);
    }
    this.shadowRoot.replaceChildren(style, card);
  }
}

class SonosFollowMeEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }
  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot.activeElement) this._render();
  }
  _render() {
    if (!this._config || !this._hass) return;
    const t = lang(this._hass);
    this.shadowRoot.replaceChildren(node("style", css));
    const titleLabel = node("label", t.title, "field"),
      title = node("input");
    title.type = "text";
    title.value = this._config.title || "";
    title.setAttribute("aria-label", t.title);
    title.addEventListener("change", () =>
      this._emit({ ...this._config, title: title.value }),
    );
    titleLabel.append(title);
    this.shadowRoot.append(titleLabel, node("p", t.choose));
    const selected = this._config.entities || [];
    for (const room of roomSwitches(this._hass)) {
      const label = node("label", undefined, "row"),
        input = node("input");
      input.type = "checkbox";
      input.checked = selected.includes(room.entity_id);
      label.append(
        node("span", room.attributes.room_name || room.entity_id),
        input,
      );
      input.addEventListener("change", () => {
        const ids = new Set(this._config.entities || []);
        input.checked ? ids.add(room.entity_id) : ids.delete(room.entity_id);
        this._emit({ ...this._config, entities: [...ids] });
      });
      this.shadowRoot.append(label);
    }
  }
  _emit(config) {
    this._config = config;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      }),
    );
  }
}
if (!customElements.get("sonos-follow-me-card"))
  customElements.define("sonos-follow-me-card", SonosFollowMeCard);
if (!customElements.get("sonos-follow-me-card-editor"))
  customElements.define("sonos-follow-me-card-editor", SonosFollowMeEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "sonos-follow-me-card"))
  window.customCards.push({
    type: "sonos-follow-me-card",
    name: "Sonos Follow Me",
    description: "Follow Me rooms, presence and volume settings",
    preview: true,
  });
