const emptyDashboard = {
  generated_at: null,
  cards: [
    { label: "Carbon market signal", value: "Dashboard data not loaded" },
    { label: "Auction demand signal", value: "Dashboard data not loaded" },
    { label: "GB power signal", value: "Dashboard data not loaded" },
    { label: "REGO control signal", value: "Dashboard data not loaded" },
    { label: "Contract exposure signal", value: "Dashboard data not loaded" },
    { label: "Data quality signal", value: "Dashboard data not loaded" }
  ],
  analyst_attention: ["Run python src/build_all.py, then serve the project root with python -m http.server 8000."],
  carbon: { series: [], uka_ccm_context: { available: false, series: [] } },
  auction: { series: [] },
  power: { series: [], latest_generation_mix: {}, source: {} },
  rego_contract_summary: [],
  rego_exceptions: [],
  source_quality: { issues: [], sources_registered: 0, warning_count: 0, stale_source_count: 0, manual_sources_requiring_notes: 0 },
  data_basis: [
    { label: "Carbon market", value: "EEX/GOV.UK + manual ICE UKA" },
    { label: "Power", value: "NESO Carbon Intensity API" },
    { label: "REGO controls", value: "Representative demo supplier-style ledger" },
    { label: "Contracts", value: "Representative demo contracts" }
  ]
};

let dashboard = emptyDashboard;

function setDataStatus(kind, message) {
  const status = document.querySelector("#data-status");
  if (!status) return;
  status.className = `data-status data-status--${kind}`;
  status.textContent = message;
}

async function loadJson(path) {
  if (window.location.protocol === "file:") {
    return {
      status: "file",
      data: emptyDashboard,
      message: "Serve the project root: python -m http.server 8000, then open http://localhost:8000."
    };
  }

  try {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) {
      return { status: "missing", data: emptyDashboard, message: `Missing ${path}. Run python src/build_all.py from the project root.` };
    }
    const data = mergeDashboard(await response.json());
    if (isDashboardStale(data)) {
      return { status: "stale", data, message: "Data loaded, but the NESO build-time fetch is more than 48 hours old. Re-run python src/build_all.py." };
    }
    return { status: "loaded", data, message: buildLoadedStatus(data) };
  } catch (error) {
    return { status: "malformed", data: emptyDashboard, message: `Dashboard JSON could not be parsed: ${error.message}` };
  }
}

function buildLoadedStatus(data) {
  if (!data.generated_at) {
    return "Python-generated signal and reconciliation outputs · Static HTML dashboard";
  }
  const timestamp = data.generated_at.endsWith("Z") ? data.generated_at.replace("Z", " UTC") : `${data.generated_at} UTC`;
  return `Built from Python-generated outputs · Last build: ${timestamp}`;
}

async function loadText(path, fallback) {
  try {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) return fallback;
    return await response.text();
  } catch {
    return fallback;
  }
}

function mergeDashboard(data) {
  return {
    ...emptyDashboard,
    ...data,
    carbon: { ...emptyDashboard.carbon, ...(data.carbon || {}) },
    auction: { ...emptyDashboard.auction, ...(data.auction || {}) },
    power: { ...emptyDashboard.power, ...(data.power || {}) },
    source_quality: { ...emptyDashboard.source_quality, ...(data.source_quality || {}) },
    cards: Array.isArray(data.cards) ? data.cards : emptyDashboard.cards,
    analyst_attention: Array.isArray(data.analyst_attention) ? data.analyst_attention : emptyDashboard.analyst_attention,
    rego_contract_summary: Array.isArray(data.rego_contract_summary) ? data.rego_contract_summary : [],
    rego_exceptions: Array.isArray(data.rego_exceptions) ? data.rego_exceptions : [],
    data_basis: Array.isArray(data.data_basis) ? data.data_basis : emptyDashboard.data_basis
  };
}

function isDashboardStale(data) {
  const fetchedAt = data.power?.source?.fetched_at || data.generated_at;
  if (!fetchedAt) return true;
  const fetchedTime = Date.parse(fetchedAt);
  if (Number.isNaN(fetchedTime)) return true;
  return Date.now() - fetchedTime > 48 * 60 * 60 * 1000;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value, digits = 0) {
  return Number(value || 0).toLocaleString("en-GB", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  });
}

function formatMoney(value) {
  return `GBP ${Number(value || 0).toLocaleString("en-GB", { maximumFractionDigits: 0 })}`;
}

