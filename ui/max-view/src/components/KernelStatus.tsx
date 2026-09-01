import React, { useEffect, useState } from 'react'
import { getKernelStatus } from '../api'

export default function KernelStatus(){
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load(){
      setLoading(true)
      try{
        const res = await getKernelStatus()
        setStatus(res)
      }catch(e){
        setStatus({ error: String(e) })
      }finally{
        setLoading(false)
      }
    }
    load()
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
