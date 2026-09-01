import React, { useEffect, useState } from 'react'
import { getKernelStatus } from '../api'
import { bus } from '../realtime'

export default function KernelStatus(){
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    async function load(){
      setLoading(true)
      try{
        const res = await getKernelStatus()
        if(mounted) setStatus(res)
      }catch(e){
        if(mounted) setStatus({ error: String(e) })
      }finally{
        if(mounted) setLoading(false)
      }
    }

    load()

    const handler = (ev: Event) => {
      const detail = (ev as CustomEvent).detail
      if (detail && detail.type === 'kernel.status'){
        setStatus(detail.payload)
      }
    }
    bus.addEventListener('realtime:event', handler as EventListener)

    return () => {
      mounted = false
      bus.removeEventListener('realtime:event', handler as EventListener)
    }
  }, [])

  return (
    <div className="card">
      <h2>Kernel Status</h2>
      {loading ? <div>Loading…</div> : (
        <pre>{JSON.stringify(status, null, 2)}</pre>
      )}
    </div>
  )
}
