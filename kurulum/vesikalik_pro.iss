; Hayal Medya Vesikalık Pro — Inno Setup kurulum betiği
#define Ad "Hayal Medya Vesikalık Pro"
#define Surum "1.2"
#ifndef Varyant
  #define Varyant "NVIDIA"
#endif
[Setup]
AppId={{E30C420D-28A5-5941-9A47-CED7906DE1DC}
AppName={#Ad}
AppVersion={#Surum}
AppPublisher=HAYAL MEDYA — Haydar Altınsaban
AppPublisherURL=tel:03122640888
DefaultDirName={autopf}\HayalMedya\VesikalikPro
DefaultGroupName=Hayal Medya
OutputDir=cikti
OutputBaseFilename=HayalMedya_VesikalikPro_{#Surum}_{#Varyant}_Kurulum
SetupIconFile=..\ui\assets\app_icon.ico
UninstallDisplayIcon={app}\VesikalikPro.exe
Compression=lzma2/ultra64
SolidCompression=yes
DiskSpanning=yes
DiskSliceSize=1900000000
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
[Tasks]
Name: "masaustu"; Description: "Masaüstüne kısayol oluştur"; Flags: checkedonce
[Files]
Source: "..\dist\VesikalikPro\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{group}\{#Ad}"; Filename: "{app}\VesikalikPro.exe"
Name: "{autodesktop}\{#Ad}"; Filename: "{app}\VesikalikPro.exe"; Tasks: masaustu
Name: "{group}\Kaldır"; Filename: "{uninstallexe}"
[Run]
Filename: "{app}\VesikalikPro.exe"; Description: "Programı başlat"; Flags: nowait postinstall skipifsilent
