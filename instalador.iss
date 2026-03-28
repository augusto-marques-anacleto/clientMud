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

[Files]
Source: "dist\clientmud\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Client Mud"; Filename: "{app}\clientmud.exe"
Name: "{autodesktop}\Client Mud"; Filename: "{app}\clientmud.exe"