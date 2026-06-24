import { useConfigs } from '@/contexts/configs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ChevronLeft, HelpCircle, ImageIcon, Menu, SettingsIcon, X } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from '@tanstack/react-router'
import ThemeButton from '@/components/theme/ThemeButton'
import { LOGO_URL } from '@/constants'
import LanguageSwitcher from './common/LanguageSwitcher'
import { cn } from '@/lib/utils'
import { UserMenu } from './auth/UserMenu'
import { onboardingStore } from '@/hooks/useOnboarding'
import { useState } from 'react'

export default function TopMenu({
  middle,
  right,
}: {
  middle?: React.ReactNode
  right?: React.ReactNode
}) {
  const { t } = useTranslation()

  const navigate = useNavigate()
  const { setShowSettingsDialog } = useConfigs()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <motion.div
      className="sticky top-0 z-20 flex w-full h-8 bg-background px-2 sm:px-4 justify-between items-center select-none border-b border-border"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center gap-4 sm:gap-8">
        <motion.div
          className="flex items-center gap-2 cursor-pointer group"
          onClick={() => navigate({ to: '/' })}
        >
          {window.location.pathname !== '/' && (
            <ChevronLeft className="size-5 group-hover:-translate-x-0.5 transition-transform duration-300" />
          )}
          <img src={LOGO_URL} alt="logo" className="size-5" draggable={false} />
          <motion.div className="flex relative overflow-hidden items-start h-7 text-xl font-bold">
            <motion.span className="flex items-center" layout>
              {window.location.pathname === '/' ? 'Jaaz' : t('canvas:back')}
            </motion.span>
          </motion.div>
        </motion.div>
        {/* Assets button: hidden on small screens (shown in hamburger) */}
        <Button
          variant={window.location.pathname === '/assets' ? 'default' : 'ghost'}
          size="sm"
          className={cn('hidden sm:flex items-center font-bold rounded-none')}
          onClick={() => navigate({ to: '/assets' })}
        >
          <ImageIcon className="size-4" />
          {t('canvas:assets', 'Library')}
        </Button>
      </div>

      <div className="flex items-center gap-2">{middle}</div>

      {/* Desktop: show all buttons inline */}
      <div className="hidden sm:flex items-center gap-2">
        {right}
        {/* <AgentSettings /> */}
        <Button
          size={'sm'}
          variant="ghost"
          onClick={() => setShowSettingsDialog(true)}
          data-tour="settings"
        >
          <SettingsIcon size={30} />
        </Button>
        <Button
          size={'sm'}
          variant="ghost"
          onClick={() => onboardingStore.getState().start()}
          aria-label="Aide / Tour"
        >
          <HelpCircle size={18} />
        </Button>
        <LanguageSwitcher />
        <ThemeButton />
        <UserMenu />
      </div>

      {/* Mobile: hamburger menu */}
      <div className="flex sm:hidden items-center">
        <Button
          size={'sm'}
          variant="ghost"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </Button>
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              className="absolute top-full right-0 mt-1 flex flex-col gap-2 p-3 bg-background border border-border rounded-lg shadow-lg min-w-48 z-50"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <Button
                variant={window.location.pathname === '/assets' ? 'default' : 'ghost'}
                size="sm"
                className="w-full justify-start"
                onClick={() => {
                  navigate({ to: '/assets' })
                  setMobileMenuOpen(false)
                }}
              >
                <ImageIcon className="size-4" />
                {t('canvas:assets', 'Library')}
              </Button>
              <Button
                size={'sm'}
                variant="ghost"
                className="w-full justify-start"
                onClick={() => {
                  setShowSettingsDialog(true)
                  setMobileMenuOpen(false)
                }}
              >
                <SettingsIcon size={20} />
                {t('settings:title', 'Settings')}
              </Button>
              <Button
                size={'sm'}
                variant="ghost"
                className="w-full justify-start"
                onClick={() => {
                  onboardingStore.getState().start()
                  setMobileMenuOpen(false)
                }}
              >
                <HelpCircle size={20} />
                Tour d'aide
              </Button>
              <div className="flex items-center justify-between gap-2 px-1">
                <LanguageSwitcher />
                <ThemeButton />
              </div>
              <UserMenu />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
