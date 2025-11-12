'use client'

import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { GitBranch, MoreHorizontal, Clock, Zap } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface LogicNodeData {
  label: string
  type: string
  description?: string
  config?: any
}

export const LogicNode = memo(({ data, selected }: NodeProps<LogicNodeData>) => {
  const getIcon = () => {
    switch (data.type) {
      case 'condition': return <GitBranch className="h-4 w-4 text-yellow-600" />
      case 'delay': return <Clock className="h-4 w-4 text-yellow-600" />
      case 'trigger': return <Zap className="h-4 w-4 text-yellow-600" />
      default: return <GitBranch className="h-4 w-4 text-yellow-600" />
    }
  }

  return (
    <div className={`bg-white border-2 rounded-lg shadow-sm min-w-[200px] ${
      selected ? 'border-yellow-500 shadow-md' : 'border-gray-200'
    }`}>
      {/* Node Header */}
      <div className="bg-yellow-50 border-b border-yellow-100 p-3 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="bg-yellow-100 p-1.5 rounded-md">
              {getIcon()}
            </div>
            <div>
              <h3 className="font-medium text-sm text-gray-900">{data.label}</h3>
              <Badge variant="outline" className="text-xs bg-yellow-50 border-yellow-200 text-yellow-700">
                Logic
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
          
          {data.config?.condition && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Condition:</span>
              <span className="font-medium text-xs truncate max-w-[100px]">
                {data.config.condition}
              </span>
            </div>
          )}

          {data.config?.delay && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Delay:</span>
              <span className="font-medium">{data.config.delay}s</span>
            </div>
          )}
        </div>
      </div>

      {/* Input Handle */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className="!w-3 !h-3 !border-2 !border-yellow-400 !bg-yellow-100"
      />

      {/* Output Handles for branching */}
      <Handle 
        type="source" 
        position={Position.Right} 
        id="true"
        className="!w-3 !h-3 !border-2 !border-yellow-400 !bg-yellow-100"
        style={{ top: '45%' }}
      />
      
      {data.type === 'condition' && (
        <Handle 
          type="source" 
          position={Position.Right} 
          id="false"
          className="!w-3 !h-3 !border-2 !border-yellow-400 !bg-yellow-100"
          style={{ top: '65%' }}
        />
      )}
      
      {/* Status Indicator */}
      <div className="absolute -top-1 -right-1">
        <div className="w-3 h-3 bg-green-400 border-2 border-white rounded-full"></div>
      </div>

      {/* Branch Labels for condition nodes */}
      {data.type === 'condition' && (
        <div className="absolute -right-8 text-xs text-gray-500">
          <div style={{ top: '40%' }} className="absolute">✓</div>
          <div style={{ top: '60%' }} className="absolute">✗</div>
        </div>
      )}
    </div>
  )
}) 