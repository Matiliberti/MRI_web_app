'use client'

import { useState, useRef, useEffect, DragEvent, ChangeEvent } from 'react'
import { supabase } from '@/lib/supabaseClient'

type UIState = 'idle' | 'dragging' | 'uploading' | 'success' | 'error'

interface MediaItem {
  id: string
  file_url: string
  created_at: string
}

function isVideoUrl(url: string) {
  return /\.(mp4|webm|mov|avi|mkv|ogg)(\?|$)/i.test(url)
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'now'
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h`
  return `${Math.floor(h / 24)}d`
}

function PiIcon({ size = 16, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 18" fill="none">
      {/* Board body */}
      <rect x="1" y="3" width="18" height="13" rx="2" stroke={color} strokeWidth="1.4" />
      {/* GPIO pins */}
      {[5, 8, 11, 14].map(x => (
        <line key={x} x1={x} y1="3" x2={x} y2="1" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
      ))}
      {/* CPU chip */}
      <rect x="8" y="7" width="5" height="5" rx="0.6" stroke={color} strokeWidth="1.2" />
      {/* USB ports left */}
      <rect x="1" y="6.5" width="2.5" height="1.8" rx="0.3" stroke={color} strokeWidth="1" />
      <rect x="1" y="10" width="2.5" height="1.8" rx="0.3" stroke={color} strokeWidth="1" />
      {/* SD card right */}
      <rect x="17" y="8.5" width="2.5" height="2.5" rx="0.3" stroke={color} strokeWidth="1" />
    </svg>
  )
}

// Corner bracket decoration for the upload zone
function Corner({ pos }: { pos: 'tl' | 'tr' | 'bl' | 'br' }) {
  const top = pos.startsWith('t')
  const left = pos.endsWith('l')
  return (
    <div
      style={{
        position: 'absolute',
        top: top ? 12 : undefined,
        bottom: top ? undefined : 12,
        left: left ? 12 : undefined,
        right: left ? undefined : 12,
        width: 18,
        height: 18,
        borderTop: top ? '2px solid var(--accent)' : 'none',
        borderBottom: top ? 'none' : '2px solid var(--accent)',
        borderLeft: left ? '2px solid var(--accent)' : 'none',
        borderRight: left ? 'none' : '2px solid var(--accent)',
        transition: 'opacity 0.25s ease',
      }}
    />
  )
}

export default function Home() {
  const [uiState, setUiState] = useState<UIState>('idle')
  const [progress, setProgress] = useState(0)
  const [errorMsg, setErrorMsg] = useState('')
  const [feed, setFeed] = useState<MediaItem[]>([])
  const [activatingId, setActivatingId] = useState<string | null>(null)
  const [piStatus, setPiStatus] = useState<'online' | 'offline' | 'unknown'>('unknown')
  const inputRef = useRef<HTMLInputElement>(null)
  const dragCount = useRef(0)
  const progressTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    loadFeed()
    checkPiStatus()
    const interval = setInterval(checkPiStatus, 15000)
    return () => clearInterval(interval)
  }, [])

  async function checkPiStatus() {
    const { data } = await supabase
      .from('pi_status')
      .select('last_seen')
      .eq('id', 1)
      .single()
    if (!data) { setPiStatus('unknown'); return }
    const age = (Date.now() - new Date(data.last_seen).getTime()) / 1000
    setPiStatus(age < 30 ? 'online' : 'offline')
  }

  async function loadFeed() {
    const { data } = await supabase
      .from('display_media')
      .select('id, file_url, created_at')
      .order('created_at', { ascending: false })
      .limit(50)
    if (data) {
      const seen = new Set<string>()
      const unique = data.filter(item => {
        if (seen.has(item.file_url)) return false
        seen.add(item.file_url)
        return true
      })
      setFeed(unique.slice(0, 9))
    }
  }

  async function setAsActive(item: MediaItem) {
    if (activatingId) return
    setActivatingId(item.id)
    const { error } = await supabase
      .from('display_media')
      .insert({ file_url: item.file_url })
    if (!error) await loadFeed()
    setActivatingId(null)
  }

  async function uploadFile(file: File) {
    setUiState('uploading')
    setProgress(0)

    const ext = file.name.split('.').pop() ?? 'bin'
    const uid = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
    const storagePath = `${uid}.${ext}`

    progressTimer.current = setInterval(() => {
      setProgress(p => (p >= 80 ? p : p + Math.random() * 14 + 3))
    }, 280)

    try {
      const { error: storageErr } = await supabase.storage
        .from('media')
        .upload(storagePath, file)

      if (progressTimer.current) clearInterval(progressTimer.current)
      if (storageErr) {
        console.error('[storage upload]', storageErr)
        throw new Error(`Storage: ${storageErr.message}`)
      }

      const { data: { publicUrl } } = supabase.storage
        .from('media')
        .getPublicUrl(storagePath)

      const { error: dbErr } = await supabase
        .from('display_media')
        .insert({ file_url: publicUrl })

      if (dbErr) {
        console.error('[db insert]', dbErr)
        throw new Error(`Database: ${dbErr.message}`)
      }

      setProgress(100)
      setUiState('success')
      loadFeed()
      setTimeout(() => { setUiState('idle'); setProgress(0) }, 2600)
    } catch (err) {
      if (progressTimer.current) clearInterval(progressTimer.current)
      setErrorMsg(err instanceof Error ? err.message : 'Upload failed')
      setUiState('error')
      setTimeout(() => { setUiState('idle'); setProgress(0) }, 3000)
    }
  }

  function onDragEnter(e: DragEvent) {
    e.preventDefault()
    dragCount.current++
    if (uiState === 'idle') setUiState('dragging')
  }
  function onDragLeave(e: DragEvent) {
    e.preventDefault()
    dragCount.current = Math.max(0, dragCount.current - 1)
    if (dragCount.current === 0 && uiState === 'dragging') setUiState('idle')
  }
  function onDragOver(e: DragEvent) { e.preventDefault() }
  function onDrop(e: DragEvent) {
    e.preventDefault()
    dragCount.current = 0
    if (uiState !== 'idle' && uiState !== 'dragging') return
    const file = e.dataTransfer.files?.[0]
    if (file) uploadFile(file)
  }
  function onInputChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) uploadFile(file)
    if (inputRef.current) inputRef.current.value = ''
  }

  const canInteract = uiState === 'idle' || uiState === 'dragging'

  const zoneBorder =
    uiState === 'success' ? 'var(--success)' :
    uiState === 'error' ? 'var(--error)' :
    uiState === 'dragging' ? 'var(--accent)' : 'var(--border-hi)'

  const zoneBg =
    uiState === 'dragging' ? 'rgba(0,87,241,0.06)' :
    uiState === 'success' ? 'rgba(34,197,94,0.04)' :
    uiState === 'error' ? 'rgba(239,68,68,0.04)' : 'var(--surface)'

  const zoneShadow =
    uiState === 'dragging' ? '0 0 70px rgba(0,87,241,0.2),inset 0 0 60px rgba(0,87,241,0.06)' :
    uiState === 'success' ? '0 0 50px rgba(34,197,94,0.12)' :
    uiState === 'error' ? '0 0 50px rgba(239,68,68,0.12)' : 'none'

  const circumference = 2 * Math.PI * 34

  return (
    <main
      style={{
        minHeight: '100svh',
        background: 'var(--bg)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '28px 16px 40px',
      }}
    >
      {/* ── Header ── */}
      <header style={{ width: '100%', maxWidth: 420, marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/logo.png"
              alt="Sedecal"
              style={{ height: 44, width: 'auto', display: 'block' }}
            />
          </div>

          {/* Right-side indicators */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10, paddingTop: 2 }}>
            {/* Upload status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div
                style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: uiState === 'error' ? 'var(--error)' : uiState === 'uploading' ? 'var(--accent)' : 'var(--success)',
                  boxShadow: uiState === 'error' ? '0 0 10px var(--error)' : uiState === 'uploading' ? '0 0 12px var(--accent)' : '0 0 9px var(--success)',
                  animation: uiState === 'uploading' ? 'blink 0.55s step-end infinite' : 'none',
                  transition: 'background 0.3s, box-shadow 0.3s',
                }}
              />
              <span className="font-display" style={{ fontSize: 11, letterSpacing: '0.04em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                {uiState === 'uploading' ? 'TX' : uiState === 'error' ? 'ERR' : 'RDY'}
              </span>
            </div>

            {/* Pi status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <PiIcon
                size={20}
                color={
                  piStatus === 'online' ? 'var(--success)' :
                  piStatus === 'offline' ? 'var(--error)' : 'var(--text-muted)'
                }
              />
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                background: piStatus === 'online' ? 'var(--success)' : piStatus === 'offline' ? 'var(--error)' : 'var(--text-muted)',
                boxShadow: piStatus === 'online' ? '0 0 9px var(--success)' : 'none',
                animation: piStatus === 'online' ? 'blink 2.5s ease-in-out infinite' : 'none',
                transition: 'background 0.3s',
              }} />
              <span className="font-display" style={{ fontSize: 11, letterSpacing: '0.04em', color: piStatus === 'online' ? 'var(--success)' : piStatus === 'offline' ? 'var(--error)' : 'var(--text-muted)', textTransform: 'uppercase' }}>
                {piStatus === 'online' ? 'LIVE' : piStatus === 'offline' ? 'OFF' : '---'}
              </span>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 14, height: 1, background: 'var(--border)' }} />
      </header>

      {/* ── Upload Zone ── */}
      <div style={{ width: '100%', maxWidth: 420 }}>
        <input
          ref={inputRef}
          type="file"
          accept="image/*,video/*"
          onChange={onInputChange}
          style={{ display: 'none' }}
          aria-hidden="true"
        />

        <div
          role="button"
          tabIndex={0}
          aria-label="Upload file"
          onClick={() => canInteract && inputRef.current?.click()}
          onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && canInteract && inputRef.current?.click()}
          onDragEnter={onDragEnter}
          onDragLeave={onDragLeave}
          onDragOver={onDragOver}
          onDrop={onDrop}
          style={{
            position: 'relative',
            width: '100%',
            aspectRatio: '1',
            background: zoneBg,
            border: `2px solid ${zoneBorder}`,
            borderRadius: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: canInteract ? 'pointer' : 'default',
            transition: 'background 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease',
            boxShadow: zoneShadow,
            userSelect: 'none',
            WebkitUserSelect: 'none',
            outline: 'none',
          }}
        >
          {/* Corner brackets */}
          <Corner pos="tl" />
          <Corner pos="tr" />
          <Corner pos="bl" />
          <Corner pos="br" />

          {/* ── Idle ── */}
          {uiState === 'idle' && (
            <div className="animate-fade-in" style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18 }}>
              <svg width="54" height="54" viewBox="0 0 54 54" fill="none" opacity={0.55}>
                <path d="M27 9V39" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
                <path d="M15 21L27 9L39 21" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M10 43H44" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeOpacity="0.45" />
                <path d="M17 47H37" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeOpacity="0.2" />
              </svg>
              <div>
                <p className="font-display" style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--accent)', textTransform: 'uppercase' }}>
                  Transmit
                </p>
                <p className="font-display" style={{ fontSize: 10, letterSpacing: '0.04em', color: 'var(--text-muted)', marginTop: 7, textTransform: 'uppercase' }}>
                  tap · drag · drop
                </p>
                <p className="font-display" style={{ fontSize: 9, letterSpacing: '0.12em', color: 'var(--text-muted)', marginTop: 4, opacity: 0.6 }}>
                  image or video
                </p>
              </div>
            </div>
          )}

          {/* ── Dragging ── */}
          {uiState === 'dragging' && (
            <div className="animate-fade-in" style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18 }}>
              <div
                style={{
                  width: 70,
                  height: 70,
                  borderRadius: '50%',
                  border: '2px solid var(--accent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  animation: 'pulse-ring 1.1s ease-in-out infinite',
                }}
              >
                <svg width="30" height="30" viewBox="0 0 30 30" fill="none">
                  <path d="M15 5V22" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
                  <path d="M8 12L15 5L22 12" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <p className="font-display" style={{ fontSize: 11, letterSpacing: '0.07em', color: 'var(--accent)', textTransform: 'uppercase' }}>
                Release to transmit
              </p>
            </div>
          )}

          {/* ── Uploading ── */}
          {uiState === 'uploading' && (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 26, width: '100%', padding: '0 64px' }}>
              {/* SVG circular progress */}
              <div style={{ position: 'relative' }}>
                <svg width="84" height="84" viewBox="0 0 84 84">
                  <circle cx="42" cy="42" r="34" fill="none" stroke="var(--border)" strokeWidth="3" />
                  <circle
                    cx="42"
                    cy="42"
                    r="34"
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={circumference * (1 - progress / 100)}
                    transform="rotate(-90 42 42)"
                    style={{ transition: 'stroke-dashoffset 0.35s ease' }}
                  />
                </svg>
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <span className="font-display" style={{ fontSize: 14, fontWeight: 600, color: 'var(--accent)' }}>
                    {Math.round(progress)}%
                  </span>
                </div>
              </div>

              {/* Linear bar */}
              <div style={{ width: '100%' }}>
                <div style={{ height: 2, background: 'var(--border)', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${progress}%`,
                      background: 'var(--accent)',
                      transition: 'width 0.35s ease',
                    }}
                  />
                </div>
                <p className="font-display" style={{ fontSize: 9, letterSpacing: '0.07em', color: 'var(--text-muted)', marginTop: 12, textAlign: 'center', textTransform: 'uppercase' }}>
                  Transmitting…
                </p>
              </div>
            </div>
          )}

          {/* ── Success ── */}
          {uiState === 'success' && (
            <div className="animate-fade-in" style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
              <svg width="58" height="58" viewBox="0 0 58 58" fill="none">
                <circle cx="29" cy="29" r="25" stroke="var(--success)" strokeWidth="2" />
                <path d="M18 29L25 36L40 21" stroke="var(--success)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="font-display" style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--success)', textTransform: 'uppercase' }}>
                Transmitted
              </p>
            </div>
          )}

          {/* ── Error ── */}
          {uiState === 'error' && (
            <div className="animate-fade-in" style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, padding: '0 36px' }}>
              <svg width="58" height="58" viewBox="0 0 58 58" fill="none">
                <circle cx="29" cy="29" r="25" stroke="var(--error)" strokeWidth="2" />
                <path d="M29 19V31" stroke="var(--error)" strokeWidth="2" strokeLinecap="round" />
                <circle cx="29" cy="38" r="2.5" fill="var(--error)" />
              </svg>
              <div>
                <p className="font-display" style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.07em', color: 'var(--error)', textTransform: 'uppercase' }}>
                  Signal Lost
                </p>
                <p className="font-display" style={{ fontSize: 10, color: '#a09080', marginTop: 7, letterSpacing: '0.05em', lineHeight: 1.6, wordBreak: 'break-word' }}>
                  {errorMsg || 'Upload failed — tap to retry'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Recent Feed ── */}
      {feed.length > 0 && (
        <section className="animate-slide-up" style={{ width: '100%', maxWidth: 420, marginTop: 30 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <h2
              className="font-display"
              style={{ fontSize: 9, letterSpacing: '0.05em', color: 'var(--text-muted)', textTransform: 'uppercase', whiteSpace: 'nowrap' }}
            >
              Recent Transmissions
            </h2>
            <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
            <span className="font-display" style={{ fontSize: 9, color: 'var(--text-muted)' }}>{feed.length}</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 7 }}>
            {feed.map((item, i) => {
              const isLive = i === 0
              const isActivating = activatingId === item.id
              return (
              <div
                key={item.id}
                role="button"
                tabIndex={0}
                onClick={() => !isLive && !activatingId && setAsActive(item)}
                onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && !isLive && !activatingId && setAsActive(item)}
                style={{
                  position: 'relative',
                  aspectRatio: '1',
                  background: 'var(--surface-2)',
                  border: `1px solid ${isLive ? 'var(--success)' : 'var(--border)'}`,
                  borderRadius: 3,
                  overflow: 'hidden',
                  cursor: isLive ? 'default' : 'pointer',
                  outline: 'none',
                  boxShadow: isLive ? '0 0 10px rgba(34,197,94,0.15)' : 'none',
                  transition: 'border-color 0.2s, box-shadow 0.2s',
                }}
              >
                {isVideoUrl(item.file_url) ? (
                  <video
                    src={`${item.file_url}#t=0.001`}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    muted
                    playsInline
                    preload="metadata"
                  />
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.file_url}
                    alt=""
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    loading="lazy"
                  />
                )}

                {/* Tap-to-activate overlay for non-live items */}
                {!isLive && !isActivating && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'rgba(0,0,0,0)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    transition: 'background 0.15s',
                  }}
                  className="thumb-overlay"
                  >
                    <span className="font-display thumb-label" style={{
                      fontSize: 8, letterSpacing: '0.15em', color: '#fff',
                      textTransform: 'uppercase', opacity: 0,
                      transition: 'opacity 0.15s',
                      background: 'rgba(0,0,0,0.55)',
                      padding: '3px 6px',
                      borderRadius: 2,
                    }}>
                      Set live
                    </span>
                  </div>
                )}

                {/* Activating spinner */}
                {isActivating && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <div style={{
                      width: 18, height: 18, borderRadius: '50%',
                      border: '2px solid rgba(0,87,241,0.3)',
                      borderTopColor: 'var(--accent)',
                      animation: 'spin 0.7s linear infinite',
                    }} />
                  </div>
                )}

                {/* Live badge */}
                {isLive && (
                  <div style={{
                    position: 'absolute', top: 5, right: 5,
                    display: 'flex', alignItems: 'center', gap: 3,
                    background: 'rgba(0,0,0,0.55)',
                    padding: '2px 5px', borderRadius: 2,
                  }}>
                    <div style={{
                      width: 5, height: 5, borderRadius: '50%',
                      background: 'var(--success)',
                      boxShadow: '0 0 5px var(--success)',
                    }} />
                    <span className="font-display" style={{ fontSize: 7, letterSpacing: '0.15em', color: 'var(--success)' }}>LIVE</span>
                  </div>
                )}

                {/* Time stamp */}
                <div
                  style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    background: 'linear-gradient(transparent, rgba(7,6,5,0.82))',
                    padding: '14px 5px 4px',
                  }}
                >
                  <span className="font-display" style={{ fontSize: 8, letterSpacing: '0.08em', color: 'rgba(255,255,255,0.35)' }}>
                    {timeAgo(item.created_at)}
                  </span>
                </div>
              </div>
            )})}
          </div>
        </section>
      )}

      {/* ── Footer ── */}
      <footer style={{ marginTop: 'auto', paddingTop: 36 }}>
        <p className="font-display" style={{ fontSize: 8, letterSpacing: '0.05em', color: 'var(--border-hi)', textTransform: 'uppercase' }}>
          v1.0 · Display Feed Controller
        </p>
      </footer>
    </main>
  )
}
