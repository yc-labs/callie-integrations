'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  Search,
  X,
  Database,
  ArrowRight,
  Filter,
  GitBranch,
  Webhook,
  Mail,
  Cloud
} from 'lucide-react'

interface NodeTemplate {
  id: string
  type: 'source' | 'transform' | 'target' | 'logic'
  name: string
  description: string
  icon: React.ReactNode
  category: string
  config: any
}

interface NodeLibraryProps {
  onAddNode: (type: string, data: any) => void
  onToggle: () => void
}

const nodeTemplates: NodeTemplate[] = [
  // Source Nodes
  {
    id: 'shipstation-read',
    type: 'source',
    name: 'ShipStation Reader',
    description: 'Read inventory data from ShipStation',
    icon: <Database className="h-4 w-4" />,
    category: 'Sources',
    config: { 
      label: 'ShipStation',
      type: 'shipstation',
      endpoint: 'inventory',
      description: 'Read inventory data from ShipStation'
    }
  },
  {
    id: 'infiplex-read',
    type: 'source',
    name: 'InfiPlex Reader',
    description: 'Read data from InfiPlex system',
    icon: <Database className="h-4 w-4" />,
    category: 'Sources',
    config: { 
      label: 'InfiPlex',
      type: 'infiplex',
      endpoint: 'inventory',
      description: 'Read data from InfiPlex system'
    }
  },
  
  // Transform Nodes
  {
    id: 'field-mapper',
    type: 'transform',
    name: 'Field Mapper',
    description: 'Map fields between different data structures',
    icon: <ArrowRight className="h-4 w-4" />,
    category: 'Transforms',
    config: { 
      label: 'Field Mapper',
      type: 'field-mapper',
      mappings: [],
      description: 'Map fields between different data structures'
    }
  },
  {
    id: 'data-filter',
    type: 'transform',
    name: 'Data Filter',
    description: 'Filter data based on conditions',
    icon: <Filter className="h-4 w-4" />,
    category: 'Transforms',
    config: { 
      label: 'Data Filter',
      type: 'filter',
      conditions: [],
      description: 'Filter data based on conditions'
    }
  },
  
  // Target Nodes
  {
    id: 'infiplex-write',
    type: 'target',
    name: 'InfiPlex Writer',
    description: 'Write data to InfiPlex system',
    icon: <Database className="h-4 w-4" />,
    category: 'Targets',
    config: { 
      label: 'InfiPlex',
      type: 'infiplex',
      operation: 'update',
      description: 'Write data to InfiPlex system'
    }
  },
  {
    id: 'webhook',
    type: 'target',
    name: 'Webhook',
    description: 'Send data to external webhook',
    icon: <Webhook className="h-4 w-4" />,
    category: 'Targets',
    config: { 
      label: 'Webhook',
      type: 'webhook',
      url: '',
      description: 'Send data to external webhook'
    }
  },
  {
    id: 'email-notification',
    type: 'target',
    name: 'Email Notification',
    description: 'Send email notifications',
    icon: <Mail className="h-4 w-4" />,
    category: 'Targets',
    config: { 
      label: 'Email',
      type: 'email',
      recipients: [],
      description: 'Send email notifications'
    }
  },
  
  // Logic Nodes
  {
    id: 'condition',
    type: 'logic',
    name: 'Condition',
    description: 'Branch workflow based on conditions',
    icon: <GitBranch className="h-4 w-4" />,
    category: 'Logic',
    config: { 
      label: 'Condition',
      type: 'condition',
      condition: '',
      description: 'Branch workflow based on conditions'
    }
  }
]

export function NodeLibrary({ onAddNode, onToggle }: NodeLibraryProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const categories = Array.from(new Set(nodeTemplates.map(node => node.category)))
  
  const filteredNodes = nodeTemplates.filter(node => {
    const matchesSearch = node.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         node.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = !selectedCategory || node.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'source': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'transform': return 'bg-green-100 text-green-800 border-green-200'
      case 'target': return 'bg-red-100 text-red-800 border-red-200'
      case 'logic': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b bg-gray-50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">Node Library</h3>
          <Button variant="ghost" size="sm" onClick={onToggle}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex flex-wrap gap-1">
          <Button
            variant={selectedCategory === null ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedCategory(null)}
          >
            All
          </Button>
          {categories.map((category) => (
            <Button
              key={category}
              variant={selectedCategory === category ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category)}
            >
              {category}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {filteredNodes.map((node) => (
            <div
              key={node.id}
              className="p-3 border rounded-lg cursor-pointer hover:shadow-md transition-shadow bg-white"
              onClick={() => onAddNode(node.type, node.config)}
            >
              <div className="flex items-start space-x-3">
                <div className={`p-2 rounded-md ${getTypeColor(node.type)}`}>
                  {node.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-medium text-sm text-gray-900">{node.name}</h4>
                    <Badge variant="outline" className="text-xs">
                      {node.type}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-600">{node.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        {filteredNodes.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Cloud className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No nodes found</p>
          </div>
        )}
      </div>
    </div>
  )
} 