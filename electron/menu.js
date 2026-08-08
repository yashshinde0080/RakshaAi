const { app, Menu } = require('electron');

function createMenu(mainWindow) {
  const isMac = process.platform === 'darwin';

  const template = [
    // App Menu (macOS only)
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    }] : []),

    // File Menu
    {
      label: 'File',
      submenu: [
        {
          label: 'Open Models Folder',
          click: async () => {
            const { shell } = require('electron');
            const path = require('path');
            const fs = require('fs');
            // Point at the backend's real models dir (portable: on the
            // pendrive next to the app, not %APPDATA%).
            const modelsPath = app.isPackaged
              ? path.join(process.resourcesPath, 'workspace', 'models')
              : path.join(__dirname, '..', 'workspace', 'models');
            fs.mkdirSync(modelsPath, { recursive: true });
            await shell.openPath(modelsPath);
          }
        },
        { type: 'separator' },
        isMac ? { role: 'close' } : { role: 'quit' }
      ]
    },

    // Edit Menu
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' }
      ]
    },

    // View Menu
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },

    // Models Menu
    {
      label: 'Models',
      submenu: [
        {
          label: 'Download Model',
          click: () => {
            mainWindow.webContents.send('navigate', '/models');
          }
        },
        {
          label: 'Triage',
          click: () => {
            mainWindow.webContents.send('navigate', '/triage');
          }
        }
      ]
    },

    // Window Menu
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        ...(isMac ? [
          { type: 'separator' },
          { role: 'front' },
        ] : [
          { role: 'close' }
        ])
      ]
    },

    // Help Menu
    {
      label: 'Help',
      submenu: [
        {
          label: 'About Raksha AI',
          click: () => {
            const { dialog } = require('electron');
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About Raksha AI',
              message: 'Raksha AI',
              detail: `Version: ${app.getVersion()}\n\nYour private, offline AI guardian — local intelligence and vitals triage decision support.\n\nBuilt with Electron, FastAPI, and Next.js`,
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

module.exports = { createMenu };