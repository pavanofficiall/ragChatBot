"use client"

import { Plus, MessageSquare, Trash2, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Chat } from "@/app/page"
import { cn } from "@/lib/utils"

interface SidebarProps {
  chats: Chat[]
  activeChat: string | null
  onSelectChat: (id: string) => void
  onNewChat: () => void
  onDeleteChat: (id: string) => void
  isOpen: boolean
  onToggle: () => void
}

export function Sidebar({ chats, activeChat, onSelectChat, onNewChat, onDeleteChat, isOpen, onToggle }: SidebarProps) {
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  const todayChats = chats.filter((c) => c.createdAt.toDateString() === today.toDateString())
  const yesterdayChats = chats.filter((c) => c.createdAt.toDateString() === yesterday.toDateString())
  const olderChats = chats.filter(
    (c) =>
      c.createdAt.toDateString() !== today.toDateString() && c.createdAt.toDateString() !== yesterday.toDateString(),
  )

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden" onClick={onToggle} />}

      <aside
        className={cn(
          "fixed md:relative z-50 flex flex-col h-full bg-sidebar border-r border-sidebar-border transition-all duration-300",
          isOpen ? "w-72 translate-x-0" : "w-0 -translate-x-full md:translate-x-0 md:w-0",
        )}
      >
        <div className={cn("flex flex-col h-full overflow-hidden", isOpen ? "opacity-100" : "opacity-0")}>
          {/* Header */}
          <div className="flex items-center justify-between p-4">
            <h1 className="text-lg font-semibold text-sidebar-foreground">AI Chat</h1>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="md:hidden text-sidebar-foreground hover:bg-sidebar-accent"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* New Chat Button */}
          <div className="px-3 pb-4">
            <Button
              onClick={onNewChat}
              className="w-full justify-start gap-2 bg-sidebar-accent text-sidebar-accent-foreground hover:bg-sidebar-accent/80"
            >
              <Plus className="h-4 w-4" />
              New chat
            </Button>
          </div>

          {/* Chat List */}
          <ScrollArea className="flex-1 px-3">
            {todayChats.length > 0 && (
              <ChatGroup
                title="Today"
                chats={todayChats}
                activeChat={activeChat}
                onSelectChat={onSelectChat}
                onDeleteChat={onDeleteChat}
              />
            )}
            {yesterdayChats.length > 0 && (
              <ChatGroup
                title="Yesterday"
                chats={yesterdayChats}
                activeChat={activeChat}
                onSelectChat={onSelectChat}
                onDeleteChat={onDeleteChat}
              />
            )}
            {olderChats.length > 0 && (
              <ChatGroup
                title="Previous 7 Days"
                chats={olderChats}
                activeChat={activeChat}
                onSelectChat={onSelectChat}
                onDeleteChat={onDeleteChat}
              />
            )}
          </ScrollArea>
        </div>
      </aside>
    </>
  )
}

function ChatGroup({
  title,
  chats,
  activeChat,
  onSelectChat,
  onDeleteChat,
}: {
  title: string
  chats: Chat[]
  activeChat: string | null
  onSelectChat: (id: string) => void
  onDeleteChat: (id: string) => void
}) {
  return (
    <div className="mb-4">
      <p className="text-xs font-medium text-muted-foreground px-2 mb-2">{title}</p>
      <div className="space-y-1">
        {chats.map((chat) => (
          <ChatItem
            key={chat.id}
            chat={chat}
            isActive={chat.id === activeChat}
            onSelect={() => onSelectChat(chat.id)}
            onDelete={() => onDeleteChat(chat.id)}
          />
        ))}
      </div>
    </div>
  )
}

function ChatItem({
  chat,
  isActive,
  onSelect,
  onDelete,
}: {
  chat: Chat
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  return (
    <div
      className={cn(
        "group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-colors",
        isActive
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent/50",
      )}
      onClick={onSelect}
    >
      <MessageSquare className="h-4 w-4 shrink-0" />
      <span className="flex-1 truncate text-sm">{chat.title}</span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 opacity-0 group-hover:opacity-100 hover:bg-destructive/20 hover:text-destructive"
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
      >
        <Trash2 className="h-3 w-3" />
      </Button>
    </div>
  )
}
