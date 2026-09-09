// Dashboard timeline. See README.md in static/js/dashboard for the feature map.

function eventAgeToSliderValue(age, lookbackDays) {
  const safeLookback = Math.max(1, Number(lookbackDays || SCREEN_DEFAULT_FILTERS.lookback_days));
  // Event age is inclusive: 0 means the current trading day/intraday bar.
  const safeAge = clampNumber(age, 0, safeLookback, 0);
  return safeLookback - safeAge;
}

function sliderValueToEventAge(value, lookbackDays) {
  const safeLookback = Math.max(1, Number(lookbackDays || SCREEN_DEFAULT_FILTERS.lookback_days));
  // The right-hand endpoint is deliberately 0d, not 1d.
  const safeValue = clampNumber(value, 0, safeLookback, safeLookback);
  return Math.round(safeLookback - safeValue);
}

function setEventSliderValue(id, age, lookbackDays) {
  const node = document.getElementById(id);
  if (!node) {
    return;
  }
  node.max = String(lookbackDays);
  node.value = String(eventAgeToSliderValue(age, lookbackDays));
}

function getEventSliderAge(id, lookbackDays, fallbackAge) {
  const node = document.getElementById(id);
  if (!node) {
    return fallbackAge;
  }
  node.max = String(lookbackDays);
  return sliderValueToEventAge(node.value, lookbackDays);
}

function formatEventAge(age) {
  const numeric = Math.max(0, Math.round(Number(age || 0)));
  return numeric === 0 ? "Today" : `${numeric}d ago`;
}

function formatTimelinePosition(age, lookbackDays) {
  const numeric = Math.max(0, Math.round(Number(age || 0)));
  const lookback = Math.max(1, Math.round(Number(lookbackDays || SCREEN_DEFAULT_FILTERS.lookback_days)));
  const positionPct = Math.round(((lookback - numeric) / lookback) * 100);
  return numeric === 0
    ? `Today only · ${positionPct}% toward today`
    : `Within last ${numeric}d · ${positionPct}% toward today`;
}

function updateEventAgeReadoutFromSlider(sliderId, readoutId) {
  const readout = document.getElementById(readoutId);
  if (!readout) {
    return;
  }
  const age = getEventSliderAge(sliderId, screenFilters.lookback_days, 0);
  readout.textContent = formatTimelinePosition(age, screenFilters.lookback_days);
}

function getMacdModeShortLabel(mode) {
  const labels = {
    low_cross_buy: "Bullish below zero",
    high_cross_sell: "Bearish above zero",
    bullish_cross: "Bullish any region",
    bearish_cross: "Bearish any region",
  };
  return labels[String(mode || "")] || labels.low_cross_buy;
}

function getMacdControlState(mode) {
  const normalized = String(mode || "");
  if (normalized === "low_cross_buy") return { direction: "bullish_cross", region: "below" };
  if (normalized === "high_cross_sell") return { direction: "bearish_cross", region: "above" };
  return { direction: normalized === "bearish_cross" ? "bearish_cross" : "bullish_cross", region: "any" };
}

function getMacdModeFromControls() {
  const direction = document.getElementById("screen-macd-cross-mode")?.value === "bearish_cross"
    ? "bearish_cross"
    : "bullish_cross";
  const region = ["below", "above", "any"].find((value) => document.getElementById(`screen-macd-cross-region-${value}`)?.checked) || "any";
  if (direction === "bullish_cross" && region === "below") return "low_cross_buy";
  if (direction === "bearish_cross" && region === "above") return "high_cross_sell";
  return direction;
}

function getRsiModeShortLabel(mode) {
  const labels = {
    cross_up: "Cross Up",
    cross_down: "Cross Down",
  };
  return labels[String(mode || "")] || labels.cross_up;
}

function getRsiModeLongLabel(mode) {
  const labels = {
    cross_up: "Cross Up",
    cross_down: "Cross Down",
  };
  return labels[String(mode || "")] || labels.cross_up;
}

