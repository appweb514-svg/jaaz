import CommonDialogContent from '@/components/common/DialogContent'
import { Dialog } from '@/components/ui/dialog'
import { SidebarProvider } from '@/components/ui/sidebar'
import { useConfigs } from '@/contexts/configs'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import SettingProviders from './providers'
import SettingProxy from './proxy'
import SettingSidebar, { SettingSidebarType } from './sidebar'
import { X } from 'lucide-react'

const SettingsDialog = () => {
  const { showSettingsDialog: open, setShowSettingsDialog } = useConfigs()
  const { t } = useTranslation()
  const [current, setCurrent] = useState<SettingSidebarType>('provider')

  const renderContent = () => {
    switch (current) {
      case 'proxy':
        return <SettingProxy />
      case 'provider':
      default:
        return <SettingProviders />
    }
  }

  return (
    <Dialog open={open} onOpenChange={setShowSettingsDialog}>
      <CommonDialogContent
        open={open}
        transformPerspective={6000}
        className="flex flex-col p-0 gap-0 w-[95vw] sm:w-full max-w-2xl h-[90vh] max-h-[100vh] rounded-lg sm:rounded-none! border shadow-lg sm:border-none! sm:shadow-none!"
      >
        <SidebarProvider className="h-[calc(100vh-60px)]! min-h-[calc(100vh-60px)]! flex-1 relative">
          <SettingSidebar
            current={current}
            setCurrent={setCurrent}
            onClose={() => setShowSettingsDialog(false)}
          />
          <div className="flex-1 overflow-y-auto pr-2 scrollbar-thin">
            {renderContent()}
          </div>
        </SidebarProvider>
      </CommonDialogContent>
    </Dialog>
  )
}

export default SettingsDialog
