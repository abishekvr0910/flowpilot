; FlowPilot Inno Setup Script
; Generates standalone FlowPilot-Setup-v3.1.0.exe installer for Windows 10/11 x64
; Non-elevated (installs into user AppData without requiring Administrator privileges)

#define MyAppName "FlowPilot"
#define MyAppVersion "3.1.0"
#define MyAppPublisher "FlowPilot Open Source"
#define MyAppURL "https://github.com/abishekvr0910/flowpilot"
#define MyAppExeName "FlowPilot.exe"
#define MyAppSourceDir "..\dist\FlowPilot"

[Setup]
AppId={{5E731F28-5E79-4B55-9B7C-A5A412A34A89}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=FlowPilot-Setup-v{#MyAppVersion}
OutputDir=..\dist
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
SetupIconFile=..\assets\flowpilot_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
AppMutex=Global\FlowPilot_Desktop_SingleInstance_Mutex

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "runonstartup"; Description: "Start FlowPilot automatically when Windows starts"; GroupDescription: "Windows Startup Options:"

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Exclude scratch, local debug dumps, and logs from distribution
Source: "..\README.md"; DestDir: "{app}"; Flags: isreadme ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FlowPilot"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: runonstartup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