function getStochModeShortLabel(mode) {
  const labels = {
    cross_up: "K/D Up",
    cross_down: "K/D Down",
  };
  return labels[String(mode || "")] || labels.cross_up;
}

function getStochModeLongLabel(mode) {
  const labels = {
    cross_up: "K/D Cross Up",
    cross_down: "K/D Cross Down",
  };
  return labels[String(mode || "")] || labels.cross_up;
}

function getStochRegionLongLabel(region) {
  const labels = { below: "Below trigger", above: "Above trigger", any: "Any region" };
  return labels[String(region || "")] || labels.below;
}

function getMacdModeLongLabel(mode) {
  const labels = {
    low_cross_buy: "MACD/Signal bullish cross below zero / Buy",
    high_cross_sell: "MACD/Signal bearish cross above zero / Sell",
    bullish_cross: "MACD/Signal bullish cross in any region",
    bearish_cross: "MACD/Signal bearish cross in any region",
  };
  return labels[String(mode || "")] || labels.low_cross_buy;
}

function getRangePairValues(minId, maxId, fallbackRange) {
  const minNode = document.getElementById(minId);
  const maxNode = document.getElementById(maxId);
  return {
    min: clampNumber(minNode?.value, fallbackRange.min, fallbackRange.max, fallbackRange.min),
    max: clampNumber(maxNode?.value, fallbackRange.min, fallbackRange.max, fallbackRange.max),
  };
}

function getScreenEventReadiness(filters = screenFilters) {
  const primaryRsi = filters.rsi_events?.find((event) => event.rsi_event_id === "rsi") || filters.rsi_events?.[0];
  const eventDefinitions = {
    rsi: filters.rsi_event_enabled
      ? { label: `RSI ${getRsiModeShortLabel(primaryRsi?.rsi_cross_mode || filters.rsi_cross_mode)}`, age: Number(primaryRsi?.rsi_event_age ?? filters.rsi_event_age ?? 0) }
      : null,
    macd: filters.macd_event_enabled
      ? { label: `MACD ${getMacdModeShortLabel(filters.macd_cross_mode)}`, age: Number(filters.macd_event_age || 0) }
      : null,
    stoch: filters.stoch_event_enabled
      ? { label: `StochRSI ${getStochModeShortLabel(filters.stoch_cross_mode)}`, age: Number(filters.stoch_event_age || 0) }
      : null,
    supertrend: filters.supertrend_event_enabled
      ? { label: `Supertrend ${filters.supertrend_cross_mode === "green_to_red" ? "green to red" : "red to green"}`, age: Number(filters.supertrend_event_age || 0) }
      : null,
    ema_relationship: filters.ema_relationship_enabled
      ? { label: `EMA ${filters.ema_relationship_fast}/${filters.ema_relationship_slow} cross`, age: Number(filters.ema_relationship_age || 0) }
      : null,
    price_ema: filters.price_ema_event_enabled
      ? { label: `${String(filters.price_ema_source || "close").toUpperCase()} ${filters.price_ema_cross_mode === "cross_down" ? "down" : "up"} EMA ${filters.price_ema_period}`, age: Number(filters.price_ema_event_age || 0) }
      : null,
    ema_flatten: filters.ema_flatten_enabled
      ? { label: `EMA ${filters.ema_flatten_period} ${filters.ema_flatten_mode} flatten`, age: Number(filters.ema_flatten_event_age || 0) }
      : null,
    volume_spike: filters.volume_spike_enabled
      ? { label: `Volume ${Number(filters.volume_spike_multiplier).toFixed(1)}x EMA${filters.volume_spike_period}`, age: Number(filters.volume_spike_age || 0) }
      : null,
    ha_ema_volume: filters.ha_ema_volume_enabled
      ? { label: `HA ${String(filters.ha_ema_volume_start_field).toUpperCase()} ${filters.ha_ema_volume_start_relation === "above" ? "GT" : "LT"} ${String(filters.ha_ema_volume_start_line).toUpperCase()} + ${String(filters.ha_ema_volume_end_field).toUpperCase()} ${filters.ha_ema_volume_end_relation === "above" ? "GT" : "LT"} ${String(filters.ha_ema_volume_end_line).toUpperCase()}`, age: Number(filters.ha_ema_volume_event_age || 0) }
      : null,
  };
  (filters.rsi_events || []).forEach((event, index) => {
    const key = event.rsi_event_id || (index === 0 ? "rsi" : `rsi_${index + 1}`);
    if (key === "rsi") return;
    const number = key.replace("rsi_", "");
    eventDefinitions[key] = {
      label: `RSI ${number} ${getRsiModeShortLabel(event.rsi_cross_mode)}`,
      age: Number(event.rsi_event_age || 0),
    };
  });
  return screenEventOrder
    .map((key) => eventDefinitions[key] ? { key, ...eventDefinitions[key] } : null)
    .filter(Boolean);
}

