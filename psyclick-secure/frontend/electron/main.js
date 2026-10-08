const { app, BrowserWindow, shell, ipcMain, dialog } = require('electron')
const { spawn } = require('child_process')
const path  = require('path')
const http  = require('http')
const fs = require('fs')
const os = require('os')

const isDev = process.env.NODE_ENV === 'development'

// One PsyClick at a time: a second copy would fight the first over the local service
if (!isDev && !app.requestSingleInstanceLock()) { app.quit(); process.exit(0) }
app.on('second-instance', () => {
  if (mainWindow) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.focus() }
})

let mainWindow
let apiProcess
let apiStartupError = null
let apiExited = false

function readDatabaseUrlFromFile(cfgPath) {
  try {
    if (!cfgPath || !fs.existsSync(cfgPath)) return null
    const raw = fs.readFileSync(cfgPath, 'utf8').replace(/^\uFEFF/, '')
    const cfg = JSON.parse(raw)
    const url = (cfg.database_url || cfg.database || '').trim()
    if (url.startsWith('postgresql://') || url.startsWith('postgres://')) {
      return url
    }
  } catch (e) {
    console.error('[CONFIG] Failed reading', cfgPath, e.message)
  }
  return null
}

/**
 * Supabase URL for the bundled API process: packaged resources, then standard PsyClick paths.
 * Matches database_manager discovery so installs work without shipping the project folder.
 */
function resolveDbUrlForApi() {
  const candidates = [
    path.join(process.resourcesPath, 'config.json'),
    path.join(process.resourcesPath, '..', 'config.json'),
  ]
  const roaming = process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming')
  candidates.push(path.join(roaming, 'PsyClick', 'config.json'))
  try {
    candidates.push(path.join(app.getPath('userData'), 'config.json'))
  } catch (_) { /* app not ready; skip */ }

  for (const p of candidates) {
    const url = readDatabaseUrlFromFile(path.normalize(p))
    if (url) {
      console.log('[CONFIG] Using database_url from', p)
      return url
    }
  }
  console.error('[CONFIG] No config.json with database_url found. Checked:', candidates)
  return null
}

// ── Start bundled Flask API (production only) ─────────────────────────────────
function startAPI() {
  const exePath = path.join(process.resourcesPath, 'psyclick_api', 'psyclick_api.exe')
  const dbUrl = resolveDbUrlForApi()
  apiStartupError = null

  if (!fs.existsSync(exePath)) {
    apiStartupError = `Bundled API executable is missing: ${exePath}`
    console.error('[API]', apiStartupError)
    return
  }

  try {
    apiProcess = spawn(exePath, [], {
      stdio: 'pipe',
      windowsHide: true,
      env: {
        ...process.env,
        ...(dbUrl ? { PSYCLICK_DB_URL: dbUrl } : {}),
      },
    })
  } catch (e) {
    apiStartupError = `Unable to start bundled API: ${e.message}`
    console.error('[API]', apiStartupError)
    return
  }

  apiProcess.stdout.on('data', d => console.log('[API]', d.toString().trim()))
  apiProcess.stderr.on('data', d => {
    const msg = d.toString().trim()
    apiStartupError = msg || apiStartupError
    console.error('[API]', msg)
  })
  apiProcess.on('error', e => {
    apiStartupError = `API process error: ${e.message}`
    console.error('[API]', apiStartupError)
  })
  apiProcess.on('exit', code => {
    apiExited = true
    if (code !== 0) apiStartupError = apiStartupError || `API exited before startup completed (code ${code}).`
    console.log('[API] exited', code)
  })
}

// ── Poll until API is ready ───────────────────────────────────────────────────
// The first launch after an install can be slow (Windows checks every new file;
// 80 s was measured), so wait up to 4 minutes, and give up early only when the
// service has actually exited.
function waitForAPI(cb, retries = 480) {
  const req = http.get('http://127.0.0.1:5101/api/ping', res => {
    res.resume()
    if (res.statusCode === 200) cb()
    else retry()
  })
  req.setTimeout(2000, () => req.destroy())
  req.on('error', retry)

  function retry() {
    if (apiExited) { console.error('API exited before it was ready', apiStartupError || ''); return cb() }
    if (retries > 0) setTimeout(() => waitForAPI(cb, retries - 1), 500)
    else { console.error('API never became ready', apiStartupError || 'No details available'); cb() }
  }
}

// Something already answering on the service port (for example a copy left
// running by an earlier crash) is reused instead of starting a second one.
function apiAlreadyRunning() {
  return new Promise(resolve => {
    const req = http.get('http://127.0.0.1:5101/api/ping', res => { res.resume(); resolve(res.statusCode === 200) })
    req.setTimeout(1500, () => { req.destroy(); resolve(false) })
    req.on('error', () => resolve(false))
  })
}

