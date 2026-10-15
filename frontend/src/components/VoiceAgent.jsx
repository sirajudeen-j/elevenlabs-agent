import { useCallback, useEffect, useRef, useState } from 'react'
import { useConversation } from '@elevenlabs/react'

// "Talk to Nova" — starts an ElevenLabs conversation with the Nova support
// agent over WebRTC. Requires microphone access. Shows a live transcript and
// whether the agent is listening or speaking.
//
// Configure with VITE_ELEVENLABS_AGENT_ID (see .env.example). The agent's
// webhook tools point at this app's backend (see README § ElevenLabs setup).

const AGENT_ID = import.meta.env.VITE_ELEVENLABS_AGENT_ID

export default function VoiceAgent() {
  const [open, setOpen] = useState(false)
  const [transcript, setTranscript] = useState([]) // [{role: 'agent'|'user', text}]
  const [error, setError] = useState(null)
  const transcriptEndRef = useRef(null)

  const conversation = useConversation({
    onMessage: (message) => {
      setTranscript((prev) => [...prev, { role: message.role, text: message.message }])
    },
    onError: (err) => {
      setError(typeof err === 'string' ? err : err?.message ?? 'Conversation error')
    },
  })

  const { status, isSpeaking } = conversation
  const isConnected = status === 'connected'

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript])

  const start = useCallback(async () => {
    setError(null)
    setTranscript([])
    if (!AGENT_ID) {
      setError('Set VITE_ELEVENLABS_AGENT_ID in frontend/.env to enable Nova.')
      return
    }
    try {
      // Ask for the microphone up front so permission errors surface here
      // rather than mid-conversation.
      await navigator.mediaDevices.getUserMedia({ audio: true })
      // WebRTC session directly with the agent ID (public agent). For
      // private agents, mint a signed URL / conversation token server-side.
      await conversation.startSession({
        agentId: AGENT_ID,
        connectionType: 'webrtc',
      })
    } catch (err) {
      setError(
        err?.name === 'NotAllowedError'
          ? 'Microphone access was denied. Allow it in your browser and try again.'
          : err?.message ?? 'Could not start the conversation.',
      )
    }
  }, [conversation])

  const stop = useCallback(async () => {
    await conversation.endSession()
  }, [conversation])

  if (!open) {
    return (
      <button className="nova-fab" onClick={() => setOpen(true)} aria-label="Talk to Nova">
        Talk to Nova
      </button>
    )
  }

  return (
    <div className="nova-panel">
      <div className="nova-header">
        <strong>Nova — NovaMart support</strong>
        <button className="nova-close" onClick={() => setOpen(false)} aria-label="Close">
          ×
        </button>
      </div>

      <div className="nova-status">
        <span
          className={`nova-indicator ${
            isConnected ? (isSpeaking ? 'speaking' : 'listening') : 'idle'
          }`}
        />
        {status !== 'connected'
          ? status === 'connecting'
            ? 'Connecting…'
            : 'Not connected'
          : isSpeaking
            ? 'Nova is speaking…'
            : 'Listening…'}
      </div>

      <div className="nova-transcript">
        {transcript.length === 0 && (
          <p className="muted">
            Ask about an order, our returns policy, or say “change my shipping address”.
          </p>
        )}
        {transcript.map((line, i) => (
          <p key={i} className={line.role === 'agent' ? 'line-agent' : 'line-user'}>
            <strong>{line.role === 'agent' ? 'Nova' : 'You'}:</strong> {line.text}
          </p>
        ))}
        <div ref={transcriptEndRef} />
      </div>

      {error && <p className="error">{error}</p>}

      <div className="nova-actions">
        {isConnected ? (
          <button className="btn" onClick={stop}>
            End conversation
          </button>
        ) : (
          <button
            className="btn btn-primary"
            onClick={start}
            disabled={status === 'connecting'}
          >
            {status === 'connecting' ? 'Connecting…' : 'Start conversation'}
          </button>
        )}
      </div>
    </div>
  )
}
