import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import ImageIcon from "@mui/icons-material/Image";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState, type ChangeEvent } from "react";
import {
  adminClients,
  adminCreateUser,
  adminDeleteUser,
  adminDiagnosticEvents,
  adminEvents,
  adminListUsers,
  adminSyncSummaries,
  deleteBackgroundImage,
  fetchMetaVersion,
  patchPreferences,
  uploadBackgroundImage,
  USER_BACKGROUND_IMAGE_SENTINEL,
  type ClientConn,
  type DiagnosticEvent,
  type MeUser,
  type ServerEvent,
  type SyncSummary,
} from "../api/http";
import { useAuth } from "../context/AuthContext";


// ⚡ Bolt: Cache Intl.DateTimeFormat instance to avoid V8 context recreation overhead during date formatting.
// Impact: Significantly faster than calling Date.prototype.toLocaleString() in a loop.
const defaultDateFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "numeric",
  second: "numeric",
});

export default function SettingsPage() {
  const { user, prefs, setPrefsLocal } = useAuth();
  const [openAppear, setOpenAppear] = useState(false);
  const [bg, setBg] = useState(prefs.content_background_image ?? "");
  const [op, setOp] = useState(prefs.content_background_opacity);
  const [diagOpen, setDiagOpen] = useState(false);
  const [events, setEvents] = useState<ServerEvent[]>([]);
  const [clients, setClients] = useState<ClientConn[]>([]);
  const [syncSummaries, setSyncSummaries] = useState<SyncSummary[]>([]);
  const [diagEvents, setDiagEvents] = useState<DiagnosticEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<DiagnosticEvent | null>(null);
  const [eventSearch, setEventSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("all");
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ api_version: string; min_supported_client_version: string } | null>(null);
  const [users, setUsers] = useState<MeUser[]>([]);
  const [newEmail, setNewEmail] = useState("");
  const [newFirst, setNewFirst] = useState("");
  const [newLast, setNewLast] = useState("");
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [isUploadingBackground, setIsUploadingBackground] = useState(false);
  const [isSavingAppearance, setIsSavingAppearance] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const v = prefs.content_background_image ?? "";
    setBg(v === USER_BACKGROUND_IMAGE_SENTINEL ? "" : v);
    setOp(prefs.content_background_opacity);
  }, [prefs]);

  const loadDiag = useCallback(async () => {
    if (!user?.is_admin) {
      return;
    }
    try {
      const [ev, cl, mv, ss, de] = await Promise.all([
        adminEvents(80),
        adminClients(),
        fetchMetaVersion(),
        adminSyncSummaries({ limit: 50 }),
        adminDiagnosticEvents({ limit: 100 }),
      ]);
      setEvents(ev);
      setClients(cl);
      setMeta(mv);
      setSyncSummaries(ss);
      setDiagEvents(de);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Diagnostics load failed");
    }
  }, [user?.is_admin]);

  const loadUsers = useCallback(async () => {
    if (!user?.is_admin) {
      return;
    }
    try {
      setUsers(await adminListUsers());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to list users");
    }
  }, [user?.is_admin]);

  useEffect(() => {
    if (diagOpen) {
      void loadDiag();
    }
  }, [diagOpen, loadDiag]);

  useEffect(() => {
    if (user?.is_admin) {
      void loadUsers();
    }
  }, [user?.is_admin, loadUsers]);

  const saveAppearance = async () => {
    setIsSavingAppearance(true);
    try {
      const trimmed = bg.trim();
      let nextImage: string | null;
      if (trimmed) {
        nextImage = trimmed;
      } else if (prefs.content_background_image === USER_BACKGROUND_IMAGE_SENTINEL) {
        nextImage = USER_BACKGROUND_IMAGE_SENTINEL;
      } else {
        nextImage = null;
      }
      const p = await patchPreferences({
        theme: prefs.theme,
        content_background_image: nextImage,
        content_background_opacity: op,
      });
      setPrefsLocal(p);
      setOpenAppear(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setIsSavingAppearance(false);
    }
  };

  const onUploadBackground = async (e: ChangeEvent<HTMLInputElement>) => {
    const input = e.target;
    const file = input.files?.[0];
    input.value = "";
    if (!file) {
      return;
    }
    setIsUploadingBackground(true);
    try {
      const p = await uploadBackgroundImage(file);
      setPrefsLocal(p);
      setBg("");
      setErr(null);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Upload failed");
    } finally {
      setIsUploadingBackground(false);
    }
  };

  const removeUploadedBackground = async () => {
    try {
      const p = await deleteBackgroundImage();
      setPrefsLocal(p);
      setBg("");
      setErr(null);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Remove failed");
    }
  };

  const createUser = async () => {
    setIsCreatingUser(true);
    try {
      await adminCreateUser({
        email: newEmail.trim(),
        first_name: newFirst.trim() || "User",
        last_name: newLast.trim() || "Name",
      });
      setNewEmail("");
      setNewFirst("");
      setNewLast("");
      await loadUsers();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Create user failed");
    } finally {
      setIsCreatingUser(false);
    }
  };

  const copyEventLlmContext = (ev: DiagnosticEvent) => {
    let prettyContext = "";
    if (ev.context_json) {
      try {
        prettyContext = JSON.stringify(JSON.parse(ev.context_json), null, 2);
      } catch {
        prettyContext = ev.context_json;
      }
    }
    const markdown = [
      "# BrandyBox Diagnostic Context",
      `**Generated**: ${new Date().toISOString()}`,
      meta ? `**Environment**: API ${meta.api_version}, Min Client ${meta.min_supported_client_version}` : "",
      "",
      "## Overview",
      ev.trace_id ? `- **Trace ID**: \`${ev.trace_id}\`` : "",
      `- **Device**: ${ev.device_name}`,
      `- **Client**: ${ev.client_type}`,
      ev.user_email ? `- **User**: ${ev.user_email}` : "",
      `- **Level**: ${ev.level.toUpperCase()}`,
      `- **Category**: ${ev.category}`,
      `- **Timestamp**: ${ev.created_at}`,
      "",
      "## Error Details",
      ev.error_code ? `- **Error Code**: \`${ev.error_code}\`` : "",
      `- **Message**: ${ev.message}`,
      "",
      prettyContext ? `## Context JSON\n\`\`\`json\n${prettyContext}\n\`\`\`` : "",
    ]
      .filter((line) => line !== "")
      .join("\n");

    void navigator.clipboard.writeText(markdown);
    const traceLabel = ev.trace_id ? `trace ${ev.trace_id.slice(0, 8)}...` : `event #${ev.id}`;
    setToastMessage(`Copied LLM context for ${traceLabel}`);
  };

  const copySummaryLlmContext = (ss: SyncSummary) => {
    let prettySummary = "";
    if (ss.error_summary_json) {
      try {
        prettySummary = JSON.stringify(JSON.parse(ss.error_summary_json), null, 2);
      } catch {
        prettySummary = ss.error_summary_json;
      }
    }
    const markdown = [
      "# BrandyBox Sync Run Summary",
      `**Generated**: ${new Date().toISOString()}`,
      meta ? `**Environment**: API ${meta.api_version}, Min Client ${meta.min_supported_client_version}` : "",
      "",
      "## Overview",
      `- **Trace ID**: \`${ss.trace_id}\``,
      `- **Device**: ${ss.device_name}`,
      `- **Client**: ${ss.client_type} v${ss.client_version}`,
      `- **User**: ${ss.user_email}`,
      `- **Status**: ${ss.status.toUpperCase()}`,
      `- **Duration**: ${ss.duration_ms != null ? `${ss.duration_ms}ms` : "In-progress / Unknown"}`,
      `- **Started**: ${ss.started_at}`,
      `- **Completed**: ${ss.completed_at}`,
      "",
      "## Transfer Stats",
      `- **Files Scanned**: ${ss.files_scanned}`,
      `- **Files Uploaded**: ${ss.files_uploaded}`,
      `- **Files Downloaded**: ${ss.files_downloaded}`,
      `- **Failure Count**: ${ss.failure_count}`,
      `- **Bytes Transferred**: ${ss.bytes_transferred}`,
      "",
      prettySummary ? `## Error Summary\n\`\`\`json\n${prettySummary}\n\`\`\`` : "",
    ]
      .filter((line) => line !== "")
      .join("\n");

    void navigator.clipboard.writeText(markdown);
    setToastMessage(`Copied LLM context for trace ${ss.trace_id.slice(0, 8)}...`);
  };

  const filteredEvents = diagEvents.filter((e) => {
    if (levelFilter !== "all" && e.level.toLowerCase() !== levelFilter.toLowerCase()) {
      return false;
    }
    if (!eventSearch) {
      return true;
    }
    const q = eventSearch.toLowerCase();
    return (
      e.message.toLowerCase().includes(q) ||
      (e.error_code && e.error_code.toLowerCase().includes(q)) ||
      (e.category && e.category.toLowerCase().includes(q)) ||
      (e.trace_id && e.trace_id.toLowerCase().includes(q)) ||
      e.device_name.toLowerCase().includes(q)
    );
  });

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Settings
      </Typography>
      <FormControl sx={{ minWidth: 200, mb: 2 }}>
        <InputLabel id="theme-label">Theme</InputLabel>
        <Select
          labelId="theme-label"
          label="Theme"
          value={prefs.theme}
          onChange={async (e) => {
            const p = await patchPreferences({ theme: String(e.target.value) });
            setPrefsLocal(p);
          }}
        >
          <MenuItem value="system">System</MenuItem>
          <MenuItem value="light">Light</MenuItem>
          <MenuItem value="dark">Dark</MenuItem>
        </Select>
      </FormControl>
      <Box sx={{ mb: 2 }}>
        <Button variant="outlined" onClick={() => setOpenAppear(true)}>
          Appearance (background)
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary">
        Web client uses the same account as the desktop app. Google sign-in only works if an admin created your
        email first.
      </Typography>

      {user?.is_admin ? (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Admin
          </Typography>
          <Typography variant="subtitle2">Create user</Typography>
          <Box component="form" onSubmit={(e: React.FormEvent) => { e.preventDefault(); void createUser(); }} sx={{ display: "flex", flexWrap: "wrap", gap: 1, my: 1 }}>
            <TextField size="small" label="Email" type="email" required value={newEmail} onChange={(e) => setNewEmail(e.target.value)} />
            <TextField size="small" label="First" value={newFirst} onChange={(e) => setNewFirst(e.target.value)} />
            <TextField size="small" label="Last" value={newLast} onChange={(e) => setNewLast(e.target.value)} />
            <Button type="submit" variant="contained" disabled={isCreatingUser} startIcon={isCreatingUser ? <CircularProgress size={20} color="inherit" /> : null}>
              {isCreatingUser ? "Creating..." : "Create"}
            </Button>
          </Box>
          <Table size="small" sx={{ mb: 2 }}>
            <TableHead>
              <TableRow>
                <TableCell>Email</TableCell>
                <TableCell>Admin</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.email}>
                  <TableCell>{u.email}</TableCell>
                  <TableCell>{u.is_admin ? "yes" : ""}</TableCell>
                  <TableCell align="right">
                    {u.email !== user.email ? (
                      <Button
                        color="error"
                        size="small"
                        onClick={() => {
                          if (window.confirm(`Delete user ${u.email}?`)) {
                            void adminDeleteUser(u.email).then(loadUsers);
                          }
                        }}
                      >
                        Delete
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : null}

      <Box sx={{ mt: 2 }}>
        <Button size="small" variant="text" onClick={() => setDiagOpen(true)}>
          Diagnostics
        </Button>
      </Box>

      <Dialog open={openAppear} onClose={() => setOpenAppear(false)} scroll="paper" fullWidth maxWidth="sm">
        <DialogTitle>Appearance</DialogTitle>
        <form onSubmit={(e) => { e.preventDefault(); void saveAppearance(); }}>
          <DialogContent dividers sx={{ overflowY: "auto", maxHeight: "70vh" }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }} flexWrap="wrap">
              <Button
                variant="outlined"
                component="label"
                disabled={isUploadingBackground}
                startIcon={isUploadingBackground ? <CircularProgress size={20} color="inherit" /> : <ImageIcon />}
              >
                {isUploadingBackground ? "Uploading..." : "Upload from computer"}
                <input
                  type="file"
                  hidden
                  accept="image/jpeg,image/png,image/gif,image/webp"
                  onChange={onUploadBackground}
                  disabled={isUploadingBackground}
                />
              </Button>
              {prefs.content_background_image === USER_BACKGROUND_IMAGE_SENTINEL ? (
                <Button color="warning" variant="text" size="small" onClick={() => void removeUploadedBackground()}>
                  Remove uploaded image
                </Button>
              ) : null}
            </Stack>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
              JPEG, PNG, GIF, or WebP — max 5 MB. The image is stored on the server under your account (not inside the
              preferences JSON).
            </Typography>
            {prefs.content_background_image === USER_BACKGROUND_IMAGE_SENTINEL ? (
              <Alert severity="info" sx={{ mb: 2 }}>
                An uploaded image is active. Enter a URL below to switch to a link instead (the uploaded file will be
                removed when you save).
              </Alert>
            ) : null}
            <TextField
              label="Background image URL"
              fullWidth
              margin="normal"
              value={bg}
              onChange={(e) => setBg(e.target.value)}
              helperText="Optional; use an https link, or upload a file above. Shown behind the main area with opacity below."
            />
            <Typography gutterBottom sx={{ mt: 2 }}>
              Image opacity
            </Typography>
            <Slider
              min={0}
              max={1}
              step={0.02}
              value={op}
              onChange={(_, v) => setOp(v as number)}
              valueLabelDisplay="auto"
              aria-label="Background opacity"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenAppear(false)} disabled={isSavingAppearance}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={isSavingAppearance}
              startIcon={isSavingAppearance ? <CircularProgress size={20} color="inherit" /> : null}
            >
              {isSavingAppearance ? "Saving..." : "Save"}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Drawer
        anchor="right"
        open={diagOpen}
        onClose={() => setDiagOpen(false)}
        PaperProps={{ sx: { width: { xs: "100%", sm: 650, md: 850 }, p: 3 } }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">System Diagnostics</Typography>
          <Button size="small" onClick={() => void loadDiag()}>
            Refresh
          </Button>
        </Stack>

        {user?.is_admin ? (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {meta ? (
              <Alert severity="info" sx={{ py: 0.5 }}>
                API {meta.api_version} · Min Client Version {meta.min_supported_client_version}
              </Alert>
            ) : null}

            {/* Active Connected Clients */}
            <Box>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Connected Clients
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>User</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Version</TableCell>
                      <TableCell>Last Sync OK</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {clients.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} align="center">
                          <Typography variant="body2" color="text.secondary">
                            No active clients registered.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      clients.map((c) => (
                        <TableRow key={`${c.user_email}-${c.client_type}`}>
                          <TableCell>{c.user_email}</TableCell>
                          <TableCell>{c.client_type}</TableCell>
                          <TableCell>{c.client_version}</TableCell>
                          <TableCell>
                            {c.last_sync_ok == null ? (
                              "—"
                            ) : c.last_sync_ok ? (
                              <Chip size="small" label="yes" color="success" />
                            ) : (
                              <Chip size="small" label="no" color="error" />
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </Box>
            </Box>

            {/* Client Sync Matrix */}
            <Box>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Client Sync Matrix
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
                Historical sync run summaries and telemetry reported by clients.
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Device / Client</TableCell>
                      <TableCell>User</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell align="right">Scanned / Up / Down / Fail</TableCell>
                      <TableCell align="right">Duration</TableCell>
                      <TableCell align="center">LLM</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {syncSummaries.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center">
                          <Typography variant="body2" color="text.secondary">
                            No sync summaries recorded yet.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      syncSummaries.map((ss) => {
                        const isOk = ss.status.toLowerCase() === "ok";
                        const isError = ss.status.toLowerCase() === "failed" || ss.status.toLowerCase() === "error";
                        return (
                          <TableRow key={ss.id}>
                            <TableCell>
                              <Typography variant="body2" fontWeight="bold">
                                {ss.device_name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {ss.client_type} v{ss.client_version}
                              </Typography>
                            </TableCell>
                            <TableCell>{ss.user_email}</TableCell>
                            <TableCell>
                              <Chip
                                size="small"
                                label={ss.status}
                                color={isOk ? "success" : isError ? "error" : "warning"}
                              />
                            </TableCell>
                            <TableCell align="right">
                              {ss.files_scanned} / {ss.files_uploaded} / {ss.files_downloaded} / {ss.failure_count}
                            </TableCell>
                            <TableCell align="right">
                              {ss.duration_ms != null ? `${(ss.duration_ms / 1000).toFixed(1)}s` : "—"}
                            </TableCell>
                            <TableCell align="center">
                              <Tooltip title="Copy LLM Context">
                                <IconButton
                                  aria-label="Copy LLM Context"
                                  size="small"
                                  color="primary"
                                  onClick={() => copySummaryLlmContext(ss)}
                                >
                                  <ContentCopyIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </Box>
            </Box>

            {/* Diagnostic Error Events */}
            <Box>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Diagnostic Error Events
              </Typography>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 1.5 }}>
                <TextField
                  size="small"
                  fullWidth
                  placeholder="Search error code, message, category, trace..."
                  value={eventSearch}
                  onChange={(e) => setEventSearch(e.target.value)}
                />
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel id="diag-level-label">Level</InputLabel>
                  <Select
                    labelId="diag-level-label"
                    label="Level"
                    value={levelFilter}
                    onChange={(e) => setLevelFilter(e.target.value)}
                  >
                    <MenuItem value="all">All</MenuItem>
                    <MenuItem value="error">Error</MenuItem>
                    <MenuItem value="warn">Warning</MenuItem>
                    <MenuItem value="info">Info</MenuItem>
                  </Select>
                </FormControl>
              </Stack>

              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Time</TableCell>
                      <TableCell>Level</TableCell>
                      <TableCell>Category / Code</TableCell>
                      <TableCell>Message</TableCell>
                      <TableCell align="center">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredEvents.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography variant="body2" color="text.secondary">
                            No diagnostic events found.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredEvents.map((ev) => (
                        <TableRow key={ev.id}>
                          <TableCell sx={{ whiteSpace: "nowrap" }}>
                            {defaultDateFormatter.format(new Date(ev.created_at))}
                          </TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={ev.level}
                              color={
                                ev.level.toLowerCase() === "error"
                                  ? "error"
                                  : ev.level.toLowerCase() === "warn"
                                  ? "warning"
                                  : "default"
                              }
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{ev.category}</Typography>
                            {ev.error_code ? (
                              <Typography variant="caption" color="text.secondary">
                                {ev.error_code}
                              </Typography>
                            ) : null}
                          </TableCell>
                          <TableCell sx={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            <Tooltip title={ev.message}>
                              <span>{ev.message}</span>
                            </Tooltip>
                          </TableCell>
                          <TableCell align="center" sx={{ whiteSpace: "nowrap" }}>
                            <Button size="small" onClick={() => setSelectedEvent(ev)}>
                              Details
                            </Button>
                            <Tooltip title="Copy LLM Context">
                              <IconButton aria-label="Copy LLM Context" size="small" onClick={() => copyEventLlmContext(ev)}>
                                <ContentCopyIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </Box>
            </Box>

            {/* Server Activity Log */}
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Recent Server System Events
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Time</TableCell>
                    <TableCell>Level</TableCell>
                    <TableCell>Message</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {events.slice(0, 15).map((ev) => (
                    <TableRow key={ev.id}>
                      <TableCell>{defaultDateFormatter.format(new Date(ev.created_at))}</TableCell>
                      <TableCell>{ev.level}</TableCell>
                      <TableCell>{ev.message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Box>
        ) : (
          <Typography variant="body2">Diagnostics details are available to administrators only.</Typography>
        )}
      </Drawer>

      {/* Selected Diagnostic Event Details Dialog */}
      <Dialog
        open={Boolean(selectedEvent)}
        onClose={() => setSelectedEvent(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Diagnostic Event Details</DialogTitle>
        <DialogContent dividers>
          {selectedEvent ? (
            <Stack spacing={1.5}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Trace ID
                </Typography>
                <Typography variant="body2" fontFamily="monospace">
                  {selectedEvent.trace_id || "—"}
                </Typography>
              </Box>
              <Stack direction="row" spacing={2} flexWrap="wrap">
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Device
                  </Typography>
                  <Typography variant="body2">{selectedEvent.device_name}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Client
                  </Typography>
                  <Typography variant="body2">{selectedEvent.client_type}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    User
                  </Typography>
                  <Typography variant="body2">{selectedEvent.user_email || "—"}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Category
                  </Typography>
                  <Typography variant="body2">{selectedEvent.category}</Typography>
                </Box>
                {selectedEvent.error_code ? (
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Error Code
                    </Typography>
                    <Typography variant="body2">{selectedEvent.error_code}</Typography>
                  </Box>
                ) : null}
              </Stack>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Message
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                  {selectedEvent.message}
                </Typography>
              </Box>
              {selectedEvent.context_json ? (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Context Payload
                  </Typography>
                  <Box
                    component="pre"
                    sx={{
                      p: 1.5,
                      bgcolor: "action.hover",
                      borderRadius: 1,
                      overflowX: "auto",
                      fontSize: "0.8rem",
                    }}
                  >
                    {(() => {
                      try {
                        return JSON.stringify(JSON.parse(selectedEvent.context_json), null, 2);
                      } catch {
                        return selectedEvent.context_json;
                      }
                    })()}
                  </Box>
                </Box>
              ) : null}
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          {selectedEvent ? (
            <Button
              startIcon={<ContentCopyIcon />}
              onClick={() => copyEventLlmContext(selectedEvent)}
            >
              Copy LLM Context
            </Button>
          ) : null}
          <Button onClick={() => setSelectedEvent(null)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(toastMessage)}
        autoHideDuration={3000}
        onClose={() => setToastMessage(null)}
        message={toastMessage}
      />

      {err ? (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => setErr(null)}>
          {err}
        </Alert>
      ) : null}
    </Box>
  );
}
