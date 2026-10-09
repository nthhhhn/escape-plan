// Assignment: connection details live in source, never in a player form.
// Local mode also supports LAN/Bonjour: API and sockets use the browser address.
// Use the explicit LAN profile only when frontend and backend are on different hosts.
// With the bundled same-origin cloud deployment, set PROFILE to 'cloud'.
export const PROFILE: 'local' | 'lan' | 'cloud' = 'local';
export const HOST = '127.0.0.1';
export const PORT = 8000;
const profile: string = PROFILE;
export const API = profile === 'lan' ? `http://${HOST}:${PORT}` : '';
export const WS_URL = profile === 'lan' ? `ws://${HOST}:${PORT}/ws` : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
