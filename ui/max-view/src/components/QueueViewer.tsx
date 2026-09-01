import React, { useEffect, useState } from 'react'
import { getQueuePreview } from '../api'

export default function QueueViewer(){
  const [preview, setPreview] = useState<any[]>([])
  const [size, setSize] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(()=>{
    async function load(){
      setLoading(true)
      try{
        const res = await getQueuePreview()
        setPreview(res.preview || [])
        setSize(res.queue_size || res.queueSize || 0)
      }catch(e){
        setPreview([])
      }finally{
        setLoading(false)
      }
    }
    load()
    const id = setInterval(load, 5000)
    return ()=>clearInterval(id)
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
