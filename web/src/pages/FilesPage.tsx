import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import UploadIcon from "@mui/icons-material/Upload";
import {
  Alert,
  Box,
  Button,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Snackbar,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  deleteFile,
  downloadBlob,
  fetchStorage,
  listFiles,
  patchPreferences,
  uploadFile,
  type FileRow,
  type StorageInfo,
} from "../api/http";
import { useAuth } from "../context/AuthContext";

function groupByFolder(files: FileRow[]): Map<string, FileRow[]> {
  const m = new Map<string, FileRow[]>();
  for (const f of files) {
    const parts = f.path.split("/");
    const folder = parts.length > 1 ? parts.slice(0, -1).join("/") : "(root)";
    if (!m.has(folder)) {
      m.set(folder, []);
    }
    m.get(folder)!.push(f);
  }
  const keys = [...m.keys()].sort();
  return new Map(keys.map((k) => [k, m.get(k)!]));
}

export default function FilesPage() {
  const { prefs, setPrefsLocal } = useAuth();
  const [files, setFiles] = useState<FileRow[]>([]);
  const [storage, setStorage] = useState<StorageInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [fl, st] = await Promise.all([listFiles(), fetchStorage()]);
      setFiles(fl);
      setStorage(st);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const grouped = useMemo(() => groupByFolder(files), [files]);

  const favSet = useMemo(() => new Set(prefs.favorite_paths), [prefs.favorite_paths]);

  const toggleFav = async (path: string) => {
    const next = new Set(favSet);
    if (next.has(path)) {
      next.delete(path);
    } else {
      next.add(path);
    }
    try {
      const p = await patchPreferences({ favorite_paths: [...next] });
      setPrefsLocal(p);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not update favorites");
    }
  };

  const pct =
    storage && storage.limit_bytes && storage.limit_bytes > 0
      ? Math.min(100, (storage.used_bytes / storage.limit_bytes) * 100)
      : 0;

  const onUpload: React.ChangeEventHandler<HTMLInputElement> = async (e) => {
    const input = e.target;
    const file = input.files?.[0];
    input.value = "";
    if (!file) {
      return;
    }
    const name = file.name;
    try {
      await uploadFile(name, file);
      setMsg(`Uploaded ${name}`);
      await load();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Upload failed");
    }
  };

  const onDownload = async (path: string) => {
    try {
      const blob = await downloadBlob(path);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = path.split("/").pop() ?? "download";
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Download failed");
    }
  };

  const onDelete = async (path: string) => {
    if (!window.confirm(`Delete ${path}?`)) {
      return;
    }
    try {
      await deleteFile(path);
      setMsg(`Deleted ${path}`);
      await load();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Delete failed");
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Files
      </Typography>
      {storage ? (
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Your storage: {(storage.used_bytes / (1024 * 1024)).toFixed(1)} MB
            {storage.limit_bytes
              ? ` of ${(storage.limit_bytes / (1024 * 1024)).toFixed(1)} MB`
              : ""}
          </Typography>
          <LinearProgress variant="determinate" value={pct} sx={{ mt: 1, height: 8, borderRadius: 1 }} />
        </Box>
      ) : null}
      <Box sx={{ mb: 2 }}>
        <Button variant="outlined" component="label" startIcon={<UploadIcon />}>
          Upload
          <input type="file" hidden onChange={onUpload} />
        </Button>
        <Button sx={{ ml: 1 }} onClick={() => void load()} disabled={loading}>
          Refresh
        </Button>
      </Box>
      {loading ? (
        <Typography variant="body2" color="text.secondary">
          Loading files…
        </Typography>
      ) : !err && files.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No files in your account yet. Upload from here or sync from the desktop app — files are listed from the
          server folder for your signed-in email.
        </Typography>
      ) : null}
      {[...grouped.entries()].map(([folder, rows]) => (
        <Box key={folder} sx={{ mb: 2 }}>
          <Typography variant="subtitle2" color="text.secondary">
            {folder}
          </Typography>
          <List dense>
            {rows.map((f) => (
              <ListItem
                key={f.path}
                secondaryAction={
                  <Box>
                    <IconButton aria-label="favorite" onClick={() => void toggleFav(f.path)} size="small">
                      {favSet.has(f.path) ? <StarIcon color="warning" /> : <StarBorderIcon />}
                    </IconButton>
                    <IconButton aria-label="download" onClick={() => void onDownload(f.path)} size="small">
                      <DownloadIcon />
                    </IconButton>
                    <IconButton aria-label="delete" onClick={() => void onDelete(f.path)} size="small">
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                }
              >
                <ListItemText primary={f.path.split("/").pop()} secondary={f.path} />
              </ListItem>
            ))}
          </List>
        </Box>
      ))}
      <Snackbar open={!!msg} autoHideDuration={4000} onClose={() => setMsg(null)} message={msg ?? ""} />
      <Snackbar open={!!err} onClose={() => setErr(null)}>
        <Alert severity="error" onClose={() => setErr(null)}>
          {err}
        </Alert>
      </Snackbar>
    </Box>
  );
}
