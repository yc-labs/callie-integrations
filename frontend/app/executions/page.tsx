import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Play,
  Clock,
  CheckCircle,
  XCircle,
  Search,
  Filter,
  RotateCcw,
  Eye,
  AlertCircle
} from 'lucide-react'
import { useExecutions } from '@/lib/hooks/useExecutions'

export default function ExecutionsPage() {
  // Fetch real execution data from API
  const { executions: apiExecutions, loading, error, refetch } = useExecutions(50)

  // Transform API data to UI format
  const executions = apiExecutions.map(execution => {
    const progress = execution.total_stages > 0 
      ? Math.round((execution.completed_stages / execution.total_stages) * 100)
      : 0

    const formatDuration = (seconds?: number) => {
      if (!seconds) return '0s'
      if (seconds < 60) return `${seconds.toFixed(1)}s`
      const minutes = Math.floor(seconds / 60)
      const remainingSeconds = seconds % 60
      return `${minutes}m ${remainingSeconds.toFixed(1)}s`
    }

    // Convert stage results to UI format
    const steps = execution.stage_results?.length > 0 
      ? execution.stage_results.map(stage => ({
          name: stage.stage_name || 'Unknown Stage',
          status: stage.status || 'pending',
          duration: stage.execution_time_seconds ? formatDuration(stage.execution_time_seconds) : null,
          error: stage.error_message
        }))
      : [{
          name: 'Workflow Execution',
          status: execution.status === 'completed' ? 'completed' : execution.status,
          duration: execution.execution_time_seconds ? formatDuration(execution.execution_time_seconds) : null,
          error: execution.error_message
        }]

    return {
      id: execution.id,
      workflowId: execution.workflow_id,
      workflowName: execution.workflow_id.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      status: execution.status === 'completed' ? 'success' as const : execution.status as const,
      startTime: execution.started_at,
      duration: execution.execution_time_seconds ? formatDuration(execution.execution_time_seconds) : 'Running...',
      itemsProcessed: execution.final_variables?.items_processed || execution.completed_stages,
      totalItems: execution.final_variables?.total_items || execution.total_stages,
      progress,
      triggeredBy: execution.triggered_by.charAt(0).toUpperCase() + execution.triggered_by.slice(1),
      steps,
      error: execution.error_message
    }
  })

  // Statistics for UI display
  const stats = {
    all: executions.length,
    running: executions.filter(e => e.status === 'running').length,
    success: executions.filter(e => e.status === 'success' || e.status === 'completed').length,
    failed: executions.filter(e => e.status === 'failed').length
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'running': return <Clock className="h-4 w-4 text-blue-500 animate-spin" />
      case 'failed': return <XCircle className="h-4 w-4 text-red-500" />
      case 'pending': return <Clock className="h-4 w-4 text-gray-400" />
      default: return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'success'
      case 'running': return 'secondary'
      case 'failed': return 'destructive'
      case 'pending': return 'secondary'
      default: return 'secondary'
    }
  }

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-3 w-3 text-green-500" />
      case 'running': return <Clock className="h-3 w-3 text-blue-500 animate-spin" />
      case 'failed': return <XCircle className="h-3 w-3 text-red-500" />
      case 'pending': return <Clock className="h-3 w-3 text-gray-400" />
      default: return <Clock className="h-3 w-3 text-gray-400" />
    }
  }

  const formatTime = (isoString: string) => {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  return (
    <div className="space-y-6">
              <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Executions</h1>
            <p className="text-gray-600">Monitor workflow executions and performance</p>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm">
              <Filter className="mr-1 h-3 w-3" />
              Filter
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={refetch}
              disabled={loading}
            >
              <RotateCcw className={`mr-1 h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

      <div className="flex items-center space-x-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search executions..."
            className="pl-9"
          />
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline">All: {stats.all}</Badge>
          <Badge variant="secondary">Running: {stats.running}</Badge>
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Success: {stats.success}</Badge>
          <Badge variant="destructive">Failed: {stats.failed}</Badge>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="h-4 w-4" />
              <span>Failed to load executions: {error}</span>
              <Button variant="outline" size="sm" onClick={refetch}>
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {loading && !error && (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-48"></div>
                    <div className="h-3 bg-gray-200 rounded w-32"></div>
                  </div>
                  <div className="h-6 bg-gray-200 rounded w-16"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Executions List */}
      {!loading && !error && (
        <div className="grid grid-cols-1 gap-6">
        {executions.map((execution) => (
          <Card key={execution.id} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(execution.status)}
                  <div>
                    <CardTitle className="text-lg">{execution.workflowName}</CardTitle>
                    <p className="text-sm text-gray-600">
                      Execution ID: {execution.id} • Started {formatTime(execution.startTime)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant={getStatusColor(execution.status) as any}>
                    {execution.status}
                  </Badge>
                  <span className="text-sm text-gray-500">{execution.duration}</span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div>
                  <p className="text-sm text-gray-600">Progress</p>
                  <div className="flex items-center space-x-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-500 h-2 rounded-full transition-all"
                        style={{ width: `${execution.progress}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium">{execution.progress}%</span>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Items Processed</p>
                  <p className="text-lg font-semibold">
                    {execution.itemsProcessed.toLocaleString()} / {execution.totalItems.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Triggered By</p>
                  <p className="text-lg font-semibold">{execution.triggeredBy}</p>
                </div>
              </div>

              {execution.error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    <span className="text-sm font-medium text-red-800">Error</span>
                  </div>
                  <p className="text-sm text-red-700 mt-1">{execution.error}</p>
                </div>
              )}

              <div className="space-y-2 mb-4">
                <h4 className="font-medium text-sm">Execution Steps</h4>
                {execution.steps.map((step, index) => (
                  <div key={index} className="flex items-center justify-between p-2 border rounded-lg">
                    <div className="flex items-center space-x-2">
                      {getStepIcon(step.status)}
                      <span className="text-sm font-medium">{step.name}</span>
                      {(step as any).error && (
                        <Badge variant="destructive" className="text-xs">
                          Error
                        </Badge>
                      )}
                    </div>
                    <div className="text-right">
                      {step.duration && (
                        <span className="text-sm text-gray-600">{step.duration}</span>
                      )}
                      {(step as any).error && (
                        <p className="text-xs text-red-600">{(step as any).error}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  Workflow: {execution.workflowId}
                </div>
                <div className="flex items-center space-x-2">
                  {execution.status === 'failed' && (
                    <Button variant="outline" size="sm">
                      <RotateCcw className="mr-1 h-3 w-3" />
                      Retry
                    </Button>
                  )}
                  <Link href={`/executions/${execution.id}`}>
                    <Button variant="outline" size="sm">
                      <Eye className="mr-1 h-3 w-3" />
                      Debug Details
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && executions.length === 0 && (
        <Card>
          <CardContent className="p-8 text-center">
            <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No executions found</h3>
            <p className="text-gray-600">No workflow executions have been run yet.</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 