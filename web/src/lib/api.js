export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001'

export async function apiFetch(path, options = {}, authParam = false) {
  const { method = 'GET', headers = {}, body, timeout = 10000, auth: authOpt = false } = options
  const auth = authParam || authOpt
  
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)

  const opts = { 
    method, 
    headers: { 'Content-Type': 'application/json', ...headers },
    signal: controller.signal
  }

  if (body !== undefined) opts.body = typeof body === 'string' ? body : JSON.stringify(body)
  
  if (auth) {
    const token = localStorage.getItem('token')
    if (token && token !== 'null' && token !== 'undefined') {
      opts.headers['Authorization'] = `Bearer ${token}`
    } else {
      console.warn('[API] Auth requested but no valid token found in localStorage')
    }
  }

  console.log(`[API] Fetching ${API_BASE}${path}`, { method, body })

  try {
    const res = await fetch(`${API_BASE}${path}`, opts)
    clearTimeout(id)
    
    console.log(`[API] Response from ${path}:`, res.status)

    if (!res.ok) {
      let msg = ''
      try { 
        const json = JSON.parse(await res.clone().text())
        msg = json.detail || json.message || ''
      } catch { 
        msg = await res.text() 
      }
      console.error(`[API] Error from ${path}:`, res.status, msg)
      
      // If unauthorized, check if we need to clear session
      if (res.status === 401) {
        if (msg.includes('session expired') || msg.includes('Invalid token') || msg.includes('User not found')) {
          console.warn('[API] Session invalid. Clearing local token.')
          localStorage.removeItem('token')
        }
      }

      const error = new Error(msg || `Request failed: ${res.status}`)
      error.status = res.status
      throw error
    }

    const text = await res.text()
    try { 
      const data = JSON.parse(text)
      return data
    } catch { 
      return text 
    }
  } catch (err) {
    clearTimeout(id)
    if (err.name === 'AbortError') {
      console.error(`[API] Timeout fetching ${path}`)
      throw new Error('Connection timed out. Please check if the server is running.')
    }
    console.error(`[API] Fetch error for ${path}:`, err)
    throw err
  }
}
