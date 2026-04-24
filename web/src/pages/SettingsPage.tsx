import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";
import {
  adminClients,
  adminCreateUser,
  adminDeleteUser,
  adminEvents,
  adminListUsers,
  fetchMetaVersion,
  patchPreferences,
  type ClientConn,
  type MeUser,
  type ServerEvent,
} from "../api/http";
import { useAuth } from "../context/AuthContext";

export default function SettingsPage() {
  const { user, prefs, setPrefsLocal } = useAuth();
  const [openAppear, setOpenAppear] = useState(false);
  const [bg, setBg] = useState(prefs.content_background_image ?? "");
  const [op, setOp] = useState(prefs.content_background_opacity);
  const [diagOpen, setDiagOpen] = useState(false);
  const [events, setEvents] = useState<ServerEvent[]>([]);
  const [clients, setClients] = useState<ClientConn[]>([]);
  const [meta, setMeta] = useState<{ api_version: string; min_supported_client_version: string } | null>(null);
  const [users, setUsers] = useState<MeUser[]>([]);
  const [newEmail, setNewEmail] = useState("");
  const [newFirst, setNewFirst] = useState("");
  const [newLast, setNewLast] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setBg(prefs.content_background_image ?? "");
    setOp(prefs.content_background_opacity);
  }, [prefs]);

  const loadDiag = useCallback(async () => {
    if (!user?.is_admin) {
      return;
    }
    try {
      const [ev, cl, mv] = await Promise.all([adminEvents(80), adminClients(), fetchMetaVersion()]);
      setEvents(ev);
      setClients(cl);
      setMeta(mv);
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
    try {
      const p = await patchPreferences({
        theme: prefs.theme,
        content_background_image: bg.trim() || null,
        content_background_opacity: op,
      });
      setPrefsLocal(p);
      setOpenAppear(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    }
  };

  const createUser = async () => {
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
    }
  };

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
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, my: 1 }}>
            <TextField size="small" label="Email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} />
            <TextField size="small" label="First" value={newFirst} onChange={(e) => setNewFirst(e.target.value)} />
            <TextField size="small" label="Last" value={newLast} onChange={(e) => setNewLast(e.target.value)} />
            <Button variant="contained" onClick={() => void createUser()}>
              Create
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
                      <Button color="error" size="small" onClick={() => void adminDeleteUser(u.email).then(loadUsers)}>
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
        <DialogContent dividers sx={{ overflowY: "auto", maxHeight: "70vh" }}>
          <TextField
            label="Background image URL"
            fullWidth
            margin="normal"
            value={bg}
            onChange={(e) => setBg(e.target.value)}
            helperText="Optional; shown behind file list with opacity below."
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
          <Button onClick={() => setOpenAppear(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => void saveAppearance()}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Drawer anchor="right" open={diagOpen} onClose={() => setDiagOpen(false)}>
        <Box sx={{ width: 360, p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Diagnostics
          </Typography>
          {user?.is_admin ? (
            <>
              {meta ? (
                <Typography variant="body2" sx={{ mb: 1 }}>
                  API {meta.api_version} · min client {meta.min_supported_client_version}
                </Typography>
              ) : null}
              <Typography variant="subtitle2">Clients</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>User</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Ver</TableCell>
                    <TableCell>Sync OK</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {clients.map((c) => (
                    <TableRow key={`${c.user_email}-${c.client_type}`}>
                      <TableCell>{c.user_email}</TableCell>
                      <TableCell>{c.client_type}</TableCell>
                      <TableCell>{c.client_version}</TableCell>
                      <TableCell>{c.last_sync_ok == null ? "—" : c.last_sync_ok ? "yes" : "no"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Typography variant="subtitle2" sx={{ mt: 2 }}>
                Recent events
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
                  {events.map((ev) => (
                    <TableRow key={ev.id}>
                      <TableCell>{new Date(ev.created_at).toLocaleString()}</TableCell>
                      <TableCell>{ev.level}</TableCell>
                      <TableCell>{ev.message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </>
          ) : (
            <Typography variant="body2">Diagnostics details are available to administrators only.</Typography>
          )}
        </Box>
      </Drawer>

      {err ? (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => setErr(null)}>
          {err}
        </Alert>
      ) : null}
    </Box>
  );
}