function getTimelineRuleDefinitions() {
  const definitions = [
    { key: "rsi", label: "RSI" },
    { key: "rsi_2", label: "RSI 2" },
    { key: "rsi_3", label: "RSI 3" },
    { key: "macd", label: "MACD" },
    { key: "stoch", label: "StochRSI" },
    { key: "supertrend", label: "Supertrend" },
    { key: "ema_relationship", label: "EMA Cross" },
    { key: "price_ema", label: "Price / EMA" },
    { key: "volume_spike", label: "Volume Spike" },
    { key: "ema_flatten", label: "EMA Flatten" },
    { key: "ha_ema_volume", label: "HA EMA + Volume" },
  ];
  REPEATABLE_TIMELINE_BASE_KEYS.forEach((key) => {
    const base = definitions.find((definition) => definition.key === key);
    if (!base) return;
    definitions.push({ key: `${key}_2`, label: `${base.label} 2` });
    definitions.push({ key: `${key}_3`, label: `${base.label} 3` });
  });
  return definitions;
}

function getTimelineDomKey(key) {
  if (key === "ema_relationship") return "ema-relationship";
  if (key === "volume_spike") return "volume-spike";
  if (key === "ema_flatten") return "ema-flatten";
  if (key === "price_ema") return "price-ema";
  if (key === "ha_ema_volume") return "ha-ema-volume";
  if (key === "rsi_2") return "rsi-2";
  if (key === "rsi_3") return "rsi-3";
  const repeatedMatch = String(key).match(/^(.+)_(2|3)$/);
  if (repeatedMatch) return `${getTimelineDomKey(repeatedMatch[1])}-${repeatedMatch[2]}`;
  return key;
}

function ensureRepeatedRsiStep() {
  const first = document.getElementById("screen-rsi-event-step");
  if (!first) return;
  [2, 3].forEach((index) => {
    const key = `rsi_${index}`;
    const stepId = `screen-rsi-${index}-event-step`;
    if (document.getElementById(stepId)) return;
    const repeated = first.cloneNode(true);
    repeated.id = stepId;
    repeated.innerHTML = repeated.innerHTML
      .replaceAll("screen-rsi-", `screen-rsi-${index}-`)
      .replaceAll('data-screen-event-remove="rsi"', `data-screen-event-remove="${key}"`)
      .replaceAll('data-screen-event-move="rsi"', `data-screen-event-move="${key}"`)
      .replace("RSI Event", `RSI Event #${index}`);
    repeated.classList.add("hidden");
    first.parentElement?.appendChild(repeated);
  });
}

