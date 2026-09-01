import React, { useState } from 'react'
import { postMessage } from '../api'

export default function MessageComposer(){
  const [type, setType] = useState('task.execute')
  const [body, setBody] = useState('{\n  "task": "hello"\n}')
  const [result, setResult] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  async function send(){
    setBusy(true)
    setResult(null)
    try{
      const payload = { type, body: JSON.parse(body) }
      const res = await postMessage(payload)
      setResult(res)
    }catch(e){
      setResult({ error: String(e) })
    }finally{
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <h2>Send Message</h2>
      <label>Type</label>
      <input value={type} onChange={e=>setType(e.target.value)} />
      <label>Body (JSON)</label>
      <textarea value={body} onChange={e=>setBody(e.target.value)} rows={8} />
      <button onClick={send} disabled={busy}>Send</button>
      {result && <pre className="result">{JSON.stringify(result, null, 2)}</pre>}
    </div>
  )
}
