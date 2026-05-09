import PageTransition from '@/components/PageTransition'
import ChatPage from './ChatPage'

export default function ChatPageWrapper() {
  return (
    <PageTransition layoutId="chat">
      <ChatPage />
    </PageTransition>
  )
}
