import axios from 'axios';

import { getApiBaseUrl } from './baseUrl';

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  withCredentials: true,
});
