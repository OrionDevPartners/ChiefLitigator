"use client"

import { useState, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface Message {
  role: "ai" | "user"
  text: string
}

const INITIAL_MESSAGES: Message[] = [
  {
    role: "ai",
    text: "Let's build your case profile. First — can you briefly describe what happened and when?",
  },
]

const FOLLOW_UP_QUESTIONS = [
  "Got it. Have you received any formal court documents or just an informal notice so far?",
  "What is the opposing party claiming, and roughly what amount are they seeking?",
  "Do you currently have legal representation, or are you handling this yourself?",
  "Are there any hard deadlines you're aware of — such as a response due date?",
]

interface Step3Props {
  onNext: () => void
  onBack: () => void
}

export function Step3Interview({ onNext, onBack }: Step3Props) {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES)
  const [input, setInput] = useState("")
  const [aiTyping, setAiTyping] = useState(false)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [files, setFiles] = useState<File[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const sendMessage = () => {
    if (!input.trim()) return

    const userMsg: Message = { role: "user", text: input.trim() }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setAiTyping(true)

    setTimeout(() => {
      const nextQ = FOLLOW_UP_QUESTIONS[questionIndex]
      if (nextQ) {
        setMessages((prev) => [...prev, { role: "ai", text: nextQ }])
        setQuestionIndex((i) => i + 1)
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "ai",
            text: "I have enough to get started. Upload any relevant documents below, or skip to continue.",
          },
        ])
      }
      setAiTyping(false)
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
    }, 1200)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const dropped = Array.from(e.dataTransfer.files)
    setFiles((prev) => [...prev, ...dropped])
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles((prev) => [...prev, ...Array.from(e.target.files!)])
    }
  }

  const removeFile = (i: number) => setFiles((prev) => prev.filter((_, idx) => idx !== i))

  return (
    <div className="flex flex-col gap-5">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-foreground text-balance">Tell me about your case</h1>
        <p className="text-sm text-muted-foreground mt-1.5">AI-guided interview — takes about 2 minutes.</p>
      </div>

      {/* Chat window */}
      <div className="rounded-xl border border-border bg-surface-1 flex flex-col overflow-hidden" style={{ minHeight: 260, maxHeight: 320 }}>
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3" style={{ maxHeight: 260 }}>
          {messages.map((msg, i) => (
            <div
              key={i}
              className={["flex gap-2.5", msg.role === "user" ? "justify-end" : "justify-start"].join(" ")}
            >
              {msg.role === "ai" && (
                <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0 mt-0.5">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary" aria-hidden="true">
                    <circle cx="12" cy="12" r="3" /><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
                  </svg>
                </div>
              )}
              <div
                className={[
                  "max-w-[80%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed",
                  msg.role === "ai"
                    ? "bg-surface-2 text-foreground rounded-tl-sm"
                    : "bg-primary text-primary-foreground rounded-tr-sm",
                ].join(" ")}
              >
                {msg.text}
              </div>
            </div>
          ))}
          {aiTyping && (
            <div className="flex gap-2.5 justify-start">
              <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary" aria-hidden="true">
                  <circle cx="12" cy="12" r="3" /><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
                </svg>
              </div>
              <div className="bg-surface-2 px-4 py-3 rounded-2xl rounded-tl-sm flex gap-1 items-center">
                {[0, 150, 300].map((delay) => (
                  <span
                    key={delay}
                    className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce"
                    style={{ animationDelay: `${delay}ms` }}
                  />
                ))}
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-border p-3 flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your response…"
            rows={1}
            className="flex-1 resize-none bg-surface-2 border-border text-foreground placeholder:text-muted-foreground text-sm min-h-0 focus-visible:ring-primary leading-relaxed"
          />
          <Button
            size="icon"
            className="h-9 w-9 shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 self-end"
            onClick={sendMessage}
            disabled={!input.trim() || aiTyping}
            aria-label="Send message"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22,2 15,22 11,13 2,9" />
            </svg>
          </Button>
        </div>
      </div>

      {/* Document upload */}
      <div>
        <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">Attach Documents (optional)</p>
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={[
            "rounded-xl border-2 border-dashed p-6 flex flex-col items-center gap-2 cursor-pointer transition-all duration-200",
            isDragOver
              ? "border-primary bg-[var(--brand-cyan-dim)]"
              : "border-border hover:border-border/80 hover:bg-surface-2",
          ].join(" ")}
          role="button"
          tabIndex={0}
          aria-label="Upload documents"
          onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={isDragOver ? "text-primary" : "text-muted-foreground"} aria-hidden="true">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="17,8 12,3 7,8" /><line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <p className="text-sm text-muted-foreground text-center">
            <span className="text-primary font-medium">Click to upload</span> or drag and drop
          </p>
          <p className="text-xs text-muted-foreground">PDF, DOCX, PNG, JPG up to 25MB each</p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
          className="hidden"
          onChange={handleFileInput}
        />

        {files.length > 0 && (
          <ul className="mt-3 flex flex-col gap-2">
            {files.map((file, i) => (
              <li key={i} className="flex items-center gap-2.5 rounded-lg bg-surface-2 border border-border px-3 py-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-primary shrink-0" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14,2 14,8 20,8" />
                </svg>
                <span className="text-xs text-foreground flex-1 truncate">{file.name}</span>
                <span className="text-xs text-muted-foreground shrink-0">{(file.size / 1024).toFixed(0)} KB</span>
                <button onClick={() => removeFile(i)} className="text-muted-foreground hover:text-foreground transition-colors" aria-label={`Remove ${file.name}`}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex gap-3">
        <Button
          variant="outline"
          className="flex-1 h-11 border-border bg-surface-2 hover:bg-surface-3 text-foreground"
          onClick={onBack}
        >
          Back
        </Button>
        <Button
          className="flex-1 h-11 bg-primary text-primary-foreground hover:bg-primary/90 font-medium"
          onClick={onNext}
        >
          Build my case
        </Button>
      </div>
    </div>
  )
}
