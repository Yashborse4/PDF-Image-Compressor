; Inno Setup Script for DocuTools Desktop Suite
#define MyAppName "DocuTools"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DocuTools"
#define MyAppURL "https://github.com/DocuTools/DocuTools"
#define MyAppExeName "DocuTools.exe"

[Setup]
AppId={{9F7B3E42-6D39-44F1-8B6C-7132924A22F0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=dist\installer
OutputBaseFilename=docutools-setup-{#MyAppVersion}
SetupIconFile=..\docutools\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\DocuTools\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\DocuTools\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
