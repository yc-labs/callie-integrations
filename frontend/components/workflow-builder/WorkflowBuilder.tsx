'use client'

import { useState, useCallback } from 'react'
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  Panel,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { NodeLibrary } from './NodeLibrary'
import { PropertiesPanel } from './PropertiesPanel'
import { WorkflowToolbar } from './WorkflowToolbar'
import { SourceNode } from './nodes/SourceNode'
import { TransformNode } from './nodes/TransformNode'
import { TargetNode } from './nodes/TargetNode'
import { LogicNode } from './nodes/LogicNode'

const nodeTypes = {
  source: SourceNode,
  transform: TransformNode,
  target: TargetNode,
  logic: LogicNode,
}

const initialNodes: Node[] = [
  {
    id: '1',
    type: 'source',
    position: { x: 100, y: 100 },
    data: { 
      label: 'ShipStation',
      type: 'shipstation',
      config: {},
      description: 'Read inventory data from ShipStation'
    },
  },
]

const initialEdges: Edge[] = []

export function WorkflowBuilder() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [isLibraryOpen, setIsLibraryOpen] = useState(true)
  const [isPropertiesOpen, setIsPropertiesOpen] = useState(true)

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node)
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
  }, [])

  const addNode = useCallback((nodeType: string, nodeData: any) => {
    const newNode: Node = {
      id: `${nodes.length + 1}`,
      type: nodeType,
      position: { x: Math.random() * 400 + 200, y: Math.random() * 400 + 200 },
      data: nodeData,
    }
    setNodes((nds) => [...nds, newNode])
  }, [nodes.length, setNodes])

  const updateNodeConfig = useCallback((nodeId: string, config: any) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, config } } : node
      )
    )
  }, [setNodes])

  return (
    <div className="flex h-screen">
      {/* Node Library Sidebar */}
      {isLibraryOpen && (
        <div className="w-80 border-r bg-white flex-shrink-0">
          <NodeLibrary 
            onAddNode={addNode}
            onToggle={() => setIsLibraryOpen(false)}
          />
        </div>
      )}

      {/* Main Canvas */}
      <div className="flex-1 relative">
        <WorkflowToolbar 
          onToggleLibrary={() => setIsLibraryOpen(!isLibraryOpen)}
          onToggleProperties={() => setIsPropertiesOpen(!isPropertiesOpen)}
          isLibraryOpen={isLibraryOpen}
          isPropertiesOpen={isPropertiesOpen}
        />
        
        <div className="h-full">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            className="bg-gray-50"
          >
            <Controls />
            <MiniMap 
              className="bg-white border"
              nodeColor={(node) => {
                switch (node.type) {
                  case 'source': return '#3b82f6'
                  case 'transform': return '#10b981'
                  case 'target': return '#ef4444'
                  case 'logic': return '#f59e0b'
                  default: return '#6b7280'
                }
              }}
            />
            <Background variant={'dots' as any} gap={12} size={1} />
            
            <Panel position="top-center" className="bg-white p-2 rounded-lg shadow-sm">
              <div className="text-sm text-gray-600">
                Drag nodes from the library to build your workflow
              </div>
            </Panel>
          </ReactFlow>
        </div>
      </div>

      {/* Properties Panel */}
      {isPropertiesOpen && (
        <div className="w-80 border-l bg-white flex-shrink-0">
          <PropertiesPanel 
            selectedNode={selectedNode}
            onConfigChange={updateNodeConfig}
            onToggle={() => setIsPropertiesOpen(false)}
          />
        </div>
      )}
    </div>
  )
} 