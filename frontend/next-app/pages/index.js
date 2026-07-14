import Link from 'next/link'
import { useState, useRef, useEffect } from 'react'

export default function Home() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const evtRef = useRef(null)

  useEffect(() => {
    return () => {
      if (evtRef.current) evtRef.current.close()
    }
  }, [])

  async function sendMessage(e) {
    e?.preventDefault()
    if (!input.trim()) return
    const userText = input.trim()
    setMessages((m) => [...m, { role: 'user', text: userText, timestamp: new Date().toLocaleTimeString() }])
    setInput('')

    const encoded = encodeURIComponent(userText)
    const url = `http://localhost:8000/sse?message=${encoded}`

    setMessages((m) => [...m, { role: 'bot', text: '', timestamp: new Date().toLocaleTimeString(), typing: true }])

    const updateBotLast = (text, extras) => {
      setMessages((m) => {
        const copy = [...m]
        for (let i = copy.length - 1; i >= 0; i--) {
          if (copy[i].role === 'bot') {
            copy[i] = { ...copy[i], text, typing: false, ...(extras || {}) }
            break
          }
        }
        return copy
      })
    }

    if (evtRef.current) {
      evtRef.current.close()
      evtRef.current = null
    }

    const evtSource = new EventSource(url)
    evtRef.current = evtSource
    let botText = ''

    const computeNewSuffix = (sent, incoming) => {
      if (incoming === sent || incoming.trim() === sent.trim()) return ''
      if (incoming.startsWith(sent)) return incoming.slice(sent.length)
      if (sent.endsWith(incoming)) return ''
      let maxOverlap = 0
      const maxLen = Math.min(sent.length, incoming.length)
      for (let i = maxLen; i > 0; i--) {
        if (sent.endsWith(incoming.slice(0, i))) {
          maxOverlap = i
          break
        }
      }
      return maxOverlap > 0 ? incoming.slice(maxOverlap) : incoming
    }

    evtSource.onmessage = (e) => {
      const payload = e.data || ''
      const newSuffix = computeNewSuffix(botText, payload)
      if (!newSuffix) return
      botText += newSuffix
      updateBotLast(botText)
    }

    evtSource.addEventListener('sources', (e) => {
      try {
        const sources = JSON.parse(e.data)
        updateBotLast(botText, { sources })
      } catch (err) {
        // ignore parse error
      }
      evtSource.close()
      evtRef.current = null
    })

    evtSource.onerror = (err) => {
      updateBotLast('Error: network or server error')
      evtSource.close()
      evtRef.current = null
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 900, margin: '0 auto', fontFamily: 'Inter, Arial, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'linear-gradient(135deg,#4f46e5,#06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700 }}>IC</div>
          <div>
            <h2 style={{ margin: 0 }}>Insurance Chatbot</h2>
            <div style={{ color: '#6b7280', fontSize: 13 }}>Streaming demo — powered by Qdrant + OpenAI</div>
          </div>
        </div>
        <Link href="/upload" style={{ textDecoration: 'none' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: '#2563eb', color: 'white', borderRadius: 10, padding: '10px 14px', cursor: 'pointer', fontWeight: 600 }}>Upload Documents</span>
        </Link>
      </div>

      <div style={{ borderRadius: 12, border: '1px solid #e6eef8', overflow: 'hidden', boxShadow: '0 6px 18px rgba(15,23,42,0.06)' }}>
        <div style={{ padding: 16, height: '64vh', overflow: 'auto', background: 'linear-gradient(180deg,#fbfcff,#ffffff)' }}>
          {messages.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#9ca3af', marginTop: 60 }}>Start the chat — ask about policies, claims, or offers</div>
          ) : (
            messages.map((m, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: m.role === 'user' ? 'row-reverse' : 'row', gap: 12, marginBottom: 12, alignItems: 'flex-end' }}>
                <div style={{ width: 40, height: 40, borderRadius: 8, background: m.role === 'user' ? '#e0f2fe' : '#eef2ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: m.role === 'user' ? '#035388' : '#0b3677', fontWeight: 700 }}>{m.role === 'user' ? 'Y' : 'B'}</div>
                <div style={{ maxWidth: '78%' }}>
                  <div style={{ background: m.role === 'user' ? '#e6f0ff' : '#f8fafc', padding: '12px 14px', borderRadius: 12, border: '1px solid #eef6ff', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                    {m.text || (m.typing ? '...' : '')}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                    <span style={{ color: '#9ca3af', fontSize: 12 }}>{m.timestamp}</span>
                    {m.sources && m.sources.length ? (
                      <div style={{ display: 'flex', gap: 6 }}>
                        {m.sources.map((s, idx) => (
                          <a key={idx} href={`http://localhost:8000/source?title=${encodeURIComponent(s.title)}&chunk_index=${s.chunk_index}`} target="_blank" rel="noreferrer" style={{ padding: '6px 8px', background: '#eef2ff', borderRadius: 999, fontSize: 12, color: '#0b3d91', textDecoration: 'none' }}>{s.title}#{s.chunk_index}</a>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <form onSubmit={sendMessage} style={{ display: 'flex', gap: 12, padding: 12, borderTop: '1px solid #eef2ff', alignItems: 'center', background: '#ffffff' }}>
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about policies, claims, or offers..." style={{ flex: 1, padding: '10px 12px', borderRadius: 10, border: '1px solid #e6eef8', outline: 'none' }} />
          <button type="submit" style={{ background: '#2563eb', color: 'white', border: 'none', padding: '10px 14px', borderRadius: 10, cursor: 'pointer', fontWeight: 600 }}>Send</button>
        </form>
      </div>
    </div>
  )
}
