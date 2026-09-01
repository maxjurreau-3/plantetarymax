import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import { connectSSE } from './realtime'

// start SSE on app boot; stop on unload
const stopSSE = connectSSE()

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

window.addEventListener('beforeunload', () => {
  stopSSE()
})
