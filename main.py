import sys
from PySide6.QtWidgets import QApplication
from modules.dashboard_ui import AirMouseDashboard


def main():
    app = QApplication(sys.argv)
    window = AirMouseDashboard(config_path="config.json")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()