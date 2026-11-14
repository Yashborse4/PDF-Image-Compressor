"""
Application Bootstrap and entry point for DocuTools.
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from docutools.core.assets import get_app_icon_path
from docutools.main_window import MainWindow


def main() -> int:
    """Run DocuTools Desktop Application."""
    app = QApplication(sys.argv)
    app.setApplicationName("DocuTools")
    app.setOrganizationName("DocuTools")
    app.setApplicationDisplayName("DocuTools Desktop Suite")

    # Set universal application icon
    app_icon = QIcon(get_app_icon_path(ico=True))
    app.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