function cardImplication(card) {
  // Prefer the rich, number-bearing subline from the Python pipeline.
  const subline = String(card.subline || "").trim();
  if (subline) return subline;

  const label = String(card.label || "").toLowerCase();
  const headline = String(card.headline || card.value || "").toLowerCase();
  if (label.includes("carbon"))  return "UKA below EUA-equivalent level; monitor UK-specific divergence.";
  if (label.includes("auction")) return "Cover ratio close to recent average.";
  if (label.includes("power")) {
    return headline.includes("below")
      ? "Lower near-term emissions-pressure signal."
      : headline.includes("above")
        ? "Higher emissions-pressure context for market review."
        : "Near recent physical emissions backdrop.";
  }
  if (label.includes("rego"))     return "Review high-severity exceptions before disclosure close.";
  if (label.includes("exposure")) return "Shortfall creates assumed replacement-cost exposure.";
  if (label.includes("quality"))  return "Resolve source-register warnings before publishing outputs.";
  return "";
}

function renderSummaryCards(cards) {
  document.querySelector("#summary-cards").innerHTML = cards.map((card) => `
    <div class="summary-item">
      <dt>${escapeHtml(card.label)}</dt>
      <dd>${escapeHtml(card.headline || card.value)}</dd>
      <p>${escapeHtml(cardImplication(card))}</p>
    </div>
  `).join("");
}

function renderDataBasis(items) {
  document.querySelector("#data-basis-list").innerHTML = items.map((item) => `
    <div class="basis-item">
      <dt>${escapeHtml(item.label)}</dt>
      <dd>${escapeHtml(item.value)}</dd>
    </div>
  `).join("");
}

