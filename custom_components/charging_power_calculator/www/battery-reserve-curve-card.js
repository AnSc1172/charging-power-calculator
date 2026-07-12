class BatteryReserveCurveCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._dragging = null;
    this._hass = null;
    this._curve = [];
    this._boundMouseMove = this._onMouseMove.bind(this);
    this._boundMouseUp = this._onMouseUp.bind(this);
    this._boundTouchMove = this._onTouchMove.bind(this);
    this._boundTouchEnd = this._onTouchEnd.bind(this);
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity (battery_reserve_power sensor)");
    }
    this._config = config;
  }

  static getConfigElement() {
    return document.createElement("battery-reserve-curve-card-editor");
  }

  static getStubConfig() {
    return { entity: "" };
  }

  getCardSize() {
    return 4;
  }

  _update() {
    if (!this._hass || !this._config.entity) return;

    const state = this._hass.states[this._config.entity];
    if (!state) {
      this.shadowRoot.innerHTML = `<ha-card header="Battery Reserve Curve"><div class="card-content">Entity not found: ${this._config.entity}</div></ha-card>`;
      return;
    }

    const curve = state.attributes.curve || [[0, 3000], [20, 2500], [60, 2000], [80, 500], [100, 500]];
    const entryId = state.attributes.entry_id;
    const currentValue = parseFloat(state.state) || 0;

    if (this._dragging === null) {
      this._curve = JSON.parse(JSON.stringify(curve));
    }

    this._entryId = entryId;
    this._currentValue = currentValue;
    this._render();
  }

  _render() {
    const curve = this._curve;
    const maxWatts = this._config.max_watts || 5000;
    const title = this._config.title || "Battery Reserve Curve";

    const padding = { top: 30, right: 30, bottom: 50, left: 60 };
    const width = 400;
    const height = 250;
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const toX = (soc) => padding.left + (soc / 100) * chartW;
    const toY = (watts) => padding.top + chartH - (watts / maxWatts) * chartH;

    let pathD = "";
    const sorted = [...curve].sort((a, b) => a[0] - b[0]);
    sorted.forEach((point, i) => {
      const x = toX(point[0]);
      const y = toY(point[1]);
      pathD += i === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`;
    });

    const gridLinesX = [0, 25, 50, 75, 100];
    const gridLinesY = [];
    for (let w = 0; w <= maxWatts; w += 1000) gridLinesY.push(w);

    let gridSvg = "";
    gridLinesX.forEach((soc) => {
      const x = toX(soc);
      gridSvg += `<line x1="${x}" y1="${padding.top}" x2="${x}" y2="${padding.top + chartH}" stroke="var(--divider-color, #e0e0e0)" stroke-width="0.5"/>`;
      gridSvg += `<text x="${x}" y="${padding.top + chartH + 18}" text-anchor="middle" fill="var(--primary-text-color)" font-size="11">${soc}%</text>`;
    });
    gridLinesY.forEach((watts) => {
      const y = toY(watts);
      gridSvg += `<line x1="${padding.left}" y1="${y}" x2="${padding.left + chartW}" y2="${y}" stroke="var(--divider-color, #e0e0e0)" stroke-width="0.5"/>`;
      gridSvg += `<text x="${padding.left - 8}" y="${y + 4}" text-anchor="end" fill="var(--primary-text-color)" font-size="11">${watts}</text>`;
    });

    let pointsSvg = "";
    sorted.forEach((point, i) => {
      const x = toX(point[0]);
      const y = toY(point[1]);
      pointsSvg += `<circle cx="${x}" cy="${y}" r="8" fill="var(--primary-color, #03a9f4)" stroke="white" stroke-width="2"
        data-index="${i}" class="draggable" style="cursor: grab;"/>`;
      pointsSvg += `<text x="${x}" y="${y - 14}" text-anchor="middle" fill="var(--primary-text-color)" font-size="10" pointer-events="none">${Math.round(point[1])}W</text>`;
    });

    let currentIndicator = "";
    if (this._hass && this._config.entity) {
      const sensorState = this._hass.states[this._config.entity];
      if (sensorState) {
        const socEntity = this._config.soc_entity;
        if (socEntity && this._hass.states[socEntity]) {
          const currentSoc = parseFloat(this._hass.states[socEntity].state) || 0;
          const cx = toX(currentSoc);
          const cy = toY(this._currentValue);
          currentIndicator = `<circle cx="${cx}" cy="${cy}" r="5" fill="var(--accent-color, #ff9800)" stroke="white" stroke-width="1.5"/>`;
          currentIndicator += `<line x1="${cx}" y1="${padding.top}" x2="${cx}" y2="${padding.top + chartH}" stroke="var(--accent-color, #ff9800)" stroke-width="1" stroke-dasharray="4 2" opacity="0.6"/>`;
        }
      }
    }

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        .chart-container { position: relative; width: 100%; max-width: 450px; margin: 0 auto; }
        svg { width: 100%; height: auto; touch-action: none; user-select: none; }
        .draggable:hover { r: 10; }
        .controls { display: flex; gap: 8px; margin-top: 12px; justify-content: center; flex-wrap: wrap; }
        .controls button {
          background: var(--primary-color, #03a9f4);
          color: white;
          border: none;
          border-radius: 4px;
          padding: 6px 12px;
          cursor: pointer;
          font-size: 12px;
        }
        .controls button:hover { opacity: 0.8; }
        .controls button.secondary {
          background: var(--secondary-text-color, #757575);
        }
        .axis-label {
          font-size: 12px;
          fill: var(--secondary-text-color, #757575);
        }
        .info { text-align: center; margin-top: 8px; font-size: 13px; color: var(--secondary-text-color); }
      </style>
      <ha-card header="${title}">
        <div class="card-content">
          <div class="chart-container">
            <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
              ${gridSvg}
              <text x="${padding.left + chartW / 2}" y="${height - 5}" text-anchor="middle" class="axis-label">Battery SoC (%)</text>
              <text x="15" y="${padding.top + chartH / 2}" text-anchor="middle" class="axis-label" transform="rotate(-90, 15, ${padding.top + chartH / 2})">Reserve (W)</text>
              <path d="${pathD}" fill="none" stroke="var(--primary-color, #03a9f4)" stroke-width="2.5" stroke-linejoin="round"/>
              <path d="${pathD} L ${toX(sorted[sorted.length - 1][0])} ${toY(0)} L ${toX(sorted[0][0])} ${toY(0)} Z" fill="var(--primary-color, #03a9f4)" opacity="0.1"/>
              ${currentIndicator}
              ${pointsSvg}
            </svg>
          </div>
          <div class="info">Current reserve: <strong>${Math.round(this._currentValue)} W</strong></div>
          <div class="controls">
            <button class="add-point">+ Add Point</button>
            <button class="remove-point secondary">- Remove Last</button>
            <button class="save-curve">Save Curve</button>
          </div>
        </div>
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll(".draggable").forEach((el) => {
      el.addEventListener("mousedown", (e) => this._onMouseDown(e));
      el.addEventListener("touchstart", (e) => this._onTouchStart(e), { passive: false });
    });

    this.shadowRoot.querySelector(".add-point").addEventListener("click", () => this._addPoint());
    this.shadowRoot.querySelector(".remove-point").addEventListener("click", () => this._removePoint());
    this.shadowRoot.querySelector(".save-curve").addEventListener("click", () => this._saveCurve());
  }

  _getSvgPoint(clientX, clientY) {
    const svg = this.shadowRoot.querySelector("svg");
    const rect = svg.getBoundingClientRect();
    const padding = { top: 30, right: 30, bottom: 50, left: 60 };
    const width = 400;
    const height = 250;
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const svgX = ((clientX - rect.left) / rect.width) * width;
    const svgY = ((clientY - rect.top) / rect.height) * height;

    const soc = Math.max(0, Math.min(100, ((svgX - padding.left) / chartW) * 100));
    const maxWatts = this._config.max_watts || 5000;
    const watts = Math.max(0, Math.min(maxWatts, ((padding.top + chartH - svgY) / chartH) * maxWatts));

    return { soc: Math.round(soc), watts: Math.round(watts / 50) * 50 };
  }

  _onMouseDown(e) {
    e.preventDefault();
    const index = parseInt(e.target.dataset.index);
    this._dragging = index;
    document.addEventListener("mousemove", this._boundMouseMove);
    document.addEventListener("mouseup", this._boundMouseUp);
  }

  _onMouseMove(e) {
    if (this._dragging === null) return;
    const { soc, watts } = this._getSvgPoint(e.clientX, e.clientY);
    const sorted = [...this._curve].sort((a, b) => a[0] - b[0]);
    sorted[this._dragging] = [soc, watts];
    this._curve = sorted;
    this._render();
  }

  _onMouseUp() {
    this._dragging = null;
    document.removeEventListener("mousemove", this._boundMouseMove);
    document.removeEventListener("mouseup", this._boundMouseUp);
  }

  _onTouchStart(e) {
    e.preventDefault();
    const index = parseInt(e.target.dataset.index);
    this._dragging = index;
    document.addEventListener("touchmove", this._boundTouchMove, { passive: false });
    document.addEventListener("touchend", this._boundTouchEnd);
  }

  _onTouchMove(e) {
    e.preventDefault();
    if (this._dragging === null) return;
    const touch = e.touches[0];
    const { soc, watts } = this._getSvgPoint(touch.clientX, touch.clientY);
    const sorted = [...this._curve].sort((a, b) => a[0] - b[0]);
    sorted[this._dragging] = [soc, watts];
    this._curve = sorted;
    this._render();
  }

  _onTouchEnd() {
    this._dragging = null;
    document.removeEventListener("touchmove", this._boundTouchMove);
    document.removeEventListener("touchend", this._boundTouchEnd);
  }

  _addPoint() {
    const sorted = [...this._curve].sort((a, b) => a[0] - b[0]);
    const lastSoc = sorted.length > 0 ? sorted[sorted.length - 1][0] : 0;
    const newSoc = Math.min(100, lastSoc + 10);
    const maxWatts = this._config.max_watts || 5000;
    this._curve.push([newSoc, maxWatts / 2]);
    this._render();
  }

  _removePoint() {
    if (this._curve.length > 2) {
      this._curve.pop();
      this._render();
    }
  }

  _saveCurve() {
    if (!this._hass || !this._entryId) return;
    const sorted = [...this._curve].sort((a, b) => a[0] - b[0]);
    this._hass.callService("charging_power_calculator", "set_battery_reserve_curve", {
      entry_id: this._entryId,
      curve: sorted,
    });
  }
}

customElements.define("battery-reserve-curve-card", BatteryReserveCurveCard);

class BatteryReserveCurveCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        .row { margin-bottom: 12px; }
        label { display: block; font-weight: 500; margin-bottom: 4px; }
        input { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid var(--divider-color); border-radius: 4px; }
      </style>
      <div>
        <div class="row">
          <label>Battery Reserve Power Entity</label>
          <input type="text" id="entity" value="${this._config.entity || ""}" placeholder="sensor.charging_power_calculator_battery_reserve_power"/>
        </div>
        <div class="row">
          <label>Battery SoC Entity (for current marker)</label>
          <input type="text" id="soc_entity" value="${this._config.soc_entity || ""}" placeholder="sensor.house_battery_soc"/>
        </div>
        <div class="row">
          <label>Max Watts (Y-axis)</label>
          <input type="number" id="max_watts" value="${this._config.max_watts || 5000}" min="1000" max="20000" step="500"/>
        </div>
        <div class="row">
          <label>Title</label>
          <input type="text" id="title" value="${this._config.title || "Battery Reserve Curve"}"/>
        </div>
      </div>
    `;

    ["entity", "soc_entity", "max_watts", "title"].forEach((field) => {
      this.shadowRoot.getElementById(field).addEventListener("change", (e) => {
        const newConfig = { ...this._config };
        newConfig[field] = field === "max_watts" ? parseInt(e.target.value) : e.target.value;
        this._config = newConfig;
        const event = new CustomEvent("config-changed", { detail: { config: newConfig } });
        this.dispatchEvent(event);
      });
    });
  }
}

customElements.define("battery-reserve-curve-card-editor", BatteryReserveCurveCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "battery-reserve-curve-card",
  name: "Battery Reserve Curve",
  description: "Visual editor for the battery reserve characteristic curve",
  preview: true,
});
