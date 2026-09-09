// Dashboard screen-bindings. See README.md in static/js/dashboard for the feature map.

function bindScreenControlInputs() {
  const dslEditor = document.getElementById("screen-dsl-editor");
  if (dslEditor && dslEditor.dataset.validationBound !== "1") {
    dslEditor.dataset.validationBound = "1";
    dslEditor.addEventListener("input", () => {
      setLoadedDslxScript();
      updateScanActionButtonsState();
    });
  }
  const exitEditor = document.getElementById("screen-exit-editor");
  if (exitEditor && exitEditor.dataset.validationBound !== "1") {
    exitEditor.dataset.validationBound = "1";
    exitEditor.addEventListener("input", updateBacktestRunButtonState);
  }
  [
    "screen-volume-min",
    "screen-volume-max",
    "screen-rsi-filter-enabled",
    "screen-rsi-filter-min",
    "screen-rsi-cross-value",
    "screen-rsi-event-enabled",
    "screen-rsi-cross-mode",
    "screen-rsi-2-cross-value",
    "screen-rsi-2-event-enabled",
    "screen-rsi-2-cross-mode",
    "screen-rsi-3-cross-value",
    "screen-rsi-3-event-enabled",
    "screen-rsi-3-cross-mode",
    "screen-stoch-cross-value",
    "screen-stoch-event-enabled",
    "screen-stoch-cross-mode",
    "screen-supertrend-event-enabled",
    "screen-supertrend-cross-mode",
    "screen-macd-event-enabled",
    "screen-macd-cross-mode",
    "screen-macd-cross-age",
    "screen-rsi-cross-age",
    "screen-rsi-2-cross-age",
    "screen-rsi-3-cross-age",
    "screen-stoch-cross-age",
    "screen-supertrend-cross-age",
    "screen-ema-relationship-age",
    "screen-ema-flatten-age",
    "screen-ema-relationship-event-enabled",
    "screen-ema-relationship-fast",
    "screen-ema-relationship-slow",
    "screen-ema-relationship-slope",
    "screen-ema-relationship-fast-slope",
    "screen-ema-relationship-slow-slope",
    "screen-ema-relationship-cross-mode",
    "screen-price-ema-event-enabled",
    "screen-price-ema-period",
    "screen-price-ema-source",
    "screen-price-ema-cross-mode",
    "screen-price-ema-cross-age",
    "screen-volume-spike-event-enabled",
    "screen-volume-spike-period",
    "screen-volume-spike-multiplier",
    "screen-volume-spike-cross-age",
    "screen-ha-ema-volume-event-enabled",
    "screen-ha-ema-volume-condition-open-enabled",
    "screen-ha-ema-volume-condition-high-enabled",
    "screen-ha-ema-volume-condition-low-enabled",
    "screen-ha-ema-volume-condition-close-enabled",
    "screen-ha-ema-volume-condition-open-zone",
    "screen-ha-ema-volume-condition-high-zone",
    "screen-ha-ema-volume-condition-low-zone",
    "screen-ha-ema-volume-condition-close-zone",
    "screen-ha-ema-volume-candle-color",
    "screen-ha-ema-volume-ema1-period",
    "screen-ha-ema-volume-ema2-period",
    "screen-ha-ema-volume-ema1-source-open",
    "screen-ha-ema-volume-ema1-source-high",
    "screen-ha-ema-volume-ema1-source-low",
    "screen-ha-ema-volume-ema1-source-close",
    "screen-ha-ema-volume-ema2-source-open",
    "screen-ha-ema-volume-ema2-source-high",
    "screen-ha-ema-volume-ema2-source-low",
    "screen-ha-ema-volume-ema2-source-close",
    "screen-ha-ema-volume-start-field",
    "screen-ha-ema-volume-start-line",
    "screen-ha-ema-volume-start-relation",
    "screen-ha-ema-volume-end-field",
    "screen-ha-ema-volume-end-line",
    "screen-ha-ema-volume-end-relation",
    "screen-ha-ema-volume-period",
    "screen-ha-ema-volume-multiplier",
    "screen-ha-ema-volume-event-age",
    "screen-ha-ema-volume-rsi-enabled",
    "screen-ha-ema-volume-rsi-min",
    "screen-ema-flatten-event-enabled",
    "screen-ema-flatten-period",
    "screen-ema-flatten-lookback",
    "screen-ema-flatten-tolerance",
    "screen-ema-flatten-mode",
    "screen-ema-slope-period-1",
    "screen-ema-slope-period-2",
    "screen-ema-slope-period-3",
    "screen-ema-slope-1",
    "screen-ema-slope-2",
    "screen-ema-slope-3",
    "screen-ema-slope-lookback",
    "screen-ema-slope-tolerance",
  ].forEach((id) => {
    const node = document.getElementById(id);
    if (!node || node.dataset.bound === "1") {
      return;
    }
    node.dataset.bound = "1";
    node.addEventListener("input", () => {
      if (id === "screen-volume-spike-multiplier" || id === "screen-ha-ema-volume-multiplier") {
        node.value = node.value.replace(",", ".");
      }
      const shouldRestoreFocus = document.activeElement === node;
      if (node.type === "checkbox" && node.id.endsWith("-event-enabled")) {
        const toggleKey = getTimelineStepKey(node.closest(".screen-timeline-step"));
        if (toggleKey) {
          if (node.checked && !screenEventOrder.includes(toggleKey)) {
            addTimelineStep(toggleKey);
            return;
          }
          // Keep an unchecked step in the stack so it can be visibly
          // greyed out and re-enabled. The remove button removes it.
          if (!node.checked && screenEventOrder.includes(toggleKey)) {
            reorderTimelineSteps();
          }
        }
      }
      syncTimelineAgeConstraints();
      const readoutIdBySlider = {
        "screen-rsi-filter-min": "screen-rsi-filter-min-readout",
        "screen-macd-cross-age": "screen-macd-cross-readout",
        "screen-rsi-cross-age": "screen-rsi-cross-readout",
        "screen-rsi-2-cross-age": "screen-rsi-2-cross-readout",
        "screen-rsi-3-cross-age": "screen-rsi-3-cross-readout",
        "screen-stoch-cross-age": "screen-stoch-cross-readout",
        "screen-supertrend-cross-age": "screen-supertrend-cross-readout",
        "screen-ema-relationship-age": "screen-ema-relationship-event-readout",
        "screen-ema-flatten-age": "screen-ema-flatten-event-readout",
        "screen-price-ema-cross-age": "screen-price-ema-event-readout",
        "screen-volume-spike-cross-age": "screen-volume-spike-cross-readout",
        "screen-ha-ema-volume-event-age": "screen-ha-ema-volume-event-readout",
      };
      const readoutId = readoutIdBySlider[id];
      if (readoutId) {
        if (id === "screen-rsi-filter-min") {
          const readout = document.getElementById(readoutId);
          if (readout) readout.textContent = String(node.value);
        } else {
          updateEventAgeReadoutFromSlider(id, readoutId);
        }
      }
      syncScreenFilterStateFromDom();
      if (shouldRestoreFocus) {
        node.focus({ preventScroll: true });
        requestAnimationFrame(() => node.focus({ preventScroll: true }));
      }
    });
    const sliderKey = screenEventOrder.find((key) => getTimelineSliderId(key) === id);
    if (sliderKey) {
      node.addEventListener("focus", () => selectTimelineEvent(sliderKey));
    }
    if (node.type === "range") {
      const stepKey = getTimelineStepKey(node.closest(".screen-timeline-step"));
      if (stepKey) {
        node.addEventListener("focus", () => selectTimelineEvent(stepKey));
      }
    }
  });
  document.querySelectorAll(".screen-timeline-step input[type=range]").forEach((node) => {
    if (node.dataset.bound === "1") return;
    node.dataset.bound = "1";
    node.addEventListener("input", () => {
      const shouldRestoreFocus = document.activeElement === node;
      const step = node.closest(".screen-timeline-step");
      const readout = step?.querySelector('[id$="-cross-readout"], [id$="-event-readout"]');
      if (readout) {
        const age = getEventSliderAge(node.id, screenFilters.lookback_days, 0);
        readout.textContent = formatTimelinePosition(age, screenFilters.lookback_days);
      }
      syncScreenFilterStateFromDom();
      if (shouldRestoreFocus) {
        node.focus({ preventScroll: true });
        requestAnimationFrame(() => node.focus({ preventScroll: true }));
      }
    });
  });
  document.querySelectorAll("[data-screen-event-move]").forEach((button) => {
    if (button.dataset.screenMoveBound === "1") return;
    button.dataset.screenMoveBound = "1";
    button.addEventListener("click", () => moveScreenEvent(button.dataset.screenEventMove, button.dataset.direction));
  });
  document.querySelectorAll("[data-screen-event-remove]").forEach((button) => {
    if (button.dataset.screenRemoveBound === "1") return;
    button.dataset.screenRemoveBound = "1";
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      removeTimelineStep(button.dataset.screenEventRemove);
    });
  });
  document.querySelectorAll(".screen-timeline-step").forEach((step) => {
    if (step.dataset.timelineSelectionBound === "1") return;
    step.dataset.timelineSelectionBound = "1";
    const key = getTimelineStepKey(step);
    step.tabIndex = 0;
    step.addEventListener("click", (event) => {
      selectTimelineEvent(key);
      if (!event.target.closest("input, select, button")) {
        step.focus({ preventScroll: true });
      }
    });
    step.addEventListener("focusin", () => selectTimelineEvent(key));
  });
  if (document.documentElement?.dataset?.timelineKeyboardBound !== "1") {
    if (document.documentElement?.dataset) {
      document.documentElement.dataset.timelineKeyboardBound = "1";
    }
    document.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const activeStep = document.getElementById(`screen-${getTimelineDomKey(screenActiveEventKey)}-event-step`);
      const target = event.target;
      if (!activeStep || (target !== document.body && target !== activeStep && !activeStep.contains(target))) return;
      event.preventDefault();
      if (target instanceof HTMLInputElement && target.type === "range") {
        const step = Number(target.step || 1);
        const min = Number(target.min || 0);
        const max = Number(target.max || 100);
        const direction = event.key === "ArrowLeft" ? -1 : 1;
        target.value = String(Math.max(min, Math.min(max, Number(target.value || 0) + (direction * step))));
        target.dispatchEvent(new Event("input", { bubbles: true }));
        target.focus({ preventScroll: true });
        requestAnimationFrame(() => target.focus({ preventScroll: true }));
        return;
      }
      adjustActiveTimelineEvent(event.key === "ArrowLeft" ? -1 : 1);
    });
  }
  selectTimelineEvent(screenActiveEventKey);
  [
    "chart-macd-fast",
    "chart-macd-slow",
    "chart-macd-signal",
    "chart-rsi-period",
    "chart-stoch-rsi-period",
    "chart-stoch-rsi-k",
    "chart-stoch-rsi-d",
    "chart-supertrend-period",
    "chart-supertrend-multiplier",
    "chart-candle-mode",
  ].forEach((id) => {
    const node = document.getElementById(id);
    if (!node || node.dataset.taApplyBound === "1") {
      return;
    }
    node.dataset.taApplyBound = "1";
    node.addEventListener("input", updateChartTAApplyButton);
  });
  ["screen-rsi-cross-value", "screen-stoch-cross-value"].forEach((id) => {
    const node = document.getElementById(id);
    if (!node || node.dataset.chartTriggerBound === "1") {
      return;
    }
    node.dataset.chartTriggerBound = "1";
    node.addEventListener("input", scheduleChartTriggerRefresh);
  });
  [
    "screen-ema-relationship-event-enabled",
    "screen-ema-relationship-fast",
    "screen-ema-relationship-slow",
    "screen-ema-relationship-mode",
    "screen-supertrend-event-enabled",
  ].forEach((id) => {
    const node = document.getElementById(id);
    if (!node || node.dataset.chartOverlayBound === "1") {
      return;
    }
    node.dataset.chartOverlayBound = "1";
    node.addEventListener("input", scheduleChartTriggerRefresh);
    node.addEventListener("change", scheduleChartTriggerRefresh);
  });
  ["below", "above", "any"].forEach((region) => {
    const node = document.getElementById(`screen-stoch-cross-region-${region}`);
    if (!node) return;
    if (node.dataset.screenRegionBound === "1") {
      return;
    }
    node.dataset.screenRegionBound = "1";
    node.addEventListener("change", syncScreenFilterStateFromDom);
  });
  ["below", "above", "any"].forEach((region) => {
    const node = document.getElementById(`screen-macd-cross-region-${region}`);
    if (!node || node.dataset.screenRegionBound === "1") {
      return;
    }
    node.dataset.screenRegionBound = "1";
    node.addEventListener("change", syncScreenFilterStateFromDom);
  });
  applyScreenFilters(screenFilters);
  setChartTAParametersApplied();
}

