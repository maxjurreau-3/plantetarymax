import React from 'react'
import KernelStatus from './components/KernelStatus'
import MessageComposer from './components/MessageComposer'
import QueueViewer from './components/QueueViewer'
import AuthPanel from './components/AuthPanel'

export default function App(){
  return (
    <div className="app">
      <header>
        <h1>Max‑View — Portal‑OS</h1>
      </header>
      <main>
        <section className="left">
          <KernelStatus />
          <AuthPanel />
        </section>
        <section className="center">
          <MessageComposer />
        </section>
        <section className="right">
          <QueueViewer />
        </section>
      </main>
    </div>
  )
}
