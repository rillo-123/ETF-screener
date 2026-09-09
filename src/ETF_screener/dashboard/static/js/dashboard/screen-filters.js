// Dashboard screen-filters. See README.md in static/js/dashboard for the feature map.

function normalizeScreenDisqualifiers(raw = null) {
  const source = raw && typeof raw === "object" ? raw : {};
  return {
    exclude_weak_liquidity: Boolean(source.exclude_weak_liquidity),
    exclude_unprofitable: Boolean(source.exclude_unprofitable),
  };
}

function readSavedScreenDisqualifiers() {
  try {
    const raw = localStorage.getItem(LAST_SCREEN_DISQUALIFIERS_KEY);
    if (!raw) {
      return normalizeScreenDisqualifiers();
    }
    return normalizeScreenDisqualifiers(JSON.parse(raw));
  } catch (err) {
    return normalizeScreenDisqualifiers();
  }
}

function persistScreenDisqualifiers() {
  try {
    localStorage.setItem(
      LAST_SCREEN_DISQUALIFIERS_KEY,
      JSON.stringify(normalizeScreenDisqualifiers(screenDisqualifiers))
    );
  } catch (err) {
    return;
  }
}

function syncScreenDisqualifierChrome() {
  const checkboxMap = {
    exclude_weak_liquidity: document.getElementById("disqualify-weak-liquidity"),
    exclude_unprofitable: document.getElementById("disqualify-unprofitable"),
  };
  Object.entries(checkboxMap).forEach(([key, node]) => {
    if (node) {
      node.checked = Boolean(screenDisqualifiers[key]);
    }
  });
}

function getScreenDisqualifierParams() {
  const params = new URLSearchParams();
  Object.entries(normalizeScreenDisqualifiers(screenDisqualifiers)).forEach(([key, enabled]) => {
    if (enabled) {
      params.set(key, "true");
    }
  });
  return params;
}

function setScreenDisqualifier(key, enabled) {
  if (!Object.prototype.hasOwnProperty.call(screenDisqualifiers, key)) {
    return;
  }
  screenDisqualifiers = {
    ...screenDisqualifiers,
    [key]: Boolean(enabled),
  };
  persistScreenDisqualifiers();
  syncScreenDisqualifierChrome();
}

function readSavedScreenAutoExportEnabled() {
  try {
    return String(localStorage.getItem(LAST_SCREEN_AUTO_EXPORT_KEY) || "").trim().toLowerCase() === "true";
  } catch (err) {
    return false;
  }
}

function persistScreenAutoExportEnabled() {
  try {
    localStorage.setItem(LAST_SCREEN_AUTO_EXPORT_KEY, screenAutoExportEnabled ? "true" : "false");
  } catch (err) {
    return;
  }
}

function syncScreenAutoExportChrome() {
  const node = document.getElementById("auto-export-google-drive");
  if (node) {
    node.checked = Boolean(screenAutoExportEnabled);
  }
}

function setScreenAutoExportEnabled(enabled) {
  screenAutoExportEnabled = Boolean(enabled);
  persistScreenAutoExportEnabled();
  syncScreenAutoExportChrome();
}

function coerceFilterBoolean(value, fallback) {
  if (typeof value === "boolean") {
    return value;
  }
  const normalized = String(value ?? "").trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no", "off"].includes(normalized)) {
    return false;
  }
  return fallback;
}

