import { useState, useRef } from 'react'

export default function Home() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const controllerRef = useRef(null)

  async function sendMessage(e) {
    e?.preventDefault()
    if (!input.trim()) return
    const userText = input.trim()
    setMessages((m) => [...m, { role: 'user', text: userText }])
    setInput('')

    // Use EventSource (SSE) via GET to avoid preflight issues
    const encoded = encodeURIComponent(userText)
    const url = `http://localhost:8000/sse?message=${encoded}`

    setMessages((m) => [...m, { role: 'bot', text: '' }])
    const updateBotLast = (text) => {
      setMessages((m) => {
        const copy = [...m]
        for (let i = copy.length - 1; i >= 0; i--) {
          if (copy[i].role === 'bot') {
            copy[i] = { role: 'bot', text }
            break
          }
        }
        return copy
      })
    }

    const evtSource = new EventSource(url)
    let botText = ''

    evtSource.onmessage = (e) => {
      const payload = e.data || ''
      botText += payload
      updateBotLast(botText)
    }

    evtSource.addEventListener('sources', (e) => {
      try {
        const sources = JSON.parse(e.data)
        botText += '\n\nSources: ' + sources.map(s => s.title + '#' + s.chunk_index).join(', ')
        updateBotLast(botText)
      } catch (err) {
        // ignore parse error
      }
      evtSource.close()
    })

    evtSource.onerror = (err) => {
      botText += ' Error: network or server error'
      updateBotLast(botText)
      evtSource.close()
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 800, margin: '0 auto', fontFamily: 'Arial' }}>
      <h1>Insurance Chatbot (Next.js Streaming Demo)</h1>
      <div style={{ border: '1px solid #ccc', padding: 12, height: '60vh', overflow: 'auto' }}>
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <b style={{ color: m.role === 'user' ? 'blue' : 'green' }}>{m.role === 'user' ? 'You' : 'Bot'}:</b>
              <span style={{ color: '#555', fontSize: '0.85rem' }}>{m.timestamp}</span>
            </div>
            <div style={{ marginTop: 6, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
              {m.text}
              {m.typing ? <span style={{ display: 'inline-block', width: 10, marginLeft: 6, animation: 'blink 1s step-end infinite' }}>█</span> : null}
            </div>
            {m.sources && m.sources.length ? (
              <div style={{ marginTop: 6, fontSize: '0.9rem' }}>
                Sources: {m.sources.map((s, idx) => (
                  <a key={idx} href={`http://localhost:8000/source?title=${encodeURIComponent(s.title)}&chunk_index=${s.chunk_index}`} target="_blank" rel="noreferrer" style={{ marginRight: 8 }}>{s.title}#{s.chunk_index}</a>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      <form onSubmit={sendMessage} style={{ marginTop: 12 }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about policies, claims..." style={{ width: '70%', padding: 8 }} />
        <button style={{ padding: '8px 12px', marginLeft: 8 }}>Send</button>
      </form>

      <style jsx>{`
        @keyframes blink { 50% { opacity: 0 } }
      `}</style>
    </div>
  )
}
