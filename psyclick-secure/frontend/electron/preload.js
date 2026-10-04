const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electron', {
  openExternal: (url) => ipcRenderer.send('open-external', url),
  saveReportPdf: (opts) => ipcRenderer.invoke('save-report-pdf', opts),
  showInFolder: (filePath) => ipcRenderer.send('show-in-folder', filePath),
})
