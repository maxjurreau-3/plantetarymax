import React, { useState } from 'react'
import { postAuth } from '../api'

export default function AuthPanel(){
  const [token, setToken] = useState('dev-token')
  const [principal, setPrincipal] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  async function check(){
    setBusy(true); setPrincipal(null)
    try{
      const res = await postAuth(token)
      setPrincipal(res)
    }catch(e){
      setPrincipal({ error: String(e) })
    }finally{ setBusy(false) }
  }

  return (
    <div className="card">
      <h2>Identity</h2>
      <input value={token} onChange={e=>setToken(e.target.value)} />
      <button onClick={check} disabled={busy}>Check</button>
      {principal && <pre>{JSON.stringify(principal, null, 2)}</pre>}
    </div>
  )
}
