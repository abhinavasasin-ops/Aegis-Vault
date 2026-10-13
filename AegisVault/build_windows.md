# Building AegisVault.exe for Windows

## Prerequisites
- Windows 10/11
- Python 3.11+ (64-bit)
- `pip install -r requirements.txt`

## Build single-file EXE

```powershell
pyinstaller --noconfirm --clean --onefile --windowed ^
    --name AegisVault ^
    --collect-all customtkinter ^
    --collect-all tkinterdnd2 ^
    --hidden-import PIL._tkinter_finder ^
    --icon aegisvault\assets\icon.ico ^
    main.py
```

The executable is produced at `dist\AegisVault.exe`.

## Notes
- First launch creates `%APPDATA%\AegisVault\` (hidden) for the SQLite DB and encrypted blobs.
- To distribute: ship only `dist\AegisVault.exe`. No Python install required on the target machine.
- For an installer, wrap with Inno Setup or NSIS pointing at `dist\AegisVault.exe`.
