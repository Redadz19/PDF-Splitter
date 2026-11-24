; Inno Setup 6 script
#define MyAppVersion GetEnv("APP_VERSION")
[Setup]
AppId={{8A11E3CE-DF9A-4C6D-9F21-0E6B72A9B210}
AppName=WARAKA
AppVersion={#MyAppVersion}
AppPublisher=Riadh Terrouche. RedaDZ19
AppCopyright=Copyright (C) 2026 Riadh Terrouche. RedaDZ19
VersionInfoCompany=Riadh Terrouche. RedaDZ19
VersionInfoDescription=WARAKA - PDF reader and page tools
VersionInfoProductName=WARAKA
VersionInfoProductVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}.0
DefaultDirName={localappdata}\Programs\WARAKA
PrivilegesRequired=lowest
DefaultGroupName=WARAKA
OutputDir=installer
OutputBaseFilename=PDF-Splitter-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
SetupIconFile=assets\pdf_splitter.ico

[Files]
Source: "dist\PDF Splitter\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\WARAKA"; Filename: "{app}\PDF Splitter.exe"
Name: "{autodesktop}\WARAKA"; Filename: "{app}\PDF Splitter.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
