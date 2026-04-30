import ArticleIcon from "@mui/icons-material/Article";
import AudioFileIcon from "@mui/icons-material/AudioFile";
import CodeIcon from "@mui/icons-material/Code";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import DeleteIcon from "@mui/icons-material/Delete";
import DescriptionIcon from "@mui/icons-material/Description";
import DownloadIcon from "@mui/icons-material/Download";
import DriveFolderUploadIcon from "@mui/icons-material/DriveFolderUpload";
import FolderIcon from "@mui/icons-material/Folder";
import FolderZipIcon from "@mui/icons-material/FolderZip";
import HomeIcon from "@mui/icons-material/Home";
import ImageIcon from "@mui/icons-material/Image";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import MovieIcon from "@mui/icons-material/Movie";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import SlideshowIcon from "@mui/icons-material/Slideshow";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import TableChartIcon from "@mui/icons-material/TableChart";
import UploadIcon from "@mui/icons-material/Upload";
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  LinearProgress,
  Link as MuiLink,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemSecondaryAction,
  ListItemText,
  Paper,
  Snackbar,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createFolder,
  deleteFile,
  downloadBlob,
  fetchStorage,
  listFiles,
  listFolders,
  patchPreferences,
  uploadFile,
  type FileRow,
  type FolderRow,
  type StorageInfo,
} from "../api/http";
import { useAuth } from "../context/AuthContext";

/** Entry shown at the current folder level. */
type Entry =
  | { kind: "parent" }
  | { kind: "folder"; name: string; path: string; childCount: number }
  | { kind: "file"; name: string; path: string; mtime: number; size?: number };

/**
 * Build the entries shown at `currentFolder`. Folders come from two sources:
 *   - inferred from file paths under `currentFolder` (gives us `childCount`)
 *   - the explicit folder list from the backend (covers truly-empty folders
 *     created via "New folder" but not yet populated with files)
 *
 * Files come from the file list. A "..\u00a0parent" entry is prepended when
 * the user is not at the root.
 */
function entriesForFolder(
  files: FileRow[],
  folders: FolderRow[],
  currentFolder: string,
): Entry[] {
  const prefix = currentFolder ? currentFolder + "/" : "";
  const folderCounts = new Map<string, number>();
  const fileEntries: Entry[] = [];

  for (const f of files) {
    if (currentFolder && !f.path.startsWith(prefix)) {
      continue;
    }
    const rest = currentFolder ? f.path.slice(prefix.length) : f.path;
    if (!rest) {
      continue;
    }
    const slash = rest.indexOf("/");
    if (slash === -1) {
      fileEntries.push({
        kind: "file",
        name: rest,
        path: f.path,
        mtime: f.mtime,
        size: f.size,
      });
    } else {
      const folderName = rest.slice(0, slash);
      folderCounts.set(folderName, (folderCounts.get(folderName) ?? 0) + 1);
    }
  }

  // Pick up empty folders (and folders not yet covered by file inference) at
  // exactly this level only.
  const folderNames = new Set<string>(folderCounts.keys());
  for (const d of folders) {
    if (!d.path) {
      continue;
    }
    if (currentFolder && !d.path.startsWith(prefix) && d.path !== currentFolder) {
      continue;
    }
    const rest = currentFolder ? d.path.slice(prefix.length) : d.path;
    if (!rest) {
      continue;
    }
    if (rest.includes("/")) {
      continue;
    }
    folderNames.add(rest);
    if (!folderCounts.has(rest)) {
      folderCounts.set(rest, 0);
    }
  }

  const folderEntries: Entry[] = [...folderNames]
    .map((name) => ({
      kind: "folder" as const,
      name,
      path: prefix + name,
      childCount: folderCounts.get(name) ?? 0,
    }))
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));

  fileEntries.sort((a, b) =>
    a.kind === "file" && b.kind === "file"
      ? a.name.localeCompare(b.name, undefined, { sensitivity: "base" })
      : 0,
  );

  const out: Entry[] = [];
  if (currentFolder) {
    out.push({ kind: "parent" });
  }
  out.push(...folderEntries, ...fileEntries);
  return out;
}

