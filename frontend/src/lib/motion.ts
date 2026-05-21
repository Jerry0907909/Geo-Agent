import type { Transition, Variants } from "framer-motion"

export const APP_SPRING: Transition = {
  type: "spring",
  stiffness: 320,
  damping: 30,
  mass: 0.86,
}

export const SOFT_SPRING: Transition = {
  type: "spring",
  stiffness: 260,
  damping: 28,
  mass: 0.9,
}

export const GENTLE_SPRING: Transition = {
  type: "spring",
  stiffness: 200,
  damping: 24,
  mass: 0.95,
}

export const FAST_FADE: Transition = {
  duration: 0.18,
  ease: [0.22, 1, 0.36, 1],
}

export const PAGE_SURFACE: Variants = {
  initial: { opacity: 0, y: 12, scale: 0.996 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -8, scale: 0.998 },
}

export const REDUCED_FADE: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
}

// Crossfade + subtle scale for tab/content switches
export const TAB_SWITCH: Variants = {
  initial: { opacity: 0, x: 6 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -6 },
}

// Directional page transitions
export const PAGE_FORWARD: Variants = {
  initial: { opacity: 0, x: 24, scale: 0.995 },
  animate: { opacity: 1, x: 0, scale: 1 },
  exit: { opacity: 0, x: -16, scale: 0.997 },
}

export const PAGE_BACKWARD: Variants = {
  initial: { opacity: 0, x: -16, scale: 0.997 },
  animate: { opacity: 1, x: 0, scale: 1 },
  exit: { opacity: 0, x: 24, scale: 0.995 },
}

// Dialog / modal entrance
export const DIALOG_OVERLAY: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
}

export const DIALOG_CONTENT: Variants = {
  initial: { opacity: 0, scale: 0.96, y: 8 },
  animate: { opacity: 1, scale: 1, y: 0 },
  exit: { opacity: 0, scale: 0.96, y: 8 },
}

// Stagger children
export const STAGGER_PARENT: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.045,
      delayChildren: 0.02,
    },
  },
}

export const STAGGER_ITEM: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -6 },
}

export const COLLAPSE_REVEAL: Variants = {
  initial: { opacity: 0, height: 0 },
  animate: { opacity: 1, height: "auto" },
  exit: { opacity: 0, height: 0 },
}
