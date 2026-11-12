; ============================================================================
; ALDx-Setup.exe  -  installer Windows "Next - Next" (Inno Setup 6)
; ============================================================================
; Alur untuk pengguna:
;   Selamat datang (cek Docker Desktop) > Folder > Pintasan > Pasang (salin berkas) > Selesai
;   > wizard pengaturan ALDx terbuka otomatis (installer\pasang.ps1: Pemeriksaan > Superadmin > Pasang).
;
; Tidak butuh hak admin (PrivilegesRequired=lowest). Berkas hasil Setup tidak bertanda "dari internet",
; jadi PowerShell tidak memblokirnya.
;
; Membangun (otomatis di GitHub Actions, .github/workflows/rilis.yml):
;   iscc /DVersi=2026.11.05 installer\setup\aldx-setup.iss      -> installer\setup\Output\ALDx-Setup.exe
;
; Versi OFFLINE (tanpa internet; job "offline" di .github/workflows/rilis.yml):
;   folder offline\ berisi aldx-images.tar.gz (docker save semua image), versi.txt, DockerDesktopInstaller.exe
;   iscc /DVersi=... /DOffline installer\setup\aldx-setup.iss  -> ALDx-Setup-Offline.exe + ALDx-Setup-Offline-1.bin, -2.bin ...
;   (berkas .bin harus satu folder dengan .exe)
;
; Isi = aplikasi + dokumentasi pengguna: tanpa log, rahasia (.env), dan perkakas pengembang.
; Dibangun lokal: installer\setup\buat-installer.ps1 [-Offline] (tanpa GitHub Actions).
; Uninstall: menanyakan "hapus juga data?" lalu menjalankan scripts\hapus-aldx.ps1 (container selalu dihapus;
; data hanya bila dipilih, dan SETELAH dicadangkan ke folder backup\ yang tidak ikut terhapus).
; ============================================================================

#ifndef Versi
  #define Versi "0.0.0"
#endif
#define Nama "ALDx"
#define Akar "..\.."

