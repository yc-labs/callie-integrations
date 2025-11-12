import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Activity, Clock, CheckCircle, XCircle, Play, TrendingUp } from 'lucide-react'

export default function DashboardPage() {
  // Mock data - will be replaced with real API calls
  const workflowHealth = {
    totalWorkflows: 3,
    activeWorkflows: 2,
    successRate: 95.8,
    avgExecutionTime: 12.5
  }

  const recentExecutions = [
    {
      id: '1',
      workflowName: 'ShipStation → InfiPlex Sync',
      status: 'success' as const,
      startTime: '2 min ago',
      duration: '8.2s',
      itemsProcessed: 160
    },
    {
      id: '2', 
      workflowName: 'Inventory Health Check',
      status: 'running' as const,
      startTime: '5 min ago',
      duration: '15.1s',
      itemsProcessed: 450
    },
    {
      id: '3',
      workflowName: 'Order Status Update',
      status: 'failed' as const,
      startTime: '12 min ago',
      duration: '2.8s',
      itemsProcessed: 0
    }
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'running': return <Clock className="h-4 w-4 text-blue-500" />
      case 'failed': return <XCircle className="h-4 w-4 text-red-500" />
      default: return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'success'
      case 'running': return 'secondary'
      case 'failed': return 'destructive'
      default: return 'secondary'
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Monitor your workflows and system health</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Workflows</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{workflowHealth.totalWorkflows}</div>
            <p className="text-xs text-muted-foreground">
              {workflowHealth.activeWorkflows} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{workflowHealth.successRate}%</div>
            <p className="text-xs text-muted-foreground">
              Last 24 hours
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Execution Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{workflowHealth.avgExecutionTime}s</div>
            <p className="text-xs text-muted-foreground">
              Per workflow run
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Quick Actions</CardTitle>
            <Play className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Button size="sm" className="w-full">
              Run Sync Now
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Executions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentExecutions.map((execution) => (
                <div key={execution.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(execution.status)}
                    <div>
                      <p className="font-medium">{execution.workflowName}</p>
                      <p className="text-sm text-gray-500">
                        Started {execution.startTime} • {execution.duration}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant={getStatusColor(execution.status) as any}>
                      {execution.status}
                    </Badge>
                    <p className="text-xs text-gray-500 mt-1">
                      {execution.itemsProcessed} items
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">API Server</span>
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Online</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">ShipStation Connector</span>
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Connected</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">InfiPlex Connector</span>
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Connected</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Scheduler</span>
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Running</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
