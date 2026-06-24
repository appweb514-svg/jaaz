import { getCanvas, renameCanvas } from '@/api/canvas'
import CanvasExcali from '@/components/canvas/CanvasExcali'
import CanvasHeader from '@/components/canvas/CanvasHeader'
import CanvasMenu from '@/components/canvas/menu'
import CanvasPopbarWrapper from '@/components/canvas/pop-bar'
// VideoCanvasOverlay removed - using native Excalidraw embeddable elements instead
import ChatInterface from '@/components/chat/Chat'
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable'
import { CanvasProvider } from '@/contexts/canvas'
import { Session } from '@/types/types'
import { createFileRoute, useParams, useSearch } from '@tanstack/react-router'
import { Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useIsMobile } from '@/hooks/use-mobile'

export const Route = createFileRoute('/canvas/$id')({
  component: Canvas,
})

function CanvasContent() {
  const { id } = useParams({ from: '/canvas/$id' })
  const [canvas, setCanvas] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [canvasName, setCanvasName] = useState('')
  const [sessionList, setSessionList] = useState<Session[]>([])
  const [activeTab, setActiveTab] = useState<'canvas' | 'chat'>('canvas')
  const isMobile = useIsMobile()
  const search = useSearch({ from: '/canvas/$id' }) as {
    sessionId: string
  }
  const searchSessionId = search?.sessionId || ''
  useEffect(() => {
    let mounted = true

    const fetchCanvas = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await getCanvas(id)
        if (mounted) {
          setCanvas(data)
          setCanvasName(data.name)
          setSessionList(data.sessions)
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch canvas data'))
          console.error('Failed to fetch canvas data:', err)
        }
      } finally {
        if (mounted) {
          setIsLoading(false)
        }
      }
    }

    fetchCanvas()

    return () => {
      mounted = false
    }
  }, [id])

  const handleNameSave = async () => {
    await renameCanvas(id, canvasName)
  }

  // Shared loading/error state
  if (isLoading) {
    return (
      <div className='flex items-center justify-center h-full'>
        <Loader2 className='w-4 h-4 animate-spin' />
      </div>
    )
  }

  if (error) {
    return (
      <div className='flex flex-col items-center justify-center h-full gap-4 p-4'>
        <p className='text-red-500 text-sm text-center'>Erreur de chargement du canevas</p>
        <button 
          className='px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg'
          onClick={() => window.location.reload()}
        >
          Recharger
        </button>
      </div>
    )
  }

  // Mobile layout
  if (isMobile) {
    return (
      <div className='flex flex-col w-full h-full'>
        <CanvasHeader
          canvasName={canvasName}
          canvasId={id}
          onNameChange={setCanvasName}
          onNameSave={handleNameSave}
        />
        {/* Tab bar */}
        <div className='flex border-b border-border bg-background sticky top-0 z-10'>
          <button
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'canvas'
                ? 'border-b-2 border-primary text-foreground'
                : 'text-muted-foreground'
            }`}
            onClick={() => setActiveTab('canvas')}
          >
            🎨 Canvas
          </button>
          <button
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'chat'
                ? 'border-b-2 border-primary text-foreground'
                : 'text-muted-foreground'
            }`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Chat
          </button>
        </div>
        <div className='flex-1 relative overflow-hidden'>
          {activeTab === 'canvas' ? (
            <div className='w-full h-full relative'>
              <CanvasExcali canvasId={id} initialData={canvas?.data} />
              <CanvasPopbarWrapper />
            </div>
          ) : (
            <div className='w-full h-full overflow-y-auto bg-background'>
              <ChatInterface
                canvasId={id}
                sessionList={sessionList}
                setSessionList={setSessionList}
                sessionId={searchSessionId}
              />
            </div>
          )}
        </div>
      </div>
    )
  }

  // Desktop layout
  return (
    <div className='flex flex-col w-full h-screen'>
      <CanvasHeader
        canvasName={canvasName}
        canvasId={id}
        onNameChange={setCanvasName}
        onNameSave={handleNameSave}
      />
      <ResizablePanelGroup
        direction='horizontal'
        className='w-full flex-1'
        autoSaveId='jaaz-chat-panel'
      >
        <ResizablePanel defaultSize={75}>
          <div className='relative w-full h-full'>
            <CanvasExcali canvasId={id} initialData={canvas?.data} />
            <CanvasMenu />
            <CanvasPopbarWrapper />
          </div>
        </ResizablePanel>

        <ResizableHandle />

        <ResizablePanel defaultSize={25}>
          <div className='flex-1 flex-grow bg-accent/50 w-full h-full overflow-y-auto'>
            <ChatInterface
              canvasId={id}
              sessionList={sessionList}
              setSessionList={setSessionList}
              sessionId={searchSessionId}
            />
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}

function Canvas() {
  return (
    <CanvasProvider>
      <CanvasContent />
    </CanvasProvider>
  )
}