import {
  hasSeenOnboarding,
  onboardingStore,
  useOnboarding,
} from '@/hooks/useOnboarding'
import { Button } from '@/components/ui/button'
import { AnimatePresence, motion } from 'motion/react'
import { useCallback, useEffect, useLayoutEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'

type TourStep = {
  title: string
  description: string
  /** data-tour attribute value to locate the target element */
  target?: string
}

const TOUR_STEPS: TourStep[] = [
  {
    title: 'Bienvenue sur Jaaz',
    description: "Votre studio créatif pour générer images et vidéos avec l'IA",
  },
  {
    title: 'Canvas',
    description: 'Dessinez, annotatez et placez vos médias sur le canvas',
    target: 'canvas',
  },
  {
    title: 'Chat IA',
    description: "Décrivez ce que vous voulez créer, l'IA génère pour vous",
    target: 'chat',
  },
  {
    title: 'Settings',
    description:
      'Configurez vos providers: OpenRouter (LLM), RunningHub (vidéo), ComfyUI',
    target: 'settings',
  },
  {
    title: 'Génération',
    description: 'Sélectionnez un modèle et lancez la génération',
    target: 'generation',
  },
]

const HIGHLIGHT_PADDING = 6
const TOOLTIP_WIDTH = 360
const TOOLTIP_EST_HEIGHT = 220
const GAP = 16

function computeTooltipStyle(
  rect: DOMRect | null,
  viewport: { w: number; h: number }
): React.CSSProperties {
  if (!rect) {
    // Center on screen for steps without a target
    return {
      top: Math.max(GAP, (viewport.h - TOOLTIP_EST_HEIGHT) / 2),
      left: Math.max(GAP, (viewport.w - TOOLTIP_WIDTH) / 2),
    }
  }

  const spaceBelow = viewport.h - rect.bottom
  const spaceAbove = rect.top
  let top: number
  let left: number

  // Vertical: prefer below, then above
  if (spaceBelow >= TOOLTIP_EST_HEIGHT + GAP) {
    top = rect.bottom + GAP
  } else if (spaceAbove >= TOOLTIP_EST_HEIGHT + GAP) {
    top = rect.top - GAP - TOOLTIP_EST_HEIGHT
  } else {
    // Not enough space on either side — use whichever has more room
    top =
      spaceBelow >= spaceAbove
        ? rect.bottom + GAP
        : rect.top - GAP - TOOLTIP_EST_HEIGHT
  }

  // Horizontal: center relative to target, clamp to viewport
  left = rect.left + rect.width / 2 - TOOLTIP_WIDTH / 2
  left = Math.max(GAP, Math.min(left, viewport.w - TOOLTIP_WIDTH - GAP))

  // Clamp vertical
  top = Math.max(GAP, Math.min(top, viewport.h - TOOLTIP_EST_HEIGHT - GAP))

  return { top, left }
}

export default function OnboardingTour() {
  const { isOpen, currentStep, next, prev, skip } = useOnboarding()
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null)
  const [viewport, setViewport] = useState({
    w: typeof window !== 'undefined' ? window.innerWidth : 1280,
    h: typeof window !== 'undefined' ? window.innerHeight : 720,
  })

  const step = TOUR_STEPS[currentStep]
  const isLastStep = currentStep === TOUR_STEPS.length - 1
  const hasTarget = !!step?.target && !!targetRect

  const updateTargetRect = useCallback(() => {
    if (!step?.target) {
      setTargetRect(null)
      return
    }
    const el = document.querySelector(`[data-tour="${step.target}"]`)
    setTargetRect(el ? el.getBoundingClientRect() : null)
  }, [step])

  // Update rect when step changes or tour opens
  useLayoutEffect(() => {
    if (isOpen) {
      // Double rAF to ensure DOM is settled after route transitions
      requestAnimationFrame(() => requestAnimationFrame(updateTargetRect))
    }
  }, [isOpen, currentStep, updateTargetRect])

  // Track viewport and scroll changes
  useEffect(() => {
    if (!isOpen) return
    const handleResize = () => {
      setViewport({ w: window.innerWidth, h: window.innerHeight })
      updateTargetRect()
    }
    const handleScroll = () => updateTargetRect()
    window.addEventListener('resize', handleResize)
    window.addEventListener('scroll', handleScroll, true)
    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('scroll', handleScroll, true)
    }
  }, [isOpen, updateTargetRect])

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') skip()
      else if (e.key === 'ArrowRight') next()
      else if (e.key === 'ArrowLeft') prev()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [isOpen, next, prev, skip])

  // Auto-start on first visit
  useEffect(() => {
    if (!hasSeenOnboarding()) {
      const timer = setTimeout(() => onboardingStore.getState().start(), 1000)
      return () => clearTimeout(timer)
    }
  }, [])

  if (!isOpen || !step) return null

  const tooltipStyle = computeTooltipStyle(targetRect, viewport)

  return (
    <div className="fixed inset-0 z-[9999]">
      {/* Click-capture layer — prevents interaction with the app underneath */}
      <div className="absolute inset-0" />

      {/* Highlight / spotlight using box-shadow cutout */}
      {hasTarget && targetRect && (
        <motion.div
          className="absolute pointer-events-none border-2 border-purple-500 rounded-lg"
          initial={{ opacity: 0 }}
          animate={{
            opacity: 1,
            top: targetRect.top - HIGHLIGHT_PADDING,
            left: targetRect.left - HIGHLIGHT_PADDING,
            width: targetRect.width + HIGHLIGHT_PADDING * 2,
            height: targetRect.height + HIGHLIGHT_PADDING * 2,
          }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease: 'easeInOut' }}
          style={{
            boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.72)',
          }}
        />
      )}

      {/* Dark backdrop for steps without a target element */}
      {!hasTarget && <div className="absolute inset-0 bg-black/72" />}

      {/* Tooltip card */}
      <AnimatePresence>
        <motion.div
          key={currentStep}
          className="absolute z-10 w-[360px] max-w-[calc(100vw-32px)] bg-zinc-900 border border-purple-500/30 rounded-xl shadow-2xl shadow-purple-500/10 p-5"
          initial={{ opacity: 0, scale: 0.95, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 8 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          style={tooltipStyle}
        >
          {/* Close button */}
          <button
            onClick={skip}
            className="absolute top-3 right-3 text-zinc-500 hover:text-zinc-300 transition-colors"
            aria-label="Fermer"
          >
            <X size={16} />
          </button>

          {/* Step indicator */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-medium text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full">
              {currentStep + 1} / {TOUR_STEPS.length}
            </span>
          </div>

          {/* Content */}
          <h3 className="text-lg font-bold text-white mb-1.5">
            {step.title}
          </h3>
          <p className="text-sm text-zinc-400 leading-relaxed mb-5">
            {step.description}
          </p>

          {/* Buttons */}
          <div className="flex items-center justify-between gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={skip}
              className="text-zinc-400 hover:text-zinc-200"
            >
              Passer
            </Button>
            <div className="flex items-center gap-2">
              {currentStep > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={prev}
                  className="border-zinc-700"
                >
                  <ChevronLeft size={14} />
                  Précédent
                </Button>
              )}
              <Button
                size="sm"
                onClick={next}
                className="bg-purple-600 hover:bg-purple-700 text-white"
              >
                {isLastStep ? 'Commencer' : 'Suivant'}
                {!isLastStep && <ChevronRight size={14} />}
              </Button>
            </div>
          </div>

          {/* Progress dots */}
          <div className="flex items-center justify-center gap-1.5 mt-4">
            {TOUR_STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  i === currentStep
                    ? 'w-6 bg-purple-500'
                    : i < currentStep
                      ? 'w-1.5 bg-purple-500/50'
                      : 'w-1.5 bg-zinc-700'
                }`}
              />
            ))}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