[Setup]
AppId={{6D3C2A61-4E0B-4C5E-9B7A-1A1D0C000001}
AppName={#Nama}
AppVersion={#Versi}
AppVerName={#Nama} {#Versi}
AppPublisher={#Nama}
AppPublisherURL=https://github.com/rntrn/aldx_superset
AppCopyright=(c) {#Nama}
VersionInfoVersion={#Versi}
VersionInfoCompany={#Nama}
VersionInfoDescription=Installer {#Nama} (aplikasi dashboard & analitik data)
VersionInfoProductName={#Nama}
VersionInfoProductVersion={#Versi}
; Tanda tangan digital (mengurangi peringatan SmartScreen/antivirus). Aktif bila ISCC dipanggil dengan
;   /DTandaTangan "/Saldx=signtool sign /f sertifikat.pfx /p PASSWORD /fd sha256 /tr http://timestamp.digicert.com /td sha256 $f"
; (dikerjakan otomatis rilis.yml bila secret CODESIGN_PFX_BASE64 & CODESIGN_PASSWORD diisi). Lihat docs/18 bagian "Peringatan Windows".
#ifdef TandaTangan
SignTool=aldx
SignedUninstaller=yes
#endif
DefaultDirName={code:FolderAwal}
UsePreviousAppDir=yes
DirExistsWarning=no
DisableProgramGroupPage=yes
DefaultGroupName={#Nama}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
ShowLanguageDialog=no
SetupIconFile=aldx.ico
UninstallDisplayIcon={app}\installer\setup\aldx.ico
UninstallDisplayName={#Nama}
OutputDir=Output
#ifdef Manifest
; Daftar isi installer (diperiksa buat-installer.ps1: berkas wajib ada, berkas terlarang tidak ikut)
OutputManifestFile=isi-installer.txt
#endif
#ifdef Offline
OutputBaseFilename=ALDx-Setup-Offline
DiskSpanning=yes
DiskSliceSize=max
Compression=lzma2/normal
SolidCompression=no
#else
OutputBaseFilename=ALDx-Setup
Compression=lzma2/max
SolidCompression=yes
#endif
ExtraDiskSpaceRequired=42949672960
CloseApplications=no

[Files]
; Seluruh isi proyek, KECUALI rahasia, cadangan, log, dan berkas pengembang.
Source: "{#Akar}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "\.git,\.github,\dist,\tests,\docs\node_modules,\docs\.vitepress,\docs\package.json,\docs\package-lock.json,\.env,\backup\*.dump,\backup\*.log,\backup\*.txt,\backup\*.sql,\backup\engine\*.zip,\installer\log,\installer\setup\Output,\server\tls\*.key,\server\tls\*.crt,\server\status,\offline,\diagnosa.txt,__pycache__,*.pyc,.pytest_cache,.ruff_cache,dump.rdb,\unins*.exe,\unins*.dat,\CHANGELOG.md,\bersih.kecuali,\scripts\buat-bersih.ps1,\docs\catatan-versi.md,\docs\cara-pasang.md,\docs\index.md,\docs\public,\docs\pdf\buat_pdf.py,\docs\pengujian\laporan-qa.md,\docs\pdf\laporan-qa.pdf,\docs\gambar\qa,\installer\setup\buat-installer.ps1,\installer\setup\terbitkan.ps1"
#ifdef Offline
; Paket offline: semua image Docker (dimuat installer\pasang.ps1 -> scripts\init.ps1, tanpa internet).
Source: "{#Akar}\offline\aldx-images.tar.gz"; DestDir: "{app}\offline"; Flags: ignoreversion nocompression
Source: "{#Akar}\offline\versi.txt"; DestDir: "{app}\offline"; Flags: ignoreversion
Source: "{#Akar}\offline\DockerDesktopInstaller.exe"; Flags: dontcopy nocompression
#endif

[Tasks]
Name: "desktop"; Description: "Buat pintasan ALDx di &Desktop"

[Icons]
Name: "{userprograms}\{#Nama}\{#Nama}"; Filename: "{app}\scripts\buka.cmd"; WorkingDir: "{app}"; Flags: runminimized; IconFilename: "{app}\installer\setup\aldx.ico"; Comment: "Buka ALDx di browser"
Name: "{userprograms}\{#Nama}\Pasang - ubah pengaturan ALDx"; Filename: "{app}\PASANG.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\installer\setup\aldx.ico"
Name: "{userprograms}\{#Nama}\Panduan pasang"; Filename: "{app}\docs\pdf\cara-pasang.pdf"
Name: "{userprograms}\{#Nama}\Folder ALDx"; Filename: "{app}"
Name: "{userprograms}\{#Nama}\Atur ulang password"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\atur-password.ps1"""; WorkingDir: "{app}"
Name: "{userprograms}\{#Nama}\Hapus ALDx"; Filename: "{uninstallexe}"
Name: "{userprograms}\{#Nama}\Hapus total (bersih)"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\hapus-total.ps1"""; WorkingDir: "{app}"; Comment: "Cadangkan lalu hapus ALDx sepenuhnya"
Name: "{userdesktop}\{#Nama}"; Filename: "{app}\scripts\buka.cmd"; WorkingDir: "{app}"; Flags: runminimized; IconFilename: "{app}\installer\setup\aldx.ico"; Tasks: desktop

[Run]
; Langkah terakhir: wizard pengaturan (akun Superadmin, menyalakan aplikasi). Dicentang bawaan.
Filename: "{app}\PASANG.cmd"; WorkingDir: "{app}"; Description: "Lanjut ke pengaturan ALDx (isi akun Superadmin)"; Flags: postinstall shellexec skipifsilent

[Code]
const
  DOCKER_EXE = '{commonpf64}\Docker\Docker\Docker Desktop.exe';
  DOCKER_URL = 'https://www.docker.com/products/docker-desktop/';

{ Folder bawaan: D:\superset bila ada drive D, kalau tidak C:\superset. Tanpa spasi. }
function FolderAwal(Param: String): String;
begin
  if DirExists('D:\') then Result := 'D:\superset'
  else Result := ExpandConstant('{sd}') + '\superset';
end;

function DockerTerpasang(): Boolean;
begin
  Result := FileExists(ExpandConstant(DOCKER_EXE));
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Folder: String;
  Kode: Integer;
begin
  Result := True;
  if CurPageID = wpWelcome then begin
    if not DockerTerpasang() then begin
#ifdef Offline
      if MsgBox('Docker Desktop belum terpasang di komputer ini.' + #13#10#13#10 +
                'Pasang Docker Desktop dari paket offline ini sekarang?' + #13#10 +
                '(Butuh hak admin: Windows akan meminta password admin. Setelah selesai, mulai ulang komputer ' +
                'bila diminta, lalu jalankan Setup ini lagi.)', mbConfirmation, MB_YESNO) = IDYES then begin
        ExtractTemporaryFile('DockerDesktopInstaller.exe');
        if not ShellExec('runas', ExpandConstant('{tmp}\DockerDesktopInstaller.exe'), 'install --accept-license', '',
                         SW_SHOWNORMAL, ewWaitUntilTerminated, Kode) then
          MsgBox('Docker Desktop tidak terpasang (dibatalkan / tanpa hak admin). Minta bantuan tim TI.', mbError, MB_OK);
      end;
#else
      if MsgBox('Docker Desktop belum terpasang di komputer ini.' + #13#10#13#10 +
                'ALDx membutuhkan Docker Desktop. Biasanya dipasang tim TI (butuh hak admin), ' +
                'lalu akun Anda dimasukkan ke grup "docker-users".' + #13#10#13#10 +
                'Buka halaman unduh Docker Desktop sekarang?' + #13#10 +
                '(Pemasangan ALDx tetap bisa dilanjutkan; pengaturan dijalankan setelah Docker siap.)',
                mbConfirmation, MB_YESNO) = IDYES then
        ShellExec('open', DOCKER_URL, '', '', SW_SHOWNORMAL, ewNoWait, Kode);
#endif
    end;
  end;
  if CurPageID = wpSelectDir then begin
    Folder := WizardDirValue();
    if Pos(' ', Folder) > 0 then begin
      MsgBox('Nama folder tidak boleh berisi spasi:' + #13#10 + Folder + #13#10#13#10 +
             'Contoh yang benar: D:\superset', mbError, MB_OK);
      Result := False;
    end else if (Pos('\ONEDRIVE', Uppercase(Folder)) > 0) or (Pos('\DESKTOP', Uppercase(Folder)) > 0) then begin
      MsgBox('Jangan memasang di folder Desktop / OneDrive (berkas bisa dikunci saat sinkronisasi).' + #13#10 +
             'Contoh yang benar: D:\superset', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

{ ---------------- Uninstall: container selalu dihapus, data hanya bila dipilih (dicadangkan dulu) ---------------- }
var
  HapusData: Boolean;

function DockerMenyala(): Boolean;
var
  Kode: Integer;
begin
  Result := Exec(ExpandConstant('{cmd}'), '/c docker info >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, Kode) and (Kode = 0);
end;

function InitializeUninstall(): Boolean;
var
  Jawab: Integer;
begin
  Result := False;
  while not DockerMenyala() do begin
    Jawab := MsgBox('Docker Desktop belum menyala. Container ALDx hanya bisa dihapus bila Docker menyala.' + #13#10#13#10 +
                    'Ya = saya sudah menyalakan Docker Desktop, periksa lagi' + #13#10 +
                    'Tidak = hapus berkas program saja (container & data dibiarkan)' + #13#10 +
                    'Batal = tidak jadi menghapus', mbConfirmation, MB_YESNOCANCEL);
    if Jawab = IDCANCEL then Exit;
    if Jawab = IDNO then begin
      HapusData := False; Result := True; Exit;
    end;
  end;
  Jawab := MsgBox('Hapus BERSIH semua data ALDx?' + #13#10 + '(dashboard, chart, pengguna, koneksi, data upload & ekstrak)' + #13#10#13#10 +
                  'Ya = hapus bersih: cadangan lengkap dibuat dulu di Dokumen\ALDx-cadangan-..., lalu container, image, volume data, ' +
                  'jaringan, objek Kubernetes ALDx, sertifikat, tugas terjadwal & seluruh folder ALDx dihapus.' + #13#10 +
                  'Tidak = hapus program & container saja. Data tetap tersimpan dan kembali bila ALDx dipasang ulang.' + #13#10 +
                  'Batal = tidak jadi menghapus', mbConfirmation, MB_YESNOCANCEL or MB_DEFBUTTON2);
  if Jawab = IDCANCEL then Exit;
  HapusData := Jawab = IDYES;
  if HapusData then
    HapusData := MsgBox('Yakin menghapus semua data ALDx? Tindakan ini tidak bisa dibatalkan (kecuali dari cadangan).',
                        mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Kode: Integer;
  Arg: String;
begin
  { Hapus bersih: sisa folder (.env, backup\, log, sertifikat) ikut dihapus setelah berkas program. }
  if (CurUninstallStep = usPostUninstall) and HapusData then begin
    { Pengaman: jangan pernah menghapus akar drive (D:\) atau folder profil pengguna. }
    if (Length(RemoveBackslash(ExpandConstant('{app}'))) > 3) and
       (CompareText(RemoveBackslash(ExpandConstant('{app}')), RemoveBackslash(ExpandConstant('{%USERPROFILE}'))) <> 0) then
      DelTree(ExpandConstant('{app}'), True, True, True);
    Exit;
  end;
  if (CurUninstallStep <> usUninstall) or not DockerMenyala() then Exit;
  if HapusData then
    { Hapus bersih: hapus-total.ps1 (cadangan ke Dokumen, Docker, Kubernetes, sertifikat, tugas terjadwal).
      Berkas program dihapus Inno; sisa folder dibersihkan di usPostUninstall. }
    Arg := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\scripts\hapus-total.ps1') + '" -Ya -SimpanFolder'
  else
    Arg := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\scripts\hapus-aldx.ps1') + '"';
  Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Arg, ExpandConstant('{app}'), SW_SHOW, ewWaitUntilTerminated, Kode);
  if HapusData and (Kode = 3) then begin
    MsgBox('Cadangan gagal dibuat, jadi data ALDx TIDAK dihapus. Folder ALDx dibiarkan agar data bisa dicadangkan manual.', mbInformation, MB_OK);
    HapusData := False;
  end;
end;

[Messages]
SetupAppTitle=Pemasangan
SetupWindowTitle=Pemasangan %1
UninstallAppTitle=Hapus
UninstallAppFullTitle=Hapus %1
ConfirmTitle=Konfirmasi
ErrorTitle=Galat
ExitSetupTitle=Keluar dari pemasangan
ExitSetupMessage=Pemasangan belum selesai. Bila keluar sekarang, ALDx belum terpasang.%n%nPemasangan bisa dijalankan lagi kapan saja.%n%nKeluar?
ButtonBack=< &Kembali
ButtonNext=&Lanjut >
ButtonInstall=&Pasang
ButtonOK=OK
ButtonCancel=Batal
ButtonYes=&Ya
ButtonYesToAll=Ya untuk &semua
ButtonNo=&Tidak
ButtonNoToAll=T&idak untuk semua
ButtonFinish=&Selesai
ButtonBrowse=&Pilih...
ButtonWizardBrowse=P&ilih...
ButtonNewFolder=&Buat folder baru
ClickNext=Klik Lanjut untuk meneruskan, atau Batal untuk keluar.
BrowseDialogTitle=Pilih folder
BrowseDialogLabel=Pilih folder, lalu klik OK.
NewFolderName=Folder baru
WelcomeLabel1=Selamat datang di pemasangan [name]
WelcomeLabel2=Program ini memasang [name/ver] di komputer Anda.%n%nLangkahnya: pilih folder > Pasang > isi akun Superadmin. Tidak perlu hak admin.%n%nPastikan Docker Desktop sudah terpasang dan menyala (ikon paus di pojok kanan bawah).
WizardSelectDir=Pilih folder
SelectDirDesc=Di mana [name] dipasang?
SelectDirLabel3=[name] akan disalin ke folder berikut. Nama folder tanpa spasi.
SelectDirBrowseLabel=Klik Lanjut untuk meneruskan. Untuk folder lain, klik Pilih.
DiskSpaceGBLabel=Dibutuhkan ruang disk kosong minimal [gb] GB (termasuk data & cadangan).
DiskSpaceMBLabel=Dibutuhkan ruang disk kosong minimal [mb] MB.
DirNameTooLong=Nama folder terlalu panjang.
InvalidDirName=Nama folder tidak sah.
DirDoesntExistTitle=Folder belum ada
DirDoesntExist=Folder:%n%n%1%n%nbelum ada. Buat folder ini?
WizardSelectTasks=Pintasan
SelectTasksDesc=Pintasan apa yang dibuat?
SelectTasksLabel2=Pilih pintasan untuk [name], lalu klik Lanjut.
WizardReady=Siap memasang
ReadyLabel1=[name] siap disalin ke komputer ini.
ReadyLabel2a=Klik Pasang untuk memulai, atau Kembali untuk mengubah pilihan.
ReadyLabel2b=Klik Pasang untuk memulai.
ReadyMemoDir=Folder:
ReadyMemoTasks=Pintasan:
WizardPreparing=Menyiapkan
PreparingDesc=Menyiapkan pemasangan [name].
WizardInstalling=Memasang
InstallingLabel=Mohon tunggu, berkas [name] sedang disalin.
FinishedHeadingLabel=Berkas [name] sudah disalin
FinishedLabelNoIcons=Satu langkah lagi: wizard pengaturan ALDx (akun Superadmin & menyalakan aplikasi) terbuka setelah Anda klik Selesai.
FinishedLabel=Satu langkah lagi: wizard pengaturan ALDx (akun Superadmin & menyalakan aplikasi) terbuka setelah Anda klik Selesai.%n%nSesudahnya, buka ALDx lewat pintasan ALDx di Desktop / menu Start.
ClickFinish=Klik Selesai.
StatusClosingApplications=Menutup aplikasi...
StatusCreateDirs=Membuat folder...
StatusExtractFiles=Menyalin berkas...
StatusCreateIcons=Membuat pintasan...
StatusCreateIniEntries=Menulis pengaturan...
StatusCreateRegistryEntries=Menulis pengaturan...
StatusSavingUninstall=Menyimpan informasi penghapusan...
StatusRunProgram=Menyelesaikan...
StatusRollback=Membatalkan perubahan...
ConfirmUninstall=Lanjutkan menghapus %1 dari komputer ini?
UninstallStatusLabel=Mohon tunggu, %1 sedang dihapus.
UninstalledAll=%1 sudah dihapus dari komputer ini.
UninstalledMost=Penghapusan %1 selesai.%n%nBeberapa berkas (pengaturan & data Anda) sengaja tidak dihapus.
WizardUninstalling=Menghapus
StatusUninstalling=Menghapus %1...