function normalizeScreenFiltersClient(raw = {}) {
  const lookbackDays = Math.round(clampNumber(raw.lookback_days, 30, 365, SCREEN_DEFAULT_FILTERS.lookback_days));
  const volumeMin = clampNumber(raw?.volume_range?.min, 0, 100000000, SCREEN_DEFAULT_FILTERS.volume_range.min);
  const volumeMax = clampNumber(raw?.volume_range?.max, 0, 100000000, SCREEN_DEFAULT_FILTERS.volume_range.max);
  const rawTimelineOrder = Array.isArray(raw.timeline_order) ? raw.timeline_order : DEFAULT_TIMELINE_ORDER;
  const timelineOrder = rawTimelineOrder.map((key) => String(key)).filter((key) => [...DEFAULT_TIMELINE_ORDER, ...REPEATABLE_TIMELINE_KEYS, ...RSI_TIMELINE_KEYS, "ha_ema_volume"].includes(key));
  const rawConditions = Array.isArray(raw.ha_ema_volume_conditions) ? raw.ha_ema_volume_conditions : SCREEN_DEFAULT_FILTERS.ha_ema_volume_conditions;
  const haConditions = ["open", "high", "low", "close"].map((field) => {
    const fallback = SCREEN_DEFAULT_FILTERS.ha_ema_volume_conditions.find((item) => item.field === field);
    const item = rawConditions.find((candidate) => candidate?.field === field) || fallback;
    const zone = ["above_ema1", "between_ema1_ema2", "below_ema2"].includes(String(item?.zone)) ? String(item.zone) : fallback.zone;
    return { field, enabled: coerceFilterBoolean(item?.enabled, fallback.enabled), zone };
  });
  const normalized = {
    lookback_days: lookbackDays,
    volume_range: {
      min: Math.min(volumeMin, volumeMax),
      max: Math.max(volumeMin, volumeMax),
    },
    ha_ema_volume_conditions: haConditions,
    ha_ema_volume_candle_color: ["any", "green", "red"].includes(String(raw.ha_ema_volume_candle_color || "").toLowerCase())
      ? String(raw.ha_ema_volume_candle_color).toLowerCase()
      : SCREEN_DEFAULT_FILTERS.ha_ema_volume_candle_color,
    macd_event_enabled: coerceFilterBoolean(raw.macd_event_enabled, SCREEN_DEFAULT_FILTERS.macd_event_enabled),
    rsi_event_enabled: coerceFilterBoolean(raw.rsi_event_enabled, SCREEN_DEFAULT_FILTERS.rsi_event_enabled),
    rsi_filter_enabled: coerceFilterBoolean(raw.rsi_filter_enabled, SCREEN_DEFAULT_FILTERS.rsi_filter_enabled),
    rsi_filter_min: clampNumber(raw.rsi_filter_min, 0, 100, SCREEN_DEFAULT_FILTERS.rsi_filter_min),
    stoch_event_enabled: coerceFilterBoolean(raw.stoch_event_enabled, SCREEN_DEFAULT_FILTERS.stoch_event_enabled),
    supertrend_event_enabled: coerceFilterBoolean(raw.supertrend_event_enabled, SCREEN_DEFAULT_FILTERS.supertrend_event_enabled),
    ema_relationship_enabled: coerceFilterBoolean(raw.ema_relationship_enabled, SCREEN_DEFAULT_FILTERS.ema_relationship_enabled),
    ema_relationship_fast: Math.round(clampNumber(raw.ema_relationship_fast, 2, 200, SCREEN_DEFAULT_FILTERS.ema_relationship_fast)),
    ema_relationship_slow: Math.round(clampNumber(raw.ema_relationship_slow, 3, 400, SCREEN_DEFAULT_FILTERS.ema_relationship_slow)),
    ema_relationship_slope: ["any", "positive", "negative"].includes(String(raw.ema_relationship_slope || "").trim()) ? String(raw.ema_relationship_slope).trim() : SCREEN_DEFAULT_FILTERS.ema_relationship_slope,
    ema_relationship_allowance: clampNumber(raw.ema_relationship_allowance, 0, 5, SCREEN_DEFAULT_FILTERS.ema_relationship_allowance),
    ema_relationship_fast_slope: ["any", "positive", "negative", "flat"].includes(String(raw.ema_relationship_fast_slope || "").trim()) ? String(raw.ema_relationship_fast_slope).trim() : (String(raw.ema_relationship_slope || "").trim() || SCREEN_DEFAULT_FILTERS.ema_relationship_fast_slope),
    ema_relationship_slow_slope: ["any", "positive", "negative", "flat"].includes(String(raw.ema_relationship_slow_slope || "").trim()) ? String(raw.ema_relationship_slow_slope).trim() : (String(raw.ema_relationship_slope || "").trim() || SCREEN_DEFAULT_FILTERS.ema_relationship_slow_slope),
    ema_relationship_cross_mode: ["cross_up", "cross_down"].includes(String(raw.ema_relationship_cross_mode || "").trim()) ? String(raw.ema_relationship_cross_mode).trim() : SCREEN_DEFAULT_FILTERS.ema_relationship_cross_mode,
    price_ema_event_enabled: coerceFilterBoolean(raw.price_ema_event_enabled, SCREEN_DEFAULT_FILTERS.price_ema_event_enabled),
    price_ema_period: Math.round(clampNumber(raw.price_ema_period, 2, 500, SCREEN_DEFAULT_FILTERS.price_ema_period)),
    price_ema_source: ["open", "high", "low", "close"].includes(String(raw.price_ema_source || "").trim().toLowerCase()) ? String(raw.price_ema_source).trim().toLowerCase() : SCREEN_DEFAULT_FILTERS.price_ema_source,
    price_ema_sources: Array.isArray(raw.price_ema_sources) && raw.price_ema_sources.length
      ? [...new Set(raw.price_ema_sources.map((source) => String(source).trim().toLowerCase()).filter((source) => ["open", "high", "low", "close"].includes(source)))]
      : [String(raw.price_ema_source || SCREEN_DEFAULT_FILTERS.price_ema_source).trim().toLowerCase()],
    price_ema_cross_mode: ["cross_up", "cross_down"].includes(String(raw.price_ema_cross_mode || "").trim()) ? String(raw.price_ema_cross_mode).trim() : SCREEN_DEFAULT_FILTERS.price_ema_cross_mode,
    price_ema_event_age: Math.round(clampNumber(raw.price_ema_event_age, 0, lookbackDays, SCREEN_DEFAULT_FILTERS.price_ema_event_age)),
    ema_flatten_enabled: coerceFilterBoolean(raw.ema_flatten_enabled, SCREEN_DEFAULT_FILTERS.ema_flatten_enabled),
    ema_flatten_period: Math.round(clampNumber(raw.ema_flatten_period, 2, 500, SCREEN_DEFAULT_FILTERS.ema_flatten_period)),
    ema_flatten_lookback: Math.round(clampNumber(raw.ema_flatten_lookback, 1, 30, SCREEN_DEFAULT_FILTERS.ema_flatten_lookback)),
    ema_flatten_tolerance: clampNumber(raw.ema_flatten_tolerance, 0, 5, SCREEN_DEFAULT_FILTERS.ema_flatten_tolerance),
    ema_flatten_mode: ["top", "bottom", "either"].includes(String(raw.ema_flatten_mode || "")) ? String(raw.ema_flatten_mode) : SCREEN_DEFAULT_FILTERS.ema_flatten_mode,
    ema_flatten_event_age: Math.round(clampNumber(raw.ema_flatten_event_age, 0, lookbackDays, SCREEN_DEFAULT_FILTERS.ema_flatten_event_age)),
    rsi_cross_value: clampNumber(raw.rsi_cross_value, 0, 100, SCREEN_DEFAULT_FILTERS.rsi_cross_value),
    rsi_cross_mode: ["cross_up", "cross_down"].includes(String(raw.rsi_cross_mode || "").trim())
      ? String(raw.rsi_cross_mode).trim()
      : SCREEN_DEFAULT_FILTERS.rsi_cross_mode,
    stoch_cross_value: clampNumber(raw.stoch_cross_value, 0, 100, SCREEN_DEFAULT_FILTERS.stoch_cross_value),
    stoch_cross_mode: ["cross_up", "cross_down"].includes(String(raw.stoch_cross_mode || "").trim())
      ? String(raw.stoch_cross_mode).trim()
      : SCREEN_DEFAULT_FILTERS.stoch_cross_mode,
    stoch_cross_region: ["below", "above", "any"].includes(String(raw.stoch_cross_region || "").trim())
      ? String(raw.stoch_cross_region).trim()
      : SCREEN_DEFAULT_FILTERS.stoch_cross_region,
    macd_cross_mode: ["low_cross_buy", "high_cross_sell", "bullish_cross", "bearish_cross"].includes(String(raw.macd_cross_mode || "").trim())
      ? String(raw.macd_cross_mode).trim()
      : SCREEN_DEFAULT_FILTERS.macd_cross_mode,
    macd_event_age: Math.round(clampNumber(
      raw.macd_event_age,
      0,
      lookbackDays,
      raw?.macd_cross_window ? (Number(raw.macd_cross_window.min || 0) + Number(raw.macd_cross_window.max || lookbackDays)) / 2 : SCREEN_DEFAULT_FILTERS.macd_event_age,
    )),
    rsi_event_age: Math.round(clampNumber(
      raw.rsi_event_age,
      0,
      lookbackDays,
      raw?.rsi_cross_window ? (Number(raw.rsi_cross_window.min || 0) + Number(raw.rsi_cross_window.max || lookbackDays)) / 2 : SCREEN_DEFAULT_FILTERS.rsi_event_age,
    )),
    stoch_event_age: Math.round(clampNumber(
      raw.stoch_event_age,
      0,
      lookbackDays,
      raw?.stoch_cross_window ? (Number(raw.stoch_cross_window.min || 0) + Number(raw.stoch_cross_window.max || lookbackDays)) / 2 : SCREEN_DEFAULT_FILTERS.stoch_event_age,
    )),
    supertrend_event_age: Math.round(clampNumber(raw.supertrend_event_age, 0, lookbackDays, SCREEN_DEFAULT_FILTERS.supertrend_event_age)),
    ema_relationship_age: Math.round(clampNumber(raw.ema_relationship_age, 0, lookbackDays, SCREEN_DEFAULT_FILTERS.ema_relationship_age)),
    volume_spike_enabled: coerceFilterBoolean(raw.volume_spike_enabled, SCREEN_DEFAULT_FILTERS.volume_spike_enabled),
    volume_spike_period: Math.round(clampNumber(raw.volume_spike_period, 2, 100, SCREEN_DEFAULT_FILTERS.volume_spike_period)),
    volume_spike_multiplier: clampNumber(raw.volume_spike_multiplier, 1.1, 10, SCREEN_DEFAULT_FILTERS.volume_spike_multiplier),
  volume_spike_age: Math.round(clampNumber(raw.volume_spike_age, 0, lookbackDays, SCREEN_DEFAULT_FILTERS.volume_spike_age)),
    ha_ema_volume_enabled: coerceFilterBoolean(raw.ha_ema_volume_enabled, SCREEN_DEFAULT_FILTERS.ha_ema_volume_enabled),
    ha_ema_volume_ema1_period: Math.round(clampNumber(raw.ha_ema_volume_ema1_period, 2, 500, SCREEN_DEFAULT_FILTERS.ha_ema_volume_ema1_period)),
    ha_ema_volume_ema1_source: ["open", "high", "low", "close"].includes(String(raw.ha_ema_volume_ema1_source || "").toLowerCase()) ? String(raw.ha_ema_volume_ema1_source).toLowerCase() : SCREEN_DEFAULT_FILTERS.ha_ema_volume_ema1_source,
    ha_ema_volume_ema2_period: Math.round(clampNumber(raw.ha_ema_volume_ema2_period, 2, 500, SCREEN_DEFAULT_FILTERS.ha_ema_volume_ema2_period)),
    ha_ema_volume_ema2_source: ["open", "high", "low", "close"].includes(String(raw.ha_ema_volume_ema2_source || "").toLowerCase()) ? String(raw.ha_ema_volume_ema2_source).toLowerCase() : SCREEN_DEFAULT_FILTERS.ha_ema_volume_ema2_source,
    ha_ema_volume_start_field: ["open", "high", "low", "close"].includes(String(raw.ha_ema_volume_start_field || "").toLowerCase()) ? String(raw.ha_ema_volume_start_field).toLowerCase() : SCREEN_DEFAULT_FILTERS.ha_ema_volume_start_field,
    ha_ema_volume_start_line: ["ema1", "ema2"].includes(String(raw.ha_ema_volume_start_line || "")) ? String(raw.ha_ema_volume_start_line) : SCREEN_DEFAULT_FILTERS.ha_ema_volume_start_line,
    ha_ema_volume_start_relation: ["above", "below"].includes(String(raw.ha_ema_volume_start_relation || "")) ? String(raw.ha_ema_volume_start_relation) : SCREEN_DEFAULT_FILTERS.ha_ema_volume_start_relation,
    ha_ema_volume_end_field: ["open", "high", "low", "close"].includes(String(raw.ha_ema_volume_end_field || "").toLowerCase()) ? String(raw.ha_ema_volume_end_field).toLowerCase() : SCREEN_DEFAULT_FILTERS.ha_ema_volume_end_field,
    ha_ema_volume_end_line: ["ema1", "ema2"].includes(String(raw.ha_ema_volume_end_line || "")) ? String(raw.ha_ema_volume_end_line) : SCREEN_DEFAULT_FILTERS.ha_ema_volume_end_line,
    ha_ema_volume_end_relation: ["above", "below"].includes(String(raw.ha_ema_volume_end_relation || "")) ? String(raw.ha_ema_volume_end_relation) : SCREEN_DEFAULT_FILTERS.ha_ema_volume_end_relation,
    ha_ema_volume_period: Math.round(clampNumber(raw.ha_ema_volume_period, 2, 100, SCREEN_DEFAULT_FILTERS.ha_ema_volume_period)),
    ha_ema_volume_multiplier: clampNumber(raw.ha_ema_volume_multiplier, 1.1, 10, SCREEN_DEFAULT_FILTERS.ha_ema_volume_multiplier),
    ha_ema_volume_event_age: Math.round(clampNumber(raw.ha_ema_volume_event_age, 0, lookbackDays, SCREEN_DEFAULT_FILTERS.ha_ema_volume_event_age)),
    supertrend_cross_mode: ["green_to_red", "red_to_green"].includes(String(raw.supertrend_cross_mode || "").trim())
      ? String(raw.supertrend_cross_mode).trim()
      : SCREEN_DEFAULT_FILTERS.supertrend_cross_mode,
    ema_slope_20: ["any", "positive", "flat", "negative"].includes(String(raw.ema_slope_20 || "").trim()) ? String(raw.ema_slope_20).trim() : "any",
    ema_slope_50: ["any", "positive", "flat", "negative"].includes(String(raw.ema_slope_50 || "").trim()) ? String(raw.ema_slope_50).trim() : "any",
    ema_slope_200: ["any", "positive", "flat", "negative"].includes(String(raw.ema_slope_200 || "").trim()) ? String(raw.ema_slope_200).trim() : "any",
    ema_slope_period_1: Math.round(clampNumber(raw.ema_slope_period_1, 2, 500, SCREEN_DEFAULT_FILTERS.ema_slope_period_1)),
    ema_slope_period_2: Math.round(clampNumber(raw.ema_slope_period_2, 2, 500, SCREEN_DEFAULT_FILTERS.ema_slope_period_2)),
    ema_slope_period_3: Math.round(clampNumber(raw.ema_slope_period_3, 2, 500, SCREEN_DEFAULT_FILTERS.ema_slope_period_3)),
    ema_slope_1: ["any", "positive", "flat", "negative"].includes(String(raw.ema_slope_1 || "").trim()) ? String(raw.ema_slope_1).trim() : (raw.ema_slope_20 || "any"),
    ema_slope_2: ["any", "positive", "flat", "negative"].includes(String(raw.ema_slope_2 || "").trim()) ? String(raw.ema_slope_2).trim() : (raw.ema_slope_50 || "any"),
    ema_slope_3: ["any", "positive", "flat", "negative"].includes(String(raw.ema_slope_3 || "").trim()) ? String(raw.ema_slope_3).trim() : (raw.ema_slope_200 || "any"),
    ema_slope_lookback: Math.round(clampNumber(raw.ema_slope_lookback, 1, 30, SCREEN_DEFAULT_FILTERS.ema_slope_lookback)),
    ema_slope_flat_tolerance: clampNumber(raw.ema_slope_flat_tolerance, 0, 5, SCREEN_DEFAULT_FILTERS.ema_slope_flat_tolerance),
    timeline_order: timelineOrder,
    chart_ta: {
      macd_fast: Math.round(clampNumber(raw?.chart_ta?.macd_fast, 2, 100, CHART_TA_DEFAULTS.macd_fast)),
      macd_slow: Math.round(clampNumber(raw?.chart_ta?.macd_slow, 3, 200, CHART_TA_DEFAULTS.macd_slow)),
      macd_signal: Math.round(clampNumber(raw?.chart_ta?.macd_signal, 1, 100, CHART_TA_DEFAULTS.macd_signal)),
      rsi_period: Math.round(clampNumber(raw?.chart_ta?.rsi_period, 2, 100, CHART_TA_DEFAULTS.rsi_period)),
      stoch_rsi_period: Math.round(clampNumber(raw?.chart_ta?.stoch_rsi_period, 2, 100, CHART_TA_DEFAULTS.stoch_rsi_period)),
      stoch_rsi_k: Math.round(clampNumber(raw?.chart_ta?.stoch_rsi_k, 1, 30, CHART_TA_DEFAULTS.stoch_rsi_k)),
      stoch_rsi_d: Math.round(clampNumber(raw?.chart_ta?.stoch_rsi_d, 1, 30, CHART_TA_DEFAULTS.stoch_rsi_d)),
      supertrend_period: Math.round(clampNumber(raw?.chart_ta?.supertrend_period, 2, 100, CHART_TA_DEFAULTS.supertrend_period)),
      supertrend_multiplier: clampNumber(raw?.chart_ta?.supertrend_multiplier, 0.5, 10, CHART_TA_DEFAULTS.supertrend_multiplier),
      candle_mode: (
        Number(raw?.chart_ta?.candle_mode_default_version || 0) < 2
          && String(raw?.chart_ta?.candle_mode || "") === "regular"
      )
        ? CHART_TA_DEFAULTS.candle_mode
        : (["regular", "heikin_ashi"].includes(String(raw?.chart_ta?.candle_mode || ""))
          ? String(raw.chart_ta.candle_mode)
          : CHART_TA_DEFAULTS.candle_mode),
      candle_mode_default_version: 2,
      rsi_trigger: clampNumber(raw?.chart_ta?.rsi_trigger, 0, 100, raw.rsi_cross_value ?? CHART_TA_DEFAULTS.rsi_trigger),
      stoch_trigger: clampNumber(raw?.chart_ta?.stoch_trigger, 0, 100, raw.stoch_cross_value ?? CHART_TA_DEFAULTS.stoch_trigger),
    },
  };
  const rawRsiEvents = Array.isArray(raw.rsi_events) && raw.rsi_events.length
    ? raw.rsi_events.slice(0, RSI_TIMELINE_KEYS.length)
    : [raw];
  normalized.rsi_events = rawRsiEvents.map((event) => ({
    rsi_cross_value: clampNumber(event?.rsi_cross_value ?? event?.cross_value, 0, 100, normalized.rsi_cross_value),
    rsi_cross_mode: ["cross_up", "cross_down"].includes(String(event?.rsi_cross_mode ?? event?.cross_mode ?? normalized.rsi_cross_mode))
      ? String(event?.rsi_cross_mode ?? event?.cross_mode ?? normalized.rsi_cross_mode)
      : normalized.rsi_cross_mode,
    rsi_event_age: Math.round(clampNumber(event?.rsi_event_age ?? event?.event_age, 0, lookbackDays, normalized.rsi_event_age)),
    rsi_event_id: event?.rsi_event_id ?? event?.id ?? null,
  }));
  normalized.price_ema_source = normalized.price_ema_sources[0] || SCREEN_DEFAULT_FILTERS.price_ema_source;
  const primaryRsi = normalized.rsi_events.find((event) => event.rsi_event_id === "rsi") || normalized.rsi_events[0];
  normalized.rsi_cross_value = primaryRsi.rsi_cross_value;
  normalized.rsi_cross_mode = primaryRsi.rsi_cross_mode;
  normalized.rsi_event_age = primaryRsi.rsi_event_age;
  RSI_TIMELINE_KEYS.slice(1).forEach((key, index) => {
    normalized[`${key}_event_enabled`] = normalized.rsi_event_enabled
      && (normalized.rsi_events.some((event) => event.rsi_event_id === key)
        || normalized.rsi_events.length > index + 1 && !normalized.rsi_events.some((event) => event.rsi_event_id));
  });
  return normalized;
}

