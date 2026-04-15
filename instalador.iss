[Setup]
AppName=Client Mud
AppVersion=5.0.1
DefaultDirName={localappdata}\ClientMud
DefaultGroupName=Client Mud
UninstallDisplayIcon={app}\clientmud.exe
Compression=none
SolidCompression=no
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=Instalador_ClientMUD

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\clientmud\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Client Mud"; Filename: "{app}\clientmud.exe"
Name: "{autodesktop}\Client Mud"; Filename: "{app}\clientmud.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\clientmud.exe"; Description: "{cm:LaunchProgram,Client Mud}"; Flags: nowait postinstall skipifsilent