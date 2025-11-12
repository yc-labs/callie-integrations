'use client'

import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Database, MoreHorizontal } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface SourceNodeData {
  label: string
  type: string
  description?: string
  config?: any
}

export const SourceNode = memo(({ data, selected }: NodeProps<SourceNodeData>) => {
  return (
    <div className={`bg-white border-2 rounded-lg shadow-sm min-w-[200px] ${
      selected ? 'border-blue-500 shadow-md' : 'border-gray-200'
    }`}>
      {/* Node Header */}
      <div className="bg-blue-50 border-b border-blue-100 p-3 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="bg-blue-100 p-1.5 rounded-md">
              <Database className="h-4 w-4 text-blue-600" />
            </div>
            <div>
              <h3 className="font-medium text-sm text-gray-900">{data.label}</h3>
              <Badge variant="outline" className="text-xs bg-blue-50 border-blue-200 text-blue-700">
                Source
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
          
          {data.config?.endpoint && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Endpoint:</span>
              <span className="font-medium">{data.config.endpoint}</span>
            </div>
          )}
        </div>
      </div>

      {/* Output Handle */}
      <Handle 
        type="source" 
        position={Position.Right} 
        className="!w-3 !h-3 !border-2 !border-blue-400 !bg-blue-100"
      />
      
      {/* Status Indicator */}
      <div className="absolute -top-1 -right-1">
        <div className="w-3 h-3 bg-green-400 border-2 border-white rounded-full"></div>
      </div>
    </div>
  )
}) 