function ensureRepeatedEventSteps() {
  REPEATABLE_TIMELINE_BASE_KEYS.forEach((key) => {
    const first = document.getElementById(getTimelineStepId(key));
    if (!first) return;
    [2, 3].forEach((index) => {
      const repeatedKey = `${key}_${index}`;
      const stepId = getTimelineStepId(repeatedKey);
      if (document.getElementById(stepId)) return;
      const repeated = first.cloneNode(true);
      repeated.id = stepId;
      const domKey = getTimelineDomKey(key);
      const repeatedDomKey = getTimelineDomKey(repeatedKey);
      repeated.innerHTML = repeated.innerHTML
        .replaceAll(`screen-${domKey}-`, `screen-${repeatedDomKey}-`)
        .replaceAll(`data-screen-event-remove="${key}"`, `data-screen-event-remove="${repeatedKey}"`)
        .replaceAll(`data-screen-event-move="${key}"`, `data-screen-event-move="${repeatedKey}"`)
        .replace(new RegExp(`${baseLabelForEvent(key)}(?![0-9])`, "g"), `${baseLabelForEvent(key)} #${index}`);
      repeated.classList.add("hidden");
      first.parentElement?.appendChild(repeated);
    });
  });
}

function baseLabelForEvent(key) {
  return {
    macd: "MACD Event",
    stoch: "StochRSI Event",
    supertrend: "Supertrend Event",
    ema_relationship: "EMA Cross Event",
    price_ema: "Price / EMA Event",
    volume_spike: "Volume Spike Event",
    ema_flatten: "EMA Flatten Event",
    ha_ema_volume: "HA EMA + Volume Event",
  }[key] || key;
}

function getTimelineStepId(key) {
  return `screen-${getTimelineDomKey(key)}-event-step`;
}

function renderTimelineRuleLibrary() {
  const select = document.getElementById("screen-rule-library-select");
  if (!select) {
    return;
  }
  const available = getTimelineRuleDefinitions().filter(
    (definition) => {
      if (definition.key.startsWith("rsi")) {
        const rsiCount = screenEventOrder.filter((key) => RSI_TIMELINE_KEYS.includes(key)).length;
        if (definition.key === "rsi") return rsiCount === 0;
        const nextRsiKey = `rsi_${rsiCount + 1}`;
        return rsiCount < RSI_TIMELINE_KEYS.length && definition.key === nextRsiKey && !screenEventOrder.includes(definition.key);
      }
      const repeatedMatch = definition.key.match(/^(.+)_(2|3)$/);
      if (repeatedMatch && REPEATABLE_TIMELINE_BASE_KEYS.includes(repeatedMatch[1])) {
        const instanceCount = screenEventOrder.filter((key) => key === repeatedMatch[1] || key.startsWith(`${repeatedMatch[1]}_`)).length;
        return instanceCount < 3 && definition.key === `${repeatedMatch[1]}_${instanceCount + 1}` && !screenEventOrder.includes(definition.key);
      }
      return !screenEventOrder.includes(definition.key);
    }
  );
  select.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  if (available.length === 0) {
    placeholder.textContent = "All rules are in the stack";
    select.disabled = true;
  } else {
    placeholder.textContent = "Add a Timeline Rule...";
    select.disabled = false;
  }
  select.appendChild(placeholder);
  available.forEach((definition) => {
    const option = document.createElement("option");
    option.value = definition.key;
     const baseKey = definition.key.replace(/_(2|3)$/, "");
     const baseDefinition = getTimelineRuleDefinitions().find((item) => item.key === baseKey);
     option.textContent = `Add ${definition.key.startsWith("rsi") ? "RSI" : (baseDefinition?.label || definition.label)}`;
    select.appendChild(option);
  });
  if (select.dataset.timelineLibraryBound !== "1") {
    select.dataset.timelineLibraryBound = "1";
    select.addEventListener("change", (event) => {
      const key = event.target.value;
      if (key) {
        addTimelineStep(key);
      }
      event.target.value = "";
    });
  }
}

