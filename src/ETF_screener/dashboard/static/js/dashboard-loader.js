const DASHBOARD_SCRIPT_SRC = "/static/js/dashboard.js?v=20260607exclude1";
const THREE_MODULE_SRC = "/static/vendor/three/three.module.js";

function injectDashboardScript() {
  if (window.__dashboardScriptInjected) {
    return;
  }
  window.__dashboardScriptInjected = true;
  const script = document.createElement("script");
  script.src = DASHBOARD_SCRIPT_SRC;
  script.defer = true;
  document.body.appendChild(script);
}

import(THREE_MODULE_SRC)
  .then((THREE) => {
    window.THREE = THREE;
  })
  .catch((err) => {
    console.error("[SWARM] Failed to load local Three.js module", err);
  })
  .finally(() => {
    injectDashboardScript();
  });
