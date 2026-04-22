const { app, BrowserWindow, session, shell, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');

// ---------------------------------------------------------------------------
// Config — adjust these if your ports / paths differ
// ---------------------------------------------------------------------------
const BACKEND_PORT = parseInt(process.env.BACKEND_PORT || '7001', 10);
const FRONTEND_PORT = parseInt(process.env.FRONTEND_PORT || '3002', 10);
const BACKEND_DIR = path.resolve(__dirname, '..', '..');          // neurocomputer-dev/
const FRONTEND_DIR = path.resolve(__dirname, '..');               // neuro_web/
const PYTHON = process.env.PYTHON_PATH || 'python';              // or full path to venv python
const FRONTEND_URL = `http://localhost:${FRONTEND_PORT}`;

let backendProc = null;
let frontendProc = null;
let mainWindow = null;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Wait until a TCP port is accepting connections (up to timeoutMs). */
function waitForPort(port, timeoutMs = 30000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    function tryConnect() {
      if (Date.now() - start > timeoutMs) {
        return reject(new Error(`Port ${port} not ready after ${timeoutMs}ms`));
      }
      const sock = new net.Socket();
      sock.once('connect', () => { sock.destroy(); resolve(); });
      sock.once('error', () => { sock.destroy(); setTimeout(tryConnect, 500); });
      sock.connect(port, '127.0.0.1');
    }
    tryConnect();
  });
}

/** Check if a port is already listening. */
function isPortOpen(port) {
  return new Promise((resolve) => {
    const sock = new net.Socket();
    sock.once('connect', () => { sock.destroy(); resolve(true); });
    sock.once('error', () => { sock.destroy(); resolve(false); });
    sock.connect(port, '127.0.0.1');
  });
}

/** Spawn a child process, pipe its stdio to the main process console. */
function spawnLogged(cmd, args, opts) {
  const child = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'], ...opts });
  const label = `[${path.basename(cmd)}:${args[0] || ''}]`;
  child.stdout?.on('data', (d) => process.stdout.write(`${label} ${d}`));
  child.stderr?.on('data', (d) => process.stderr.write(`${label} ${d}`));
  child.on('error', (e) => console.error(`${label} spawn error:`, e.message));
  return child;
}

// ---------------------------------------------------------------------------
// Server management
// ---------------------------------------------------------------------------

async function startBackend() {
  if (await isPortOpen(BACKEND_PORT)) {
    console.log(`Backend already running on port ${BACKEND_PORT}`);
    return;
  }
  console.log(`Starting backend on port ${BACKEND_PORT}...`);
  backendProc = spawnLogged(PYTHON, ['server.py'], {
    cwd: BACKEND_DIR,
    env: { ...process.env, PORT: String(BACKEND_PORT) },
  });
  await waitForPort(BACKEND_PORT);
  console.log('Backend ready.');
}

async function startFrontend() {
  if (await isPortOpen(FRONTEND_PORT)) {
    console.log(`Frontend already running on port ${FRONTEND_PORT}`);
    return;
  }
  console.log(`Starting frontend on port ${FRONTEND_PORT}...`);
  // Use `next dev` so no production build is required and source changes
  // hot-reload inside the Electron window. Override with NEXT_MODE=start
  // to use the production server (requires `next build` first).
  const mode = (process.env.NEXT_MODE || 'dev').toLowerCase();
  frontendProc = spawnLogged('npx', ['next', mode, '-p', String(FRONTEND_PORT)], {
    cwd: FRONTEND_DIR,
    env: { ...process.env },
    shell: true,
  });
  await waitForPort(FRONTEND_PORT);
  console.log('Frontend ready.');
}

function killProc(proc) {
  if (!proc || proc.killed) return;
  try {
    // Kill the process group to catch child processes
    process.kill(-proc.pid, 'SIGTERM');
  } catch {
    try { proc.kill('SIGTERM'); } catch {}
  }
}

function cleanup() {
  killProc(backendProc);
  killProc(frontendProc);
}

// ---------------------------------------------------------------------------
// Electron window
// ---------------------------------------------------------------------------

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'Neuro',
    backgroundColor: '#0a0a1a',
    frame: false,
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL(FRONTEND_URL);

  // Open external links in the system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ---------------------------------------------------------------------------
// IPC: window controls from renderer
// ---------------------------------------------------------------------------
ipcMain.on('window:minimize', () => mainWindow?.minimize());
ipcMain.on('window:maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.on('window:close', () => mainWindow?.close());

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------

app.on('ready', async () => {
  // Auto-grant microphone / camera / media permissions for the app's own
  // pages. Without this, navigator.mediaDevices.getUserMedia() rejects and
  // LiveKit's createLocalAudioTrack() surfaces as "Requested device not found"
  // (actually a permission issue in many cases).
  session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback) => {
    const allowed = new Set([
      'media',
      'audioCapture',
      'videoCapture',
      'mediaKeySystem',
      'display-capture',
    ]);
    callback(allowed.has(permission));
  });
  session.defaultSession.setPermissionCheckHandler((_webContents, permission) => {
    return ['media', 'audioCapture', 'videoCapture', 'mediaKeySystem'].includes(permission);
  });

  try {
    await startBackend();
    await startFrontend();
  } catch (e) {
    console.error('Failed to start servers:', e.message);
    // Still open the window — user might have servers running manually
  }
  createWindow();
});

app.on('window-all-closed', () => {
  cleanup();
  app.quit();
});

app.on('before-quit', cleanup);

// macOS: re-create window when dock icon clicked
app.on('activate', () => {
  if (mainWindow === null) createWindow();
});
