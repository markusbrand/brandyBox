import MenuIcon from "@mui/icons-material/Menu";
import FolderIcon from "@mui/icons-material/Folder";
import SettingsIcon from "@mui/icons-material/Settings";
import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { apiFetchAuth, USER_BACKGROUND_IMAGE_SENTINEL } from "../api/http";
import { useAuth } from "../context/AuthContext";

const drawerWidth = 240;

export default function AppLayout() {
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));
  const [open, setOpen] = useState(!mobile);
  const navigate = useNavigate();
  const loc = useLocation();
  const { user, prefs, logout } = useAuth();

  /** Blob URL when prefs use the server-stored upload sentinel (CSS url() cannot send JWT). */
  const [bgBlobUrl, setBgBlobUrl] = useState<string | null>(null);
  const bgBlobRef = useRef<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    const raw = prefs.content_background_image?.trim();

    if (raw !== USER_BACKGROUND_IMAGE_SENTINEL) {
      if (bgBlobRef.current) {
        URL.revokeObjectURL(bgBlobRef.current);
        bgBlobRef.current = null;
      }
      setBgBlobUrl(null);
      return () => ac.abort();
    }

    if (bgBlobRef.current) {
      URL.revokeObjectURL(bgBlobRef.current);
      bgBlobRef.current = null;
    }
    setBgBlobUrl(null);

    void (async () => {
      try {
        const res = await apiFetchAuth("/api/users/me/background-image", { signal: ac.signal });
        if (!res.ok) {
          return;
        }
        const blob = await res.blob();
        if (ac.signal.aborted) {
          return;
        }
        const u = URL.createObjectURL(blob);
        if (bgBlobRef.current) {
          URL.revokeObjectURL(bgBlobRef.current);
        }
        bgBlobRef.current = u;
        setBgBlobUrl(u);
      } catch {
        /* aborted or network */
      }
    })();

    return () => {
      ac.abort();
      if (bgBlobRef.current) {
        URL.revokeObjectURL(bgBlobRef.current);
        bgBlobRef.current = null;
      }
      setBgBlobUrl(null);
    };
  }, [prefs.content_background_image]);

  const drawer = (
    <Box sx={{ width: drawerWidth, pt: 2 }}>
      <Typography variant="subtitle2" sx={{ px: 2, pb: 1, color: "text.secondary" }}>
        {user?.email}
      </Typography>
      <List>
        <ListItemButton selected={loc.pathname.startsWith("/files")} onClick={() => navigate("/files")}>
          <ListItemIcon>
            <FolderIcon />
          </ListItemIcon>
          <ListItemText primary="Files" />
        </ListItemButton>
        <ListItemButton selected={loc.pathname.startsWith("/settings")} onClick={() => navigate("/settings")}>
          <ListItemIcon>
            <SettingsIcon />
          </ListItemIcon>
          <ListItemText primary="Settings" />
        </ListItemButton>
      </List>
    </Box>
  );

  const rawBg = prefs.content_background_image?.trim();
  const bgUrl =
    rawBg === USER_BACKGROUND_IMAGE_SENTINEL ? bgBlobUrl : rawBg && rawBg.length > 0 ? rawBg : null;
  const opacity = prefs.content_background_opacity ?? 0.12;

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        position="fixed"
        sx={{
          zIndex: (t) => t.zIndex.drawer + 1,
          paddingTop: "env(safe-area-inset-top)",
        }}
      >
        <Toolbar>
          <IconButton color="inherit" edge="start" onClick={() => setOpen((o) => !o)} sx={{ mr: 1 }}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Brandy Box
          </Typography>
          <Typography
            variant="body2"
            sx={{ cursor: "pointer", mr: 1 }}
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </Typography>
        </Toolbar>
      </AppBar>
      {mobile ? (
        <Drawer open={open} onClose={() => setOpen(false)} ModalProps={{ keepMounted: true }}>
          {drawer}
        </Drawer>
      ) : (
        <Drawer variant="persistent" open={open} sx={{ width: open ? drawerWidth : 0, flexShrink: 0 }}>
          {drawer}
        </Drawer>
      )}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          pt: (t) => `calc(56px + ${t.spacing(2)} + env(safe-area-inset-top))`,
          px: 2,
          pb: 4,
          width: "100%",
          position: "relative",
          backgroundColor: "background.default",
        }}
      >
        {bgUrl ? (
          <Box
            aria-hidden
            sx={{
              position: "fixed",
              inset: 0,
              zIndex: 0,
              backgroundImage: `url(${JSON.stringify(bgUrl)})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
              opacity,
              pointerEvents: "none",
            }}
          />
        ) : null}
        <Box sx={{ position: "relative", zIndex: 1 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
