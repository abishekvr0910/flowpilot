/**
 * FlowPilot Full-Stack Node.js Integration & Web/API Client Test
 * Validates:
 * 1. FastAPI Web Server startup & Static File Serving (HTML, CSS, JS)
 * 2. REST API endpoints (/api/config) via Node.js native fetch
 * 3. Bidirectional WebSocket protocol (/ws) via Node.js native WebSocket
 * 4. State synchronization between web client and core orchestrator
 */

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const TEST_PORT = 8766;
const BASE_URL = `http://127.0.0.1:${TEST_PORT}`;
const WS_URL = `ws://127.0.0.1:${TEST_PORT}/ws`;

console.log("=".repeat(70));
console.log("  FLOWPILOT FULL-STACK NODE.JS INTEGRATION & CLIENT VERIFICATION");
console.log("=".repeat(70));
console.log(`Node.js Runtime: ${process.version}`);
console.log(`Target Test Endpoint: ${BASE_URL}\n`);

// Phase 1: Launch FastAPI Engine Server
console.log("[Phase 1] Launching Python FastAPI / Uvicorn Server on port " + TEST_PORT + "...");
const serverProcess = spawn("python", [
  "-c",
  `import uvicorn; from engine.server import app; uvicorn.run(app, host='127.0.0.1', port=${TEST_PORT}, log_level='warning')`
], { stdio: "pipe" });

serverProcess.stderr.on("data", (chunk) => {
  const msg = chunk.toString();
  if (msg.includes("ERROR")) {
    console.error(`[Server Error] ${msg.trim()}`);
  }
});

let serverReady = false;
for (let i = 0; i < 20; i++) {
  await sleep(500);
  try {
    const res = await fetch(`${BASE_URL}/api/config`);
    if (res.ok) {
      serverReady = true;
      console.log(`Server responded successfully after ${(i + 1) * 0.5}s.`);
      break;
    }
  } catch {
    // Retry until bound
  }
}

if (!serverReady) {
  console.error("FATAL: Python server failed to start within 10 seconds.");
  serverProcess.kill();
  process.exit(1);
}

try {
  // Phase 2: Static Assets Verification
  console.log("\n[Phase 2] Verifying Web Companion Static File Serving...");
  
  const indexRes = await fetch(`${BASE_URL}/`);
  const indexHtml = await indexRes.text();
  console.log(`  GET / -> Status: ${indexRes.status} (Length: ${indexHtml.length} bytes)`);
  if (!indexHtml.includes("FlowPilot")) throw new Error("Index HTML does not contain 'FlowPilot'");

  const cssRes = await fetch(`${BASE_URL}/styles.css`);
  console.log(`  GET /styles.css -> Status: ${cssRes.status}`);
  if (cssRes.status !== 200) throw new Error("styles.css failed to load");

  const jsRes = await fetch(`${BASE_URL}/app.js`);
  const jsContent = await jsRes.text();
  console.log(`  GET /app.js -> Status: ${jsRes.status} (Length: ${jsContent.length} bytes)`);
  if (!jsContent.includes("connectWebSocket")) throw new Error("app.js missing WebSocket logic");

  console.log("  -> SUCCESS: All web companion assets served cleanly.");

  // Phase 3: REST API Verification
  console.log("\n[Phase 3] Testing REST API (/api/config)...");
  
  const configRes = await fetch(`${BASE_URL}/api/config`);
  const configData = await configRes.json();
  console.log(`  GET /api/config -> Status: ${configRes.status}`);
  console.log(`  Reported Engine Mode: ${configData.engine_mode || "local"}`);
  console.log(`  Active Tone Mode: ${configData.active_tone_mode || "developer"}`);

  const postRes = await fetch(`${BASE_URL}/api/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active_tone_mode: "developer", engine_mode: "local" })
  });
  const postResult = await postRes.json();
  console.log(`  POST /api/config -> Status: ${postRes.status}, Result: ${postResult.status}`);
  if (postResult.status !== "success") throw new Error("POST /api/config did not return 'success'");

  // Phase 4: Native Node.js WebSocket Protocol Verification
  console.log("\n[Phase 4] Testing Bidirectional WebSocket (/ws) via Native Node.js WebSocket...");
  
  await new Promise((resolve, reject) => {
    const ws = new WebSocket(WS_URL);
    const timeout = setTimeout(() => {
      ws.close();
      reject(new Error("WebSocket handshake timed out"));
    }, 8000);

    let stage = 0;

    ws.onopen = () => {
      console.log("  WebSocket connection established successfully.");
    };

    ws.onmessage = async (event) => {
      try {
        const msg = JSON.parse(event.data);
        // Stage 0: Initial handshake
        if (stage === 0) {
          console.log(`  [WS Stage 0] Received handshake event: state='${msg.state}'`);
          if (msg.state === "connected") {
            stage = 1;
            console.log("  [WS Stage 1] Dispatching action: 'start'...");
            ws.send(JSON.stringify({ action: "start" }));
          }
        } else if (stage === 1) {
          // Stage 1: Transitioning to listening
          if (msg.state === "starting" || msg.state === "listening") {
            console.log(`  [WS Stage 1] State transition confirmed: state='${msg.state}'`);
            if (msg.state === "listening") {
              stage = 2;
              console.log("  [WS Stage 2] Dispatching action: 'stop' to finalize dictation...");
              await sleep(300);
              ws.send(JSON.stringify({ action: "stop" }));
            }
          }
        } else if (stage === 2) {
          // Stage 2: Stop/transition - ignore intermediate audio levels and assert terminal state
          if (msg.state === "audio_level") {
            return;
          }
          if (["stopping", "processing", "formatting", "pasted", "idle"].includes(msg.state)) {
            console.log(`  [WS Stage 2] Finalization lifecycle confirmed: state='${msg.state}'`);
            clearTimeout(timeout);
            ws.close();
            resolve();
          }
        }
      } catch (err) {
        clearTimeout(timeout);
        ws.close();
        reject(err);
      }
    };

    ws.onerror = (err) => {
      clearTimeout(timeout);
      reject(err);
    };
  });

  console.log("  -> SUCCESS: Full bidirectional WebSocket lifecycle verified.");

  console.log("\n" + "=".repeat(70));
  console.log("  FULL-STACK NODE.JS & FASTAPI INTEGRATION: ALL CHECKS PASSED");
  console.log("=".repeat(70));

} finally {
  console.log("\n[Cleanup] Terminating Python server process (PID: " + serverProcess.pid + ")...");
  serverProcess.kill("SIGTERM");
  await sleep(1000);
  try {
    process.kill(serverProcess.pid, "SIGKILL");
  } catch {
    // Already terminated
  }
}
