import { deploymentEnv, routes } from '@vercel/config/v1';

const backendUrl = process.env.BACKEND_URL?.replace(/\/$/, '');

if (!backendUrl) {
  throw new Error('BACKEND_URL is required');
}

export const config = {
  framework: 'vite',

  rewrites: [
    routes.rewrite('/api/(.*)', `${backendUrl}/$1`, {
      requestHeaders: {
        authorization: `Bearer ${deploymentEnv('API_AUTH_TOKEN')}`,
      },
    }),

    routes.rewrite('/(.*)', '/index.html'),
  ],
};