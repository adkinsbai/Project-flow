const { app, BrowserWindow, Menu, Tray, shell, nativeImage, ipcMain } = require('electron');
const path = require('path');

let mainWindow;
let tray;
let isQuitting = false;

function createTrayImage() {
  const svg = `
    <svg width="64" height="64" xmlns="http://www.w3.org/2000/svg">
      <rect width="64" height="64" rx="14" fill="#0d1117"/>
      <path d="M18 38h12v8H18zm16-20h12v8H34zm0 20h12v8H34z" fill="#58a6ff"/>
      <path d="M30 42h4M30 22h4M46 22v20" stroke="#bc8cff" stroke-width="4" stroke-linecap="round"/>
    </svg>`;
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`);
}

function showMainWindow() {
  if (!mainWindow) createMainWindow();
  mainWindow.show();
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.focus();
}

function sendToRenderer(channel, payload) {
  showMainWindow();
  mainWindow.webContents.send(channel, payload);
}

function buildTrayMenu() {
  return Menu.buildFromTemplate([
    { label: '反馈意见', click: () => sendToRenderer('desktop:open-panel', 'feedback') },
    { type: 'separator' },
    { label: '打开 Project Flow 主页', click: showMainWindow },
    { label: '显示历史记录', click: () => sendToRenderer('desktop:open-panel', 'history') },
    { label: '将词汇添加到词典', click: () => sendToRenderer('desktop:open-panel', 'dictionary') },
    { type: 'separator' },
    { label: '设置...', click: () => sendToRenderer('desktop:open-panel', 'settings') },
    {
      label: '选择麦克风',
      submenu: [
        { label: '系统默认麦克风', type: 'radio', checked: true, click: () => sendToRenderer('desktop:microphone', 'default') },
        { label: '稍后在应用内配置', click: () => sendToRenderer('desktop:open-panel', 'microphone') }
      ]
    },
    { type: 'separator' },
    { label: `版本 ${app.getVersion()}`, enabled: false },
    { label: '检查更新...', click: () => sendToRenderer('desktop:open-panel', 'updates') },
    { label: '退出 Project Flow', click: () => { isQuitting = true; app.quit(); } }
  ]);
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 980,
    minHeight: 640,
    title: 'Project Flow',
    backgroundColor: '#0d1117',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'index.html'));
  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(() => {
  app.setAppUserModelId('com.projectflow.app');
  createMainWindow();
  tray = new Tray(createTrayImage());
  tray.setToolTip('Project Flow');
  tray.setContextMenu(buildTrayMenu());
  tray.on('double-click', showMainWindow);
});

app.on('activate', showMainWindow);
app.on('before-quit', () => { isQuitting = true; });
app.on('window-all-closed', (event) => {
  event.preventDefault();
});

ipcMain.handle('desktop:get-version', () => app.getVersion());