const EXT_GROUPS: Array<{ exts: string[]; icon: ReactNode }> = [
  {
    exts: ["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "ico", "heic", "heif", "tif", "tiff"],
    icon: <ImageIcon sx={{ color: "#26A69A" }} />,
  },
  {
    exts: ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "mpeg", "mpg"],
    icon: <MovieIcon sx={{ color: "#EF5350" }} />,
  },
  {
    exts: ["mp3", "wav", "flac", "ogg", "aac", "m4a", "wma", "opus"],
    icon: <AudioFileIcon sx={{ color: "#AB47BC" }} />,
  },
  {
    exts: ["pdf"],
    icon: <PictureAsPdfIcon sx={{ color: "#E53935" }} />,
  },
  {
    exts: ["doc", "docx", "odt", "rtf"],
    icon: <DescriptionIcon sx={{ color: "#1E88E5" }} />,
  },
  {
    exts: ["xls", "xlsx", "ods", "csv", "tsv"],
    icon: <TableChartIcon sx={{ color: "#43A047" }} />,
  },
  {
    exts: ["ppt", "pptx", "odp", "key"],
    icon: <SlideshowIcon sx={{ color: "#FB8C00" }} />,
  },
  {
    exts: ["txt", "md", "log", "ini", "cfg", "conf", "yml", "yaml", "toml", "env"],
    icon: <ArticleIcon sx={{ color: "#78909C" }} />,
  },
  {
    exts: [
      "js", "ts", "tsx", "jsx", "py", "rs", "go", "java", "c", "cpp", "h",
      "hpp", "cs", "rb", "php", "sh", "bash", "zsh", "sql", "html", "htm",
      "css", "scss", "sass", "less", "json", "xml", "kt", "swift", "dart",
    ],
    icon: <CodeIcon sx={{ color: "#5C6BC0" }} />,
  },
  {
    exts: ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz", "tbz2", "zst"],
    icon: <FolderZipIcon sx={{ color: "#8D6E63" }} />,
  },
];

/** Pick a Material icon for a file based on its extension. */
function fileIconFor(name: string): ReactNode {
  const dot = name.lastIndexOf(".");
  const ext = dot >= 0 && dot < name.length - 1 ? name.slice(dot + 1).toLowerCase() : "";
  if (ext) {
    for (const group of EXT_GROUPS) {
      if (group.exts.includes(ext)) {
        return group.icon;
      }
    }
  }
  return <InsertDriveFileIcon sx={{ color: "text.secondary" }} />;
}

