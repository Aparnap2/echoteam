import { useState } from "react";
import "./App.css";
import {
  useClones,
  usePendingActions,
  useApproveAction,
  useRejectAction,
  useActionStats,
} from "./lib/hooks";
import { useAuth } from "./lib/auth.tsx";

type View = "dashboard" | "clones" | "actions" | "analytics" | "settings" | "onboarding" | "context";
type CloneType = "calendar" | "email" | "ops" | "research";

// Icons as SVG components
const Icons = {
  Dashboard: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
  ),
  Clones: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" x2="12" y1="22.08" y2="12"/></svg>
  ),
  Actions: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v12"/><path d="m8 11 4 4 4-4"/><path d="M8 5H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-4"/></svg>
  ),
  Analytics: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
  ),
  Settings: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
  ),
  Check: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
  ),
  X: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
  ),
  Calendar: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
  ),
  Email: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
  ),
  Ops: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="8" height="8" x="3" y="3" rx="2"/><rect width="8" height="8" x="13" y="3" rx="2"/><rect width="8" height="8" x="3" y="13" rx="2"/><rect width="8" height="8" x="13" y="13" rx="2"/></svg>
  ),
  Research: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/><path d="M11 8h6"/></svg>
  ),
  Alert: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>
  ),
  Context: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
  ),
  Activity: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
  ),
  Zap: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
  ),
  QuickAction: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
  ),
  Refresh: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/></svg>
  ),
  CheckCircle: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
  ),
};

interface CloneCardProps {
  type: CloneType;
  name: string;
  enabled: boolean;
  description: string;
}

function CloneCard({ type, name, enabled, description }: CloneCardProps) {
  const getIcon = () => {
    switch (type) {
      case "calendar": return Icons.Calendar;
      case "email": return Icons.Email;
      case "ops": return Icons.Ops;
      case "research": return Icons.Research;
      default: return Icons.Clones;
    }
  };
  const Icon = getIcon();

  return (
    <div className={`clone-card ${enabled ? "enabled" : ""}`}>
      <div className="clone-icon-wrapper">
        <Icon />
      </div>
      <div className="clone-content">
        <h3>{name}</h3>
        <p>{description}</p>
      </div>
      <div className="clone-toggle">
        <span className={`status-badge ${enabled ? "active" : "inactive"}`}>
          {enabled ? "Active" : "Inactive"}
        </span>
      </div>
    </div>
  );
}

function StatsCards() {
  const { data: stats, isLoading } = useActionStats();

  if (isLoading || !stats) {
    return (
      <div className="stats-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="stat-card skeleton" />
        ))}
      </div>
    );
  }

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <span className="stat-value">{stats.pending}</span>
        <span className="stat-label">Pending</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.approved}</span>
        <span className="stat-label">Approved</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.executed}</span>
        <span className="stat-label">Executed</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.autoExecuted}</span>
        <span className="stat-label">Auto</span>
      </div>
    </div>
  );
}

