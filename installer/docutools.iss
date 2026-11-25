; =====================================================================
; Inno Setup Script for DocuTools Desktop Suite
; Permanent Professional Windows Application Installer & Clean Uninstaller
; =====================================================================

#define MyAppName "DocuTools"
#define MyAppFullName "DocuTools Desktop Suite"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DocuTools"
#define MyAppURL "https://github.com/Yashborse4/PDF-Image-Compressor"
#define MyAppExeName "DocuTools.exe"
#define MyProgId "DocuTools.Document"

[Setup]
; Permanent Unique AppId - STABLE for clean upgrades and uninstalls
AppId={{9F7B3E42-6D39-44F1-8B6C-7132924A22F0}
AppName={#MyAppFullName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppFullName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Source directory relative to script root
SourceDir=..

; Install Directory: 64-bit Program Files if admin, or AppData\Programs if standard user
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=dist\installer
OutputBaseFilename=DocuTools-Setup-v{#MyAppVersion}
SetupIconFile=docutools\assets\icon.ico
UninstallDisplayName={#MyAppFullName}
UninstallDisplayIcon={app}\{#MyAppExeName}

; 64-bit Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Privilege elevation handling (per-user by default, user can choose 'all users' via dialog)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline

; Compression & Engine
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; System Integration
ChangesAssociations=yes
CloseApplications=yes
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Complete application distribution payload
Source: "dist\DocuTools\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "docutools\assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; Clean up previous internal bundles on update to prevent orphaned libraries
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"; Comment: "Universal Offline Document & PDF Suite"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"; Comment: "Universal Offline Document & PDF Suite"; Tasks: desktopicon

[Registry]
; --- ProgID registration for DocuTools ---
Root: HKA; Subkey: "Software\Classes\{#MyProgId}"; ValueType: string; ValueData: "PDF Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyProgId}\DefaultIcon"; ValueType: string; ValueData: "{app}\icon.ico,0"
Root: HKA; Subkey: "Software\Classes\{#MyProgId}\shell\open"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#MyAppFullName}"
Root: HKA; Subkey: "Software\Classes\{#MyProgId}\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

; --- Capabilities registration for Windows Default Apps ---
Root: HKA; Subkey: "Software\DocuTools"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\DocuTools\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#MyAppFullName}"
Root: HKA; Subkey: "Software\DocuTools\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Universal 100% Offline Document and PDF Management Suite"
Root: HKA; Subkey: "Software\DocuTools\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: "{app}\icon.ico,0"
Root: HKA; Subkey: "Software\DocuTools\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "{#MyProgId}"

; --- RegisteredApplications registration ---
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: "Software\DocuTools\Capabilities"; Flags: uninsdeletevalue

; --- Open-With menu integration ---
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgIds"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue

[UninstallDelete]
; Clean up runtime caches and temporary files on uninstallation
Type: filesandordirs; Name: "{localappdata}\DocuTools"
Type: filesandordirs; Name: "{userappdata}\DocuTools"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppFullName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
