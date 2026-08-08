const { app, BrowserWindow, ipcMain, dialog, protocol, net, Notification } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const { createMenu } = require('./menu');
const { createTray } = require('./tray');

let mainWindow;
let backendProcess;
let tray;

const isDev = !app.isPackaged;
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 3000;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    titleBarStyle: 'hiddenInset',
    show: false,
  });

  // Load URL based on environment
  const useDevServer = process.env.USE_DEV_SERVER === 'true';
  if (isDev && useDevServer) {
    mainWindow.loadURL(`http://localhost:${FRONTEND_PORT}`);
    mainWindow.webContents.openDevTools();
  } else {
    // Load from built frontend via custom protocol
    mainWindow.loadURL('app://-/');
    if (isDev) {
      mainWindow.webContents.openDevTools();
    }
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('close', (event) => {
    if (app.isQuitting) {
      mainWindow = null;
    } else {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

async function startBackend() {
  return new Promise((resolve, reject) => {
    const backendPath = isDev
      ? path.join(__dirname, '..', 'backend')
      : path.join(process.resourcesPath, 'backend');

    // Determine python path. Use virtual env if it exists, otherwise use system python.
    const platform = process.platform;
    const venvPythonPath = platform === 'win32'
      ? path.join(backendPath, '.venv', 'Scripts', 'python.exe')
      : path.join(backendPath, '.venv', 'bin', 'python');
      
    const fs = require('fs');
    const pythonPath = fs.existsSync(venvPythonPath) ? venvPythonPath : (platform === 'win32' ? 'python' : 'python3');

    console.log('Starting backend from:', backendPath);

    backendProcess = spawn(pythonPath, [
      '-m', 'uvicorn',
      'app.main:app',
      '--host', '127.0.0.1',
      '--port', String(BACKEND_PORT),
    ], {
      cwd: backendPath,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    });

    backendProcess.stdout.on('data', (data) => {
      console.log(`Backend: ${data}`);
      if (data.toString().includes('Uvicorn running')) {
        resolve();
      }
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`Backend Error: ${data}`);
    });

    backendProcess.on('error', (error) => {
      console.error('Failed to start backend (it might already be running):', error);
      resolve(); // Do not reject, so the app still opens
    });

    backendProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`);
    });

    // Timeout for backend startup
    setTimeout(() => {
      resolve(); // Resolve anyway after timeout
    }, 10000);
  });
}

function stopBackend() {
  if (backendProcess) {
    console.log('Stopping backend...');
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
    } else {
      backendProcess.kill('SIGTERM');
    }
    backendProcess = null;
  }
}

// IPC Handlers
ipcMain.handle('get-app-path', () => {
  return app.getAppPath();
});

ipcMain.handle('show-notification', (event, { title, body }) => {
  if (Notification.isSupported()) {
    // ponytail: native Electron notification, no library needed
    const n = new Notification({ title, body });
    n.onclick = () => {
      if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
      }
    };
  }
  return { success: true };
});

ipcMain.handle('get-version', () => {
  return app.getVersion();
});

ipcMain.handle('show-open-dialog', async (event, options) => {
  return dialog.showOpenDialog(mainWindow, options);
});

ipcMain.handle('show-save-dialog', async (event, options) => {
  return dialog.showSaveDialog(mainWindow, options);
});

ipcMain.handle('restart-backend', async () => {
  stopBackend();
  await startBackend();
  return { success: true };
});

protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, bypassCSP: true } }
]);

// App lifecycle
app.whenReady().then(async () => {
  try {
    console.log('Starting Raksha AI...');
    
    // Register custom protocol for Next.js static export
    protocol.handle('app', (request) => {
      const urlPath = new URL(request.url).pathname;
      const decodedPath = decodeURI(urlPath);
      const basePath = isDev 
        ? path.join(__dirname, '..', 'frontend', 'out') 
        : path.join(process.resourcesPath, 'frontend');
      
      let filePath = path.join(basePath, decodedPath);
      const fs = require('fs');
      
      try {
        if (decodedPath === '/' || decodedPath === '') {
          filePath = path.join(basePath, 'index.html');
        } else if (fs.existsSync(filePath)) {
          if (fs.statSync(filePath).isDirectory()) {
            const indexPath = path.join(filePath, 'index.html');
            if (fs.existsSync(indexPath)) {
              filePath = indexPath;
            }
          }
        } else {
          if (fs.existsSync(path.join(filePath, 'index.html'))) {
            filePath = path.join(filePath, 'index.html');
          } else if (fs.existsSync(filePath + '.html')) {
            filePath = filePath + '.html';
          } else {
            filePath = path.join(basePath, 'index.html');
          }
        }
      } catch (err) {
        filePath = path.join(basePath, 'index.html');
      }
      const { pathToFileURL } = require('url');
      return net.fetch(pathToFileURL(filePath).href);
    });

    // Start backend first
    await startBackend();
    console.log('Backend started');

    // Create window
    createWindow();

    // Create menu
    createMenu(mainWindow);

    // Create tray
    tray = createTray(mainWindow);

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      } else {
        mainWindow.show();
      }
    });
  } catch (error) {
    console.error('Failed to start application:', error);
    dialog.showErrorBox('Startup Error', `Failed to start: ${error.message}`);
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  stopBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopBackend();
    app.quit();
  }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  dialog.showErrorBox('Error', error.message);
});