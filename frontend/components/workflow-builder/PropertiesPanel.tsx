'use client'

import { useState } from 'react'
import { Node } from 'reactflow'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { X, Settings, Database, ArrowRight, GitBranch, Target } from 'lucide-react'

interface PropertiesPanelProps {
  selectedNode: Node | null
  onConfigChange: (nodeId: string, config: any) => void
  onToggle: () => void
}

export function PropertiesPanel({ selectedNode, onConfigChange, onToggle }: PropertiesPanelProps) {
  const [config, setConfig] = useState(selectedNode?.data?.config || {})

  const handleConfigUpdate = (key: string, value: any) => {
    const newConfig = { ...config, [key]: value }
    setConfig(newConfig)
    if (selectedNode) {
      onConfigChange(selectedNode.id, newConfig)
    }
  }

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'source': return <Database className="h-4 w-4" />
      case 'transform': return <ArrowRight className="h-4 w-4" />
      case 'target': return <Target className="h-4 w-4" />
      case 'logic': return <GitBranch className="h-4 w-4" />
      default: return <Settings className="h-4 w-4" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'source': return 'bg-blue-100 text-blue-800'
      case 'transform': return 'bg-green-100 text-green-800'
      case 'target': return 'bg-red-100 text-red-800'
      case 'logic': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (!selectedNode) {
    return (
      <div className="h-full flex flex-col">
        <div className="p-4 border-b bg-gray-50">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Properties</h3>
            <Button variant="ghost" size="sm" onClick={onToggle}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <Settings className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Select a node to configure</p>
          </div>
        </div>
      </div>
    )
  }

  const renderConfigFields = () => {
    const nodeType = selectedNode.data?.type

    switch (nodeType) {
      case 'shipstation':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="endpoint">Endpoint</Label>
              <Input
                id="endpoint"
                value={config.endpoint || ''}
                onChange={(e) => handleConfigUpdate('endpoint', e.target.value)}
                placeholder="e.g., inventory"
              />
            </div>
            <div>
              <Label htmlFor="warehouse">Warehouse ID</Label>
              <Input
                id="warehouse"
                value={config.warehouseId || ''}
                onChange={(e) => handleConfigUpdate('warehouseId', e.target.value)}
                placeholder="Optional warehouse filter"
              />
            </div>
          </div>
        )

      case 'infiplex':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="operation">Operation</Label>
              <select
                id="operation"
                value={config.operation || 'read'}
                onChange={(e) => handleConfigUpdate('operation', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="read">Read</option>
                <option value="update">Update</option>
                <option value="create">Create</option>
              </select>
            </div>
            <div>
              <Label htmlFor="warehouse">Warehouse ID</Label>
              <Input
                id="warehouse"
                value={config.warehouseId || '17'}
                onChange={(e) => handleConfigUpdate('warehouseId', e.target.value)}
                placeholder="Warehouse ID"
              />
            </div>
          </div>
        )

      case 'field-mapper':
        return (
          <div className="space-y-4">
            <div>
              <Label>Field Mappings</Label>
              <div className="space-y-2 mt-2">
                {(config.mappings || []).map((mapping: any, index: number) => (
                  <div key={index} className="flex space-x-2">
                    <Input
                      placeholder="Source field"
                      value={mapping.source || ''}
                      onChange={(e) => {
                        const newMappings = [...(config.mappings || [])]
                        newMappings[index] = { ...mapping, source: e.target.value }
                        handleConfigUpdate('mappings', newMappings)
                      }}
                    />
                    <ArrowRight className="h-8 w-8 text-gray-400" />
                    <Input
                      placeholder="Target field"
                      value={mapping.target || ''}
                      onChange={(e) => {
                        const newMappings = [...(config.mappings || [])]
                        newMappings[index] = { ...mapping, target: e.target.value }
                        handleConfigUpdate('mappings', newMappings)
                      }}
                    />
                  </div>
                ))}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const newMappings = [...(config.mappings || []), { source: '', target: '' }]
                    handleConfigUpdate('mappings', newMappings)
                  }}
                >
                  Add Mapping
                </Button>
              </div>
            </div>
          </div>
        )

      case 'webhook':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="url">Webhook URL</Label>
              <Input
                id="url"
                value={config.url || ''}
                onChange={(e) => handleConfigUpdate('url', e.target.value)}
                placeholder="https://example.com/webhook"
              />
            </div>
            <div>
              <Label htmlFor="method">HTTP Method</Label>
              <select
                id="method"
                value={config.method || 'POST'}
                onChange={(e) => handleConfigUpdate('method', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="PATCH">PATCH</option>
              </select>
            </div>
          </div>
        )

      default:
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="custom-config">Configuration</Label>
              <Textarea
                id="custom-config"
                value={JSON.stringify(config, null, 2)}
                onChange={(e) => {
                  try {
                    const newConfig = JSON.parse(e.target.value)
                    setConfig(newConfig)
                  } catch (error) {
                    // Invalid JSON, ignore
                  }
                }}
                rows={8}
                placeholder="Enter JSON configuration..."
              />
            </div>
          </div>
        )
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b bg-gray-50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">Properties</h3>
          <Button variant="ghost" size="sm" onClick={onToggle}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-md ${getTypeColor(selectedNode.type || 'default')}`}>
            {getNodeIcon(selectedNode.type || 'default')}
          </div>
          <div>
            <h4 className="font-medium">{selectedNode.data?.label}</h4>
            <Badge variant="outline" className="text-xs">
              {selectedNode.type}
            </Badge>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Basic Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="label">Display Name</Label>
                <Input
                  id="label"
                  value={selectedNode.data?.label || ''}
                  onChange={(e) => handleConfigUpdate('label', e.target.value)}
                  placeholder="Node display name"
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={selectedNode.data?.description || ''}
                  onChange={(e) => handleConfigUpdate('description', e.target.value)}
                  placeholder="Optional description"
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              {renderConfigFields()}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Testing</CardTitle>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" className="w-full">
                Test Node
              </Button>
              <p className="text-xs text-gray-600 mt-2">
                Test this node with sample data
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
} 