"""
GHOST Autostart Setup
Windows Startup papkasiga shortcut qo'shadi.
Bir marta ishga tushiring: python setup_autostart.py
"""

import os
import sys
import winreg
import subprocess
from pathlib import Path


def create_startup_shortcut():
    """Windows Startup papkasiga .vbs shortcut yaratish (oyna chiqmaydi)"""
    project_dir = Path(__file__).parent.resolve()
    python_exe  = project_dir / "ghost_env" / "Scripts" / "pythonw.exe"
    main_script = project_dir / "main.py"

    # pythonw.exe yo'q bo'lsa — oddiy python
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    # Startup papkasi
    startup_dir = Path(os.environ.get("APPDATA", "")) / \
                  "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_dir.mkdir(parents=True, exist_ok=True)

    vbs_path = startup_dir / "GHOST_Assistant.vbs"

    # VBScript — oyna chiqmay ishga tushiradi
    vbs_content = f'''Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = "{project_dir}"
oShell.Run """{python_exe}"" ""{main_script}""", 0, False
'''
    vbs_path.write_text(vbs_content, encoding="utf-8")
    print(f"✅ Shortcut yaratildi: {vbs_path}")
    return True


def remove_startup_shortcut():
    """Startup shortcut ni o'chirish"""
    startup_dir = Path(os.environ.get("APPDATA", "")) / \
                  "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    vbs_path = startup_dir / "GHOST_Assistant.vbs"

    if vbs_path.exists():
        vbs_path.unlink()
        print("✅ Autostart o'chirildi")
    else:
        print("ℹ️  Autostart allaqachon o'chirilgan")


def check_status():
    startup_dir = Path(os.environ.get("APPDATA", "")) / \
                  "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    vbs_path = startup_dir / "GHOST_Assistant.vbs"
    if vbs_path.exists():
        print("✅ Autostart: YOQILGAN")
    else:
        print("❌ Autostart: O'CHIRILGAN")


if __name__ == "__main__":
    print("👻 GHOST Autostart Setup\n")

    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove_startup_shortcut()
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        check_status()
    else:
        if create_startup_shortcut():
            print("\nEndi noutbuk yoqilganda GHOST avtomatik ishga tushadi.")
            print("O'chirish uchun: python setup_autostart.py remove")
