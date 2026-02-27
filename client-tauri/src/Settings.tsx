import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  TextField,
  FormControlLabel,
  Switch,
  FormControl,
  RadioGroup,
  Radio,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  LinearProgress,
  Collapse,
} from "@mui/material";
import ExpandMore from "@mui/icons-material/ExpandMore";
import ExpandLess from "@mui/icons-material/ExpandLess";
import Refresh from "@mui/icons-material/Refresh";

function formatBytes(n: number): string {
  if (n < 0) return "0 B";
  if (n >= 1024 ** 4) return `${(n / 1024 ** 4).toFixed(1)} TiB`;
  if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toFixed(1)} GiB`;
  if (n >= 1024 ** 2) return `${(n / 1024 ** 2).toFixed(1)} MiB`;
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KiB`;
  return `${n} B`;
}

interface SettingsProps {
  email: string | null;
  onLogout: () => void;
}

export default function Settings({ email, onLogout }: SettingsProps) {
  const [syncFolder, setSyncFolder] = useState("");
  const [autostart, setAutostart] = useState(false);
  const [baseUrlMode, setBaseUrlMode] = useState<"automatic" | "manual">("automatic");
  const [manualBaseUrl, setManualBaseUrl] = useState("");
  const [storage, setStorage] = useState<{ used_bytes: number; limit_bytes: number | null } | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [adminOpen, setAdminOpen] = useState(false);
  const [users, setUsers] = useState<Array<{ email: string; first_name?: string; last_name?: string; is_admin?: boolean; storage_limit_bytes?: number | null }>>([]);
  const [changePwdOpen, setChangePwdOpen] = useState(false);
  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [changePwdError, setChangePwdError] = useState("");
  const [createUserOpen, setCreateUserOpen] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserFirst, setNewUserFirst] = useState("");
  const [newUserLast, setNewUserLast] = useState("");
  const [syncProgress, setSyncProgress] = useState<{ phase: string; current: number; total: number } | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const loadSettings = async () => {
    try {
      const [folder, start, mode, manual, url, stor] = await Promise.all([
        invoke<string>("get_sync_folder_path"),
        invoke<boolean>("get_autostart"),
        invoke<string>("get_base_url_mode"),
        invoke<string>("get_manual_base_url"),
        invoke<string>("get_base_url"),
        invoke<{ used_bytes: number; limit_bytes: number | null }>("api_get_storage").catch(() => null),
      ]);
      setSyncFolder(folder);
      setAutostart(start);
      setBaseUrlMode(mode as "automatic" | "manual");
      setManualBaseUrl(manual);
      setBaseUrl(url);
      setStorage(stor);
    } catch {
      // ignore
    }
  };

  const loadUsers = async () => {
    try {
      const list = await invoke<typeof users>("api_list_users");
      setUsers(list);
    } catch {
      setUsers([]);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  useEffect(() => {
    invoke<{ status: string; message?: string | null }>("get_sync_status")
      .then((s) => {
        if (s.status === "error" && s.message) setSyncError(s.message);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (adminOpen) loadUsers();
  }, [adminOpen]);

  useEffect(() => {
    const unlistenPromise = listen<{ status: string; message?: string | null }>("sync-status", (event) => {
      const { status, message } = event.payload;
      if (status === "synced" || status === "error") {
        setSyncing(false);
        setSyncProgress(null);
        if (status === "error" && message) setSyncError(message);
        if (status === "synced") loadSettings();
      }
    });
    return () => {
      unlistenPromise.then((fn) => fn());
    };
  }, []);

  useEffect(() => {
    if (!syncing) return;
    const interval = setInterval(async () => {
      try {
        const p = await invoke<{ phase: string; current: number; total: number } | null>("get_sync_progress");
        if (p) setSyncProgress(p);
      } catch {
        // ignore
      }
    }, 500);
    return () => clearInterval(interval);
  }, [syncing]);

  const handleAutostart = async (_: unknown, checked: boolean) => {
    await invoke("set_autostart", { enabled: checked });
    setAutostart(checked);
  };

  const handleBaseUrlMode = async (mode: string) => {
    await invoke("set_base_url_mode", { mode });
    setBaseUrlMode(mode as "automatic" | "manual");
    const url = await invoke<string>("get_base_url");
    setBaseUrl(url);
  };

  const handleManualUrl = async () => {
    await invoke("set_manual_base_url", { url: manualBaseUrl });
    const url = await invoke<string>("get_base_url");
    setBaseUrl(url);
  };

  const handleChangePassword = async () => {
    setChangePwdError("");
    try {
      await invoke("api_change_password", { currentPassword: currentPwd, newPassword: newPwd });
      setChangePwdOpen(false);
      setCurrentPwd("");
      setNewPwd("");
    } catch (e) {
      setChangePwdError(String(e));
    }
  };

  const handleCreateUser = async () => {
    try {
      await invoke("api_create_user", {
        email: newUserEmail,
        first_name: newUserFirst,
        last_name: newUserLast,
      });
      setCreateUserOpen(false);
      setNewUserEmail("");
      setNewUserFirst("");
      setNewUserLast("");
      loadUsers();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteUser = async (userEmail: string) => {
    if (!confirm(`Delete user ${userEmail}?`)) return;
    try {
      await invoke("api_delete_user", { email: userEmail });
      loadUsers();
    } catch (e) {
      console.error(e);
    }
  };

  const handleSyncNow = async () => {
    setSyncing(true);
    setSyncError(null);
    setSyncProgress({ phase: "Starting…", current: 0, total: 0 });
    try {
      await invoke<{ started?: boolean }>("run_sync");
      // Sync runs in background; sync-status event will set syncing false and update error
    } catch (e) {
      setSyncing(false);
      setSyncProgress(null);
      const msg = e instanceof Error ? e.message : String(e);
      setSyncError(msg);
      console.error(e);
    }
  };

  return (
    <Box sx={{ p: 2, maxWidth: 560, mx: "auto" }}>
      <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>
        Settings
      </Typography>

      <Card sx={{ mb: 2 }} variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Account
          </Typography>
          <Typography variant="body1">{email ?? "—"}</Typography>
          {storage && (
            <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mt: 1 }}>
              <Box sx={{ position: "relative", flexShrink: 0 }}>
                {/* Full circle = 100% of available space (grey track) */}
                <CircularProgress
                  variant="determinate"
                  value={100}
                  size={64}
                  thickness={4}
                  sx={{
                    color: "action.disabledBackground",
                    position: "absolute",
                    left: 0,
                    top: 0,
                  }}
                />
                {/* Blue arc = used percentage of limit */}
                <CircularProgress
                  variant="determinate"
                  value={
                    storage.limit_bytes != null && storage.limit_bytes > 0
                      ? Math.min(100, (storage.used_bytes / storage.limit_bytes) * 100)
                      : 0
                  }
                  size={64}
                  thickness={4}
                  sx={{ color: "primary.main" }}
                />
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  <strong>Storage space</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Used: {formatBytes(storage.used_bytes)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Available:{" "}
                  {storage.limit_bytes != null
                    ? formatBytes(Math.max(0, storage.limit_bytes - storage.used_bytes))
                    : "No maximum"}
                </Typography>
              </Box>
            </Box>
          )}
          <Box sx={{ mt: 1 }}>
            <Button size="small" onClick={() => setChangePwdOpen(true)}>
              Change password
            </Button>
            <Button size="small" color="error" onClick={onLogout} sx={{ ml: 1 }}>
              Log out
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Card sx={{ mb: 2 }} variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Sync folder
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <TextField
              size="small"
              fullWidth
              value={syncFolder}
              onChange={(e) => setSyncFolder(e.target.value)}
              onBlur={async () => {
                try {
                  await invoke("set_sync_folder_path", { folder: syncFolder });
                } catch {
                  // ignore
                }
              }}
              placeholder="e.g. ~/brandyBox"
            />
          </Box>
        </CardContent>
      </Card>

      <Card sx={{ mb: 2 }} variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Connection
          </Typography>
          <FormControl component="fieldset" sx={{ display: "block", mb: 1 }}>
            <RadioGroup row value={baseUrlMode} onChange={(_, v) => handleBaseUrlMode(v)}>
              <FormControlLabel value="automatic" control={<Radio />} label="Automatic (LAN / Cloudflare)" />
              <FormControlLabel value="manual" control={<Radio />} label="Manual URL" />
            </RadioGroup>
          </FormControl>
          {baseUrlMode === "manual" && (
            <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
              <TextField
                size="small"
                fullWidth
                label="Base URL"
                value={manualBaseUrl}
                onChange={(e) => setManualBaseUrl(e.target.value)}
                onBlur={handleManualUrl}
              />
            </Box>
          )}
          <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
            Current: {baseUrl}
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ mb: 2 }} variant="outlined">
        <CardContent>
          <FormControlLabel
            control={<Switch checked={autostart} onChange={handleAutostart} />}
            label="Start Brandy Box when I log in"
          />
        </CardContent>
      </Card>

      <Card sx={{ mb: 2 }} variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Sync
          </Typography>
          <Button
            variant="contained"
            startIcon={syncing ? <CircularProgress size={18} color="inherit" /> : <Refresh />}
            onClick={handleSyncNow}
            disabled={syncing}
          >
            Sync now
          </Button>
          {syncError && (
            <Alert severity="error" onClose={() => setSyncError(null)} sx={{ mt: 1 }}>
              {syncError}
            </Alert>
          )}
          {syncProgress && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption">{syncProgress.phase} {syncProgress.total > 0 ? `${syncProgress.current} / ${syncProgress.total}` : ""}</Typography>
              {syncProgress.total > 0 && (
                <LinearProgress variant="determinate" value={(syncProgress.current / syncProgress.total) * 100} sx={{ mt: 0.5 }} />
              )}
            </Box>
          )}
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Button
            fullWidth
            onClick={() => setAdminOpen(!adminOpen)}
            endIcon={adminOpen ? <ExpandLess /> : <ExpandMore />}
            sx={{ justifyContent: "space-between" }}
          >
            Admin – User management
          </Button>
          <Collapse in={adminOpen}>
            <Box sx={{ mt: 1 }}>
              <Button size="small" onClick={() => setCreateUserOpen(true)}>
                Create user
              </Button>
              <List dense>
                {users.map((u) => (
                  <ListItem key={u.email}>
                    <ListItemText primary={u.email} secondary={u.first_name || u.last_name ? `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim() : undefined} />
                    <ListItemSecondaryAction>
                      <IconButton edge="end" size="small" onClick={() => handleDeleteUser(u.email)} color="error">
                        Delete
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </Box>
          </Collapse>
        </CardContent>
      </Card>

      <Dialog open={changePwdOpen} onClose={() => setChangePwdOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Change password</DialogTitle>
        <DialogContent>
          {changePwdError && <Alert severity="error" sx={{ mb: 1 }}>{changePwdError}</Alert>}
          <TextField fullWidth label="Current password" type="password" value={currentPwd} onChange={(e) => setCurrentPwd(e.target.value)} margin="dense" />
          <TextField fullWidth label="New password" type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} margin="dense" />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setChangePwdOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleChangePassword}>Change</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={createUserOpen} onClose={() => setCreateUserOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Create user</DialogTitle>
        <DialogContent>
          <TextField fullWidth label="Email" type="email" value={newUserEmail} onChange={(e) => setNewUserEmail(e.target.value)} margin="dense" />
          <TextField fullWidth label="First name" value={newUserFirst} onChange={(e) => setNewUserFirst(e.target.value)} margin="dense" />
          <TextField fullWidth label="Last name" value={newUserLast} onChange={(e) => setNewUserLast(e.target.value)} margin="dense" />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateUserOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateUser}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
