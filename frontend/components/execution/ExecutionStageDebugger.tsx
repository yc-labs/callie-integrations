'use client'

import { useState } from 'react'
import toast from 'react-hot-toast'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Eye,
  EyeOff
} from 'lucide-react'

interface StageData {
  id: string
  name: string
  status: string
  startTime: string
  endTime?: string
  duration: string
  input: any
  output: any
  error?: string
}

interface ExecutionStageDebuggerProps {
  stage: StageData
  stageNumber: number
}

export function ExecutionStageDebugger({ stage, stageNumber }: ExecutionStageDebuggerProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showRawInput, setShowRawInput] = useState(false)
  const [showRawOutput, setShowRawOutput] = useState(false)

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'running': return <Clock className="h-4 w-4 text-blue-500 animate-spin" />
      case 'failed': return <XCircle className="h-4 w-4 text-red-500" />
      case 'pending': return <Clock className="h-4 w-4 text-gray-400" />
      default: return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'outline'
      case 'running': return 'outline'
      case 'failed': return 'destructive'
      case 'pending': return 'secondary'
      default: return 'secondary'
    }
  }

  const getStatusClassName = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-50 text-green-700 border-green-200'
      case 'running': return 'bg-blue-50 text-blue-700 border-blue-200'
      case 'failed': return ''
      case 'pending': return ''
      default: return ''
    }
  }

  const copyToClipboard = (data: any, type: string) => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    toast.success(`${type.charAt(0).toUpperCase() + type.slice(1)} data copied to clipboard!`)
  }

  const downloadData = (data: any, filename: string) => {
    const dataStr = JSON.stringify(data, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
    toast.success(`Debug data downloaded as ${filename}`)
  }

  const formatTime = (isoString: string) => {
    return new Date(isoString).toLocaleTimeString()
  }

  const renderDataPreview = (data: any, maxItems = 3) => {
    if (Array.isArray(data)) {
      return (
        <div className="space-y-1">
          <p className="text-xs text-gray-600">Array ({data.length} items)</p>
          {data.slice(0, maxItems).map((item, index) => (
            <div key={index} className="text-xs bg-gray-50 p-2 rounded border">
              {typeof item === 'object' ? JSON.stringify(item, null, 2) : String(item)}
            </div>
          ))}
          {data.length > maxItems && (
            <p className="text-xs text-gray-500">... and {data.length - maxItems} more items</p>
          )}
        </div>
      )
    } else if (typeof data === 'object' && data !== null) {
      return (
        <div className="space-y-1">
          {Object.entries(data).slice(0, maxItems).map(([key, value]) => (
            <div key={key} className="text-xs">
              <span className="font-medium text-gray-700">{key}:</span>{' '}
              <span className="text-gray-600">
                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
              </span>
            </div>
          ))}
          {Object.keys(data).length > maxItems && (
            <p className="text-xs text-gray-500">... and {Object.keys(data).length - maxItems} more fields</p>
          )}
        </div>
      )
    } else {
      return <p className="text-xs text-gray-600">{String(data)}</p>
    }
  }

  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardHeader className="cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              <span className="font-medium text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">
                Stage {stageNumber}
              </span>
            </div>
            {getStatusIcon(stage.status)}
            <div>
              <CardTitle className="text-lg">{stage.name}</CardTitle>
              <p className="text-sm text-gray-600">
                {formatTime(stage.startTime)} • {stage.duration}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant={getStatusColor(stage.status) as any} className={getStatusClassName(stage.status)}>
              {stage.status}
            </Badge>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-0">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Input Section */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-medium text-green-700 flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Input Data</span>
                </h4>
                <div className="flex items-center space-x-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowRawInput(!showRawInput)}
                  >
                    {showRawInput ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(stage.input, 'input')}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => downloadData(stage.input, `${stage.id}_input.json`)}
                  >
                    <Download className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                {showRawInput ? (
                  <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(stage.input, null, 2)}
                  </pre>
                ) : (
                  renderDataPreview(stage.input)
                )}
              </div>
            </div>

            {/* Output Section */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-medium text-blue-700 flex items-center space-x-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span>Output Data</span>
                </h4>
                <div className="flex items-center space-x-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowRawOutput(!showRawOutput)}
                  >
                    {showRawOutput ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(stage.output, 'output')}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => downloadData(stage.output, `${stage.id}_output.json`)}
                  >
                    <Download className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                {showRawOutput ? (
                  <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(stage.output, null, 2)}
                  </pre>
                ) : (
                  renderDataPreview(stage.output)
                )}
              </div>
            </div>
          </div>

          {/* Error Section */}
          {stage.error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center space-x-2 mb-2">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                <h4 className="font-medium text-red-700">Error Details</h4>
              </div>
              <pre className="text-xs text-red-700 whitespace-pre-wrap">{stage.error}</pre>
            </div>
          )}

          {/* Data Flow Visualization */}
          <div className="mt-4 p-3 bg-gray-50 border rounded-lg">
            <h4 className="font-medium text-gray-700 mb-2">Data Flow Summary</h4>
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span>Input: {typeof stage.input === 'object' ? Object.keys(stage.input).length + ' fields' : 'Simple value'}</span>
              </div>
              <div className="text-gray-400">→</div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                <span>Output: {typeof stage.output === 'object' ? Object.keys(stage.output).length + ' fields' : 'Simple value'}</span>
              </div>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
} 