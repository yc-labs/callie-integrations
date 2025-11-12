import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  ArrowLeft,
  Clock, 
  CheckCircle, 
  XCircle,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Copy,
  Download
} from 'lucide-react'
import { ExecutionStageDebugger } from '@/components/execution/ExecutionStageDebugger'
import { useExecution } from '@/lib/hooks/useExecutions'

interface ExecutionDetailPageProps {
  params: Promise<{ id: string }>
}

export default async function ExecutionDetailPage({ params }: ExecutionDetailPageProps) {
  const { id } = await params
  
  return <ExecutionDetailContent executionId={id} />
}

function ExecutionDetailContent({ executionId }: { executionId: string }) {
  // Fetch real execution data from API
  const { execution: apiExecution, loading, error } = useExecution(executionId)

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
        </div>
        <Card className="animate-pulse">
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !apiExecution) {
    return (
      <div className="space-y-6">
        <Link href="/executions">
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Executions
          </Button>
        </Link>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-6">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="h-4 w-4" />
              <span>Failed to load execution: {error || 'Execution not found'}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Transform API data to UI format
  const formatDuration = (seconds?: number) => {
    if (!seconds) return '0s'
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds.toFixed(1)}s`
  }

  const execution = {
    id: apiExecution.id,
    workflowId: apiExecution.workflow_id,
    workflowName: apiExecution.workflow_id.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    status: apiExecution.status === 'completed' ? 'success' as const : apiExecution.status as const,
    startTime: apiExecution.started_at,
    endTime: apiExecution.completed_at,
    duration: apiExecution.execution_time_seconds ? formatDuration(apiExecution.execution_time_seconds) : 'Running...',
    itemsProcessed: apiExecution.final_variables?.items_processed || apiExecution.completed_stages,
    totalItems: apiExecution.final_variables?.total_items || apiExecution.total_stages,
    triggeredBy: apiExecution.triggered_by.charAt(0).toUpperCase() + apiExecution.triggered_by.slice(1),
    stages: apiExecution.stage_results?.length > 0 
      ? apiExecution.stage_results.map((stage, index) => ({
          id: stage.stage_id || `stage-${index}`,
          name: stage.stage_name || 'Unknown Stage',
          status: stage.status || 'pending',
          startTime: stage.started_at || apiExecution.started_at,
          endTime: stage.completed_at,
          duration: stage.execution_time_seconds ? formatDuration(stage.execution_time_seconds) : 'Running...',
          input: stage.input_data || {},
          output: stage.output_data || {},
          error: stage.error_message
        }))
      : [{
          id: 'execution-summary',
          name: 'Workflow Execution',
          status: apiExecution.status === 'completed' ? 'completed' : apiExecution.status,
          startTime: apiExecution.started_at,
          endTime: apiExecution.completed_at,
          duration: apiExecution.execution_time_seconds ? formatDuration(apiExecution.execution_time_seconds) : 'Failed immediately',
          input: { workflow_id: apiExecution.workflow_id },
          output: apiExecution.final_variables || {},
          error: apiExecution.error_message
        }]
  }

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
      case 'success': return 'outline'
      case 'running': return 'secondary'
      case 'failed': return 'destructive'
      case 'pending': return 'secondary'
      default: return 'secondary'
    }
  }

  const getStatusClassName = (status: string) => {
    switch (status) {
      case 'success': return 'bg-green-50 text-green-700 border-green-200'
      case 'running': return ''
      case 'failed': return ''
      case 'pending': return ''
      default: return ''
    }
  }

  const formatTime = (isoString: string) => {
    return new Date(isoString).toLocaleString()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/executions">
            <Button variant="outline" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Executions
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{execution.workflowName}</h1>
            <p className="text-gray-600">Execution ID: {execution.id}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={getStatusColor(execution.status) as any} className={getStatusClassName(execution.status)}>
            {execution.status}
          </Badge>
          <Button variant="outline" size="sm">
            <Download className="mr-1 h-3 w-3" />
            Export Debug Data
          </Button>
        </div>
      </div>

      {/* Execution Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Execution Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-600">Duration</p>
              <p className="text-lg font-semibold">{execution.duration}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Items Processed</p>
              <p className="text-lg font-semibold">{execution.itemsProcessed.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Started</p>
              <p className="text-lg font-semibold">{formatTime(execution.startTime)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Triggered By</p>
              <p className="text-lg font-semibold">{execution.triggeredBy}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stage Details with Debug Info */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-gray-900">Stage Details & Debug Information</h2>
        {execution.stages.map((stage, index) => (
          <ExecutionStageDebugger 
            key={stage.id}
            stage={stage}
            stageNumber={index + 1}
          />
        ))}
      </div>
    </div>
  )
} 