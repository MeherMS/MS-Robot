'use client'

import ChatContainer from '@/components/ChatContainer'
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-white">
      <ChatContainer />
      <Footer />
    </main>
  )
}