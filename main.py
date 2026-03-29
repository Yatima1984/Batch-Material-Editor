"""
main.py — エントリーポイント
"""

import sys
import os

# カレントディレクトリを bgsm_tool に設定（インポート解決のため）
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui_main import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Batch Material Editor")
    app.setOrganizationName("BGSMTool")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
