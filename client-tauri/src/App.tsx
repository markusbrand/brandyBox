import { useState, useEffect, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { defaultWindowIcon } from "@tauri-apps/api/app";
import { resolveResource } from "@tauri-apps/api/path";
import { listen } from "@tauri-apps/api/event";
import { isPermissionGranted, requestPermission, sendNotification } from "@tauri-apps/plugin-notification";
import { TrayIcon } from "@tauri-apps/api/tray";
import { Menu } from "@tauri-apps/api/menu";
import { Box, ThemeProvider, createTheme, CssBaseline } from "@mui/material";
import Login from "./Login";
import Settings from "./Settings";
import TitleBar from "./TitleBar";

type SyncStatus = "idle" | "syncing" | "synced" | "warning" | "error";

interface SyncStatusPayload {
  status: SyncStatus;
  message?: string | null;
}

const SYNC_NOTIFY_THRESHOLD_BYTES = 5 * 1024 * 1024; // 5 MB

interface SyncCompletedPayload {
  bytesDownloaded: number;
  bytesUploaded: number;
}

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#1a73e8" },
    background: { default: "#f5f5f5", paper: "#ffffff" },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

export default function App() {
  const [view, setView] = useState<"loading" | "login" | "settings">("loading");
  const [email, setEmail] = useState<string | null>(null);
  const [tray, setTray] = useState<TrayIcon | null>(null);
  const trayRef = useRef<TrayIcon | null>(null);

  const refreshAuth = useCallback(async () => {
    const storedEmail = await invoke<string | null>("get_stored_email").catch(() => null);
    if (!storedEmail) {
      setView("login");
      setEmail(null);
      return;
    }
    const token = await invoke<string | null>("get_valid_access_token").catch(() => null);
    if (!token) {
      setView("login");
      setEmail(null);
      return;
    }
    setEmail(storedEmail);
    setView("settings");
  }, []);

  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  // Window is shown only when user clicks "Settings" in tray (show_main_window).
  // Never auto-show on startup.

  /** Preloaded paths: blue = idle/synced, yellow = syncing, red = error. Set at tray init. */
  const stateIconsRef = useRef<{ blue: string; yellow: string; red: string } | null>(null);

  const updateTrayFromStatus = useCallback(
    (trayIcon: TrayIcon | null, payload: SyncStatusPayload) => {
      if (!trayIcon) return;
      const icons = stateIconsRef.current;
      if (!icons) return;
      const { status, message } = payload;
      const tooltip =
        status === "error" && message
          ? `Brandy Box – Error: ${message.slice(0, 80)}`
          : status === "warning" && message
            ? `Brandy Box – ${message.slice(0, 80)}`
            : status === "syncing"
              ? "Brandy Box – Syncing…"
              : "Brandy Box";
      try {
        trayIcon.setTooltip(tooltip);
      } catch {
        try {
          trayIcon.setTitle(tooltip);
        } catch (_) {}
      }
      let path =
        status === "syncing" || status === "warning"
          ? icons.yellow
          : status === "error"
            ? icons.red
            : icons.blue;
      if (path) {
        trayIcon.setIcon(path).catch(() => {});
      } else {
        const name =
          status === "syncing" || status === "warning"
            ? "icon_syncing.png"
            : status === "error"
              ? "icon_error.png"
              : "icon_synced.png";
        resolveResource(`icons/${name}`)
          .then((p) => {
            if (p && stateIconsRef.current) {
              if (status === "syncing") stateIconsRef.current.yellow = p;
              else if (status === "error") stateIconsRef.current.red = p;
              else stateIconsRef.current.blue = p;
              trayIcon.setIcon(p).catch(() => {});
            }
          })
          .catch(() => {});
      }
    },
    []
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const menu = await Menu.new({
          items: [
            {
              id: "settings",
              text: "Settings",
              action: async () => {
                await invoke("show_main_window").catch((e) => console.error("show_main_window failed", e));
              },
            },
            {
              id: "open_folder",
              text: "Open folder",
              action: async () => {
                await invoke("open_sync_folder").catch(() => {});
              },
            },
            {
              id: "sync_now",
              text: "Sync now",
              action: async () => {
                await invoke("run_sync").catch(() => {});
              },
            },
            { item: "Separator" },
            {
              id: "quit",
              text: "Quit",
              action: async () => {
                await invoke("quit_app");
              },
            },
          ],
        });
        if (cancelled) return;
        const fallback = await resolveResource("icons/32x32.png").catch(() => null);
        const defaultIcon = fallback ?? (await defaultWindowIcon().catch(() => null)) ?? undefined;
        const blue =
          (await resolveResource("icons/icon_synced.png").catch(() => null)) ?? fallback ?? "";
        const yellow =
          (await resolveResource("icons/icon_syncing.png").catch(() => null)) ?? fallback ?? "";
        const red =
          (await resolveResource("icons/icon_error.png").catch(() => null)) ?? fallback ?? "";
        stateIconsRef.current = { blue, yellow, red };
        const trayIcon = await TrayIcon.new({
          icon: blue || defaultIcon,
          tooltip: "Brandy Box",
          menu,
          menuOnLeftClick: true,
        });
        if (cancelled) {
          trayIcon.close?.();
          return;
        }
        trayRef.current = trayIcon;
        setTray(trayIcon);
        const initial = await invoke<SyncStatusPayload>("get_sync_status").catch(() => ({
          status: "idle" as SyncStatus,
          message: null,
        }));
        updateTrayFromStatus(trayIcon, initial);
      } catch (e) {
        console.error("Tray init failed:", e);
      }
    })();
    return () => {
      cancelled = true;
      trayRef.current?.close?.();
      trayRef.current = null;
    };
  }, [updateTrayFromStatus]);

  useEffect(() => {
    if (!tray) return;
    const unlistenPromise = listen<SyncStatusPayload>("sync-status", (event) => {
      const payload = event.payload;
      updateTrayFromStatus(tray, payload);
      if (payload.status === "error" && payload.message) {
        const message = payload.message;
        (async () => {
          try {
            let granted = await isPermissionGranted();
            if (!granted) {
              const perm = await requestPermission();
              granted = perm === "granted";
            }
            if (granted) {
              await sendNotification({
                title: "Brandy Box – Sync failed",
                body: message.slice(0, 200),
              });
            }
          } catch (_) {}
        })();
      }
    });
    return () => {
      unlistenPromise.then((fn) => fn());
    };
  }, [tray, updateTrayFromStatus]);

  useEffect(() => {
    const unlistenPromise = listen<SyncCompletedPayload>("sync-completed", (event) => {
      const { bytesDownloaded = 0, bytesUploaded = 0 } = event.payload;
      const total = bytesDownloaded + bytesUploaded;
      if (total < SYNC_NOTIFY_THRESHOLD_BYTES) return;
      (async () => {
        try {
          let granted = await isPermissionGranted();
          if (!granted) {
            const perm = await requestPermission();
            granted = perm === "granted";
          }
          if (granted) {
            await sendNotification({
              title: "Brandy Box",
              body: "Sync finished successfully.",
            });
          }
        } catch (_) {}
      })();
    });
    return () => {
      unlistenPromise.then((fn) => fn());
    };
  }, []);

  const handleLoginSuccess = useCallback(() => {
    refreshAuth();
  }, [refreshAuth]);

  const handleLogout = useCallback(async () => {
    await invoke("logout");
    setEmail(null);
    setView("login");
  }, []);

  if (view === "loading") {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box sx={{ display: "flex", flexDirection: "column", height: "100vh" }}>
          <TitleBar />
          <Box sx={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            Loading…
          </Box>
        </Box>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
        <TitleBar />
        <Box sx={{ flex: 1, overflow: "auto" }}>
          {view === "login" ? (
            <Login onSuccess={handleLoginSuccess} onCancel={undefined} />
          ) : (
            <Settings email={email} onLogout={handleLogout} />
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}