function validateHaEmaVolumeConditions(conditions) {
  const rank = { below_ema2: 0, between_ema1_ema2: 1, above_ema1: 2 };
  const active = Object.fromEntries((conditions || [])
    .filter((item) => item.enabled)
    .map((item) => [item.field, rank[item.zone]]));
  const messages = [];
  [["low", "open"], ["low", "close"], ["low", "high"], ["open", "high"], ["close", "high"]].forEach(([lower, upper]) => {
    if (active[lower] !== undefined && active[upper] !== undefined && active[lower] > active[upper]) {
      messages.push(`${lower.toUpperCase()} cannot be in a higher zone than ${upper.toUpperCase()}.`);
    }
  });
  const node = document.getElementById("screen-ha-ema-volume-validation");
  if (node) {
    node.textContent = messages.join(" ");
    node.classList.toggle("hidden", messages.length === 0);
  }
  return messages;
}

function syncScreenFilterStateFromDom() {
  const haEmaVolumeConditions = ["open", "high", "low", "close"].map((field) => ({
    field,
    enabled: Boolean(document.getElementById(`screen-ha-ema-volume-condition-${field}-enabled`)?.checked),
    zone: document.getElementById(`screen-ha-ema-volume-condition-${field}-zone`)?.value || "above_ema1",
  }));
  const nextFilters = normalizeScreenFiltersClient({
    lookback_days: screenFilters.lookback_days,
    volume_range: getRangePairValues(
      "screen-volume-min",
      "screen-volume-max",
      { min: 0, max: SCREEN_DEFAULT_FILTERS.volume_range.max }
    ),
    macd_event_enabled: document.getElementById("screen-macd-event-enabled")?.checked,
    rsi_event_enabled: screenEventOrder.some((key) => RSI_TIMELINE_KEYS.includes(key)),
    rsi_filter_enabled: document.getElementById("screen-rsi-filter-enabled")?.checked,
    rsi_filter_min: document.getElementById("screen-rsi-filter-min")?.value,
    stoch_event_enabled: document.getElementById("screen-stoch-event-enabled")?.checked,
    supertrend_event_enabled: document.getElementById("screen-supertrend-event-enabled")?.checked,
    ema_relationship_enabled: document.getElementById("screen-ema-relationship-event-enabled")?.checked,
    price_ema_event_enabled: document.getElementById("screen-price-ema-event-enabled")?.checked,
    volume_spike_enabled: document.getElementById("screen-volume-spike-event-enabled")?.checked,
    ha_ema_volume_enabled: document.getElementById("screen-ha-ema-volume-event-enabled")?.checked,
    ha_ema_volume_conditions: haEmaVolumeConditions,
    ha_ema_volume_candle_color: document.getElementById("screen-ha-ema-volume-candle-color")?.value,
    ema_flatten_enabled: document.getElementById("screen-ema-flatten-event-enabled")?.checked,
    volume_spike_period: document.getElementById("screen-volume-spike-period")?.value,
    volume_spike_multiplier: document.getElementById("screen-volume-spike-multiplier")?.value,
    ha_ema_volume_ema1_period: document.getElementById("screen-ha-ema-volume-ema1-period")?.value,
    ha_ema_volume_ema1_source: ["open", "high", "low", "close"]
      .map((source) => document.getElementById(`screen-ha-ema-volume-ema1-source-${source}`))
      .find((node) => node?.checked)?.value,
    ha_ema_volume_ema2_period: document.getElementById("screen-ha-ema-volume-ema2-period")?.value,
    ha_ema_volume_ema2_source: ["open", "high", "low", "close"]
      .map((source) => document.getElementById(`screen-ha-ema-volume-ema2-source-${source}`))
      .find((node) => node?.checked)?.value,
    ha_ema_volume_start_field: document.getElementById("screen-ha-ema-volume-start-field")?.value,
    ha_ema_volume_start_line: document.getElementById("screen-ha-ema-volume-start-line")?.value,
    ha_ema_volume_start_relation: document.getElementById("screen-ha-ema-volume-start-relation")?.value,
    ha_ema_volume_end_field: document.getElementById("screen-ha-ema-volume-end-field")?.value,
    ha_ema_volume_end_line: document.getElementById("screen-ha-ema-volume-end-line")?.value,
    ha_ema_volume_end_relation: document.getElementById("screen-ha-ema-volume-end-relation")?.value,
    ha_ema_volume_period: document.getElementById("screen-ha-ema-volume-period")?.value,
    ha_ema_volume_multiplier: document.getElementById("screen-ha-ema-volume-multiplier")?.value,
    ha_ema_volume_event_age: getEventSliderAge("screen-ha-ema-volume-event-age", screenFilters.lookback_days, screenFilters.ha_ema_volume_event_age),
    ema_flatten_period: document.getElementById("screen-ema-flatten-period")?.value,
    ema_flatten_lookback: document.getElementById("screen-ema-flatten-lookback")?.value,
    ema_flatten_tolerance: document.getElementById("screen-ema-flatten-tolerance")?.value,
    ema_flatten_mode: document.getElementById("screen-ema-flatten-mode")?.value,
    ema_relationship_fast: document.getElementById("screen-ema-relationship-fast")?.value,
    ema_relationship_slow: document.getElementById("screen-ema-relationship-slow")?.value,
    ema_relationship_slope: document.getElementById("screen-ema-relationship-slope")?.value,
    ema_relationship_allowance: document.getElementById("screen-ema-relationship-allowance")?.value,
    ema_relationship_fast_slope: document.getElementById("screen-ema-relationship-fast-slope")?.value,
    ema_relationship_slow_slope: document.getElementById("screen-ema-relationship-slow-slope")?.value,
    ema_relationship_cross_mode: document.getElementById("screen-ema-relationship-cross-mode")?.value,
    price_ema_period: document.getElementById("screen-price-ema-period")?.value,
    price_ema_source: document.getElementById("screen-price-ema-source")?.value,
    price_ema_sources: [...(document.getElementById("screen-price-ema-source")?.selectedOptions || [])].map((option) => option.value),
    price_ema_cross_mode: document.getElementById("screen-price-ema-cross-mode")?.value,
    rsi_cross_value: document.getElementById("screen-rsi-cross-value")?.value,
    rsi_cross_mode: document.getElementById("screen-rsi-cross-mode")?.value,
    rsi_events: screenEventOrder
      .filter((key) => RSI_TIMELINE_KEYS.includes(key))
      .map((key) => {
        const domKey = getTimelineDomKey(key);
        return {
          rsi_event_id: key,
          rsi_cross_value: document.getElementById(`screen-${domKey}-cross-value`)?.value,
          rsi_cross_mode: document.getElementById(`screen-${domKey}-cross-mode`)?.value,
          rsi_event_age: getEventSliderAge(`screen-${domKey}-cross-age`, screenFilters.lookback_days, screenFilters.rsi_event_age),
        };
      }),
    stoch_cross_value: document.getElementById("screen-stoch-cross-value")?.value,
    stoch_cross_mode: document.getElementById("screen-stoch-cross-mode")?.value,
    stoch_cross_region: ["below", "above", "any"].find((region) => document.getElementById(`screen-stoch-cross-region-${region}`)?.checked),
    macd_cross_mode: getMacdModeFromControls(),
    macd_event_age: getEventSliderAge("screen-macd-cross-age", screenFilters.lookback_days, screenFilters.macd_event_age),
    rsi_event_age: getEventSliderAge("screen-rsi-cross-age", screenFilters.lookback_days, screenFilters.rsi_event_age),
    stoch_event_age: getEventSliderAge("screen-stoch-cross-age", screenFilters.lookback_days, screenFilters.stoch_event_age),
    supertrend_cross_mode: document.getElementById("screen-supertrend-cross-mode")?.value,
    supertrend_event_age: getEventSliderAge("screen-supertrend-cross-age", screenFilters.lookback_days, screenFilters.supertrend_event_age),
    ema_relationship_age: getEventSliderAge("screen-ema-relationship-age", screenFilters.lookback_days, screenFilters.ema_relationship_age),
    price_ema_event_age: getEventSliderAge("screen-price-ema-cross-age", screenFilters.lookback_days, screenFilters.price_ema_event_age),
    volume_spike_age: getEventSliderAge("screen-volume-spike-cross-age", screenFilters.lookback_days, screenFilters.volume_spike_age),
    ema_flatten_event_age: getEventSliderAge("screen-ema-flatten-age", screenFilters.lookback_days, screenFilters.ema_flatten_event_age),
    ema_slope_20: document.getElementById("screen-ema-20-slope")?.value,
    ema_slope_50: document.getElementById("screen-ema-50-slope")?.value,
    ema_slope_200: document.getElementById("screen-ema-200-slope")?.value,
    ema_slope_period_1: document.getElementById("screen-ema-slope-period-1")?.value,
    ema_slope_period_2: document.getElementById("screen-ema-slope-period-2")?.value,
    ema_slope_period_3: document.getElementById("screen-ema-slope-period-3")?.value,
    ema_slope_1: document.getElementById("screen-ema-slope-1")?.value,
    ema_slope_2: document.getElementById("screen-ema-slope-2")?.value,
    ema_slope_3: document.getElementById("screen-ema-slope-3")?.value,
    ema_slope_lookback: document.getElementById("screen-ema-slope-lookback")?.value,
    ema_slope_flat_tolerance: document.getElementById("screen-ema-slope-tolerance")?.value,
    timeline_order: [...screenEventOrder],
  });
  validateHaEmaVolumeConditions(nextFilters.ha_ema_volume_conditions);
  screenFilters = nextFilters;
  writeStickyValue(LAST_SCREEN_FILTERS_KEY, JSON.stringify(nextFilters));
  applyScreenFilters(nextFilters, { syncPreset: false });
  refreshScreenProjection();
  return nextFilters;
}

