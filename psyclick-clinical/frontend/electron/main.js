const { app, BrowserWindow, shell, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path  = require('path')
const http  = require('http')
const fs = require('fs')
const os = require('os')

const isDev = process.env.NODE_ENV === 'development'

let mainWindow
let apiProcess
let apiStartupError = null

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
    if (code !== 0) apiStartupError = apiStartupError || `API exited before startup completed (code ${code}).`
    console.log('[API] exited', code)
  })
}

// ── Poll until API is ready ───────────────────────────────────────────────────
function waitForAPI(cb, retries = 60) {
  http.get('http://127.0.0.1:5001/api/ping', res => {
    if (res.statusCode === 200) cb()
    else retry()
  }).on('error', retry)

  function retry() {
    if (retries > 0) setTimeout(() => waitForAPI(cb, retries - 1), 500)
    else { console.error('API never became ready', apiStartupError || 'No details available'); cb() }
  }
}

// ── Create window ─────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width:          1440,
    height:         900,
    minWidth:       1100,
    minHeight:      700,
    backgroundColor:'#F0F4F8',
    title:          'PsyClick Clinical Edition — Clinical Decision Support',
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

// ── Lifecycle ─────────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  // In dev, concurrently already starts Flask — skip duplicate spawn
  if (!isDev) startAPI()
  waitForAPI(createWindow)
})

app.on('window-all-closed', () => {
  if (apiProcess) apiProcess.kill()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  if (apiProcess) apiProcess.kill()
})
