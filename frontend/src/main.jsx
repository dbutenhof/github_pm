// ai-generated: Cursor
import React from 'react';
import ReactDOM from 'react-dom/client';
import '@patternfly/react-core/dist/styles/base.css';
import App from './App';
import faviconUrl from './assets/favicon.ico';

// Set favicon dynamically
const link =
  document.querySelector("link[rel~='icon']") || document.createElement('link');
link.rel = 'icon';
link.type = 'image/png';
link.href = faviconUrl;
document.getElementsByTagName('head')[0].appendChild(link);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
