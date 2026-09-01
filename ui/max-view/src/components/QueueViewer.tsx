import React, { useEffect, useState } from 'react'
import { getQueuePreview } from '../api'
import { bus } from '../realtime'

export default function QueueViewer(){
  const [preview, setPreview] = useState<any[]>([])
  const [size, setSize] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(()=>{
    let mounted = true
    async function load(){
      setLoading(true)
      try{
        const res = await getQueuePreview()
        if(!mounted) return
        setPreview(res.preview || [])
        setSize(res.queue_size || res.queueSize || 0)
      }catch(e){
        if(mounted) setPreview([])
      }finally{
        if(mounted) setLoading(false)
      }
    }
    load()
    const id = setInterval(load, 5000)

    const handler = (ev: Event) => {
      const detail = (ev as CustomEvent).detail
      if(!detail || !detail.type) return

      if(detail.type === 'message.enqueued'){
        setSize(s => s + 1)
        setPreview(p => [{ id: detail.payload.id, type: detail.payload.type }, ...p].slice(0, 20))
      }else if(detail.type === 'message.processed'){
        setSize(s => Math.max(0, s - 1))
        setPreview(p => p.filter(x => x.id !== detail.payload.id))
      }
    }
    bus.addEventListener('realtime:event', handler as EventListener)

    return ()=>{
      mounted = false
      clearInterval(id)
      bus.removeEventListener('realtime:event', handler as EventListener)
    }
  }, [])

  return (
    <div className="card">
      <h2>Queue</h2>
      {loading ? <div>Loading…</div> : (
        <div>
          <div>Size: {size}</div>
          <ul>
            {preview.map((p, i)=> <li key={p.id||i}>{p.id} — {p.type}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
