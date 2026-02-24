import { getCurrentWindow } from "@tauri-apps/api/window";
import { invoke } from "@tauri-apps/api/core";
import { Box, IconButton } from "@mui/material";
import Close from "@mui/icons-material/Close";
import Remove from "@mui/icons-material/Remove";
import CropSquare from "@mui/icons-material/CropSquare";

const appWindow = getCurrentWindow();

export default function TitleBar() {
  return (
    <Box
      data-tauri-drag-region
      sx={{
        height: 32,
        minHeight: 32,
        background: "#1a73e8",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingLeft: 1,
        paddingRight: 0,
        userSelect: "none",
        "-webkit-app-region": "drag",
        appRegion: "drag",
      }}
    >
      <Box component="span" sx={{ fontSize: 13, fontWeight: 600 }}>
        Brandy Box
      </Box>
      <Box sx={{ "-webkit-app-region": "no-drag", appRegion: "no-drag", display: "flex" }}>
        <IconButton
          size="small"
          sx={{ color: "inherit", borderRadius: 0, "&:hover": { bgcolor: "rgba(255,255,255,0.15)" } }}
          onClick={() => appWindow.minimize()}
        >
          <Remove fontSize="small" />
        </IconButton>
        <IconButton
          size="small"
          sx={{ color: "inherit", borderRadius: 0, "&:hover": { bgcolor: "rgba(255,255,255,0.15)" } }}
          onClick={() => appWindow.toggleMaximize()}
        >
          <CropSquare fontSize="small" />
        </IconButton>
        <IconButton
          size="small"
          sx={{
            color: "inherit",
            borderRadius: 0,
            "&:hover": { bgcolor: "rgba(255,255,255,0.2)" },
          }}
          onClick={() => invoke("hide_main_window")}
        >
          <Close fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );
}