function renderAttention(items) {
  document.querySelector("#analyst-attention").innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderExecutiveStrip(summary) {
  const contracts = summary.rego_contract_summary || [];
  const exceptions = summary.rego_exceptions || [];
  const sourceQuality = summary.source_quality || {};
  const totalShortfall = contracts.reduce((sum, row) => sum + Number(row.shortfall_mwh || 0), 0);
  const totalExposure = contracts.reduce((sum, row) => sum + Number(row.estimated_replacement_exposure_gbp || 0), 0);
  const affectedContracts = contracts.filter((row) => Number(row.shortfall_mwh || 0) > 0).length;
  const highExceptions = exceptions.filter((row) => row.severity === "High").length;

  document.querySelector("#executive-strip").innerHTML = [
    { label: "Affected contracts", value: `${formatNumber(affectedContracts)} with shortfall` },
    { label: "Eligible shortfall", value: `${formatNumber(totalShortfall)} MWh` },
    { label: "Replacement exposure", value: formatMoney(totalExposure) },
    { label: "High exceptions", value: formatNumber(highExceptions) },
    { label: "Source warnings", value: formatNumber(sourceQuality.warning_count) }
  ].map((item) => `
    <dl class="strip-item">
      <dt>${escapeHtml(item.label)}</dt>
      <dd>${escapeHtml(item.value)}</dd>
    </dl>
  `).join("");
}

function renderFactRow(selector, facts) {
  document.querySelector(selector).innerHTML = facts.map((fact) => `
    <div class="fact">
      <dt>${escapeHtml(fact.label)}</dt>
      <dd>${escapeHtml(fact.value)}</dd>
    </div>
  `).join("");
}

function renderCarbonConcepts(summary) {
  const carbon = summary.carbon || {};
  const ccm = carbon.uka_ccm_context || {};
  const marketReference = carbon.market_reference || {};
  const auctionPeriod = carbon.sample_period_start && carbon.sample_period_end
    ? `${carbon.sample_period_start} to ${carbon.sample_period_end}`
    : "n/a";
  const ccmLine = ccm.available
    ? `${ccm.latest_month || "n/a"} monthly average ${ccm.latest_monthly_average_price_gbp !== null && ccm.latest_monthly_average_price_gbp !== undefined ? `GBP ${ccm.latest_monthly_average_price_gbp}` : "n/a"}; trigger ${ccm.latest_trigger_price_gbp !== null && ccm.latest_trigger_price_gbp !== undefined ? `GBP ${ccm.latest_trigger_price_gbp}` : "n/a"}`
    : "GOV.UK CCM data not loaded.";
  const marketTitle = marketReference.enabled && marketReference.available
    ? "Trading Economics EU Carbon"
    : "Not configured";
  const marketStatus = marketReference.enabled && marketReference.available
    ? "Third-party reference only"
    : "No API-key source loaded";
  const marketDetail = marketReference.enabled && marketReference.available
    ? `Latest ${marketReference.latest_price_eur !== undefined ? `EUR ${marketReference.latest_price_eur}` : "n/a"} on ${marketReference.latest_date || "n/a"}; not an official exchange feed.`
    : "Trading Economics integration is optional and runs only in the Python/GitHub Actions build when a secret is configured.";

  const concepts = [
    {
      label: "Official auction signal",
      title: "UKA/EUA primary auctions",
      detail: `EEX EUA auction data + manually curated ICE UKA input. Comparison window: ${auctionPeriod}.`,
      status: "Used for spread and auction demand",
    },
    {
      label: "Official UKA context",
      title: "GOV.UK CCM table",
      detail: ccmLine,
      status: "Monthly futures-average and trigger context",
    },
    {
      label: "Optional market reference",
      title: marketTitle,
      detail: marketDetail,
      status: marketStatus,
    },
  ];

  document.querySelector("#carbon-concepts").innerHTML = concepts.map((item) => `
    <article class="carbon-concept">
      <p>${escapeHtml(item.label)}</p>
      <h3>${escapeHtml(item.title)}</h3>
      <strong>${escapeHtml(item.status)}</strong>
      <span>${escapeHtml(item.detail)}</span>
    </article>
  `).join("");
}

function renderCarbonMetrics(summary) {
  const carbon = summary.carbon || {};
  const auction = summary.auction || {};
  const ccm = carbon.uka_ccm_context || {};
  const ccmAverage = ccm.latest_monthly_average_price_gbp !== undefined && ccm.latest_monthly_average_price_gbp !== null
    ? `GBP ${ccm.latest_monthly_average_price_gbp}`
    : "n/a";
  const ccmTrigger = ccm.latest_trigger_price_gbp !== undefined && ccm.latest_trigger_price_gbp !== null
    ? `GBP ${ccm.latest_trigger_price_gbp}`
    : "n/a";
  document.querySelector("#carbon-sample-period").textContent = formatCarbonSampleWindow(carbon.sample_period_label);
  document.querySelector("#carbon-fx-note").textContent = formatCarbonFxNote(carbon.currency_note);
  const feedNote = document.querySelector("#carbon-feed-note");
  if (feedNote) {
    const marketPhrase = carbon.market_reference && carbon.market_reference.enabled && carbon.market_reference.available
      ? `Optional third-party reference: Trading Economics ${carbon.market_reference.latest_date || "latest date n/a"} at EUR ${carbon.market_reference.latest_price_eur ?? "n/a"}; not an official exchange feed.`
      : "Optional third-party market reference not configured.";
    feedNote.textContent = ccm.available
      ? `Auction signal: official EEX EUA + manually curated ICE UKA. UKA context: GOV.UK CCM monthly table. ${marketPhrase} Latest CCM month: ${ccm.latest_month || "n/a"}; triggered: ${ccm.latest_ccm_triggered || "n/a"}.`
      : `Auction signal: EEX/ICE auction inputs. UKA CCM context not loaded. ${marketPhrase}`;
  }
  renderFactRow("#carbon-metrics", [
    { label: "Latest UKA", value: carbon.latest_uka_price_gbp ? `GBP ${carbon.latest_uka_price_gbp}` : "n/a" },
    { label: "Latest EUA", value: carbon.latest_eua_price_eur ? `EUR ${carbon.latest_eua_price_eur}` : "n/a" },
    { label: "EUA in GBP", value: carbon.latest_eua_price_gbp ? `GBP ${carbon.latest_eua_price_gbp}` : "n/a" },
    { label: "Spread in GBP", value: carbon.latest_spread_gbp !== undefined ? `GBP ${carbon.latest_spread_gbp}` : "n/a" },
    { label: "UKA CCM avg", value: ccmAverage },
    { label: "CCM trigger", value: ccmTrigger },
    { label: "Regime", value: carbon.spread_regime ?? "n/a" },
    { label: "Auction demand", value: auction.demand_signal ?? "n/a" }
  ]);
}

function formatCarbonSampleWindow(label) {
  return String(label || "").replace(/^Carbon market (sample|comparison) period:\s*/i, "");
}

function formatCarbonFxNote(note) {
  const match = String(note || "").match(/EUR\/GBP assumption of ([0-9.]+)/i);
  return match ? `static EUR/GBP ${match[1]}` : String(note || "");
}

function renderPowerMetrics(summary) {
  const power = summary.power || {};
  renderFactRow("#power-metrics", [
    { label: "Latest intensity", value: power.latest_carbon_intensity_gco2_kwh ? `${power.latest_carbon_intensity_gco2_kwh} g/kWh` : "n/a" },
    { label: "Recent average", value: power.average_recent_carbon_intensity_gco2_kwh ? `${power.average_recent_carbon_intensity_gco2_kwh} g/kWh` : "n/a" },
    { label: "Gas share", value: power.gas_share !== undefined ? `${power.gas_share}%` : "n/a" },
    { label: "Wind + solar", value: power.wind_solar_share !== undefined ? `${power.wind_solar_share}%` : "n/a" },
    { label: "Fetched", value: power.source?.fetched_at || "n/a" }
  ]);
}

function setChartCaption(selector, text) {
  const element = document.querySelector(selector);
  if (element) element.textContent = text;
}

function renderChartCaptions(summary) {
  const power = summary.power || {};
  const mix = power.latest_generation_mix || {};
  const latest = Number(power.latest_carbon_intensity_gco2_kwh || 0);
  const average = Number(power.average_recent_carbon_intensity_gco2_kwh || 0);
  const gas = power.gas_share !== undefined ? `${power.gas_share}%` : "n/a";
  const topMix = Object.entries(mix).sort((a, b) => Number(b[1]) - Number(a[1]))[0];
  const intensityContext = latest && average && latest < average
    ? `Latest intensity remains below the recent average; gas share is ${gas}.`
    : latest && average && latest > average
      ? `Latest intensity is above the recent average; gas share is ${gas}.`
      : `Latest intensity is close to the recent average; gas share is ${gas}.`;

  setChartCaption("#power-line-caption", intensityContext);
  setChartCaption(
    "#generation-bars-caption",
    topMix ? `${topMix[0]} is the largest current contributor in the latest mix; gas share remains an important emissions driver.` : "Latest mix data are loaded from the power signal output."
  );
  setChartCaption("#carbon-price-caption", "Official EEX EUA auction data are compared with manually curated ICE UKA auction inputs over the displayed period.");
  setChartCaption("#carbon-spread-caption", "Spread is FX-adjusted using the stated EUR/GBP assumption; GOV.UK CCM context is separate from auction clearing prices.");
  const ccm = summary.carbon?.uka_ccm_context || {};
  setChartCaption(
    "#ccm-price-caption",
    ccm.available
      ? "Official GOV.UK CCM monthly average futures prices are shown against trigger prices; these are not auction clearing prices."
      : "GOV.UK CCM context is not loaded."
  );
}

function renderSourceQuality(sourceQuality) {
  renderFactRow("#source-quality", [
    { label: "Sources", value: formatNumber(sourceQuality.sources_registered) },
    { label: "Warnings", value: formatNumber(sourceQuality.warning_count) },
    { label: "Stale", value: formatNumber(sourceQuality.stale_source_count) },
    { label: "Manual notes", value: formatNumber(sourceQuality.manual_sources_requiring_notes) }
  ]);

  const issues = sourceQuality.issues || [];
  if (!issues.length) {
    document.querySelector("#source-issues").innerHTML = '<p class="empty-state">No source-register warnings found.</p>';
    return;
  }
  document.querySelector("#source-issues").innerHTML = table([
    "Severity", "Source", "Control", "Issue", "Suggested action"
  ], issues.map((issue) => [
    severity(issue.severity),
    `${idCell(issue.source_id)}<br><span class="muted">${escapeHtml(issue.dataset_name)}</span>`,
    idCell(issue.control_id),
    escapeHtml(issue.issue),
    escapeHtml(issue.suggested_action)
  ]));
}

function renderContractSummary(contracts) {
  if (!contracts.length) {
    document.querySelector("#rego-summary").innerHTML = '<p class="empty-state">No contract summary available. Run the Python pipeline.</p>';
    return;
  }

  document.querySelector("#rego-summary").innerHTML = table([
    "Contract", "Counterparty", "Required", "Eligible", "Shortfall / surplus", "Estimated cover cost", "Status"
  ], contracts.map((row) => [
    idCell(row.contract_id),
    escapeHtml(row.counterparty),
    `${formatNumber(row.required_mwh)} MWh`,
    `${formatNumber(row.eligible_matched_mwh)} MWh`,
    coverageDelta(row),
    row.shortfall_mwh > 0 ? formatMoney(row.estimated_replacement_exposure_gbp) : "GBP 0",
    `<span class="status-pill ${statusClass(row.coverage_status)}">${escapeHtml(row.coverage_status)}</span>`
  ]));

  renderCoverageBars("rego-bars", contracts);
}

function coverageDelta(row) {
  if (Number(row.shortfall_mwh) > 0) {
    return `${formatNumber(row.shortfall_mwh)} MWh shortfall`;
  }
  if (Number(row.surplus_mwh) > 0) {
    return `${formatNumber(row.surplus_mwh)} MWh surplus`;
  }
  return "No gap";
}

function statusClass(status) {
  return {
    Covered: "status-covered",
    Surplus: "status-surplus",
    Shortfall: "status-shortfall",
    Review: "status-review"
  }[status] || "status-review";
}

function renderCoverageBars(containerId, contracts) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (!contracts.length) {
    container.innerHTML = '<p class="empty-state">No contract coverage available.</p>';
    return;
  }

  container.innerHTML = contracts.map((row) => {
    const required = Number(row.required_mwh) || 0;
    const eligible = Number(row.eligible_matched_mwh) || 0;
    const shortfall = Math.max(Number(row.shortfall_mwh) || 0, 0);
    const surplus = Math.max(Number(row.surplus_mwh) || 0, 0);
    const coveredWidth = required ? Math.min(eligible, required) / required * 100 : 0;
    const shortfallWidth = required ? shortfall / required * 100 : 0;
    const rowStatusClass = statusClass(row.coverage_status).replace("status-", "coverage-row--");
    const label = `${escapeHtml(row.contract_id)} ${escapeHtml(row.counterparty)}`;
    const delta = shortfall > 0
      ? `${formatNumber(shortfall)} MWh shortfall · ${formatMoney(row.estimated_replacement_exposure_gbp)} cover cost`
      : surplus > 0
        ? `Covered · ${formatNumber(surplus)} MWh surplus`
        : "Covered exactly";

    return `
      <div class="coverage-row ${rowStatusClass}">
        <div class="coverage-row__head">
          <span>${label}</span>
          <strong>${escapeHtml(row.coverage_status)}</strong>
        </div>
        <div class="coverage-track" aria-label="${label}: ${escapeHtml(delta)}">
          <span class="coverage-fill" style="width:${coveredWidth}%"></span>
          ${shortfall > 0 ? `<span class="coverage-gap" style="left:${coveredWidth}%; width:${shortfallWidth}%"></span>` : ""}
          ${surplus > 0 ? '<span class="coverage-surplus-marker" title="Surplus"></span>' : ""}
        </div>
        <div class="coverage-row__meta">
          <span>${formatNumber(eligible)} eligible MWh / ${formatNumber(required)} required MWh</span>
          <span>${delta}</span>
        </div>
      </div>
    `;
  }).join("");
}

