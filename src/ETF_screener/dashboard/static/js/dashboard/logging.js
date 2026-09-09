// Dashboard logging. See README.md in static/js/dashboard for the feature map.

// --- Console Log Capture System ---
const consoleLogs = [];
const maxLogsBeforeSend = 50;

function setupConsoleCapture() {
  const originalLog = console.log;
  const originalError = console.error;
  const originalWarn = console.warn;
  const originalInfo = console.info;
  
  const captureLog = (level, args) => {
    const timestamp = new Date().toISOString();
    const message = args.map(arg => {
      if (typeof arg === 'object') {
        try { return JSON.stringify(arg); } catch { return String(arg); }
      }
      return String(arg);
    }).join(' ');
    
    consoleLogs.push({ timestamp, level, message });
    if (consoleLogs.length >= maxLogsBeforeSend) {
      flushConsoleLogs();
    }
  };
  
  console.log = function(...args) {
    originalLog.apply(console, args);
    captureLog('LOG', args);
  };
  
  console.error = function(...args) {
    originalError.apply(console, args);
    captureLog('ERROR', args);
  };
  
  console.warn = function(...args) {
    originalWarn.apply(console, args);
    captureLog('WARN', args);
  };
  
  console.info = function(...args) {
    originalInfo.apply(console, args);
    captureLog('INFO', args);
  };
  
  // Flush remaining logs on page unload
  window.addEventListener('beforeunload', flushConsoleLogs);
  
  // Flush logs every 30 seconds
  setInterval(flushConsoleLogs, 30000);
}

async function flushConsoleLogs() {
  if (consoleLogs.length === 0) return;
  const logsToSend = [...consoleLogs];
  consoleLogs.length = 0;
  
  try {
    await fetch('/api/log/console', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ logs: logsToSend })
    });
  } catch (err) {
    // Silently fail to avoid infinite loops if logging fails
  }
}


