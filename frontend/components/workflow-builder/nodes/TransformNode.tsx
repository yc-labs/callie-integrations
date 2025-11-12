'use client'

import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { ArrowRight, MoreHorizontal, Filter, GitMerge } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface TransformNodeData {
  label: string
  type: string
  description?: string
  config?: any
}

export const TransformNode = memo(({ data, selected }: NodeProps<TransformNodeData>) => {
  const getIcon = () => {
    switch (data.type) {
      case 'field-mapper': return <ArrowRight className="h-4 w-4 text-green-600" />
      case 'filter': return <Filter className="h-4 w-4 text-green-600" />
      case 'merge': return <GitMerge className="h-4 w-4 text-green-600" />
      default: return <ArrowRight className="h-4 w-4 text-green-600" />
    }
  }

  return (
    <div className={`bg-white border-2 rounded-lg shadow-sm min-w-[200px] ${
      selected ? 'border-green-500 shadow-md' : 'border-gray-200'
    }`}>
      {/* Node Header */}
      <div className="bg-green-50 border-b border-green-100 p-3 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="bg-green-100 p-1.5 rounded-md">
              {getIcon()}
            </div>
            <div>
              <h3 className="font-medium text-sm text-gray-900">{data.label}</h3>
              <Badge variant="outline" className="text-xs bg-green-50 border-green-200 text-green-700">
                Transform
              </Badge>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
            <MoreHorizontal className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3">
        {data.description && (
          <p className="text-xs text-gray-600 mb-2">{data.description}</p>
        )}
        
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Type:</span>
            <span className="font-medium">{data.type}</span>
          </div>
          
          {data.config?.mappings && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Mappings:</span>
              <span className="font-medium">{data.config.mappings.length}</span>
            </div>
          )}

          {data.config?.conditions && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Conditions:</span>
              <span className="font-medium">{data.config.conditions.length}</span>
            </div>
          )}
        </div>
      </div>

      {/* Input Handle */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className="!w-3 !h-3 !border-2 !border-green-400 !bg-green-100"
      />

      {/* Output Handle */}
      <Handle 
        type="source" 
        position={Position.Right} 
        className="!w-3 !h-3 !border-2 !border-green-400 !bg-green-100"
      />
      
      {/* Status Indicator */}
      <div className="absolute -top-1 -right-1">
        <div className="w-3 h-3 bg-green-400 border-2 border-white rounded-full"></div>
      </div>
    </div>
  )
}) 