function reorderTimelineSteps() {
  const stack = document.getElementById("screen-sequence-badges")?.parentElement;
  if (!stack) return;
  getTimelineRuleDefinitions().forEach(({ key }) => {
    const step = document.getElementById(getTimelineStepId(key));
    if (step) {
      step.classList.toggle("hidden", !screenEventOrder.includes(key));
    }
  });
  screenEventOrder.forEach((key) => {
    const step = document.getElementById(getTimelineStepId(key));
    if (step) stack.appendChild(step);
  });
  renderTimelineRuleLibrary();
}

function addTimelineStep(key) {
  const definition = getTimelineRuleDefinitions().find((item) => item.key === key);
  if (!definition || screenEventOrder.includes(key)) {
    return;
  }
  let insertAt = screenEventOrder.length;
  if (key.startsWith("rsi")) {
    const lastRsiIndex = screenEventOrder.reduce(
      (last, item, index) => RSI_TIMELINE_KEYS.includes(item) ? index : last,
      -1,
    );
    insertAt = lastRsiIndex >= 0 ? lastRsiIndex + 1 : Math.min(1, screenEventOrder.length);
  }
  screenEventOrder.splice(insertAt, 0, key);
  const checkbox = document.getElementById(`screen-${getTimelineDomKey(key)}-event-enabled`);
  if (checkbox) {
    checkbox.checked = true;
  }
  screenActiveEventKey = key;
  reorderTimelineSteps();
  syncTimelineAgeConstraints();
  syncScreenFilterStateFromDom();
  selectTimelineEvent(key);
}

function removeTimelineStep(key) {
  if (!screenEventOrder.includes(key)) {
    return;
  }
  screenEventOrder = screenEventOrder.filter((item) => item !== key);
  const checkbox = document.getElementById(`screen-${getTimelineDomKey(key)}-event-enabled`);
  if (checkbox) {
    checkbox.checked = false;
  }
  if (screenActiveEventKey === key) {
    screenActiveEventKey = screenEventOrder[screenEventOrder.length - 1] || "";
  }
  reorderTimelineSteps();
  syncTimelineAgeConstraints();
  syncScreenFilterStateFromDom();
  selectTimelineEvent(screenActiveEventKey);
}

function getTimelineSliderId(key) {
  return key === "ema_relationship"
    ? "screen-ema-relationship-age"
    : key === "ema_flatten"
      ? "screen-ema-flatten-age"
    : `screen-${getTimelineDomKey(key)}-cross-age`;
}

function syncTimelineAgeConstraints({ clampValues = true } = {}) {
  // Event windows are independent for now; chronological ordering is intentionally disabled.
}

function syncTimelineMoveButtons() {
  document.querySelectorAll("[data-screen-event-move]").forEach((button) => {
    const index = screenEventOrder.indexOf(button.dataset.screenEventMove);
    button.disabled = button.dataset.direction === "up" ? index <= 0 : index < 0 || index >= screenEventOrder.length - 1;
  });
}

function updateRelativeTimelineVisuals(filters = screenFilters) {
  const enabledOrder = getScreenEventReadiness(filters).map((item) => item.key);
  const firstKey = enabledOrder[0];
  const lookback = Math.max(1, Number(filters.lookback_days || SCREEN_DEFAULT_FILTERS.lookback_days));
  const firstAge = firstKey ? Number(getScreenEventReadiness(filters).find((item) => item.key === firstKey)?.age || 0) : 0;
  const firstPosition = ((lookback - firstAge) / lookback) * 100;

  screenEventOrder.forEach((key) => {
    const slider = document.getElementById(getTimelineSliderId(key));
    const track = slider?.closest?.(".screen-range-track");
    if (!slider || !track) return;
    const marker = track.querySelector(".screen-relative-age-marker");
    const relativeIndex = enabledOrder.indexOf(key);
    if (!firstKey || relativeIndex <= 0) {
      slider.classList.remove("screen-relative-age-input");
      track.classList.remove("screen-relative-age-track");
      marker?.remove();
      return;
    }
    slider.classList.add("screen-relative-age-input");
    track.classList.add("screen-relative-age-track");
    const age = Number(getScreenEventReadiness(filters).find((item) => item.key === key)?.age || 0);
    const position = firstAge > 0
      ? firstPosition + ((firstAge - age) / firstAge) * (100 - firstPosition)
      : firstPosition;
    const nextMarker = marker || document.createElement("span");
    nextMarker.className = "screen-relative-age-marker";
    nextMarker.style.left = `${Math.max(firstPosition, Math.min(100, position))}%`;
    nextMarker.setAttribute("aria-hidden", "true");
    if (!marker) track.appendChild(nextMarker);
  });
}

