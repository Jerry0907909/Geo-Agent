import { motion } from 'framer-motion'

interface PageTransitionProps {
  children: React.ReactNode
  layoutId?: string
}

export default function PageTransition({ 
  children, 
  layoutId
}: PageTransitionProps) {

  return (
    <motion.div
      layoutId={layoutId}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{
        duration: 0.2,
        ease: [0.4, 0, 0.2, 1]
      }}
      className="w-full h-full"
    >
      {children}
    </motion.div>
  )
}
