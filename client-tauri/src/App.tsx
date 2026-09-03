import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { isPermissionGranted, requestPermission, sendNotification } from "@tauri-apps/plugin-notification";
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

  const refreshAuth = useCallback(async (): Promise<boolean> => {
    const storedEmail = await invoke<string | null>("get_stored_email").catch(() => null);
    if (!storedEmail) {
      setView("login");
      setEmail(null);
      await invoke("show_main_window").catch(() => {});
      return false;
    }
    const token = await invoke<string | null>("get_valid_access_token").catch(() => null);
    if (!token) {
      setView("login");
      setEmail(null);
      await invoke("show_main_window").catch(() => {});
      return false;
    }
    setEmail(storedEmail);
    setView("settings");
    return true;
  }, []);

  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  useEffect(() => {
    const unlistenPromise = listen<SyncStatusPayload>("sync-status", (event) => {
      const payload = event.payload;
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
  }, []);

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

  const handleLoginSuccess = useCallback(async () => {
    const ok = await refreshAuth();
    if (!ok) {
      throw new Error("Unable to establish authenticated session. Please check your connection and try again.");
    }
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
