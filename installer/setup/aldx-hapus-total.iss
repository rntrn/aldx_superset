; ============================================================================
;  ALDx-HapusTotal.exe — pembersih total ALDx dalam satu berkas
;
;  Untuk komputer yang ingin bersih sepenuhnya dari ALDx, termasuk bila folder ALDx sudah terhapus,
;  Settings > Apps rusak, atau ALDx dipasang dari git/ZIP (tanpa uninstaller).
;  Menjalankan salinan scripts\hapus-total.ps1 dari folder sementara:
;    cadangan ke Dokumen\ALDx-cadangan-<waktu> (bila folder ALDx masih ada) -> container, image, volume,
;    jaringan, objek Kubernetes ALDx, tugas terjadwal, sertifikat, pintasan, entri Apps, folder ALDx.
;  Tidak memasang apa pun dan tidak meninggalkan berkas. Konfirmasi "ketik HAPUS" tetap diminta.
;
;  Dibangun: installer\setup\buat-installer.ps1 (bersama ALDx-Setup.exe).
; ============================================================================

#ifndef Versi
  #define Versi "0.0.0"
#endif
#define Akar "..\.."
#define AppIdALDx "{6D3C2A61-4E0B-4C5E-9B7A-1A1D0C000001}_is1"

[Setup]
AppId={{6D3C2A61-4E0B-4C5E-9B7A-1A1D0C0000FF}
AppName=ALDx Hapus Total
AppVersion={#Versi}
AppPublisher=ALDx
VersionInfoVersion={#Versi}
VersionInfoCompany=ALDx
VersionInfoDescription=Pembersih total ALDx (cadangkan lalu hapus container, image, volume, data, pintasan)
VersionInfoProductName=ALDx
VersionInfoProductVersion={#Versi}
VersionInfoCopyright=ALDx
#ifdef TandaTangan
SignTool=aldx
#endif
PrivilegesRequired=lowest
Uninstallable=no
CreateAppDir=yes
DefaultDirName={code:FolderALDx}
AppendDefaultDirName=no
DirExistsWarning=no
UsePreviousAppDir=no
DisableProgramGroupPage=yes
DisableReadyPage=no
DisableFinishedPage=no
WizardStyle=modern
SetupIconFile=aldx.ico
OutputDir=Output
OutputBaseFilename=ALDx-HapusTotal
Compression=lzma2/max
SolidCompression=yes
#ifdef Manifest
OutputManifestFile=isi-hapus-total.txt
#endif

[Languages]
Name: "id"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#Akar}\scripts\hapus-total.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "{#Akar}\scripts\_umum.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{tmp}\hapus-total.ps1"" -Akar ""{app}"""; \
  StatusMsg: "Menjalankan pembersihan ALDx (ikuti petunjuk di jendela biru)..."; Flags: waituntilterminated

[Code]
{ Folder ALDx: dari entri Settings > Apps (InstallLocation) bila ada; selain itu D:\superset. }
function FolderALDx(Param: String): String;
var
  Lokasi: String;
begin
  if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppIdALDx}', 'InstallLocation', Lokasi) or
     RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppIdALDx}', 'InstallLocation', Lokasi) then
    Result := RemoveBackslash(Lokasi)
  else
    Result := 'D:\superset';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Folder: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then begin
    Folder := RemoveBackslash(WizardDirValue());
    if (Length(Folder) <= 3) or (CompareText(Folder, RemoveBackslash(ExpandConstant('{%USERPROFILE}'))) = 0) or
       (CompareText(Folder, RemoveBackslash(ExpandConstant('{win}'))) = 0) then begin
      MsgBox('Pilih folder ALDx yang sebenarnya (bukan akar drive, folder Windows, atau folder profil).', mbError, MB_OK);
      Result := False;
    end else if not FileExists(Folder + '\docker-compose.yml') then
      Result := MsgBox('Folder ini bukan folder ALDx (atau sudah terhapus):' + #13#10 + Folder + #13#10#13#10 +
                       'Lanjut? Container, image, volume, Kubernetes & jejak Windows ALDx tetap dibersihkan, ' +
                       'tetapi data TIDAK bisa dicadangkan.', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  end;
end;

[Messages]
SetupAppTitle=ALDx Hapus Total
SetupWindowTitle=ALDx Hapus Total
WelcomeLabel1=Hapus total ALDx
WelcomeLabel2=Program ini membersihkan ALDx sepenuhnya dari komputer ini:%n%n• Cadangan data lebih dulu ke Dokumen\ALDx-cadangan-... (bila folder ALDx masih ada)%n• Container, image, volume data, jaringan Docker%n• Objek Kubernetes milik ALDx (bila ada)%n• Tugas terjadwal, sertifikat HTTPS, pintasan, entri Settings > Apps%n• Folder ALDx%n%nDocker Desktop, Ollama/LM Studio, dan project Docker lain tidak disentuh.%nNyalakan Docker Desktop sebelum melanjutkan.
SelectDirLabel3=Pilih folder tempat ALDx dipasang. Folder yang sudah terhapus pun boleh dipilih.
SelectDirBrowseLabel=Folder ALDx yang akan dibersihkan:
ReadyLabel1=Siap membersihkan ALDx.
ReadyLabel2a=Klik Hapus. Jendela biru akan menampilkan ringkasan dan meminta Anda mengetik HAPUS sebagai konfirmasi akhir.
ButtonInstall=&Hapus
ButtonNext=&Lanjut >
ButtonBack=< &Kembali
ButtonCancel=Batal
ButtonFinish=&Selesai
ButtonBrowse=&Pilih...
FinishedHeadingLabel=Selesai
FinishedLabelNoIcons=Pembersihan ALDx selesai. Lihat jendela biru untuk hasil dan lokasi cadangan.
FinishedLabel=Pembersihan ALDx selesai. Lihat jendela biru untuk hasil dan lokasi cadangan.
ExitSetupMessage=Pembersihan belum dijalankan. Keluar?