/** Format a unix timestamp (seconds) for compact display. */
function formatMtime(ts: number): string {
  if (!ts || !Number.isFinite(ts)) {
    return "";
  }
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) {
    return "";
  }
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Format a byte count using binary units (1024). */
function formatBytes(bytes: number | undefined): string {
  if (bytes === undefined || !Number.isFinite(bytes) || bytes < 0) {
    return "";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ["KB", "MB", "GB", "TB", "PB"];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value < 10 ? value.toFixed(1) : Math.round(value)} ${units[i]}`;
}

/**
 * Quick client-side check matching the backend's segment validation. Used to
 * reject obvious garbage before hitting the network. The backend remains the
 * source of truth.
 */
function validateNewFolderName(name: string): string | null {
  const trimmed = name.trim();
  if (!trimmed) {
    return "Name cannot be empty.";
  }
  if (trimmed === "." || trimmed === "..") {
    return "That name is reserved.";
  }
  if (/[\\/]/.test(trimmed)) {
    return "Name cannot contain '/' or '\\\\'.";
  }
  if (/[\u0000-\u001F]/.test(trimmed)) {
    return "Name cannot contain control characters.";
  }
  return null;
}

export default function FilesPage() {
  const { prefs, setPrefsLocal } = useAuth();
  const [files, setFiles] = useState<FileRow[]>([]);
  const [folders, setFolders] = useState<FolderRow[]>([]);
  const [storage, setStorage] = useState<StorageInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [currentFolder, setCurrentFolder] = useState<string>("");

  const [newFolderOpen, setNewFolderOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [newFolderError, setNewFolderError] = useState<string | null>(null);
  const [newFolderBusy, setNewFolderBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [fl, dl, st] = await Promise.all([listFiles(), listFolders(), fetchStorage()]);
      setFiles(fl);
      setFolders(dl);
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

  const entries = useMemo(
    () => entriesForFolder(files, folders, currentFolder),
    [files, folders, currentFolder],
  );

  // If the user is inside a folder that no longer exists (e.g. last file
  // deleted, or remote sync removed it), step up the hierarchy until we find
  // a level that still has content (or the root). The "parent" entry doesn't
  // count as content for this purpose.
  useEffect(() => {
    if (loading || !currentFolder) {
      return;
    }
    const realEntries = entries.filter((e) => e.kind !== "parent");
    if (realEntries.length > 0) {
      return;
    }
    const stillExistsInFiles = files.some(
      (f) => f.path === currentFolder || f.path.startsWith(currentFolder + "/"),
    );
    const stillExistsInFolders = folders.some(
      (d) => d.path === currentFolder || d.path.startsWith(currentFolder + "/"),
    );
    if (!stillExistsInFiles && !stillExistsInFolders) {
      const parts = currentFolder.split("/");
      parts.pop();
      setCurrentFolder(parts.join("/"));
    }
  }, [entries, currentFolder, files, folders, loading]);

  const favSet = useMemo(() => new Set(prefs.favorite_paths), [prefs.favorite_paths]);

  const goUp = useCallback(() => {
    setCurrentFolder((cur) => {
      if (!cur) {
        return cur;
      }
      const parts = cur.split("/");
      parts.pop();
      return parts.join("/");
    });
  }, []);

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
    const targetPath = currentFolder ? `${currentFolder}/${file.name}` : file.name;
    try {
      await uploadFile(targetPath, file);
      setMsg(`Uploaded ${targetPath}`);
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

  const openNewFolderDialog = () => {
    setNewFolderName("");
    setNewFolderError(null);
    setNewFolderOpen(true);
  };

  const submitNewFolder = async () => {
    const validation = validateNewFolderName(newFolderName);
    if (validation) {
      setNewFolderError(validation);
      return;
    }
    const name = newFolderName.trim();
    const target = currentFolder ? `${currentFolder}/${name}` : name;
    setNewFolderBusy(true);
    try {
      const result = await createFolder(target);
      setMsg(
        result.created
          ? `Created folder ${target}`
          : `Folder ${target} already exists`,
      );
      setNewFolderOpen(false);
      await load();
      setCurrentFolder(target);
    } catch (ex) {
      setNewFolderError(ex instanceof Error ? ex.message : "Could not create folder");
    } finally {
      setNewFolderBusy(false);
    }
  };

  const folderSegments = currentFolder ? currentFolder.split("/") : [];
  const hasAnyContent = files.length > 0 || folders.length > 0;

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
          <LinearProgress
            variant="determinate"
            value={pct}
            sx={{ mt: 1, height: 8, borderRadius: 1 }}
          />
        </Box>
      ) : null}

      <Stack direction="row" spacing={1} sx={{ mb: 2 }} alignItems="center" flexWrap="wrap">
        <Button variant="contained" component="label" startIcon={<UploadIcon />}>
          Upload here
          <input type="file" hidden onChange={onUpload} />
        </Button>
        <Button
          variant="outlined"
          startIcon={<CreateNewFolderIcon />}
          onClick={openNewFolderDialog}
        >
          New folder
        </Button>
        <Button variant="outlined" onClick={() => void load()} disabled={loading}>
          Refresh
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        {currentFolder ? (
          <Typography variant="caption" color="text.secondary">
            Uploads will go into <strong>{currentFolder}</strong>
          </Typography>
        ) : (
          <Typography variant="caption" color="text.secondary">
            Uploads will go into your <strong>home</strong> folder
          </Typography>
        )}
      </Stack>

      <Paper
        variant="outlined"
        sx={{
          px: 2,
          py: 1,
          mb: 1,
          backgroundColor: (t) =>
            t.palette.mode === "dark"
              ? "rgba(255,255,255,0.04)"
              : "rgba(0,0,0,0.02)",
        }}
      >
        <Breadcrumbs aria-label="folder path" separator="/">
          {folderSegments.length === 0 ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <HomeIcon fontSize="small" sx={{ color: "primary.main" }} />
              <Typography color="text.primary" sx={{ fontWeight: 500 }}>
                home
              </Typography>
            </Box>
          ) : (
            <MuiLink
              component="button"
              underline="hover"
              color="inherit"
              onClick={() => setCurrentFolder("")}
              sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
            >
              <HomeIcon fontSize="small" />
              home
            </MuiLink>
          )}
          {folderSegments.map((seg, idx) => {
            const isLast = idx === folderSegments.length - 1;
            const segPath = folderSegments.slice(0, idx + 1).join("/");
            if (isLast) {
              return (
                <Typography key={segPath} color="text.primary" sx={{ fontWeight: 500 }}>
                  {seg}
                </Typography>
              );
            }
            return (
              <MuiLink
                key={segPath}
                component="button"
                underline="hover"
                color="inherit"
                onClick={() => setCurrentFolder(segPath)}
              >
                {seg}
              </MuiLink>
            );
          })}
        </Breadcrumbs>
      </Paper>

      {loading ? (
        <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
          Loading files…
        </Typography>
      ) : !err && !hasAnyContent ? (
        <Paper variant="outlined" sx={{ p: 3, textAlign: "center" }}>
          <Typography variant="body1" color="text.secondary" gutterBottom>
            No files in your account yet.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Upload from here, create a folder, or sync from the desktop app — files are listed from
            the server folder for your signed-in email.
          </Typography>
        </Paper>
      ) : entries.length === 0 || (entries.length === 1 && entries[0].kind === "parent") ? (
        <Paper variant="outlined">
          <List disablePadding>
            {currentFolder ? renderParentRow(goUp, true) : null}
            <Box sx={{ p: 3, textAlign: "center" }}>
              <Typography variant="body2" color="text.secondary">
                This folder is empty.
              </Typography>
            </Box>
          </List>
        </Paper>
      ) : (
        <Paper variant="outlined">
          <List disablePadding>
            {entries.map((entry, idx) => {
              const isLast = idx === entries.length - 1;
              const rowSx = {
                borderBottom: isLast ? 0 : 1,
                borderColor: "divider",
              } as const;

              if (entry.kind === "parent") {
                return (
                  <ListItemButton key="parent" onClick={goUp} sx={rowSx}>
                    <ListItemIcon sx={{ minWidth: 44 }}>
                      <DriveFolderUploadIcon sx={{ color: "text.secondary" }} />
                    </ListItemIcon>
                    <ListItemText
                      primary=".."
                      secondary="Parent folder"
                      primaryTypographyProps={{ fontWeight: 500 }}
                    />
                  </ListItemButton>
                );
              }

              if (entry.kind === "folder") {
                const empty = entry.childCount === 0;
                return (
                  <ListItemButton
                    key={"d:" + entry.path}
                    onClick={() => setCurrentFolder(entry.path)}
                    sx={rowSx}
                  >
                    <ListItemIcon sx={{ minWidth: 44 }}>
                      <FolderIcon sx={{ color: "#FFB300" }} />
                    </ListItemIcon>
                    <ListItemText
                      primary={entry.name}
                      secondary={
                        empty
                          ? "Empty folder"
                          : `${entry.childCount} item${entry.childCount === 1 ? "" : "s"}`
                      }
                      primaryTypographyProps={{ fontWeight: 500 }}
                    />
                  </ListItemButton>
                );
              }

              const fav = favSet.has(entry.path);
              const sizeStr = formatBytes(entry.size);
              const dateStr = formatMtime(entry.mtime);
              const secondary = [sizeStr, dateStr].filter(Boolean).join(" · ");
              return (
                <ListItemButton
                  key={"f:" + entry.path}
                  onClick={() => void onDownload(entry.path)}
                  sx={{ ...rowSx, pr: 16 }}
                >
                  <ListItemIcon sx={{ minWidth: 44 }}>{fileIconFor(entry.name)}</ListItemIcon>
                  <ListItemText primary={entry.name} secondary={secondary} />
                  <ListItemSecondaryAction>
                    <Tooltip title={fav ? "Remove from favorites" : "Add to favorites"}>
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={(ev) => {
                          ev.stopPropagation();
                          void toggleFav(entry.path);
                        }}
                      >
                        {fav ? <StarIcon color="warning" /> : <StarBorderIcon />}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Download">
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={(ev) => {
                          ev.stopPropagation();
                          void onDownload(entry.path);
                        }}
                      >
                        <DownloadIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={(ev) => {
                          ev.stopPropagation();
                          void onDelete(entry.path);
                        }}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </ListItemSecondaryAction>
                </ListItemButton>
              );
            })}
          </List>
        </Paper>
      )}

      <Dialog
        open={newFolderOpen}
        onClose={() => (newFolderBusy ? null : setNewFolderOpen(false))}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>New folder</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Create an empty folder inside{" "}
            <strong>{currentFolder ? currentFolder : "home"}</strong>.
          </DialogContentText>
          <TextField
            autoFocus
            fullWidth
            label="Folder name"
            value={newFolderName}
            onChange={(e) => {
              setNewFolderName(e.target.value);
              if (newFolderError) {
                setNewFolderError(null);
              }
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void submitNewFolder();
              }
            }}
            error={!!newFolderError}
            helperText={newFolderError ?? "Letters, numbers, spaces, '.', '_', '-', '()', '+' are allowed."}
            disabled={newFolderBusy}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewFolderOpen(false)} disabled={newFolderBusy}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => void submitNewFolder()}
            disabled={newFolderBusy || !newFolderName.trim()}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!msg}
        autoHideDuration={4000}
        onClose={() => setMsg(null)}
        message={msg ?? ""}
      />
      <Snackbar open={!!err} onClose={() => setErr(null)}>
        <Alert severity="error" onClose={() => setErr(null)}>
          {err}
        </Alert>
      </Snackbar>
    </Box>
  );
}

/** Render the ".." parent row when the current folder is empty. */
function renderParentRow(onUp: () => void, withDivider: boolean): ReactNode {
  return (
    <ListItemButton
      key="parent"
      onClick={onUp}
      sx={{
        borderBottom: withDivider ? 1 : 0,
        borderColor: "divider",
      }}
    >
      <ListItemIcon sx={{ minWidth: 44 }}>
        <DriveFolderUploadIcon sx={{ color: "text.secondary" }} />
      </ListItemIcon>
      <ListItemText
        primary=".."
        secondary="Parent folder"
        primaryTypographyProps={{ fontWeight: 500 }}
      />
    </ListItemButton>
  );
}