function renderRegisterSummary(exceptions) {
  const target = document.querySelector("#register-summary");
  if (!target) return;
  const rows = exceptions || [];
  const high   = rows.filter((r) => r.severity === "High").length;
  const medium = rows.filter((r) => r.severity === "Medium").length;
  const low    = rows.filter((r) => r.severity === "Low").length;

  target.innerHTML = [
    { label: "Exceptions logged", value: formatNumber(rows.length), cls: "" },
    { label: "High severity",     value: formatNumber(high),        cls: "register-high" },
    { label: "Medium severity",   value: formatNumber(medium),      cls: "register-medium" },
    { label: "Low severity",      value: formatNumber(low),         cls: "register-low" }
  ].map((item) => `
    <div>
      <dt>${escapeHtml(item.label)}</dt>
      <dd class="${item.cls}">${escapeHtml(item.value)}</dd>
    </div>
  `).join("");
}

function renderExceptionSummary(exceptions) {
  const bySeverity = countBy(exceptions, "severity");
  const byControl = Object.entries(countBy(exceptions, "control_type"))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  const severityBars = Object.entries(bySeverity).map(([label, value]) => ({
    label,
    value,
    display: String(value),
    color: severityColor(label)
  }));
  const controlBars = byControl.map(([label, value]) => ({
    label,
    value,
    display: String(value),
    color: "#4f6475"
  }));

  document.querySelector("#exception-summary").innerHTML = `
    <div class="register-panel register-panel--severity">
      <h3>Severity profile</h3>
      <div id="severity-bars" class="bars-panel"></div>
    </div>
    <div class="register-panel register-panel--controls">
      <h3>Most frequent controls</h3>
      <div id="control-bars" class="bars-panel"></div>
    </div>
  `;
  renderBarList("severity-bars", severityBars);
  renderBarList("control-bars", controlBars);
}