function stepDecimalInput(inputId, delta) {
  const node = document.getElementById(inputId);
  if (!node) return;
  const current = Number(String(node.value).replace(",", "."));
  const next = Number.isFinite(current) ? current + delta : 2.5;
  node.value = Math.min(10, Math.max(1.1, next)).toFixed(1);
  node.dispatchEvent(new Event("input", { bubbles: true }));
}

function applyScreenFilters(filters, { syncPreset = false } = {}) {
  screenFilters = normalizeScreenFiltersClient(filters);
  const enabledTimelineKeys = new Set([
    ...(screenFilters.rsi_event_enabled
      ? ((screenFilters.rsi_events || []).length
        ? screenFilters.rsi_events.map((event, index) => event.rsi_event_id || (index === 0 ? "rsi" : `rsi_${index + 1}`))
        : ["rsi"])
      : []),
    ...(screenFilters.macd_event_enabled ? ["macd"] : []),
    ...(screenFilters.stoch_event_enabled ? ["stoch"] : []),
    ...(screenFilters.supertrend_event_enabled ? ["supertrend"] : []),
    ...(screenFilters.ema_relationship_enabled ? ["ema_relationship"] : []),
    ...(screenFilters.price_ema_event_enabled ? ["price_ema"] : []),
    ...(screenFilters.volume_spike_enabled ? ["volume_spike"] : []),
    ...(screenFilters.ha_ema_volume_enabled ? ["ha_ema_volume"] : []),
    ...(screenFilters.ema_flatten_enabled ? ["ema_flatten"] : []),
    ...(Array.isArray(screenFilters.timeline_order)
      ? screenFilters.timeline_order.filter((key) => REPEATABLE_TIMELINE_KEYS.includes(key) && key.includes("_"))
      : []),
  ]);
  const savedTimelineOrder = (Array.isArray(screenFilters.timeline_order)
    ? [...screenFilters.timeline_order]
    : [...DEFAULT_TIMELINE_ORDER]
  );
  const previouslyVisibleTimelineKeys = new Set(
    screenEventOrder.filter((key) => enabledTimelineKeys.has(key))
  );
  // Older saved filters may enable a rule that did not exist when their
  // timeline_order was written. Keep those enabled rules visible by
  // appending them after the remembered order.
  enabledTimelineKeys.forEach((key) => {
    if (!savedTimelineOrder.includes(key)) {
      savedTimelineOrder.push(key);
    }
  });
  screenEventOrder = savedTimelineOrder.filter((key) => (
    enabledTimelineKeys.has(key) || previouslyVisibleTimelineKeys.has(key)
  ));
  enabledTimelineKeys.forEach((key) => {
    if (!screenEventOrder.includes(key)) {
      screenEventOrder.push(key);
    }
  });
  const chartTA = screenFilters.chart_ta || CHART_TA_DEFAULTS;
  Object.entries({
    macd_fast: "chart-macd-fast",
    macd_slow: "chart-macd-slow",
    macd_signal: "chart-macd-signal",
    rsi_period: "chart-rsi-period",
    stoch_rsi_period: "chart-stoch-rsi-period",
    stoch_rsi_k: "chart-stoch-rsi-k",
    stoch_rsi_d: "chart-stoch-rsi-d",
    supertrend_period: "chart-supertrend-period",
    supertrend_multiplier: "chart-supertrend-multiplier",
    candle_mode: "chart-candle-mode",
  }).forEach(([key, id]) => {
    const node = document.getElementById(id);
    if (node && chartTA[key] !== undefined) {
      node.value = String(chartTA[key]);
    }
  });
  saveChartTAParameters({
    ...chartTA,
    rsi_trigger: screenFilters.rsi_cross_value,
    stoch_trigger: screenFilters.stoch_cross_value,
  });
  const volumeMinNode = document.getElementById("screen-volume-min");
  const volumeMaxNode = document.getElementById("screen-volume-max");
  if (volumeMinNode) volumeMinNode.value = String(screenFilters.volume_range.min);
  if (volumeMaxNode) volumeMaxNode.value = String(screenFilters.volume_range.max);
  const rsiFilterEnabledNode = document.getElementById("screen-rsi-filter-enabled");
  const rsiFilterMinNode = document.getElementById("screen-rsi-filter-min");
  const rsiFilterReadout = document.getElementById("screen-rsi-filter-min-readout");
  if (rsiFilterEnabledNode) rsiFilterEnabledNode.checked = Boolean(screenFilters.rsi_filter_enabled);
  if (rsiFilterMinNode) rsiFilterMinNode.value = String(screenFilters.rsi_filter_min);
  if (rsiFilterReadout) rsiFilterReadout.textContent = String(screenFilters.rsi_filter_min);
  updateTimelineTrackBounds(screenFilters.lookback_days);
  setEventSliderValue("screen-macd-cross-age", screenFilters.macd_event_age, screenFilters.lookback_days);
  setEventSliderValue("screen-rsi-cross-age", screenFilters.rsi_event_age, screenFilters.lookback_days);
  (screenFilters.rsi_events || []).forEach((event, index) => {
    const key = event.rsi_event_id || (index === 0 ? "rsi" : `rsi_${index + 1}`);
    setEventSliderValue(`screen-${getTimelineDomKey(key)}-cross-age`, event.rsi_event_age, screenFilters.lookback_days);
  });
  setEventSliderValue("screen-stoch-cross-age", screenFilters.stoch_event_age, screenFilters.lookback_days);
    setEventSliderValue("screen-supertrend-cross-age", screenFilters.supertrend_event_age, screenFilters.lookback_days);
  setEventSliderValue("screen-ema-relationship-age", screenFilters.ema_relationship_age, screenFilters.lookback_days);
  setEventSliderValue("screen-price-ema-cross-age", screenFilters.price_ema_event_age, screenFilters.lookback_days);
  setEventSliderValue("screen-volume-spike-cross-age", screenFilters.volume_spike_age, screenFilters.lookback_days);
  setEventSliderValue("screen-ha-ema-volume-event-age", screenFilters.ha_ema_volume_event_age, screenFilters.lookback_days);
  setEventSliderValue("screen-ema-flatten-age", screenFilters.ema_flatten_event_age, screenFilters.lookback_days);
  reorderTimelineSteps();
  syncTimelineAgeConstraints();
  [
    ["screen-ema-20-slope", screenFilters.ema_slope_20],
    ["screen-ema-50-slope", screenFilters.ema_slope_50],
    ["screen-ema-200-slope", screenFilters.ema_slope_200],
    ["screen-ema-slope-lookback", screenFilters.ema_slope_lookback],
    ["screen-ema-slope-tolerance", screenFilters.ema_slope_flat_tolerance],
    ["screen-ema-slope-period-1", screenFilters.ema_slope_period_1],
    ["screen-ema-slope-period-2", screenFilters.ema_slope_period_2],
    ["screen-ema-slope-period-3", screenFilters.ema_slope_period_3],
    ["screen-ema-slope-1", screenFilters.ema_slope_1],
    ["screen-ema-slope-2", screenFilters.ema_slope_2],
    ["screen-ema-slope-3", screenFilters.ema_slope_3],
    ["screen-ema-relationship-fast", screenFilters.ema_relationship_fast],
    ["screen-ema-relationship-slow", screenFilters.ema_relationship_slow],
    ["screen-ema-relationship-slope", screenFilters.ema_relationship_slope],
    ["screen-ema-relationship-allowance", screenFilters.ema_relationship_allowance],
    ["screen-ema-relationship-fast-slope", screenFilters.ema_relationship_fast_slope],
    ["screen-ema-relationship-slow-slope", screenFilters.ema_relationship_slow_slope],
    ["screen-ema-relationship-cross-mode", screenFilters.ema_relationship_cross_mode],
    ["screen-price-ema-period", screenFilters.price_ema_period],
    ["screen-price-ema-cross-mode", screenFilters.price_ema_cross_mode],
    ["screen-volume-spike-period", screenFilters.volume_spike_period],
    ["screen-volume-spike-multiplier", screenFilters.volume_spike_multiplier],
    ["screen-ha-ema-volume-ema1-period", screenFilters.ha_ema_volume_ema1_period],
    ["screen-ha-ema-volume-ema2-period", screenFilters.ha_ema_volume_ema2_period],
    ["screen-ha-ema-volume-candle-color", screenFilters.ha_ema_volume_candle_color],
    ["screen-ha-ema-volume-start-field", screenFilters.ha_ema_volume_start_field],
    ["screen-ha-ema-volume-start-line", screenFilters.ha_ema_volume_start_line],
    ["screen-ha-ema-volume-start-relation", screenFilters.ha_ema_volume_start_relation],
    ["screen-ha-ema-volume-end-field", screenFilters.ha_ema_volume_end_field],
    ["screen-ha-ema-volume-end-line", screenFilters.ha_ema_volume_end_line],
    ["screen-ha-ema-volume-end-relation", screenFilters.ha_ema_volume_end_relation],
    ["screen-ha-ema-volume-period", screenFilters.ha_ema_volume_period],
    ["screen-ha-ema-volume-multiplier", screenFilters.ha_ema_volume_multiplier],
    ["screen-ema-flatten-period", screenFilters.ema_flatten_period],
    ["screen-ema-flatten-lookback", screenFilters.ema_flatten_lookback],
    ["screen-ema-flatten-tolerance", screenFilters.ema_flatten_tolerance],
    ["screen-ema-flatten-mode", screenFilters.ema_flatten_mode],
  ].forEach(([id, value]) => {
    const node = document.getElementById(id);
    if (node) node.value = String(value);
  });
  const priceEmaSourceNode = document.getElementById("screen-price-ema-source");
  if (priceEmaSourceNode) {
    const selectedSources = new Set(screenFilters.price_ema_sources || [screenFilters.price_ema_source]);
    Array.from(priceEmaSourceNode.options || []).forEach((option) => { option.selected = selectedSources.has(option.value); });
  }
  ["open", "high", "low", "close"].forEach((source) => {
    const ema1Node = document.getElementById(`screen-ha-ema-volume-ema1-source-${source}`);
    const ema2Node = document.getElementById(`screen-ha-ema-volume-ema2-source-${source}`);
    if (ema1Node) ema1Node.checked = source === screenFilters.ha_ema_volume_ema1_source;
    if (ema2Node) ema2Node.checked = source === screenFilters.ha_ema_volume_ema2_source;
    const condition = (screenFilters.ha_ema_volume_conditions || []).find((item) => item.field === source);
    const enabledNode = document.getElementById(`screen-ha-ema-volume-condition-${source}-enabled`);
    const zoneNode = document.getElementById(`screen-ha-ema-volume-condition-${source}-zone`);
    if (condition && enabledNode) enabledNode.checked = Boolean(condition.enabled);
    if (condition && zoneNode) zoneNode.value = condition.zone;
  });
  validateHaEmaVolumeConditions(screenFilters.ha_ema_volume_conditions);
  syncScreenEventToggleChrome(screenFilters);
  (screenFilters.rsi_events || []).forEach((event, index) => {
    const key = event.rsi_event_id || (index === 0 ? "rsi" : `rsi_${index + 1}`);
    const domKey = getTimelineDomKey(key);
    const valueNode = document.getElementById(`screen-${domKey}-cross-value`);
    const modeNode = document.getElementById(`screen-${domKey}-cross-mode`);
    const valueReadout = document.getElementById(`screen-${domKey}-cross-value-readout`);
    const modeReadout = document.getElementById(`screen-${domKey}-mode-readout`);
    if (valueNode) valueNode.value = String(event.rsi_cross_value);
    if (modeNode) modeNode.value = String(event.rsi_cross_mode);
    if (valueReadout) valueReadout.textContent = `${Math.round(event.rsi_cross_value)}`;
    if (modeReadout) modeReadout.textContent = getRsiModeLongLabel(event.rsi_cross_mode);
  });
  const stochCrossNode = document.getElementById("screen-stoch-cross-value");
  if (stochCrossNode) {
    stochCrossNode.value = String(screenFilters.stoch_cross_value);
  }
  const stochModeNode = document.getElementById("screen-stoch-cross-mode");
  if (stochModeNode) {
    stochModeNode.value = String(screenFilters.stoch_cross_mode || SCREEN_DEFAULT_FILTERS.stoch_cross_mode);
  }
  ["below", "above", "any"].forEach((region) => {
    const node = document.getElementById(`screen-stoch-cross-region-${region}`);
    if (node) node.checked = region === String(screenFilters.stoch_cross_region || "below");
  });
  const macdModeNode = document.getElementById("screen-macd-cross-mode");
  if (macdModeNode) {
    macdModeNode.value = getMacdControlState(screenFilters.macd_cross_mode).direction;
  }
  const macdControlState = getMacdControlState(screenFilters.macd_cross_mode);
  ["below", "above", "any"].forEach((region) => {
    const node = document.getElementById(`screen-macd-cross-region-${region}`);
    if (node) node.checked = region === macdControlState.region;
  });
  const supertrendModeNode = document.getElementById("screen-supertrend-cross-mode");
  if (supertrendModeNode) supertrendModeNode.value = String(screenFilters.supertrend_cross_mode || SCREEN_DEFAULT_FILTERS.supertrend_cross_mode);
  const volumeReadout = document.getElementById("screen-volume-readout");
  if (volumeReadout) {
    volumeReadout.textContent = `${formatCompactVolume(screenFilters.volume_range.min)} - ${formatCompactVolume(screenFilters.volume_range.max)}`;
  }
  const rsiCrossReadout = document.getElementById("screen-rsi-cross-value-readout");
  if (rsiCrossReadout) {
    rsiCrossReadout.textContent = `${Math.round(screenFilters.rsi_cross_value)}`;
  }
  const rsiModeReadout = document.getElementById("screen-rsi-mode-readout");
  if (rsiModeReadout) {
    rsiModeReadout.textContent = getRsiModeLongLabel(screenFilters.rsi_cross_mode);
  }
  const stochCrossReadout = document.getElementById("screen-stoch-cross-value-readout");
  if (stochCrossReadout) {
    stochCrossReadout.textContent = `${Math.round(screenFilters.stoch_cross_value)}`;
  }
  const stochModeReadout = document.getElementById("screen-stoch-mode-readout");
  if (stochModeReadout) {
    stochModeReadout.textContent = `${getStochModeLongLabel(screenFilters.stoch_cross_mode)} · ${getStochRegionLongLabel(screenFilters.stoch_cross_region)}`;
  }
  const macdReadout = document.getElementById("screen-macd-cross-readout");
  if (macdReadout) {
    macdReadout.textContent = formatTimelinePosition(screenFilters.macd_event_age, screenFilters.lookback_days);
  }
  const macdModeReadout = document.getElementById("screen-macd-mode-readout");
  if (macdModeReadout) {
    macdModeReadout.textContent = getMacdModeLongLabel(screenFilters.macd_cross_mode);
  }
  const rsiEventReadout = document.getElementById("screen-rsi-cross-readout");
  if (rsiEventReadout) {
    rsiEventReadout.textContent = formatTimelinePosition(screenFilters.rsi_event_age, screenFilters.lookback_days);
  }
  (screenFilters.rsi_events || []).forEach((event, index) => {
    const key = event.rsi_event_id || (index === 0 ? "rsi" : `rsi_${index + 1}`);
    const readout = document.getElementById(`screen-${getTimelineDomKey(key)}-cross-readout`);
    if (readout) readout.textContent = formatTimelinePosition(event.rsi_event_age, screenFilters.lookback_days);
  });
  const stochReadout = document.getElementById("screen-stoch-cross-readout");
  if (stochReadout) {
    stochReadout.textContent = formatTimelinePosition(screenFilters.stoch_event_age, screenFilters.lookback_days);
  }
  const supertrendReadout = document.getElementById("screen-supertrend-cross-readout");
  if (supertrendReadout) supertrendReadout.textContent = formatTimelinePosition(screenFilters.supertrend_event_age, screenFilters.lookback_days);
  const emaRelationshipReadout = document.getElementById("screen-ema-relationship-event-readout");
  if (emaRelationshipReadout) emaRelationshipReadout.textContent = formatTimelinePosition(screenFilters.ema_relationship_age, screenFilters.lookback_days);
  const emaRelationshipLabel = document.getElementById("screen-ema-relationship-readout");
  if (emaRelationshipLabel) emaRelationshipLabel.textContent = `${screenFilters.ema_relationship_fast} / ${screenFilters.ema_relationship_slow} · ${screenFilters.ema_relationship_cross_mode === "cross_down" ? "down" : "up"}`;
  const priceEmaReadout = document.getElementById("screen-price-ema-event-readout");
  if (priceEmaReadout) priceEmaReadout.textContent = formatTimelinePosition(screenFilters.price_ema_event_age, screenFilters.lookback_days);
  const priceEmaLabel = document.getElementById("screen-price-ema-readout");
  if (priceEmaLabel) priceEmaLabel.textContent = `PRICE ${screenFilters.price_ema_cross_mode === "cross_down" ? "down" : "up"} EMA ${screenFilters.price_ema_period}`;
  const supertrendModeReadout = document.getElementById("screen-supertrend-mode-readout");
  if (supertrendModeReadout) supertrendModeReadout.textContent = screenFilters.supertrend_cross_mode === "green_to_red" ? "Green to red" : "Red to green";
  const volumeSpikeLabel = document.getElementById("screen-volume-spike-readout");
  if (volumeSpikeLabel) volumeSpikeLabel.textContent = `${Number(screenFilters.volume_spike_multiplier).toFixed(1)}x EMA ${screenFilters.volume_spike_period}`;
  const volumeSpikeReadout = document.getElementById("screen-volume-spike-cross-readout");
  if (volumeSpikeReadout) volumeSpikeReadout.textContent = formatTimelinePosition(screenFilters.volume_spike_age, screenFilters.lookback_days);
  const haEmaVolumeReadout = document.getElementById("screen-ha-ema-volume-event-readout");
  if (haEmaVolumeReadout) haEmaVolumeReadout.textContent = formatTimelinePosition(screenFilters.ha_ema_volume_event_age, screenFilters.lookback_days);
  const haEmaVolumeLabel = document.getElementById("screen-ha-ema-volume-readout");
  if (haEmaVolumeLabel) {
    const zoneLabels = { above_ema1: "above EMA1", between_ema1_ema2: "between EMA1/EMA2", below_ema2: "below EMA2" };
    const conditions = (screenFilters.ha_ema_volume_conditions || [])
      .filter((condition) => condition.enabled)
      .map((condition) => `${String(condition.field).toUpperCase()} ${zoneLabels[condition.zone] || condition.zone}`);
    haEmaVolumeLabel.textContent = `${conditions.join(" + ") || "No OHLC condition"} + volume ${Number(screenFilters.ha_ema_volume_multiplier).toFixed(1)}x EMA ${screenFilters.ha_ema_volume_period}`;
  }
  const emaFlattenReadout = document.getElementById("screen-ema-flatten-event-readout");
  if (emaFlattenReadout) emaFlattenReadout.textContent = formatTimelinePosition(screenFilters.ema_flatten_event_age, screenFilters.lookback_days);
  const emaFlattenLabel = document.getElementById("screen-ema-flatten-readout");
  if (emaFlattenLabel) emaFlattenLabel.textContent = `EMA ${screenFilters.ema_flatten_period} · ${screenFilters.ema_flatten_mode}`;
  updateTimelineStepPositions(screenFilters);
  updateScreenSequenceSummary(screenFilters);
  if (syncPreset) {
    populateScreenPresetSelect();
  }
}

