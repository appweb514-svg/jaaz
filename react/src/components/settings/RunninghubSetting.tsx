import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PROVIDER_NAME_MAPPING } from '@/constants'
import { LLMConfig } from '@/types/types'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, Loader2, Play } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

interface RunninghubSettingProps {
  config: LLMConfig
  onConfigChange: (key: string, newConfig: LLMConfig) => void
}

export default function RunninghubSetting({
  config,
  onConfigChange,
}: RunninghubSettingProps) {
  const { t } = useTranslation()
  const provider = PROVIDER_NAME_MAPPING.runninghub
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{status?: string; coins?: string; wallet?: string} | null>(null)

  const handleChange = (field: keyof LLMConfig, value: string | number) => {
    onConfigChange('runninghub', {
      ...config,
      [field]: value,
    })
  }

  const testConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await fetch('/runninghub/test', { method: 'POST' })
      const data = await res.json()
      setTestResult(data)
      if (data.status === 'ok') {
        toast.success(`Connecté ! Coins: ${data.coins}, Wallet: $${data.wallet}`)
      } else {
        toast.error(data.message || 'Échec de connexion')
      }
    } catch (e: any) {
      toast.error(`Erreur: ${e.message}`)
      setTestResult({ status: 'error', message: e.message })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Provider Header */}
      <div className="flex items-center gap-2">
        <img
          src={provider.icon}
          alt={provider.name}
          className="w-10 h-10 rounded-full"
        />
        <p className="font-bold text-2xl w-fit">{provider.name}</p>
        <span>🎬 Vidéo & 🎨 Image</span>
      </div>

      {/* Test Connection */}
      <Button
        variant="outline"
        size="sm"
        onClick={testConnection}
        disabled={testing || !config.api_key}
        className="border-purple-300 text-purple-700 hover:bg-purple-50 dark:border-purple-700 dark:text-purple-400"
      >
        {testing ? (
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        ) : (
          <Play className="w-4 h-4 mr-2" />
        )}
        Tester la connexion
      </Button>

      {testResult && (
        <div className={`text-sm px-3 py-2 rounded-md ${
          testResult.status === 'ok' 
            ? 'bg-green-500/10 text-green-600' 
            : 'bg-red-500/10 text-red-600'
        }`}>
          {testResult.status === 'ok' 
            ? `✅ Connecté — ${testResult.coins} coins, $${testResult.wallet} wallet`
            : `❌ ${testResult.message}`}
        </div>
      )}

      {/* API Key Input */}
      <div className="space-y-2">
        <Label htmlFor="rh-api-key">{t('settings:provider.apiKey')}</Label>
        <Input
          id="rh-api-key"
          type="password"
          placeholder="Enter RunningHub API key"
          value={config.api_key ?? ''}
          onChange={(e) => handleChange('api_key', e.target.value)}
          className="w-full"
        />
        <p className="text-xs text-gray-500">
          RunningHub API key — disponible sur runninghub.ai
        </p>
      </div>

      {/* Workflow ID (ComfyUI) */}
      <div className="space-y-2">
        <Label htmlFor="rh-workflow">🖥️ Workflow ComfyUI</Label>
        <Input
          id="rh-workflow"
          placeholder="2069523159090552833"
          value={config.workflow_id ?? ''}
          onChange={(e) => {
            onConfigChange('runninghub', {
              ...config,
              workflow_id: e.target.value,
            })
            // Also save to /runninghub/settings endpoint
            fetch('/runninghub/settings', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ workflow_id: e.target.value }),
            }).catch(() => {})
          }}
          className="w-full"
        />
        <p className="text-xs text-gray-500">
          ID du workflow ComfyUI sur RunningHub (ex: LTX 2.3 = 2069523159090552833)
        </p>
      </div>

      {/* Enable/Disable */}
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={config.enabled ?? false}
            onChange={(e) => {
              const enabled = e.target.checked
              onConfigChange('runninghub', { ...config, enabled })
              fetch('/runninghub/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled }),
              }).catch(() => {})
            }}
            className="rounded"
          />
          <span className="text-sm">Activer RunningHub</span>
        </label>
        {config.enabled && <CheckCircle2 className="w-4 h-4 text-green-500" />}
      </div>
    </div>
  )
}