function populateFilters(exceptions) {
  [
    ["#severity-filter", uniqueValues(exceptions, "severity")],
    ["#contract-filter", uniqueValues(exceptions, "contract_id")],
    ["#control-filter", uniqueValues(exceptions, "control_type")]
  ].forEach(([selector, values]) => {
    document.querySelector(selector).innerHTML = '<option value="">All</option>' + values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
  });
}

function renderExceptionTable() {
  const rows = filteredExceptions();
  if (!rows.length) {
    document.querySelector("#exception-table").innerHTML = '<p class="empty-state">No exceptions match the current filters.</p>';
    return;
  }
  document.querySelector("#exception-table").innerHTML = table([
    "Exception", "Severity", "Control", "Certificate", "Contract", "Issue", "Suggested action"
  ], rows.map((row) => [
    idCell(row.exception_id),
    severity(row.severity),
    `${idCell(row.control_id)}<br><span class="muted">${escapeHtml(row.control_type)}</span>`,
    idCell(row.certificate_id || "-"),
    idCell(row.contract_id || "-"),
    escapeHtml(row.exception_message),
    escapeHtml(row.suggested_action)
  ]));
}

function filteredExceptions() {
  const severityValue = document.querySelector("#severity-filter").value;
  const contractValue = document.querySelector("#contract-filter").value;
  const controlValue = document.querySelector("#control-filter").value;
  return (dashboard.rego_exceptions || []).filter((row) => (
    (!severityValue || row.severity === severityValue)
    && (!contractValue || row.contract_id === contractValue)
    && (!controlValue || row.control_type === controlValue)
  ));
}

