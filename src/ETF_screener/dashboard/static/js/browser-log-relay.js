(function () {
      const LOG_ENDPOINT = "/api/log";
      // Keep reference to original methods before we wrap them
      const _orig = {
        log: console.log.bind(console),
        info: console.info.bind(console),
        warn: console.warn.bind(console),
        error: console.error.bind(console),
        debug: console.debug.bind(console),
      };

      let _sending = false; // guard against recursive logging inside fetch()

      function sendLog(level, args) {
        if (_sending) return;
        try {
          const message = args
            .map((a) => {
              if (a instanceof Error) {
                return `${a.name}: ${a.message}`;
              }
              if (typeof a === "object" && a !== null) {
                try {
                  return JSON.stringify(a, null, 2);
                } catch (_) {
                  return String(a);
                }
              }
              return String(a);
            })
            .join(" ");

          // Capture stack for errors
          let stack = null;
          if (level === "error") {
            const errArg = args.find((a) => a instanceof Error);
            if (errArg?.stack) {
              stack = errArg.stack;
            } else {
              try { stack = new Error().stack; } catch (_) { }
            }
          }

          _sending = true;
          fetch(LOG_ENDPOINT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            // keepalive: true so the request survives page unload
            keepalive: true,
            body: JSON.stringify({
              level,
              message,
              stack,
              url: window.location.href,
              line: "",
            }),
          }).finally(() => { _sending = false; });
        } catch (_) {
          _sending = false;
        }
      }

      // Wrap each console method
      ["log", "info", "warn", "error", "debug"].forEach((method) => {
        console[method] = function (...args) {
          _orig[method](...args); // still write to DevTools
          sendLog(method === "log" ? "info" : method, args);
        };
      });

      // Also capture uncaught JS errors
      window.addEventListener("error", (event) => {
        sendLog("error", [
          `Uncaught ${event.message}`,
          `at ${event.filename}:${event.lineno}:${event.colno}`,
        ]);
      });

      // And unhandled promise rejections
      window.addEventListener("unhandledrejection", (event) => {
        sendLog("error", [
          "Unhandled promise rejection:",
          event.reason instanceof Error
            ? event.reason.message
            : String(event.reason),
        ]);
      });

      _orig.info("[ETF-Logger] Browser console → /api/log relay active");
    })();
