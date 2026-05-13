; wheelmap installer (Inno Setup script)
;
; Usage:
;   1. Run build.bat first to produce dist\wheelmap\
;   2. Download ViGEmBus installer to installer\vendor\ViGEmBus.exe
;      (https://github.com/nefarius/ViGEmBus/releases/download/v1.22.0/ViGEmBus_1.22.0_x64_x86_arm64.exe)
;   3. Open this .iss in Inno Setup and click Compile
;   4. Output: installer\Output\wheelmap-setup.exe
;
; What it does:
;   - Installs wheelmap into Program Files\wheelmap\
;   - Runs the bundled ViGEmBus installer if the driver isn't already present
;   - Creates Start Menu and (optional) Desktop shortcuts
;   - Allows clean uninstall

#define MyAppName "wheelmap"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Arvind"
#define MyAppExeName "wheelmap.exe"

[Setup]
AppId={{C7E1B5F8-9A3E-4D2E-8C5B-7F4A6D8B1E22}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=wheelmap-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Bundle everything PyInstaller produced
Source: "..\dist\wheelmap\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; The ViGEmBus installer (download to installer\vendor\ before compiling)
Source: "vendor\ViGEmBus.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedsViGEmBus

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Install ViGEmBus silently if not present
Filename: "{tmp}\ViGEmBus.exe"; Parameters: "/S"; StatusMsg: "Installing ViGEmBus driver..."; Flags: waituntilterminated; Check: NeedsViGEmBus
; Offer to launch on finish
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function NeedsViGEmBus(): Boolean;
var
  ResultCode: Integer;
begin
  // sc.exe returns 0 if service exists, 1060 if it doesn't.
  Exec(ExpandConstant('{sys}\sc.exe'), 'query ViGEmBus', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := (ResultCode <> 0);
end;