function stopAPI() {
  if (!apiProcess) return
  try {
    // taskkill /T ends the whole tree, so no service is left behind holding the port
    spawn('taskkill', ['/PID', String(apiProcess.pid), '/T', '/F'], { windowsHide: true })
  } catch (_) { try { apiProcess.kill() } catch (_) { /* already gone */ } }
  apiProcess = null
}

const SPLASH = 'data:text/html;charset=utf-8,' + encodeURIComponent(`<!doctype html><meta charset="utf-8">
<title>PsyClick</title><style>
  html,body{height:100%;margin:0;background:#F0F4F8;font-family:Segoe UI,system-ui,sans-serif;color:#0F2A33}
  main{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;text-align:center;padding:24px}
  .ring{width:44px;height:44px;border-radius:50%;border:4px solid #CFE3E6;border-top-color:#0A6B80;animation:s 0.9s linear infinite}
  @keyframes s{to{transform:rotate(360deg)}} h1{font-size:22px;margin:6px 0 0} p{margin:0;color:#4A6670;max-width:42ch;line-height:1.5}
</style><main><div class="ring"></div><h1>Starting PsyClick…</h1>
<p>The first start after installing can take a minute or two while Windows checks the app. PsyClick opens by itself.</p></main>`)

// ── Create window ─────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width:          1440,
    height:         900,
    minWidth:       1100,
    minHeight:      700,
    backgroundColor:'#F0F4F8',
    title:          'PsyClick Secure — Clinical Decision Support',
    icon:           isDev ? path.join(__dirname, '..', '..', 'images', 'LOGOggg.png') : path.join(process.resourcesPath, 'images', 'LOGOggg.png'),
    webPreferences: {
      nodeIntegration:  false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  })

  mainWindow.maximize()
  mainWindow.setMenuBarVisibility(false)

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }
  mainWindow.on('closed', () => { mainWindow = null })

  // Ensure keyboard focus goes to the renderer whenever the window is focused
  mainWindow.on('focus', () => {
    mainWindow.webContents.focus()
    // Force focus into the active element (textarea/input) in the renderer
    mainWindow.webContents.executeJavaScript(
      'if (document.activeElement && typeof document.activeElement.focus === "function") { document.activeElement.focus() }'
    ).catch(() => {})
  })
  mainWindow.webContents.on('did-finish-load', () => mainWindow.webContents.focus())

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url); return { action: 'deny' }
  })
}

// ── IPC — open file in browser (for exports) ──────────────────────────────────
ipcMain.on('open-external', (_e, url) => shell.openExternal(url))

// ── IPC — save the open report as a PDF where the clinician chooses ──────────
ipcMain.handle('save-report-pdf', async (event, { defaultName } = {}) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  const safeName = String(defaultName || 'PsyClick report.pdf').replace(/[<>:"/\\|?*]+/g, '-')
  const { canceled, filePath } = await dialog.showSaveDialog(win, {
    title: 'Save report as PDF',
    defaultPath: path.join(app.getPath('documents'), safeName),
    filters: [{ name: 'PDF document', extensions: ['pdf'] }],
  })
  if (canceled || !filePath) return { canceled: true }
  try {
    const pdf = await event.sender.printToPDF({
      printBackground: true,
      pageSize: 'A4',
      margins: { marginType: 'custom', top: 0.4, bottom: 0.4, left: 0.4, right: 0.4 },
    })
    await fs.promises.writeFile(filePath, pdf)
    return { filePath }
  } catch (e) {
    return { error: `The PDF could not be saved: ${e.message}` }
  }
})
ipcMain.on('show-in-folder', (_e, filePath) => shell.showItemInFolder(filePath))

// ── Lifecycle ─────────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  if (isDev) return waitForAPI(createWindow)      // concurrently already starts Flask in dev
  // Show a window straight away, so a slow first start never looks like a hang
  const splash = new BrowserWindow({ width: 560, height: 360, frame: false, resizable: false, center: true,
    backgroundColor: '#F0F4F8', show: true, icon: path.join(process.resourcesPath, 'images', 'LOGOggg.png') })
  splash.loadURL(SPLASH)
  if (!(await apiAlreadyRunning())) startAPI()
  waitForAPI(() => { createWindow(); mainWindow.once('ready-to-show', () => splash.destroy()); setTimeout(() => { if (!splash.isDestroyed()) splash.destroy() }, 4000) })
})

app.on('window-all-closed', () => {
  stopAPI()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', stopAPI)
