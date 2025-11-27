"use client"

import { useState, useEffect } from "react"
import { Sidebar } from "@/components/sidebar"
import { ChatArea } from "@/components/chat-area"

export interface Chat {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  source?: string
  mode?: string
}

export default function Home() {
  const [chats, setChats] = useState<Chat[]>([
    {
      id: "1",
      title: "What is React?",
      messages: [
        { id: "1", role: "user", content: "What is React?", timestamp: new Date() },
        {
          id: "2",
          role: "assistant",
          content:
            "React is a JavaScript library for building user interfaces, particularly single-page applications. It was developed by Facebook and is now maintained by Meta and a community of developers.",
          timestamp: new Date(),
        },
      ],
      createdAt: new Date(),
    },
    {
      id: "2",
      title: "Help me with Python",
      messages: [
        { id: "1", role: "user", content: "Can you help me learn Python?", timestamp: new Date(Date.now() - 86400000) },
        {
          id: "2",
          role: "assistant",
          content: "Of course! Python is a great language to learn. What specific topics would you like to cover?",
          timestamp: new Date(Date.now() - 86400000),
        },
      ],
      createdAt: new Date(Date.now() - 86400000),
    },
    {
      id: "3",
      title: "Explain machine learning",
      messages: [],
      createdAt: new Date(Date.now() - 172800000),
    },
  ])
  const [activeChat, setActiveChat] = useState<string | null>("1")
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const currentChat = chats.find((c) => c.id === activeChat)
  const [geminiConfigured, setGeminiConfigured] = useState<boolean | null>(null)

  // Read health at mount
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
  useEffect(() => {
    ;(async () => {
      try {
        const res = await fetch(`${API_URL}/health`)
        if (!res.ok) return
        const json = await res.json()
        setGeminiConfigured(Boolean(json?.gemini_configured))
      } catch (e) {
        setGeminiConfigured(false)
      }
    })()
  }, [])

  const createNewChat = () => {
    const newChat: Chat = {
      id: Date.now().toString(),
      title: "New chat",
      messages: [],
      createdAt: new Date(),
    }
    setChats([newChat, ...chats])
    setActiveChat(newChat.id)
  }

  const deleteChat = (id: string) => {
    setChats(chats.filter((c) => c.id !== id))
    if (activeChat === id) {
      setActiveChat(chats.length > 1 ? chats.find((c) => c.id !== id)?.id || null : null)
    }
  }

  const addMessage = async (content: string) => {
    if (!activeChat) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date(),
    }
    // Append the user's message using functional state update
    setChats((prevChats) =>
      prevChats.map((chat) => {
        if (chat.id === activeChat) {
          const updatedMessages = [...chat.messages, userMessage]
          return {
            ...chat,
            messages: updatedMessages,
            title: chat.messages.length === 0 ? content.slice(0, 30) + (content.length > 30 ? "..." : "") : chat.title,
          }
        }
        return chat
      }),
    )

    // Call backend API for assistant response
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
    let assistantText = ""
    let assistantSource: string | undefined = undefined
    let assistantMode: string | undefined = undefined
    try {
      const res = await fetch(`${API_URL}/query/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: content }),
      })
      if (!res.ok) {
        throw new Error(`API responded with ${res.status}`)
      }
      const json = await res.json()
      console.log('Backend response:', json)
      assistantText = json?.answer || "No relevant info found."
      assistantSource = json?.source
      assistantMode = json?.mode
    } catch (err) {
      // If backend fails, use local fallback response
      console.error("Failed to fetch assistant response:", err)
      assistantText = generateResponse(content)
    }

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: assistantText,
      source: assistantSource,
      mode: assistantMode,
      timestamp: new Date(),
    }

    // Append the assistant's response
    // Append assistant message using functional state update to avoid stale state
    setChats((prevChats) =>
      prevChats.map((chat) => {
        if (chat.id === activeChat) {
          const updatedMessages = [...chat.messages, assistantMessage]
          return {
            ...chat,
            messages: updatedMessages,
            title: chat.messages.length === 0 ? content.slice(0, 30) + (content.length > 30 ? "..." : "") : chat.title,
          }
        }
        return chat
      }),
    )
  }

  const generateResponse = (input: string): string => {
    const responses = [
      "That's a great question! Let me think about that for a moment. Based on my knowledge, I would say that understanding context is key to providing helpful responses.",
      "I understand what you're asking. Here's my perspective on this topic - it's important to consider multiple angles when approaching complex questions.",
      "Thanks for sharing that with me. I'd be happy to help you explore this further. What specific aspects would you like me to focus on?",
      "Interesting point! From my understanding, there are several factors to consider here. Would you like me to elaborate on any particular aspect?",
      "I appreciate your curiosity. This is actually a topic I find fascinating. Let me share some insights that might be helpful for you.",
    ]
    return responses[Math.floor(Math.random() * responses.length)]
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar
        chats={chats}
        activeChat={activeChat}
        onSelectChat={setActiveChat}
        onNewChat={createNewChat}
        onDeleteChat={deleteChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      <ChatArea
        chat={currentChat}
        onSendMessage={addMessage}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        sidebarOpen={sidebarOpen}
        geminiConfigured={geminiConfigured}
      />
    </div>
  )
}
