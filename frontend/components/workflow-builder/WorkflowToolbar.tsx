'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { 
  Save, 
  Play, 
  Undo, 
  Redo, 
  PanelLeftOpen,
  PanelLeftClose,
  PanelRightOpen,
  PanelRightClose,
  Zap
} from 'lucide-react'

interface WorkflowToolbarProps {
  onToggleLibrary: () => void
  onToggleProperties: () => void
  isLibraryOpen: boolean
  isPropertiesOpen: boolean
}

export function WorkflowToolbar({ 
  onToggleLibrary, 
  onToggleProperties, 
  isLibraryOpen, 
  isPropertiesOpen 
}: WorkflowToolbarProps) {
  return (
    <div className="absolute top-0 left-0 right-0 z-10 bg-white border-b p-3 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <Button
          variant="outline"
          size="sm"
          onClick={onToggleLibrary}
        >
          {isLibraryOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
        </Button>
        
        <div className="flex items-center space-x-2">
          <Input 
            placeholder="Workflow Name" 
            className="w-48"
            defaultValue="New Workflow"
          />
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Button variant="outline" size="sm">
          <Undo className="mr-1 h-3 w-3" />
          Undo
        </Button>
        <Button variant="outline" size="sm">
          <Redo className="mr-1 h-3 w-3" />
          Redo
        </Button>
        <Button variant="outline" size="sm">
          <Zap className="mr-1 h-3 w-3" />
          Test
        </Button>
        <Button variant="outline" size="sm">
          <Play className="mr-1 h-3 w-3" />
          Run
        </Button>
        <Button size="sm">
          <Save className="mr-1 h-3 w-3" />
          Save
        </Button>
        
        <Button
          variant="outline"
          size="sm"
          onClick={onToggleProperties}
        >
          {isPropertiesOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  )
} 