function moveScreenEvent(key, direction) {
  const index = screenEventOrder.indexOf(key);
  const targetIndex = index + (direction === "up" ? -1 : 1);
  if (index < 0 || targetIndex < 0 || targetIndex >= screenEventOrder.length) return;
  const currentSlider = document.getElementById(getTimelineSliderId(key));
  const targetKey = screenEventOrder[targetIndex];
  const targetSlider = document.getElementById(getTimelineSliderId(targetKey));
  if (currentSlider && targetSlider) {
    [currentSlider.value, targetSlider.value] = [targetSlider.value, currentSlider.value];
  }
  [screenEventOrder[index], screenEventOrder[targetIndex]] = [screenEventOrder[targetIndex], screenEventOrder[index]];
  reorderTimelineSteps();
  syncTimelineAgeConstraints();
  syncScreenFilterStateFromDom();
}

function getTimelineStepKey(step) {
  const id = String(step?.id || "");
  const match = id.match(/^screen-(.+)-event-step$/);
  if (!match) return "";
  if (match[1] === "ema-relationship") return "ema_relationship";
  if (match[1] === "volume-spike") return "volume_spike";
  if (match[1] === "ema-flatten") return "ema_flatten";
  if (match[1] === "price-ema") return "price_ema";
  if (match[1] === "ha-ema-volume") return "ha_ema_volume";
  const rsiMatch = match[1].match(/^rsi-(\d+)$/);
  return rsiMatch ? `rsi_${rsiMatch[1]}` : match[1];
}

function selectTimelineEvent(key) {
  screenActiveEventKey = screenEventOrder.includes(key) ? key : "";
  document.querySelectorAll(".screen-timeline-step").forEach((step) => {
    step.classList.toggle("is-active", getTimelineStepKey(step) === screenActiveEventKey);
  });
}

function adjustActiveTimelineEvent(delta) {
  const slider = document.getElementById(getTimelineSliderId(screenActiveEventKey));
  if (!slider) return;
  slider.value = String(Math.max(0, Math.min(Number(slider.max || 0), Number(slider.value || 0) + delta)));
  syncTimelineAgeConstraints();
  syncScreenFilterStateFromDom();
}

function updateTimelineStepPositions(filters = screenFilters) {
  const badges = getScreenEventReadiness(filters);
  const node = document.getElementById("screen-sequence-badges");
  if (!node) {
    return;
  }
  if (badges.length === 0) {
    node.innerHTML = '<span class="rounded-full bg-white/85 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Volume only</span>';
    syncTimelineMoveButtons();
    updateRelativeTimelineVisuals(filters);
    return;
  }
  node.innerHTML = badges
    .map((item) => `<span class="rounded-full bg-white/85 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-rose-700">${escapeHtml(item.label)} ${escapeHtml(formatEventAge(item.age))}</span>`)
    .join("");
  syncTimelineMoveButtons();
  updateRelativeTimelineVisuals(filters);
}

