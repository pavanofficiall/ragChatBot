"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Menu, Send, Bot, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import type { Chat, Message } from "@/app/page"
import { cn } from "@/lib/utils"

interface ChatAreaProps {
  chat: Chat | undefined
  onSendMessage: (content: string) => void
  onToggleSidebar: () => void
  sidebarOpen: boolean
  geminiConfigured?: boolean | null
  isLoading?: boolean
}

export function ChatArea({ chat, onSendMessage, onToggleSidebar, sidebarOpen, geminiConfigured, isLoading }: ChatAreaProps) {
  // Show a small banner if Gemini LLM is not configured
  const showBanner = (typeof (chat) !== 'undefined')
  
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [chat?.messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) {
      onSendMessage(input.trim())
      setInput("")
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto"
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px"
    }
  }

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-3 border-b border-border">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleSidebar}
          className={cn("text-foreground hover:bg-secondary", sidebarOpen && "md:hidden")}
        >
          <Menu className="h-5 w-5" />
        </Button>
        <h2 className="font-medium text-foreground truncate">{chat?.title || "New chat"}</h2>
        {geminiConfigured === false && (
          <div className="ml-auto text-xs text-amber-400">LLM not configured</div>
        )}
        {geminiConfigured === true && (
          <div className="ml-auto text-xs text-green-400">LLM configured</div>
        )}
      </header>

      {/* Messages */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        {chat?.messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {chat?.messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Input */}
      <div className="p-4 border-t border-border">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
            <div className="relative flex items-end gap-2 bg-secondary rounded-2xl px-4 py-3">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              disabled={!!isLoading}
              placeholder="Message AI Chat..."
              className="flex-1 min-h-[24px] max-h-[200px] resize-none bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 p-0 text-foreground placeholder:text-muted-foreground"
              rows={1}
            />
            <Button
              type="submit"
              size="icon"
              disabled={!input.trim() || !!isLoading}
              className="h-8 w-8 shrink-0 rounded-full bg-foreground text-background hover:bg-foreground/90 disabled:opacity-30"
            >
              {isLoading ? (
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-2">
            AI Chat can make mistakes. Consider checking important information.
          </p>
        </form>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <Avatar className={cn("h-8 w-8 shrink-0", isUser ? "bg-accent" : "bg-secondary")}>
        <AvatarFallback
          className={cn(isUser ? "bg-accent text-accent-foreground" : "bg-secondary text-secondary-foreground")}
        >
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div className={cn("flex-1 space-y-1", isUser && "text-right")}>
        <p className="text-xs font-medium text-muted-foreground">{isUser ? "You" : "AI Chat"}</p>
        <div
          className={cn(
            "inline-block px-4 py-2 rounded-2xl max-w-[85%] text-left",
            isUser ? "bg-accent text-accent-foreground" : "bg-secondary text-secondary-foreground",
          )}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          {message.source && (
            <p className="text-xs text-muted-foreground mt-1">Source: {message.source}</p>
          )}
          {message.source === "loading" && (
            <div className="mt-2">
              <span className="inline-block h-2 w-2 rounded-full bg-muted-foreground animate-pulse mr-2" />
              <span className="text-xs text-muted-foreground">Generating answer...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center px-4">
      <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mb-4">
        <Bot className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-xl font-semibold text-foreground mb-2">How can I help you today?</h3>
      <p className="text-muted-foreground max-w-md">
        Start a conversation by typing a message below. I can help with questions, creative writing, analysis, and more.
      </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-8 w-full max-w-lg">
        {[
          "Explain quantum computing in simple terms",
          "Write a creative story about a robot",
          "Help me debug my Python code",
          "Suggest healthy meal prep ideas",
        ].map((suggestion, i) => (
          <button
            key={i}
            className="px-4 py-3 text-sm text-left bg-secondary hover:bg-secondary/80 rounded-xl text-foreground transition-colors"
            onClick={() => onSendMessage(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}
