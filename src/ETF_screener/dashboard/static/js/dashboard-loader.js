const DASHBOARD_SCRIPT_SRC = "/static/js/dashboard.js?v=20260507e";
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
    console.info("[SWARM] Local Three.js module loaded", {
      revision: THREE?.REVISION || "unknown",
      source: THREE_MODULE_SRC,
    });
  })
  .catch((err) => {
    console.error("[SWARM] Failed to load local Three.js module", err);
  })
  .finally(() => {
    injectDashboardScript();
  });