function updateTimelineTrackBounds(lookbackDays) {
  ["screen-rsi-cross-age", "screen-rsi-2-cross-age", "screen-rsi-3-cross-age", "screen-macd-cross-age", "screen-stoch-cross-age", "screen-supertrend-cross-age", "screen-ema-relationship-age", "screen-ema-flatten-age", "screen-price-ema-cross-age", "screen-volume-spike-cross-age", "screen-ha-ema-volume-event-age"].forEach((id) => {
    const node = document.getElementById(id);
    if (node) {
      node.max = String(lookbackDays);
    }
  });
  syncTimelineAgeConstraints({ clampValues: false });
  const leftLabel = `${Math.round(lookbackDays)}d ago`;
  ["screen-rsi-axis-left", "screen-macd-axis-left", "screen-stoch-axis-left", "screen-supertrend-axis-left"].forEach((id) => {
    const node = document.getElementById(id);
    if (node) {
      node.textContent = leftLabel;
    }
  });
  const emaLeftLabel = document.getElementById("screen-ema-relationship-axis-left");
  if (emaLeftLabel) {
    emaLeftLabel.textContent = leftLabel;
  }
  const priceEmaLeftLabel = document.getElementById("screen-price-ema-axis-left");
  if (priceEmaLeftLabel) {
    priceEmaLeftLabel.textContent = leftLabel;
  }
  const emaFlattenLeftLabel = document.getElementById("screen-ema-flatten-axis-left");
  if (emaFlattenLeftLabel) {
    emaFlattenLeftLabel.textContent = leftLabel;
  }
  const haEmaVolumeLeftLabel = document.getElementById("screen-ha-ema-volume-axis-left");
  if (haEmaVolumeLeftLabel) {
    haEmaVolumeLeftLabel.textContent = leftLabel;
  }
}

function updateScreenSequenceSummary(filters = screenFilters) {
  const node = document.getElementById("screen-sequence-summary");
  if (!node) {
    return;
  }
  const phases = getScreenEventReadiness(filters);
  node.textContent = phases.length > 0
    ? `${phases.map((phase) => phase.label).join(" -> ")} by event point`
    : "Volume-only screen with no event requirements";
}

function syncScreenEventToggleChrome(filters = screenFilters) {
  [
    { key: "rsi_event_enabled", checkboxId: "screen-rsi-event-enabled", stepId: "screen-rsi-event-step" },
    { key: "rsi_2_event_enabled", checkboxId: "screen-rsi-2-event-enabled", stepId: "screen-rsi-2-event-step" },
    { key: "rsi_3_event_enabled", checkboxId: "screen-rsi-3-event-enabled", stepId: "screen-rsi-3-event-step" },
    { key: "macd_event_enabled", checkboxId: "screen-macd-event-enabled", stepId: "screen-macd-event-step" },
    { key: "stoch_event_enabled", checkboxId: "screen-stoch-event-enabled", stepId: "screen-stoch-event-step" },
    { key: "supertrend_event_enabled", checkboxId: "screen-supertrend-event-enabled", stepId: "screen-supertrend-event-step" },
    { key: "ema_relationship_enabled", checkboxId: "screen-ema-relationship-event-enabled", stepId: "screen-ema-relationship-event-step" },
    { key: "price_ema_event_enabled", checkboxId: "screen-price-ema-event-enabled", stepId: "screen-price-ema-event-step" },
    { key: "volume_spike_enabled", checkboxId: "screen-volume-spike-event-enabled", stepId: "screen-volume-spike-event-step" },
    { key: "ema_flatten_enabled", checkboxId: "screen-ema-flatten-event-enabled", stepId: "screen-ema-flatten-event-step" },
    { key: "ha_ema_volume_enabled", checkboxId: "screen-ha-ema-volume-event-enabled", stepId: "screen-ha-ema-volume-event-step" },
  ].forEach(({ key, checkboxId, stepId }) => {
    const enabled = Boolean(filters[key]);
    const checkbox = document.getElementById(checkboxId);
    const step = document.getElementById(stepId);
    if (checkbox) {
      checkbox.checked = enabled;
    }
    if (step) {
      step.classList.toggle("is-disabled", !enabled);
      step.setAttribute("aria-disabled", enabled ? "false" : "true");
    }
  });
}

