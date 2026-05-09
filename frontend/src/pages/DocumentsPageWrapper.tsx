import PageTransition from '@/components/PageTransition'
import DocumentsPage from './DocumentsPage'

export default function DocumentsPageWrapper() {
  return (
    <PageTransition layoutId="documents">
      <DocumentsPage />
    </PageTransition>
  )
}
