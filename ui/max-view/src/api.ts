import axios from 'axios'

const BASE = (import.meta.env.VITE_API_BASE || '')

export async function getKernelStatus(){
  const res = await axios.get(`${BASE}/kernel/status`)
  return res.data
}

export async function postMessage(payload:any){
  const res = await axios.post(`${BASE}/message`, payload)
  return res.data
}

export async function getQueuePreview(){
  const res = await axios.get(`${BASE}/queue`)
  return res.data
}

export async function postAuth(token:string){
  const res = await axios.post(`${BASE}/auth`, {}, { headers: { Authorization: `Bearer ${token}` } })
  return res.data
}
