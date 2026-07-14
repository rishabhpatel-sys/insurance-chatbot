import { useState } from 'react'
import Link from 'next/link'

export default function UploadPage() {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [fileName, setFileName] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [chunks, setChunks] = useState(null)

  const handleFileChange = async (event) => {
    setError('')
    const file = event.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setSelectedFile(file)

    const isPdf = file.type === 'application/pdf' || file.name.match(/\.pdf$/i)
    const allowedText = ['text/plain', 'text/markdown', 'application/json']
    const allowedMarkdown = file.name.match(/\.(txt|md|markdown)$/i)
    if (!isPdf && !allowedMarkdown && !allowedText.includes(file.type)) {
      setError('Please upload a .txt, .md, or .pdf file for best results.')
      setContent('')
      return
    }

    if (isPdf) {
      setContent('')
      if (!title) {
        setTitle(file.name.replace(/\.[^.]+$/, ''))
      }
      return
    }

    try {
      const text = await file.text()
      setContent(text)
      if (!title) {
        setTitle(file.name.replace(/\.[^.]+$/, ''))
      }
    } catch (err) {
      setError('Unable to read the selected file. Please try a plain text or markdown file.')
    }
  }

  const handleUpload = async (event) => {
    event.preventDefault()
    setError('')
    setStatus('')
    setChunks(null)

    if (!title.trim() || !content.trim()) {
      setError('Please provide a title and file content before uploading.')
      return
    }

    setStatus('Uploading document...')
    try {
      let response
      if (selectedFile) {
        const formData = new FormData()
        formData.append('title', title.trim())
        formData.append('source', fileName || title.trim())
        formData.append('file', selectedFile)
        if (!selectedFile.name.match(/\.pdf$/i) && content.trim()) {
          formData.append('content', content)
        }
        response = await fetch('http://localhost:8000/upload-document', {
          method: 'POST',
          body: formData,
        })
      } else {
        response = await fetch('http://localhost:8000/upload-document', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: title.trim(), content, metadata: { source: title.trim() } }),
        })
      }

      const data = await response.json()
      if (!response.ok) {
        setError(data.detail || 'Upload failed. Please check the backend.')
        setStatus('')
        return
      }
      setStatus(`Success! Indexed ${data.chunks_indexed} chunks.`)
      setChunks(data.chunks_indexed)
      setError('')
    } catch (err) {
      setError('Upload error: ' + (err.message || 'unable to connect to backend'))
      setStatus('')
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 900, margin: '0 auto', fontFamily: 'Inter, Arial, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0 }}>Upload Insurance Document</h2>
          <p style={{ color: '#6b7280', margin: '6px 0 0' }}>Add more policy or claim docs so the chatbot can answer more accurately.</p>
        </div>
        <Link href="/" style={{ textDecoration: 'none' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: '#2563eb', color: 'white', borderRadius: 10, padding: '10px 14px', cursor: 'pointer', fontWeight: 600 }}>Back to Chat</span>
        </Link>
      </div>

      <form onSubmit={handleUpload} style={{ background: '#fff', border: '1px solid #e5ebf1', borderRadius: 16, padding: 24, boxShadow: '0 10px 30px rgba(15,23,42,0.06)' }}>
        <label style={{ display: 'block', marginBottom: 12, color: '#334155', fontWeight: 600 }}>Choose a policy or claim document</label>
        <input type="file" accept=".txt,.md,.markdown,.pdf" onChange={handleFileChange} style={{ width: '100%', padding: '12px 10px', borderRadius: 12, border: '1px solid #d1d5db', marginBottom: 18 }} />

        <label style={{ display: 'block', marginBottom: 8, color: '#334155', fontWeight: 600 }}>Document title</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Policy title or file name" style={{ width: '100%', padding: '12px 14px', borderRadius: 12, border: '1px solid #d1d5db', marginBottom: 18 }} />

        <label style={{ display: 'block', marginBottom: 8, color: '#334155', fontWeight: 600 }}>Document content</label>
        <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={10} placeholder="File content will be loaded here. You can also paste text directly." style={{ width: '100%', resize: 'vertical', padding: '14px', borderRadius: 12, border: '1px solid #d1d5db', marginBottom: 18, fontFamily: 'Inter, Arial, sans-serif' }} />

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 16 }}>
          <button type="submit" style={{ background: '#0f172a', color: '#fff', border: 'none', padding: '12px 18px', borderRadius: 12, cursor: 'pointer', fontWeight: 600 }}>Upload Document</button>
          {status ? <span style={{ color: '#0b6f50' }}>{status}</span> : null}
          {error ? <span style={{ color: '#b91c1c' }}>{error}</span> : null}
        </div>

        <div style={{ color: '#64748b', fontSize: 14 }}>
          Supported file types: .txt, .md, .markdown. The text is chunked and indexed so the chatbot can use it as context on later queries.
        </div>
      </form>
    </div>
  )
}
