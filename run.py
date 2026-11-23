"""
DocuTools Launcher and Runtime Shell.
Handles frozen-bundle extraction paths, uncaught exception logging,
and native Windows crash diagnostics.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def _install_crash_reporter() -> None:
    """Ensure any fatal startup exception is logged and displayed via native Windows dialog."""
    def _handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        # Write to log file
        log_paths = []
        try:
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                appdata_log_dir = Path(local_appdata) / "DocuTools" / "logs"
                appdata_log_dir.mkdir(parents=True, exist_ok=True)
                log_paths.append(appdata_log_dir / "crash.log")
        except Exception:
            pass

        try:
            cwd_log = Path.cwd() / "crash.log"
            log_paths.append(cwd_log)
        except Exception:
            pass

        for lp in log_paths:
            try:
                with open(lp, "a", encoding="utf-8") as f:
                    f.write(f"\n--- Crash Report [{sys.argv}] ---\n")
                    f.write(tb_text)
            except Exception:
                pass

        # Native Windows MessageBox if on Windows
        if sys.platform == "win32":
            try:
                import ctypes
                primary_log = str(log_paths[0]) if log_paths else "crash.log"
                msg = (
                    f"DocuTools encountered an unhandled startup exception:\n\n"
                    f"{exc_type.__name__}: {exc_value}\n\n"
                    f"A crash log has been written to:\n{primary_log}"
                )
                ctypes.windll.user32.MessageBoxW(0, msg, "DocuTools Fatal Error", 0x10)
            except Exception:
                pass

        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _handle_exception


# 1. Install crash reporter immediately before imports
_install_crash_reporter()

# 2. Configure import paths for development and PyInstaller frozen execution
root_dir = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    base_dir = Path(getattr(sys, "_MEIPASS", root_dir))
else:
    base_dir = root_dir

candidate_paths = [
    base_dir,
    base_dir / "src",
    base_dir / "app",
    root_dir,
    root_dir / "src",
    root_dir / "app",
]
for p in candidate_paths:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from docutools.app import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        if sys.excepthook:
            sys.excepthook(*sys.exc_info())
        sys.exit(1)