function ActionQueue({ compact = false }: { compact?: boolean }) {
  const { data: actions, isLoading } = usePendingActions();
  const approveMutation = useApproveAction();
  const rejectMutation = useRejectAction();

  const handleApprove = async (actionId: string) => {
    await approveMutation.mutateAsync({ id: actionId });
  };

  const handleReject = async (actionId: string) => {
    await rejectMutation.mutateAsync({ id: actionId });
  };

  if (isLoading) {
    return (
      <div className="action-queue">
        <div className="section-header">
          <h2>Action Queue</h2>
        </div>
        <div className="loading">Loading actions...</div>
      </div>
    );
  }

  const pendingActions = actions || [];

  return (
    <div className="action-queue">
      <div className="section-header">
        <h2>Action Queue</h2>
        <span className="badge">{pendingActions.length}</span>
      </div>
      {pendingActions.length === 0 ? (
        <div className="empty-state">
          <p>No pending actions. Your clones are working!</p>
        </div>
      ) : (
        <div className="action-list">
          {pendingActions.slice(0, compact ? 3 : undefined).map((action) => (
            <div key={action.id} className="action-item">
              <div className="action-content">
                <div className="action-header">
                  <span className="action-type">{action.type}</span>
                  <span className="action-clone">{action.cloneType}</span>
                </div>
                <div className="action-meta">
                  <span className="confidence">
                    {Math.round(action.confidence * 100)}% confidence
                  </span>
                </div>
              </div>
              <div className="action-buttons">
                <button
                  className="btn btn-approve"
                  onClick={() => handleApprove(action.id)}
                  disabled={approveMutation.isPending}
                >
                  <Icons.Check />
                </button>
                <button
                  className="btn btn-reject"
                  onClick={() => handleReject(action.id)}
                  disabled={rejectMutation.isPending}
                >
                  <Icons.X />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DashboardView() {
  const { data: clones, isLoading: clonesLoading } = useClones();

  return (
    <div className="view-content">
      <StatsCards />

      {/* Pattern Alerts Section */}
      <section className="section">
        <PatternAlertsPanel />
      </section>

      <section className="section">
        <div className="section-header">
          <h2>Your Clones</h2>
          <span className="badge">{clones?.length || 0}</span>
        </div>
        {clonesLoading ? (
          <div className="loading">Loading clones...</div>
        ) : (
          <div className="clones-grid">
            {(clones || []).map((clone) => (
              <CloneCard
                key={clone.id}
                type={clone.type.toLowerCase() as CloneType}
                name={clone.name}
                enabled={clone.enabled}
                description={
                  clone.type === "CALENDAR"
                    ? "Manages calendar, blocks focus time"
                    : clone.type === "EMAIL"
                    ? "Reads, drafts, and sends emails"
                    : clone.type === "OPS"
                    ? "Manages tasks and workflows"
                    : clone.type === "RESEARCH"
                    ? "Researches topics and detects patterns"
                    : "EchoTeam clone"
                }
              />
            ))}
          </div>
        )}
      </section>

      <div className="dashboard-grid">
        <div className="dashboard-left">
          <ActionQueue compact />
        </div>
        <div className="dashboard-right">
          <QuickActions />
          <ActivityLog />
        </div>
      </div>
    </div>
  );
}

function ClonesView() {
  const { data: clones, isLoading: clonesLoading } = useClones();
  const { data: stats } = useActionStats();

  const getCloneDescription = (type: string) => {
    switch (type) {
      case "CALENDAR":
        return "Manages your calendar, blocks focus time, detects conflicts";
      case "EMAIL":
        return "Summarizes inbox, drafts replies, categorizes emails";
      case "OPS":
        return "Creates tasks, prioritizes work, manages projects";
      case "RESEARCH":
        return "Web scans, competitor updates, trend summaries, pattern alerts";
      default:
        return "AI-powered clone";
    }
  };

  return (
    <div className="view-content">
      <div className="view-header">
        <h1>Clone Management</h1>
        <p>Manage your AI clones and their configurations</p>
      </div>

      <div className="analytics-grid">
        <div className="analytics-card">
          <h3>Total Actions</h3>
          <span className="analytics-value">
            {(stats?.approved || 0) + (stats?.executed || 0)}
          </span>
        </div>
        <div className="analytics-card">
          <h3>Active Clones</h3>
          <span className="analytics-value">
            {clones?.filter((c) => c.enabled).length || 0}
          </span>
        </div>
        <div className="analytics-card">
          <h3>Automation Rate</h3>
          <span className="analytics-value">
            {stats?.executed
              ? Math.round(
                  (stats.autoExecuted / (stats.executed + stats.approved)) * 100
                )
              : 0}
            %
          </span>
        </div>
      </div>

      <section className="section">
        <h2>All Clones</h2>
        {clonesLoading ? (
          <div className="loading">Loading...</div>
        ) : (
          <div className="clones-list">
            {(clones || []).map((clone) => (
              <CloneCard
                key={clone.id}
                type={clone.type.toLowerCase() as CloneType}
                name={clone.name}
                enabled={clone.enabled}
                description={getCloneDescription(clone.type)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Clone Activity Log */}
      <section className="section">
        <ActivityLog />
      </section>
    </div>
  );
}

function ActionsView() {
  return (
    <div className="view-content">
      <div className="view-header">
        <h1>Action Queue</h1>
        <p>Review and approve actions generated by your clones</p>
      </div>
      <ActionQueue />
    </div>
  );
}

function AnalyticsView() {
  const { data: stats, isLoading } = useActionStats();

  return (
    <div className="view-content">
      <div className="view-header">
        <h1>Analytics</h1>
        <p>Overview of your clone workforce performance</p>
      </div>

      {isLoading ? (
        <div className="loading">Loading analytics...</div>
      ) : (
        <>
          <div className="analytics-grid">
            <div className="analytics-card primary">
              <h3>Total Processed</h3>
              <span className="analytics-value">
                {(stats?.approved || 0) +
                  (stats?.executed || 0) +
                  (stats?.pending || 0)}
              </span>
            </div>
            <div className="analytics-card">
              <h3>Pending Review</h3>
              <span className="analytics-value">{stats?.pending || 0}</span>
            </div>
            <div className="analytics-card">
              <h3>Approved</h3>
              <span className="analytics-value">{stats?.approved || 0}</span>
            </div>
            <div className="analytics-card">
              <h3>Auto-Executed</h3>
              <span className="analytics-value">{stats?.autoExecuted || 0}</span>
            </div>
          </div>

          <section className="section">
            <h2>Performance Metrics</h2>
            <div className="metrics-list">
              <div className="metric-row">
                <span>Approval Rate</span>
                <div className="metric-bar">
                  <div
                    className="metric-fill"
                    style={{
                      width: `${stats?.approved
                        ? (stats.approved /
                            (stats.approved + stats.executed)) *
                          100
                        : 0}%`,
                    }}
                  />
                </div>
                <span className="metric-value">
                  {stats?.approved
                    ? Math.round(
                        (stats.approved /
                          (stats.approved + stats.executed)) *
                          100
                      )
                    : 0}
                  %
                </span>
              </div>
              <div className="metric-row">
                <span>Automation Rate</span>
                <div className="metric-bar">
                  <div
                    className="metric-fill success"
                    style={{
                      width: `${
                        stats?.autoExecuted
                          ? (stats.autoExecuted / stats.executed) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
                <span className="metric-value">
                  {stats?.autoExecuted && stats?.executed
                    ? Math.round(
                        (stats.autoExecuted / stats.executed) * 100
                      )
                    : 0}
                  %
                </span>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

// ============================================================================
// New Components for PRD Features
// ============================================================================

interface PatternAlert {
  id: string;
  type: "opportunity" | "risk" | "pattern" | "insight";
  title: string;
  description: string;
  clone: CloneType;
  timestamp: string;
  read: boolean;
}

function PatternAlertsPanel() {
  // Mock alerts - in real app, these come from Research Clone
  const [alerts, setAlerts] = useState<PatternAlert[]>([
    {
      id: "1",
      type: "pattern",
      title: "Email Response Time Improving",
      description: "Your response time decreased by 23% this week compared to last month.",
      clone: "email",
      timestamp: new Date().toISOString(),
      read: false,
    },
    {
      id: "2",
      type: "opportunity",
      title: "Similar to Q4 Success",
      description: "This project pattern matches your successful Q4 launch — suggest proactive stakeholder update?",
      clone: "research",
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      read: false,
    },
    {
      id: "3",
      type: "risk",
      title: "Task Overdue Alert",
      description: "3 tasks are pending beyond their due dates — recommend follow-up?",
      clone: "ops",
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      read: true,
    },
  ]);

  const markAsRead = (id: string) => {
    setAlerts(alerts.map(a => a.id === id ? { ...a, read: true } : a));
  };

  const unreadCount = alerts.filter(a => !a.read).length;

  return (
    <div className="pattern-alerts-panel">
      <div className="section-header">
        <h2><Icons.Alert /> Pattern Alerts</h2>
        {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
      </div>
      {alerts.length === 0 ? (
        <div className="empty-state">
          <p>No new pattern alerts</p>
        </div>
      ) : (
        <div className="alerts-list">
          {alerts.map(alert => (
            <div key={alert.id} className={`alert-item ${alert.read ? "read" : "unread"} ${alert.type}`}>
              <div className="alert-header">
                <span className="alert-type">{alert.type}</span>
                <span className="alert-clone">{alert.clone}</span>
              </div>
              <h4>{alert.title}</h4>
              <p>{alert.description}</p>
              <div className="alert-actions">
                <button className="btn btn-small" onClick={() => markAsRead(alert.id)}>
                  Dismiss
                </button>
                <button className="btn btn-small btn-primary">
                  Take Action
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface ContextItem {
  id: string;
  source: string;
  content: string;
  timestamp: string;
  relevance: number;
}

function ContextPreviewPanel({ contextFor }: { contextFor: string }) {
  // Mock context from Graphiti - shows what context was used
  const [contextItems] = useState<ContextItem[]>([
    {
      id: "1",
      source: "email",
      content: "User prefers concise, bullet-point responses in professional emails",
      timestamp: new Date(Date.now() - 86400000 * 5).toISOString(),
      relevance: 0.95,
    },
    {
      id: "2",
      source: "meeting",
      content: "Discussed project timeline on Jan 15 — agreed on 2-week sprint cycles",
      timestamp: new Date(Date.now() - 86400000 * 7).toISOString(),
      relevance: 0.88,
    },
    {
      id: "3",
      source: "task",
      content: "Created follow-up task: Review Q4 analytics report",
      timestamp: new Date(Date.now() - 86400000 * 3).toISOString(),
      relevance: 0.75,
    },
  ]);

  return (
    <div className="context-preview-panel">
      <div className="section-header">
        <h2><Icons.Context /> Context Used</h2>
        <span className="context-for">for: {contextFor}</span>
      </div>
      <div className="context-items">
        {contextItems.map(item => (
          <div key={item.id} className="context-item">
            <div className="context-source">
              <span className={`source-badge ${item.source}`}>{item.source}</span>
              <span className="relevance">{Math.round(item.relevance * 100)}% match</span>
            </div>
            <p className="context-content">{item.content}</p>
            <span className="context-time">
              {new Date(item.timestamp).toLocaleDateString()}
            </span>
          </div>
        ))}
      </div>
      <div className="context-footer">
        <button className="btn btn-small">
          <Icons.Refresh /> Refresh Context
        </button>
      </div>
    </div>
  );
}

interface ActivityLogEntry {
  id: string;
  clone: CloneType;
  action: string;
  status: "completed" | "approved" | "pending" | "rejected";
  timestamp: string;
  details?: string;
}

function ActivityLog() {
  const [activities] = useState<ActivityLogEntry[]>([
    {
      id: "1",
      clone: "email",
      action: "Drafted reply to client inquiry",
      status: "approved",
      timestamp: new Date(Date.now() - 1800000).toISOString(),
      details: "Based on 3 past client threads",
    },
    {
      id: "2",
      clone: "ops",
      action: "Created task: Follow up on proposal",
      status: "completed",
      timestamp: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: "3",
      clone: "research",
      action: "Analyzed competitor launch",
      status: "completed",
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      details: "Found 2 similar products",
    },
    {
      id: "4",
      clone: "calendar",
      action: "Suggested focus time block",
      status: "pending",
      timestamp: new Date(Date.now() - 10800000).toISOString(),
    },
  ]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "success";
      case "approved": return "primary";
      case "pending": return "warning";
      case "rejected": return "danger";
      default: return "";
    }
  };

  return (
    <div className="activity-log">
      <div className="section-header">
        <h2><Icons.Activity /> Clone Activity</h2>
        <span className="activity-count">{activities.length} recent</span>
      </div>
      <div className="activity-list">
        {activities.map(entry => (
          <div key={entry.id} className="activity-item">
            <div className="activity-icon">
              {entry.clone === "email" && <Icons.Email />}
              {entry.clone === "ops" && <Icons.Ops />}
              {entry.clone === "research" && <Icons.Research />}
              {entry.clone === "calendar" && <Icons.Calendar />}
            </div>
            <div className="activity-content">
              <span className="activity-action">{entry.action}</span>
              {entry.details && <p className="activity-details">{entry.details}</p>}
              <span className="activity-time">
                {new Date(entry.timestamp).toLocaleString()}
              </span>
            </div>
            <span className={`status-badge ${getStatusColor(entry.status)}`}>
              {entry.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function QuickActions() {
  const [isLoading, setIsLoading] = useState<string | null>(null);

  const quickActions = [
    { id: "email", label: "Compose Email", icon: Icons.Email, clone: "email" },
    { id: "task", label: "Create Task", icon: Icons.Ops, clone: "ops" },
    { id: "research", label: "Quick Research", icon: Icons.Research, clone: "research" },
    { id: "schedule", label: "Schedule Meeting", icon: Icons.Calendar, clone: "calendar" },
    { id: "digest", label: "Generate Daily Digest", icon: Icons.Zap, clone: "admin" },
  ];

  const handleQuickAction = async (actionId: string) => {
    setIsLoading(actionId);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    setIsLoading(null);
  };

  return (
    <div className="quick-actions-panel">
      <div className="section-header">
        <h2><Icons.QuickAction /> Quick Actions</h2>
      </div>
      <div className="quick-actions-grid">
        {quickActions.map(action => (
          <button
            key={action.id}
            className="quick-action-btn"
            onClick={() => handleQuickAction(action.id)}
            disabled={isLoading !== null}
          >
            <action.icon />
            <span>{action.label}</span>
            {isLoading === action.id && <span className="loading-spinner" />}
          </button>
        ))}
      </div>
    </div>
  );
}

function OnboardingView() {
  const [step, setStep] = useState(1);
  const [connectedTools, setConnectedTools] = useState<string[]>([]);

  const tools = [
    { id: "gmail", name: "Gmail", description: "Sync emails for context" },
    { id: "calendar", name: "Calendar", description: "Sync events and meetings" },
    { id: "notion", name: "Notion", description: "Sync tasks and notes" },
    { id: "drive", name: "Drive", description: "Sync files and documents" },
  ];

  const toggleTool = (toolId: string) => {
    setConnectedTools(prev =>
      prev.includes(toolId)
        ? prev.filter(t => t !== toolId)
        : [...prev, toolId]
    );
  };

  const simulateSync = async () => {
    setStep(3);
    // Simulate sync progress
    await new Promise(resolve => setTimeout(resolve, 2000));
    setStep(4);
  };

  return (
    <div className="onboarding-view">
      <div className="onboarding-card">
        {step === 1 && (
          <>
            <div className="onboarding-header">
              <Icons.CheckCircle />
              <h1>Welcome to EchoTeam</h1>
              <p>Your AI-powered clone workforce</p>
            </div>
            <div className="onboarding-content">
              <h2>Connect Your Tools</h2>
              <p>Select the tools you want EchoTeam to access. We'll sync your data to build your personal context graph.</p>
              <div className="tools-list">
                {tools.map(tool => (
                  <div
                    key={tool.id}
                    className={`tool-item ${connectedTools.includes(tool.id) ? "connected" : ""}`}
                    onClick={() => toggleTool(tool.id)}
                  >
                    <div className="tool-info">
                      <h3>{tool.name}</h3>
                      <p>{tool.description}</p>
                    </div>
                    <div className={`tool-status ${connectedTools.includes(tool.id) ? "connected" : ""}`}>
                      {connectedTools.includes(tool.id) ? "Connected" : "Not connected"}
                    </div>
                  </div>
                ))}
              </div>
              <button
                className="btn btn-primary btn-large"
                onClick={() => setStep(2)}
                disabled={connectedTools.length === 0}
              >
                Continue
              </button>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <div className="onboarding-header">
              <Icons.Refresh />
              <h1>Syncing Your Data</h1>
              <p>Building your temporal context graph</p>
            </div>
            <div className="sync-progress">
              <div className="sync-steps">
                <div className="sync-step completed">
                  <Icons.Check />
                  <span>Connected {connectedTools.length} tools</span>
                </div>
                <div className="sync-step">
                  <span className="sync-step-number">2</span>
                  <span>Analyzing recent emails, calendar events, tasks...</span>
                </div>
                <div className="sync-step">
                  <span className="sync-step-number">3</span>
                  <span>Building context graph...</span>
                </div>
                <div className="sync-step">
                  <span className="sync-step-number">4</span>
                  <span>Training clones on your patterns...</span>
                </div>
              </div>
              <button className="btn btn-primary btn-large" onClick={simulateSync}>
                Start Sync
              </button>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <div className="onboarding-header">
              <div className="loading-spinner large" />
              <h1>Syncing Your Data</h1>
              <p>This may take a few minutes...</p>
            </div>
            <div className="sync-status">
              <p>Analyzing 847 emails...</p>
              <p>Processing 156 calendar events...</p>
              <p>Indexing 234 tasks...</p>
            </div>
          </>
        )}

        {step === 4 && (
          <>
            <div className="onboarding-header">
              <Icons.CheckCircle />
              <h1>You're All Set!</h1>
              <p>Here's what we learned from your data</p>
            </div>
            <div className="wow-moment">
              <div className="wow-stat">
                <span className="wow-number">847</span>
                <span className="wow-label">Emails Analyzed</span>
              </div>
              <div className="wow-stat">
                <span className="wow-number">156</span>
                <span className="wow-label">Events Processed</span>
              </div>
              <div className="wow-stat">
                <span className="wow-number">234</span>
                <span className="wow-label">Tasks Indexed</span>
              </div>
            </div>
            <div className="context-preview-example">
              <h3>Your Clones Now Know:</h3>
              <ul>
                <li>You prefer concise, bullet-point email responses</li>
                <li>You're most productive 9am-12pm (focus time)</li>
                <li>You follow up on client emails within 24 hours</li>
                <li>You categorize expenses weekly on Fridays</li>
              </ul>
            </div>
            <button className="btn btn-primary btn-large" onClick={() => setStep(5)}>
              Start Using EchoTeam
            </button>
          </>
        )}

        {step === 5 && (
          <>
            <div className="onboarding-header">
              <Icons.Zap />
              <h1>Try Your First Clone</h1>
              <p>Click below to see your clones in action</p>
            </div>
            <QuickActions />
            <button className="btn btn-secondary" onClick={() => setStep(1)}>
              Back to Dashboard
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function SettingsView() {
  return (
    <div className="view-content">
      <div className="view-header">
        <h1>Settings</h1>
        <p>Configure your EchoTeam preferences</p>
      </div>

      {/* Integrations Section */}
      <section className="section">
        <h2>Integrations</h2>
        <p className="section-description">Connect your tools to enable auto-ingestion</p>
        <div className="integrations-grid">
          <div className="integration-card">
            <div className="integration-header">
              <Icons.Email />
              <h3>Gmail</h3>
            </div>
            <p>Sync emails for context and drafting</p>
            <button className="btn btn-secondary">Connect</button>
          </div>
          <div className="integration-card">
            <div className="integration-header">
              <Icons.Calendar />
              <h3>Calendar</h3>
            </div>
            <p>Sync events and meetings</p>
            <button className="btn btn-secondary">Connect</button>
          </div>
          <div className="integration-card">
            <div className="integration-header">
              <Icons.Ops />
              <h3>Notion</h3>
            </div>
            <p>Sync tasks and notes</p>
            <button className="btn btn-secondary">Connect</button>
          </div>
          <div className="integration-card">
            <div className="integration-header">
              <Icons.Research />
              <h3>Drive</h3>
            </div>
            <p>Sync files and documents</p>
            <button className="btn btn-secondary">Connect</button>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>General</h2>
        <div className="settings-form">
          <div className="setting-item">
            <label>Email Notifications</label>
            <input type="checkbox" defaultChecked />
          </div>
          <div className="setting-item">
            <label>Auto-execute high confidence actions</label>
            <input type="checkbox" />
          </div>
          <div className="setting-item">
            <label>Confidence threshold</label>
            <select defaultValue="0.85">
              <option value="0.7">70%</option>
              <option value="0.85">85%</option>
              <option value="0.95">95%</option>
            </select>
          </div>
        </div>
      </section>
    </div>
  );
}

function App() {
  const [currentView, setCurrentView] = useState<View>("dashboard");
  const { user, signIn, signOut, isLoading: authLoading } = useAuth();
  const [loginEmail, setLoginEmail] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail) return;
    await signIn(loginEmail);
  };

  if (authLoading) {
    return (
      <div className="loading-screen">
        <div className="loader" />
        <p>Loading EchoTeam...</p>
      </div>
    );
  }

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: Icons.Dashboard },
    { id: "clones", label: "Clones", icon: Icons.Clones },
    { id: "actions", label: "Actions", icon: Icons.Actions },
    { id: "analytics", label: "Analytics", icon: Icons.Analytics },
    { id: "settings", label: "Settings", icon: Icons.Settings },
  ] as const;

  return (
    <div className="app-layout">
      {!user ? (
        <div className="login-screen">
          <div className="login-card">
            <div className="login-header">
              <h1>EchoTeam</h1>
              <p>Your AI-powered clone workforce</p>
            </div>
            <form onSubmit={handleLogin} className="login-form">
              <input
                type="email"
                placeholder="Enter your email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                required
              />
              <button type="submit" className="btn btn-primary">
                Sign In
              </button>
            </form>
            <p className="login-note">Demo mode - use any email</p>
          </div>
        </div>
      ) : (
        <>
          {/* Sidebar */}
          <aside className="sidebar">
            <div className="sidebar-header">
              <h1>EchoTeam</h1>
            </div>
            <nav className="sidebar-nav">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  className={`nav-item ${currentView === item.id ? "active" : ""}`}
                  onClick={() => setCurrentView(item.id)}
                >
                  <item.icon />
                  <span>{item.label}</span>
                </button>
              ))}
            </nav>
            <div className="sidebar-footer">
              <div className="user-info">
                <div className="user-avatar">
                  {user.name?.charAt(0) || user.email?.charAt(0)}
                </div>
                <div className="user-details">
                  <span className="user-name">{user.name || user.email}</span>
                </div>
              </div>
              <button className="btn btn-ghost" onClick={signOut}>
                Sign Out
              </button>
            </div>
          </aside>

          {/* Main Content */}
          <main className="main-content">
            {currentView === "onboarding" && <OnboardingView />}
            {currentView === "dashboard" && <DashboardView />}
            {currentView === "clones" && <ClonesView />}
            {currentView === "actions" && <ActionsView />}
            {currentView === "analytics" && <AnalyticsView />}
            {currentView === "settings" && <SettingsView />}
            {currentView === "context" && <ContextPreviewPanel contextFor="Last Action" />}
          </main>
        </>
      )}
    </div>
  );
}

export default App;
