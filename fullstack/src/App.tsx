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

type View = "dashboard" | "clones" | "actions" | "analytics" | "settings";
type CloneType = "calendar" | "email" | "ops";

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
};

interface CloneCardProps {
  type: CloneType;
  name: string;
  enabled: boolean;
  description: string;
}

function CloneCard({ type, name, enabled, description }: CloneCardProps) {
  const Icon = Icons[type === "calendar" ? "Calendar" : type === "email" ? "Email" : "Ops"];

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
                  clone.type === "CALENDAR" && "Manages calendar, blocks focus time"
                }
              />
            ))}
          </div>
        )}
      </section>
      <ActionQueue compact />
    </div>
  );
}

function ClonesView() {
  const { data: clones, isLoading: clonesLoading } = useClones();
  const { data: stats } = useActionStats();

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
                description={
                  clone.type === "CALENDAR"
                    ? "Manages your calendar, blocks focus time, detects conflicts"
                    : clone.type === "EMAIL"
                    ? "Summarizes inbox, drafts replies, categorizes emails"
                    : "Creates tasks, prioritizes work, manages projects"
                }
              />
            ))}
          </div>
        )}
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

function SettingsView() {
  return (
    <div className="view-content">
      <div className="view-header">
        <h1>Settings</h1>
        <p>Configure your EchoTeam preferences</p>
      </div>

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
            {currentView === "dashboard" && <DashboardView />}
            {currentView === "clones" && <ClonesView />}
            {currentView === "actions" && <ActionsView />}
            {currentView === "analytics" && <AnalyticsView />}
            {currentView === "settings" && <SettingsView />}
          </main>
        </>
      )}
    </div>
  );
}

export default App;
