const DEFAULT_API_PORT = '8000';
const DEFAULT_API_PROTOCOL = 'http:';
const DEFAULT_API_HOSTNAME = 'localhost';

const normalizeBaseUrl = (value: string) => value.replace(/\/+$/, '');

export const getApiBaseUrl = () => {
  const configuredBaseUrl = import.meta.env.VITE_API_URL?.trim();
  if (configuredBaseUrl) {
    return normalizeBaseUrl(configuredBaseUrl);
  }

  if (typeof window === 'undefined') {
    return `${DEFAULT_API_PROTOCOL}//${DEFAULT_API_HOSTNAME}:${DEFAULT_API_PORT}`;
  }

  const protocol = window.location.protocol || DEFAULT_API_PROTOCOL;
  const hostname = window.location.hostname || DEFAULT_API_HOSTNAME;
  return `${protocol}//${hostname}:${DEFAULT_API_PORT}`;
};
