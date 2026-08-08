const { Tray, Menu, nativeImage, app } = require('electron');
const path = require('path');

function createTray(mainWindow) {
  const iconPath = path.join(__dirname, 'assets', 'tray-icon.png');
  
  // Create tray icon (16x16 or 22x22 for Linux)
  let trayIcon;
  try {
    trayIcon = nativeImage.createFromPath(iconPath);
    if (process.platform === 'darwin') {
      trayIcon = trayIcon.resize({ width: 16, height: 16 });
    }
  } catch (error) {
    console.error('Failed to load tray icon:', error);
    return null;
  }

  const tray = new Tray(trayIcon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show Raksha AI',
      click: () => {
        mainWindow.show();
      }
    },
    {
      label: 'Hide',
      click: () => {
        mainWindow.hide();
      }
    },
    { type: 'separator' },
    {
      label: 'Console',
      click: () => {
        mainWindow.show();
        mainWindow.webContents.send('navigate', '/console');
      }
    },
    {
      label: 'Triage',
      click: () => {
        mainWindow.show();
        mainWindow.webContents.send('navigate', '/triage');
      }
    },
    {
      label: 'System Info',
      click: () => {
        mainWindow.show();
        mainWindow.webContents.send('navigate', '/system');
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('Raksha AI');
  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
    }
  });

  tray.on('double-click', () => {
    mainWindow.show();
  });

  return tray;
}

module.exports = { createTray };