function table(headers, rows) {
  return `
    <table>
      <thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody>
    </table>
  `;
}

function severity(value) {
  return `<span class="severity-${escapeHtml(String(value).toLowerCase())}">${escapeHtml(value)}</span>`;
}

function idCell(value) {
  return `<span class="id-text">${escapeHtml(value)}</span>`;
}

function severityColor(value) {
  return { High: "#b3261e", Medium: "#9a5b00", Low: "#4f6475" }[value] || "#4f6475";
}

function uniqueValues(rows, key) {
  return [...new Set(rows.map((row) => row[key]).filter(Boolean))].sort();
}

function countBy(items, key) {
  return items.reduce((acc, item) => {
    const value = item[key] || "Unknown";
    acc[value] = (acc[value] || 0) + 1;
    return acc;
  }, {});
}

function markdownToHtml(markdown) {
  return escapeHtml(markdown)
    .split(/\n{2,}/)
    .map((block) => {
      if (block.startsWith("# ")) return `<h3>${block.slice(2)}</h3>`;
      if (block.startsWith("## ")) return `<h3>${block.slice(3)}</h3>`;
      return `<p>${block.replace(/\n/g, "<br>")}</p>`;
    })
    .join("");
}

function attachFilterEvents() {
  ["#severity-filter", "#contract-filter", "#control-filter"].forEach((selector) => {
    document.querySelector(selector).addEventListener("change", renderExceptionTable);
  });
}

async function initDashboard() {
  const result = await loadJson("data/processed/dashboard_summary.json");
  dashboard = result.data;
  setDataStatus(result.status, result.message);

  renderDataBasis(dashboard.data_basis);
  renderSummaryCards(dashboard.cards);
  renderAttention(dashboard.analyst_attention);
  renderExecutiveStrip(dashboard);
  renderContractSummary(dashboard.rego_contract_summary);
  renderRegisterSummary(dashboard.rego_exceptions);
  renderExceptionSummary(dashboard.rego_exceptions);
  populateFilters(dashboard.rego_exceptions);
  renderExceptionTable();
  renderPowerMetrics(dashboard);
  renderCarbonConcepts(dashboard);
  renderCarbonMetrics(dashboard);
  renderChartCaptions(dashboard);
  renderSourceQuality(dashboard.source_quality);

  const note = await loadText("outputs/analyst_note.md", "# Analyst Note\n\nRun the Python pipeline to generate the analyst note.");
  document.querySelector("#analyst-note").innerHTML = markdownToHtml(note);

  attachFilterEvents();
  if (typeof renderDashboardVisuals === "function") {
    renderDashboardVisuals(dashboard);
  }
}

initDashboard();