function getScreenFiltersForRequest() {
  return syncScreenFilterStateFromDom();
}

function buildScreenFilterParams() {
  const filters = getScreenFiltersForRequest();
  const params = new URLSearchParams();
  params.set("lookback_days", String(filters.lookback_days));
  params.set("volume_min", String(filters.volume_range.min));
  params.set("volume_max", String(filters.volume_range.max));
  params.set("macd_event_enabled", filters.macd_event_enabled ? "true" : "false");
  params.set("rsi_event_enabled", filters.rsi_event_enabled ? "true" : "false");
  params.set("rsi_filter_enabled", filters.rsi_filter_enabled ? "true" : "false");
  params.set("rsi_filter_min", String(filters.rsi_filter_min));
  params.set("stoch_event_enabled", filters.stoch_event_enabled ? "true" : "false");
  params.set("rsi_cross_value", String(filters.rsi_cross_value));
  params.set("rsi_cross_mode", String(filters.rsi_cross_mode || SCREEN_DEFAULT_FILTERS.rsi_cross_mode));
  params.set("rsi_events", JSON.stringify(filters.rsi_events || []));
  params.set("stoch_cross_value", String(filters.stoch_cross_value));
  params.set("stoch_cross_mode", String(filters.stoch_cross_mode || SCREEN_DEFAULT_FILTERS.stoch_cross_mode));
  params.set("stoch_cross_region", String(filters.stoch_cross_region || SCREEN_DEFAULT_FILTERS.stoch_cross_region));
  params.set("macd_cross_mode", String(filters.macd_cross_mode || SCREEN_DEFAULT_FILTERS.macd_cross_mode));
  params.set("macd_event_age", String(filters.macd_event_age));
  params.set("rsi_event_age", String(filters.rsi_event_age));
  params.set("stoch_event_age", String(filters.stoch_event_age));
  params.set("supertrend_event_enabled", filters.supertrend_event_enabled ? "true" : "false");
  params.set("supertrend_cross_mode", String(filters.supertrend_cross_mode || SCREEN_DEFAULT_FILTERS.supertrend_cross_mode));
  params.set("supertrend_event_age", String(filters.supertrend_event_age));
  params.set("ema_relationship_enabled", filters.ema_relationship_enabled ? "true" : "false");
  params.set("ema_relationship_fast", String(filters.ema_relationship_fast));
  params.set("ema_relationship_slow", String(filters.ema_relationship_slow));
  params.set("ema_relationship_slope", String(filters.ema_relationship_slope));
  params.set("ema_relationship_allowance", String(filters.ema_relationship_allowance));
  params.set("ema_relationship_fast_slope", String(filters.ema_relationship_fast_slope));
  params.set("ema_relationship_slow_slope", String(filters.ema_relationship_slow_slope));
  params.set("ema_relationship_cross_mode", String(filters.ema_relationship_cross_mode));
  params.set("ema_relationship_age", String(filters.ema_relationship_age));
  params.set("price_ema_event_enabled", filters.price_ema_event_enabled ? "true" : "false");
  params.set("price_ema_period", String(filters.price_ema_period));
  params.set("price_ema_source", String(filters.price_ema_source || SCREEN_DEFAULT_FILTERS.price_ema_source));
  params.set("price_ema_sources", JSON.stringify(filters.price_ema_sources || [filters.price_ema_source || SCREEN_DEFAULT_FILTERS.price_ema_source]));
  params.set("price_ema_cross_mode", String(filters.price_ema_cross_mode || SCREEN_DEFAULT_FILTERS.price_ema_cross_mode));
  params.set("price_ema_event_age", String(filters.price_ema_event_age));
  params.set("ema_flatten_enabled", filters.ema_flatten_enabled ? "true" : "false");
  params.set("ema_flatten_period", String(filters.ema_flatten_period));
  params.set("ema_flatten_lookback", String(filters.ema_flatten_lookback));
  params.set("ema_flatten_tolerance", String(filters.ema_flatten_tolerance));
  params.set("ema_flatten_mode", String(filters.ema_flatten_mode));
  params.set("ema_flatten_event_age", String(filters.ema_flatten_event_age));
  params.set("volume_spike_enabled", filters.volume_spike_enabled ? "true" : "false");
  params.set("volume_spike_period", String(filters.volume_spike_period));
  params.set("volume_spike_multiplier", String(filters.volume_spike_multiplier));
    params.set("volume_spike_age", String(filters.volume_spike_age));
  params.set("ha_ema_volume_enabled", filters.ha_ema_volume_enabled ? "true" : "false");
  params.set("ha_ema_volume_ema1_period", String(filters.ha_ema_volume_ema1_period));
  params.set("ha_ema_volume_ema1_source", String(filters.ha_ema_volume_ema1_source));
  params.set("ha_ema_volume_ema2_period", String(filters.ha_ema_volume_ema2_period));
  params.set("ha_ema_volume_ema2_source", String(filters.ha_ema_volume_ema2_source));
  params.set("ha_ema_volume_start_field", String(filters.ha_ema_volume_start_field));
  params.set("ha_ema_volume_start_line", String(filters.ha_ema_volume_start_line));
  params.set("ha_ema_volume_start_relation", String(filters.ha_ema_volume_start_relation));
  params.set("ha_ema_volume_end_field", String(filters.ha_ema_volume_end_field));
  params.set("ha_ema_volume_end_line", String(filters.ha_ema_volume_end_line));
  params.set("ha_ema_volume_end_relation", String(filters.ha_ema_volume_end_relation));
  params.set("ha_ema_volume_conditions", JSON.stringify(filters.ha_ema_volume_conditions || []));
  params.set("ha_ema_volume_candle_color", String(filters.ha_ema_volume_candle_color || "green"));
  params.set("ha_ema_volume_period", String(filters.ha_ema_volume_period));
  params.set("ha_ema_volume_multiplier", String(filters.ha_ema_volume_multiplier));
  params.set("ha_ema_volume_event_age", String(filters.ha_ema_volume_event_age));
  params.set("timeline_order", JSON.stringify(filters.timeline_order || []));
  const chartTA = getChartTAParameters();
  params.set("supertrend_period", String(chartTA.supertrend_period));
  params.set("supertrend_multiplier", String(chartTA.supertrend_multiplier));
  params.set("ema_slope_20", String(filters.ema_slope_20 || "any"));
  params.set("ema_slope_50", String(filters.ema_slope_50 || "any"));
  params.set("ema_slope_200", String(filters.ema_slope_200 || "any"));
  params.set("ema_slope_period_1", String(filters.ema_slope_period_1));
  params.set("ema_slope_period_2", String(filters.ema_slope_period_2));
  params.set("ema_slope_period_3", String(filters.ema_slope_period_3));
  params.set("ema_slope_1", String(filters.ema_slope_1 || "any"));
  params.set("ema_slope_2", String(filters.ema_slope_2 || "any"));
  params.set("ema_slope_3", String(filters.ema_slope_3 || "any"));
  params.set("ema_slope_lookback", String(filters.ema_slope_lookback));
  params.set("ema_slope_flat_tolerance", String(filters.ema_slope_flat_tolerance));
  const presetSelect = document.getElementById("screen-preset-select");
  if (presetSelect && presetSelect.value) {
    params.set("preset_name", presetSelect.value);
  }
  return params;
}

