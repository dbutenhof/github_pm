// Generated-by: Cursor
import React from 'react';
import ReactDOM from 'react-dom/client';
import '@patternfly/react-core/dist/styles/base.css';
/* Bundled after PatternFly so GitHub Markdown styles win over PF resets. */
import 'github-markdown-css/github-markdown-light.css';
import './markdown-body.css';
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
