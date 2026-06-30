const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('projectFlowDesktop', {
  platform: process.platform,
  getVersion: () => ipcRenderer.invoke('desktop:get-version'),
  onOpenPanel: (handler) => {
    const listener = (_event, panel) => handler(panel);
    ipcRenderer.on('desktop:open-panel', listener);
    return () => ipcRenderer.removeListener('desktop:open-panel', listener);
  },
  onMicrophone: (handler) => {
    const listener = (_event, device) => handler(device);
    ipcRenderer.on('desktop:microphone', listener);
    return () => ipcRenderer.removeListener('desktop:microphone', listener);
  }
});
