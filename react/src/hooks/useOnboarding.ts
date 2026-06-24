import { create } from 'zustand'

const STORAGE_KEY = 'jaaz-onboarding-completed'
export const ONBOARDING_TOTAL_STEPS = 5

type OnboardingState = {
  currentStep: number
  isOpen: boolean
  start: () => void
  next: () => void
  prev: () => void
  skip: () => void
  complete: () => void
}

function markCompleted() {
  try {
    localStorage.setItem(STORAGE_KEY, 'true')
  } catch {
    // ignore storage errors
  }
}

const useOnboardingStore = create<OnboardingState>((set, get) => ({
  currentStep: 0,
  isOpen: false,
  start: () => set({ isOpen: true, currentStep: 0 }),
  next: () => {
    const { currentStep } = get()
    if (currentStep >= ONBOARDING_TOTAL_STEPS - 1) {
      markCompleted()
      set({ isOpen: false, currentStep: 0 })
    } else {
      set({ currentStep: currentStep + 1 })
    }
  },
  prev: () =>
    set((s) => ({ currentStep: Math.max(0, s.currentStep - 1) })),
  skip: () => {
    markCompleted()
    set({ isOpen: false, currentStep: 0 })
  },
  complete: () => {
    markCompleted()
    set({ isOpen: false, currentStep: 0 })
  },
}))

export function useOnboarding() {
  return useOnboardingStore()
}

/** Direct store access for non-React contexts (e.g. auto-start effect) */
export const onboardingStore = useOnboardingStore

export function hasSeenOnboarding(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}
