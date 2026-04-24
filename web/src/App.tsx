import { ThemeProvider, createTheme } from "@mui/material/styles";
import { useMemo } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AppLayout from "./components/AppLayout";
import FilesPage from "./pages/FilesPage";
import LoginPage from "./pages/LoginPage";
import SettingsPage from "./pages/SettingsPage";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return null;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function ThemedShell({ children }: { children: React.ReactNode }) {
  const { prefs } = useAuth();
  const mode = useMemo(() => {
    if (prefs.theme === "dark") {
      return "dark";
    }
    if (prefs.theme === "light") {
      return "light";
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }, [prefs.theme]);

  const theme = useMemo(
    () =>
      createTheme({
        palette: { mode },
        cssVariables: true,
      }),
    [mode],
  );

  return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
}

export default function App() {
  return (
    <AuthProvider>
      <ThemedShell>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <Protected>
                <AppLayout />
              </Protected>
            }
          >
            <Route index element={<Navigate to="/files" replace />} />
            <Route path="files" element={<FilesPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/files" replace />} />
        </Routes>
      </ThemedShell>
    </AuthProvider>
  );
}
