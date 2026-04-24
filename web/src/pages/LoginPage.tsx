import GoogleIcon from "@mui/icons-material/Google";
import {
  Alert,
  Box,
  Button,
  Container,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { fetchMetaVersion, loginPassword, oauthComplete } from "../api/http";
import { useAuth } from "../context/AuthContext";

const errMap: Record<string, string> = {
  no_account: "No Brandy Box account for this Google user. Ask an admin to create your email first.",
  oauth_denied: "Google sign-in was cancelled.",
  oauth_invalid: "Sign-in session expired. Try again.",
  oauth_token: "Could not complete Google sign-in. Check server logs.",
  oauth_profile: "Could not read your Google profile.",
  oauth_account: "This Google account does not match the linked Brandy Box user.",
};

export default function LoginPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const { reload, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [googleAvailable, setGoogleAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    void fetchMetaVersion()
      .then((m) => setGoogleAvailable(m.google_signin_available))
      .catch(() => setGoogleAvailable(false));
  }, []);

  useEffect(() => {
    if (user) {
      navigate("/files", { replace: true });
    }
  }, [user, navigate]);

  useEffect(() => {
    const ex = params.get("exchange");
    const err = params.get("error");
    if (err) {
      setError(errMap[err] ?? "Sign-in failed.");
      setParams({}, { replace: true });
      return;
    }
    if (!ex) {
      return;
    }
    setBusy(true);
    oauthComplete(ex)
      .then(() => reload())
      .catch((e) => setError(e instanceof Error ? e.message : "Exchange failed"))
      .finally(() => {
        setBusy(false);
        setParams({}, { replace: true });
      });
  }, [params, setParams, reload]);

  const onPassword = async () => {
    setError(null);
    setBusy(true);
    try {
      await loginPassword(email.trim(), password);
      await reload();
      navigate("/files", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  const googleStart = () => {
    window.location.href = "/api/auth/google/start";
  };

  return (
    <Container maxWidth="sm" sx={{ pt: 8 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Brandy Box
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          Sign in to access your files in the browser.
          {googleAvailable === false ? (
            <> Google sign-in is not enabled on this server; use email and password.</>
          ) : null}
        </Typography>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <TextField
          label="Email"
          type="email"
          fullWidth
          margin="normal"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
        />
        <TextField
          label="Password"
          type="password"
          fullWidth
          margin="normal"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 1 }}>
          <Button variant="contained" disabled={busy} onClick={() => void onPassword()}>
            Sign in
          </Button>
          {googleAvailable ? (
            <Button variant="outlined" startIcon={<GoogleIcon />} disabled={busy} onClick={googleStart}>
              Continue with Google
            </Button>
          ) : null}
        </Box>
      </Paper>
    </Container>
  );
}
