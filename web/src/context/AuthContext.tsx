import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  type MeUser,
  type Preferences,
  clientPing,
  fetchMe,
  fetchPreferences,
  logout as httpLogout,
} from "../api/http";

type AuthState = {
  user: MeUser | null;
  prefs: Preferences;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setPrefsLocal: (p: Preferences) => void;
  logout: () => void;
};

const defaultPrefs: Preferences = {
  theme: "system",
  content_background_image: null,
  content_background_opacity: 0.12,
  favorite_paths: [],
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeUser | null>(null);
  const [prefs, setPrefs] = useState<Preferences>(defaultPrefs);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const token = localStorage.getItem("bb_access_token");
    if (!token) {
      setUser(null);
      setPrefs(defaultPrefs);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [me, pr] = await Promise.all([fetchMe(), fetchPreferences()]);
      setUser(me);
      setPrefs(pr);
      void clientPing({}).catch(() => {});
    } catch (e) {
      setUser(null);
      setError(e instanceof Error ? e.message : "Session expired");
      httpLogout();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const logout = useCallback(() => {
    httpLogout();
    setUser(null);
    setPrefs(defaultPrefs);
  }, []);

  const value = useMemo(
    () => ({
      user,
      prefs,
      loading,
      error,
      reload,
      setPrefsLocal: setPrefs,
      logout,
    }),
    [user, prefs, loading, error, reload, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth outside AuthProvider");
  }
  return ctx;
}
