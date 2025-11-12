'use client'

import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Database, MoreHorizontal, Webhook, Mail, Target } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface TargetNodeData {
  label: string
  type: string
  description?: string
  config?: any
}

export const TargetNode = memo(({ data, selected }: NodeProps<TargetNodeData>) => {
  const getIcon = () => {
    switch (data.type) {
      case 'infiplex': return <Database className="h-4 w-4 text-red-600" />
      case 'webhook': return <Webhook className="h-4 w-4 text-red-600" />
      case 'email': return <Mail className="h-4 w-4 text-red-600" />
      default: return <Target className="h-4 w-4 text-red-600" />
    }
  }

  return (
    <div className={`bg-white border-2 rounded-lg shadow-sm min-w-[200px] ${
      selected ? 'border-red-500 shadow-md' : 'border-gray-200'
    }`}>
      {/* Node Header */}
      <div className="bg-red-50 border-b border-red-100 p-3 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="bg-red-100 p-1.5 rounded-md">
              {getIcon()}
            </div>
            <div>
              <h3 className="font-medium text-sm text-gray-900">{data.label}</h3>
              <Badge variant="outline" className="text-xs bg-red-50 border-red-200 text-red-700">
                Target
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
          
          {data.config?.operation && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Operation:</span>
              <span className="font-medium">{data.config.operation}</span>
            </div>
          )}

          {data.config?.url && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">URL:</span>
              <span className="font-medium text-xs truncate max-w-[100px]">
                {data.config.url}
              </span>
            </div>
          )}

          {data.config?.warehouseId && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Warehouse:</span>
              <span className="font-medium">{data.config.warehouseId}</span>
            </div>
          )}
        </div>
      </div>

      {/* Input Handle */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className="!w-3 !h-3 !border-2 !border-red-400 !bg-red-100"
      />
      
      {/* Status Indicator */}
      <div className="absolute -top-1 -right-1">
        <div className="w-3 h-3 bg-green-400 border-2 border-white rounded-full"></div>
      </div>
    </div>
  )
}) 