// Server addresses and ports are source-defined; players never enter them.
// Build with VITE_SERVER_PROFILE=local|lan|cloud. Vite dev uses local;
// ordinary production builds use LAN, and Docker selects cloud.
export const CLOUD_IP = '34.21.135.108';
export const SERVERS = {
  local: { host: '127.0.0.1', port: 8000, secure: false },
  lan: { host: 'escape-plan15.local', port: 8000, secure: false },
  cloud: { host: `${CLOUD_IP}.nip.io`, port: 443, secure: true },
} as const;
const selected = import.meta.env.VITE_SERVER_PROFILE || (import.meta.env.DEV ? 'local' : 'lan');
if (!(selected in SERVERS)) throw new Error('Unknown VITE_SERVER_PROFILE');
export const PROFILE = selected as keyof typeof SERVERS;
const server = SERVERS[PROFILE];
export const HOST = server.host;
export const PORT = server.port;
export const API = `${server.secure ? 'https' : 'http'}://${HOST}:${PORT}`;
export const WS_URL = `${server.secure ? 'wss' : 'ws'}://${HOST}:${PORT}/ws`;
