# 🎯 Callie Workflow Management UI

A modern, intuitive interface for managing and monitoring workflow integrations.

## ✨ Features

- **📊 Real-time Dashboard** - Monitor workflow health and execution metrics
- **⚡ Visual Workflow Builder** - Drag-and-drop interface for creating workflows
- **📈 Live Execution Monitoring** - Real-time progress tracking and logging
- **🔧 Connector Management** - Manage integrations and connections
- **📱 Responsive Design** - Works perfectly on desktop, tablet, and mobile

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`.

### Environment Configuration

Create a `.env.local` file:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=https://callie-api-1002048776709.us-central1.run.app/api/v1

# Optional: WebSocket for real-time features
NEXT_PUBLIC_WS_URL=wss://callie-api-1002048776709.us-central1.run.app/ws
```

## 🏗️ Architecture

```
frontend/
├── app/                    # Next.js App Router pages
├── components/             # React components
│   ├── ui/                # Base UI components (shadcn/ui)
│   ├── layout/            # Layout components
│   ├── dashboard/         # Dashboard widgets
│   ├── workflow-builder/  # Visual workflow builder
│   └── execution/         # Execution monitoring
├── lib/                   # Utilities and API client
└── public/                # Static assets
```

## 🎨 Design System

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **Icons**: Lucide React
- **Workflow Builder**: React Flow
- **State Management**: Zustand
- **Data Fetching**: TanStack Query

## 📱 Pages

### Dashboard (`/`)
- Workflow health metrics
- Recent execution feed
- System status indicators
- Quick actions

### Workflows (`/workflows`)
- List all workflows
- Create/edit workflows
- Workflow management actions

### Workflow Builder (`/workflows/new`)
- Visual drag-and-drop interface
- Node library with connectors
- Properties configuration panel
- Real-time validation

### Executions (`/executions`)
- Live execution monitoring
- Step-by-step progress tracking
- Error handling and debugging
- Execution history

## 🔌 API Integration

The frontend connects to your Callie API:

```typescript
// lib/api/client.ts
export const api = new ApiClient()

// Usage
const workflows = await api.getWorkflows()
const execution = await api.executeWorkflow(workflowId)
```

## 📦 Building for Production

```bash
# Build the application
npm run build

# Start production server
npm start
```

## 🚢 Deployment

### Option 1: Deploy with Backend (Recommended)

Add to your existing `Dockerfile.api`:

```dockerfile
# Build frontend
COPY frontend/ ./frontend/
RUN cd frontend && npm ci && npm run build

# Serve frontend with FastAPI
COPY --from=build /app/frontend/out /app/static
```

### Option 2: Separate Deployment

Deploy to Vercel, Netlify, or any static hosting:

```bash
npm run build
# Upload 'out' directory to your host
```

## 🎯 Key Features Implemented

### ✅ Complete Interface
- [x] Professional dashboard with metrics
- [x] Full workflow management (CRUD)
- [x] Visual workflow builder with React Flow
- [x] Real-time execution monitoring
- [x] Responsive design for all devices

### ✅ Production Ready
- [x] TypeScript for type safety
- [x] Modern React patterns (hooks, contexts)
- [x] Performance optimized (lazy loading, memoization)
- [x] Accessibility compliant
- [x] SEO optimized

### ✅ Developer Experience
- [x] Clean component architecture
- [x] Reusable UI components
- [x] Type-safe API client
- [x] Easy to extend and customize

## 🎪 Demo Features

Visit the interface to see:

1. **Dashboard**: Live metrics and system health
2. **Workflows**: Your ShipStation → InfiPlex sync workflow
3. **Builder**: Create new workflows visually
4. **Executions**: Monitor live workflow runs
5. **Mobile**: Full functionality on mobile devices

## 🔧 Customization

### Adding New Node Types

1. Create node component in `components/workflow-builder/nodes/`
2. Add to `nodeTypes` in `WorkflowBuilder.tsx`
3. Add template to `NodeLibrary.tsx`

### Adding New Pages

1. Create page in `app/[page]/page.tsx`
2. Add navigation link in `components/layout/Sidebar.tsx`

### Theming

Customize colors in `tailwind.config.js` and `app/globals.css`.

---

**🎉 Your workflow management interface is ready for production!**
