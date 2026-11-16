; Inno Setup 6 script
[Setup]
AppId={{8A11E3CE-DF9A-4C6D-9F21-0E6B72A9B210}
AppName=PDF Splitter
AppVersion=1.0.0
AppPublisher=PDF Splitter
DefaultDirName={autopf}\PDF Splitter
DefaultGroupName=PDF Splitter
OutputDir=installer
OutputBaseFilename=PDF-Splitter-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Files]
Source: "dist\PDF Splitter\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PDF Splitter"; Filename: "{app}\PDF Splitter.exe"
Name: "{autodesktop}\PDF Splitter"; Filename: "{app}\PDF Splitter.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
