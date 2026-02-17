; Inno Setup script for Brandy Box (Windows, per-user install, no admin)
; Build: build the client with PyInstaller first, then run iscc brandybox.iss
; Requires: Inno Setup 6, and a built folder dist/BrandyBox with BrandyBox.exe

#define MyAppName "Brandy Box"
#define MyAppExe "BrandyBox.exe"
; Default path - override on command line or set below to your dist path
#define SourceDir "..\..\client\dist\BrandyBox"
#define InstallDir "{localappdata}\BrandyBox"

[Setup]
AppId=rocks.brandstaetter.brandybox
AppName={#MyAppName}
AppVersion=0.1.0
DefaultDirName={#InstallDir}
DefaultGroupName={#MyAppName}
OutputDir=..\..\client\dist
OutputBaseFilename=BrandyBox-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
DisableWelcomePage=no
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Start Brandy Box when I log in"; GroupDescription: "Startup"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not FileExists(ExpandConstant('{#SourceDir}\{#MyAppExe}')) then
  begin
    MsgBox('Build folder not found. Run PyInstaller first: pyinstaller client/brandybox.spec', mbError, MB_OK);
    Result := False;
  end;
end;
