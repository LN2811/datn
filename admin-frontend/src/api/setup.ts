import { client } from '../generated/client.gen';
import { getApiBaseUrl } from './baseUrl';

client.setConfig({
  baseUrl: getApiBaseUrl(),
  credentials: 'include',
});
