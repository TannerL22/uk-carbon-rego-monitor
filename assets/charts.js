function renderLineChart(containerId, series, fields, options = {}) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (!series.length || !fields.length) {
    container.innerHTML = '<p class="empty-state">No series data available.</p>';
    return;
  }

  const width = 720;
  const height = 220;
  const pad = { top: 12, right: 20, bottom: 30, left: 48 };
  const values = [];
  fields.forEach((field) => {
    series.forEach((row) => {
      const value = Number(row[field.key]);
      if (Number.isFinite(value)) values.push(value);
    });
  });
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const xStep = (width - pad.left - pad.right) / Math.max(series.length - 1, 1);
  const yFor = (value) => pad.top + (max - value) / range * (height - pad.top - pad.bottom);
  const xFor = (index) => pad.left + index * xStep;
  const ticks = [min, min + range / 2, max];

  const paths = fields.map((field) => {
    const d = series.map((row, index) => {
      const value = Number(row[field.key]);
      const x = xFor(index).toFixed(1);
      const y = yFor(Number.isFinite(value) ? value : min).toFixed(1);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    }).join(" ");
    return `<path d="${d}" fill="none" stroke="${field.color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`;
  }).join("");

  // Latest-value annotation on the primary (first) field.
  const lastIndex = series.length - 1;
  const primary = fields[0];
  const lastRaw = lastIndex >= 0 ? Number(series[lastIndex][primary.key]) : NaN;
  let annotation = "";
  if (Number.isFinite(lastRaw)) {
    const lx = xFor(lastIndex);
    const ly = yFor(lastRaw);
    const label = formatAxis(lastRaw, options.unit);
    const textW = Math.max(26, String(label).length * 6.6 + 10);
    const boxX = Math.min(width - pad.right - textW, lx + 6);
    const boxY = Math.max(pad.top, ly - 8);
    annotation = `
      <circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="2.8" fill="${primary.color}" stroke="#fff" stroke-width="1.2"/>
      <rect class="chart-annot-box" x="${boxX.toFixed(1)}" y="${boxY.toFixed(1)}" width="${textW.toFixed(1)}" height="16" rx="2"/>
      <text class="chart-annot" x="${(boxX + textW / 2).toFixed(1)}" y="${(boxY + 11).toFixed(1)}" text-anchor="middle">${escapeHtml(label)}</text>
    `;
  }

  const legend = fields.map((field) => `
    <span class="legend-item"><i style="background:${field.color}"></i>${escapeHtml(field.label)}</span>
  `).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(options.label || "line chart")}">
      <line x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" class="axis-line"/>
      ${ticks.map((tick) => `
        <g>
          <line x1="${pad.left}" y1="${yFor(tick).toFixed(1)}" x2="${width - pad.right}" y2="${yFor(tick).toFixed(1)}" class="grid-line"/>
          <text x="${pad.left - 8}" y="${yFor(tick).toFixed(1)}" text-anchor="end" dominant-baseline="middle">${formatAxis(tick, options.unit)}</text>
        </g>
      `).join("")}
      ${paths}
      ${annotation}
      <text x="${pad.left}" y="${height - 9}" class="axis-label">${escapeHtml(series[0].date || series[0].month || "")}</text>
      <text x="${width - pad.right}" y="${height - 9}" text-anchor="end" class="axis-label">${escapeHtml(series[series.length - 1].date || series[series.length - 1].month || "")}</text>
    </svg>
    <div class="chart-legend">${legend}</div>
  `;
}

function renderBarList(containerId, rows, options = {}) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (!rows.length) {
    container.innerHTML = '<p class="empty-state">No values available.</p>';
    return;
  }
  const max = Math.max(...rows.map((row) => Math.abs(Number(row.value) || 0)), 1);
  container.innerHTML = rows.map((row) => {
    const value = Number(row.value) || 0;
    const width = Math.max(2, Math.abs(value) / max * 100);
    return `
      <div class="bar-row">
        <div class="bar-label">${escapeHtml(row.label)}</div>
        <div class="bar-track"><span style="width:${width}%; background:${row.color || options.color || "#1f6b58"}"></span></div>
        <div class="bar-value">${escapeHtml(row.display ?? formatNumber(value, options.digits ?? 0))}</div>
      </div>
    `;
  }).join("");
}

function renderDashboardVisuals(summary) {
  renderLineChart(
    "power-line",
    summary.power?.series || [],
    [{ key: "carbon_intensity_gco2_kwh", label: "gCO2/kWh", color: "#b3261e" }],
    { label: "GB carbon intensity trend", unit: "g" }
  );

  const mix = summary.power?.latest_generation_mix || {};
  renderBarList("generation-bars", Object.entries(mix).map(([label, value]) => ({
    label,
    value,
    display: `${formatNumber(value, 1)}%`,
    color: generationColor(label)
  })), { digits: 1 });

  renderLineChart(
    "carbon-price-line",
    summary.carbon?.series || [],
    [
      { key: "uka_price_gbp", label: "UKA GBP", color: "#1f6b58" },
      { key: "eua_price_gbp", label: "EUA GBP via FX assumption", color: "#496a9e" }
    ],
    { label: "UKA and EUA auction prices converted to GBP" }
  );

  renderLineChart(
    "carbon-spread-line",
    summary.carbon?.series || [],
    [{ key: "spread_gbp", label: "UKA-EUA spread GBP", color: "#9a5b00" }],
    { label: "UKA-EUA spread in GBP" }
  );

  renderLineChart(
    "ccm-price-line",
    summary.carbon?.uka_ccm_context?.series || [],
    [
      { key: "monthly_average_price_gbp", label: "Monthly average", color: "#1f6b58" },
      { key: "trigger_price_gbp", label: "CCM trigger", color: "#9a5b00" }
    ],
    { label: "UK ETS CCM monthly average and trigger price" }
  );
}

function generationColor(label) {
  const colors = {
    Gas: "#b3261e",
    Wind: "#1f6b58",
    Solar: "#d9a11b",
    Nuclear: "#496a9e",
    Biomass: "#6b7f3f",
    Hydro: "#4f8aa8",
    Imports: "#6f5f7f",
    Coal: "#5d5148",
    Other: "#8b8f88"
  };
  return colors[label] || "#4f6475";
}

function formatAxis(value, unit) {
  const rounded = Math.round(value);
  return unit ? `${rounded}${unit}` : String(rounded);
}
