"""
ui_main.py — メインウィンドウ
設定タブの追加・翻訳(tr)対応・テーマ/背景管理の連携
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QTextEdit, QSplitter, QFileDialog,
    QStatusBar, QToolBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QAction, QFont, QIcon, QColor

from ui_editor import EditorTab
from ui_batch_editor import BatchEditorTab
from ui_generator import GeneratorTab
from ui_nif_batch import NifBatchTab
from ui_settings import SettingsTab
from config import AppConfig, tr
from utils import get_resource_path


class BackgroundWidget(QWidget):
    """背景画像を描画するベースウィジェット"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_pixmap: QPixmap | None = None
        self._bg_opacity: float = 0.25

    def set_background(self, path: str, opacity: float = 0.25):
        if path:
            if not os.path.isabs(path):
                path = get_resource_path(path)
            
            if os.path.isfile(path):
                try:
                    self._bg_pixmap = QPixmap(path)
                    self._bg_opacity = opacity
                    self.update()
                except Exception:
                    self.clear_background()
            else:
                self.clear_background()
        else:
            self.clear_background()

    def clear_background(self):
        self._bg_pixmap = None
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        # 背景をテーマ色で塗りつぶし（画像未設定時や透過時に背面の黒が透けないため）
        if AppConfig.theme == "light":
            painter.fillRect(self.rect(), QColor(239, 241, 245))  # #eff1f5
        else:
            painter.fillRect(self.rect(), QColor(30, 30, 46))    # #1e1e2e

        if self._bg_pixmap and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            # 画像自体は元の不透明度で描画
            painter.drawPixmap(x, y, scaled)

            # 画像の上に現在のテーマに応じた半透明マスク（フィルター）を描画する
            mask_alpha = int(255 * (1.0 - self._bg_opacity))
            if AppConfig.theme == "light":
                # ライトモード時は白っぽい背景を乗せる
                painter.fillRect(self.rect(), QColor(239, 241, 245, mask_alpha))
            else:
                # ダークモード時は暗い背景を乗せる
                painter.fillRect(self.rect(), QColor(30, 30, 46, mask_alpha))

        painter.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Batch Material Editor")
        self.setMinimumSize(900, 650)
        
        # ウィンドウのアイコンを設定
        icon_path = get_resource_path("Icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.editor_tab = EditorTab()
        self.batch_tab = BatchEditorTab(log_callback=self._log)
        self.gen_tab = GeneratorTab(log_callback=self._log)
        self.nif_batch_tab = NifBatchTab(log_callback=self._log)
        self.settings_tab = SettingsTab()

        self._log_history: list[str] = []

        self._build_ui()
        self._connect_config_signals()
        
        # 初期状態のロードと反映
        self.retranslate(AppConfig.lang)
        AppConfig.apply_theme(None)  # アプリ全体のQSS適用
        if AppConfig.bg_path:
            self._bg_widget.set_background(AppConfig.bg_path)
            
        # Tooltip反映
        self._on_tooltips_changed(AppConfig.show_tooltips)

        # 起動時自動インデックス構築
        if AppConfig.auto_build_index:
            self._log(tr("Building index...", AppConfig.lang))
            self.settings_tab._build_index(silent=True)
            # スレッド終了をフックしてログに出す
            self.settings_tab._idx_thread.finished_signal.connect(
                lambda count: self._log(tr("Index built: {count} textures found", AppConfig.lang).replace("{count}", str(count)))
            )

        # 定期構築用タイマー
        self._build_timer = QTimer(self)
        self._build_timer.timeout.connect(self._on_periodic_timeout)
        self._update_periodic_timer()
        AppConfig.periodic_settings_changed.connect(self._update_periodic_timer)

    def _update_periodic_timer(self):
        self._build_timer.stop()
        if AppConfig.periodic_build_index:
            ms = AppConfig.build_interval_min * 60 * 1000
            self._build_timer.start(ms)
            self._log(f"[Timer] Periodic index build enabled: every {AppConfig.build_interval_min} min")
        else:
            self._log("[Timer] Periodic index build disabled")

    def _on_periodic_timeout(self):
        # 実行中のチェックなどはSettingsTab側でよしなにされる（二重起動防止はスレッド管理等が必要だが、
        # ここではシンプルにボタンを無効化する既存の_build_indexを流用）
        self._log(tr("Building index...", AppConfig.lang) + " (Scheduled)")
        self.settings_tab._build_index(silent=True)
        # 完了ログはStartupと同じ接続で処理される（同じSettingsTabのインスタンスなので）

    def _build_ui(self):
        # ---- メニュー ----
        self.menu = self.menuBar()

        # File メニュー
        self.file_menu = self.menu.addMenu(tr("File", AppConfig.lang))
        
        from PyQt6.QtGui import QAction
        self.action_new = QAction(tr("New", AppConfig.lang), self)
        self.action_new.setShortcut("Ctrl+N")
        self.action_new.triggered.connect(self._do_new)

        self.action_open = QAction(tr("Open", AppConfig.lang), self)
        self.action_open.setShortcut("Ctrl+O")
        self.action_open.triggered.connect(self._do_open)

        self.action_save = QAction(tr("Save", AppConfig.lang), self)
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.triggered.connect(self._do_save)

        self.action_save_as = QAction(tr("Save As", AppConfig.lang), self)
        self.action_save_as.setShortcut("Ctrl+Alt+S")
        self.action_save_as.triggered.connect(self._do_save_as)

        self.action_close = QAction(tr("Close", AppConfig.lang), self)
        self.action_close.setShortcut("Ctrl+W")
        self.action_close.triggered.connect(self._do_close)

        self.action_exit = QAction(tr("Exit", AppConfig.lang), self)
        self.action_exit.setShortcut("Alt+F4")
        self.action_exit.triggered.connect(self.close)

        self.file_menu.addAction(self.action_new)
        self.file_menu.addAction(self.action_open)
        self.file_menu.addAction(self.action_save)
        self.file_menu.addAction(self.action_save_as)
        self.file_menu.addAction(self.action_close)
        self.file_menu.addSeparator()
        self.recent_menu = self.file_menu.addMenu(tr("Recent Files", AppConfig.lang))
        self._update_recent_menu()
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.action_exit)

        # View メニュー
        self.view_menu = self.menu.addMenu("View")
        self.action_set_bg = QAction("Set Background Image...", self)
        self.action_set_bg.triggered.connect(self._set_background)
        self.action_clear_bg = QAction("Clear Background Image", self)
        self.action_clear_bg.triggered.connect(self._clear_background)
        self.view_menu.addAction(self.action_set_bg)
        self.view_menu.addAction(self.action_clear_bg)

        # ---- 中央ウィジェット ----
        central = BackgroundWidget()
        self._bg_widget = central
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(4)

        # タブ
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tabs.addTab(self.editor_tab, "")
        self.tabs.addTab(self.batch_tab, "")
        self.tabs.addTab(self.gen_tab, "")
        self.tabs.addTab(self.nif_batch_tab, "")
        self.tabs.addTab(self.settings_tab, "")

        splitter.addWidget(self.tabs)

        # ログエリア
        log_widget = QWidget()
        ll = QVBoxLayout(log_widget)
        ll.setContentsMargins(6, 4, 6, 6)
        ll.setSpacing(2)
        self.lbl_log = QLabel("Log")
        self.lbl_log.setStyleSheet("font-size: 11px;")
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(180)
        # ログの背景色はコード側で指定（テーマと競合しないように）
        self.log_area.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px;"
        )
        self.btn_clear_log = QPushButton("Clear")
        self.btn_clear_log.setFixedWidth(60)
        self.btn_clear_log.setFixedHeight(22)
        self.btn_clear_log.clicked.connect(self._clear_log)
        top_bar = QHBoxLayout()
        top_bar.addWidget(self.lbl_log)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_clear_log)
        ll.addLayout(top_bar)
        ll.addWidget(self.log_area)
        splitter.addWidget(log_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)
        self.statusBar().showMessage(tr("Ready", AppConfig.lang))

    def _connect_config_signals(self):
        AppConfig.language_changed.connect(self.retranslate)
        AppConfig.tooltips_changed.connect(self._on_tooltips_changed)
        self.editor_tab.file_opened.connect(self.notify_file_opened)
        self.editor_tab.file_saved.connect(self.notify_file_saved)

    def retranslate(self, lang: str):
        """言語変更時の全体再翻訳パイプライン"""
        self.setWindowTitle(tr("FO4 BGSM Tool", lang))
        
        # Menu
        self.file_menu.setTitle(tr("File", lang))
        self.action_new.setText(tr("New", lang))
        self.action_open.setText(tr("Open", lang))
        self.action_save.setText(tr("Save", lang))
        self.action_save_as.setText(tr("Save As", lang))
        self.action_close.setText(tr("Close", lang))
        self.action_exit.setText(tr("Exit", lang))
        self.recent_menu.setTitle(tr("Recent Files", lang))
        self._update_recent_menu()
        self.view_menu.setTitle(tr("View", lang))
        self.action_set_bg.setText(tr("Set Background Image...", lang))
        self.action_clear_bg.setText(tr("Clear Background Image", lang))

        # Tabs
        self.tabs.setTabText(0, tr("Single Editor", lang))
        self.tabs.setTabText(1, tr("Batch Editor", lang))
        self.tabs.setTabText(2, tr("Generator", lang))
        self.tabs.setTabText(3, tr("NIF Generator", lang))
        self.tabs.setTabText(4, tr("Settings", lang))

        # Log
        self.lbl_log.setText(tr("Log", lang))
        self.btn_clear_log.setText(tr("Clear", lang))

        # サブタブ全体の再翻訳
        if hasattr(self.editor_tab, 'retranslate'):
            self.editor_tab.retranslate(lang)
        if hasattr(self.batch_tab, 'retranslate'):
            self.batch_tab.retranslate(lang)
        if hasattr(self.gen_tab, 'retranslate'):
            self.gen_tab.retranslate(lang)
        if hasattr(self.nif_batch_tab, 'retranslate'):
            self.nif_batch_tab.retranslate(lang)

        # ステータスバー
        self.statusBar().showMessage(tr("Ready", lang))

    def _on_tooltips_changed(self, show: bool):
        # タブ内のツールチップ切り替えトリガー
        if hasattr(self.editor_tab, 'set_tooltips_enabled'):
            self.editor_tab.set_tooltips_enabled(show)
        if hasattr(self.batch_tab, 'set_tooltips_enabled'):
            self.batch_tab.set_tooltips_enabled(show)

    # ---- メニュートリガー ----
    def _do_new(self):
        self.tabs.setCurrentIndex(0)
        self.editor_tab.new_file()

    def _do_open(self):
        self.tabs.setCurrentIndex(0)
        self.editor_tab.open_file()

    def _do_save(self):
        self.tabs.setCurrentIndex(0)
        self.editor_tab.save_file()

    def _do_save_as(self):
        self.tabs.setCurrentIndex(0)
        self.editor_tab.save_as()

    def _do_close(self):
        self.tabs.setCurrentIndex(0)
        self.editor_tab.close_file()

    def _clear_log(self):
        self._log_history.clear()
        self.log_area.clear()

    def _log(self, msg: str):
        self._log_history.append(msg)
        if len(self._log_history) > 1000:
            self._log_history.pop(0)

        # 最新行は緑（#a6e3a1）、それ以前は白（#cdd6f4）
        import html
        escaped_history = [html.escape(m) for m in self._log_history]
        
        if len(escaped_history) == 1:
            content = f'<span style="color: #a6e3a1;">{escaped_history[0]}</span>'
        else:
            past = "<br>".join(f'<span style="color: #cdd6f4;">{m}</span>' for m in escaped_history[:-1])
            latest = f'<span style="color: #a6e3a1;">{escaped_history[-1]}</span>'
            content = past + "<br>" + latest
            
        self.log_area.setHtml(content)
        
        # スクロールバーを一番下に下げる
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        self.statusBar().showMessage(msg[-80:])

    def _update_recent_menu(self):
        self.recent_menu.clear()
        recent = AppConfig.get_recent_files()
        if not recent:
            action = self.recent_menu.addAction(tr("No Recent Files", AppConfig.lang))
            action.setEnabled(False)
        else:
            for path in recent:
                action = self.recent_menu.addAction(os.path.basename(path))
                action.setToolTip(path)
                action.triggered.connect(lambda checked, p=path: self._open_recent(p))

    def _open_recent(self, path: str):
        if os.path.isfile(path):
            self.editor_tab.open_by_path(path)
            AppConfig.add_recent_file(path)
            self._update_recent_menu()
            self.tabs.setCurrentIndex(0)  # 単体編集タブに切り替え
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, tr("Warning", AppConfig.lang), f"ファイルが見つかりません: {path}")

    def notify_file_opened(self, path: str):
        """エディタタブからファイルの読み込みを通知されたときに履歴を更新する"""
        AppConfig.add_recent_file(path)
        self._update_recent_menu()

    def notify_file_saved(self, path: str):
        """保存完了時にログ出力と履歴更新を行う"""
        AppConfig.add_recent_file(path)
        self._update_recent_menu()
        self._log(f"{tr('Saved: ', AppConfig.lang)}{path}")

    def _set_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Set Background Image...", AppConfig.lang), "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All (*)"
        )
        if path:
            AppConfig.set_bg_path(path)
            self._bg_widget.set_background(path)

    def _clear_background(self):
        AppConfig.set_bg_path("")
        self._bg_widget.clear_background()

    def closeEvent(self, event):
        """ウィンドウを閉じる際に未保存の変更がある場合は警告する"""
        if not self.editor_tab.confirm_discard_changes():
            event.ignore()
        else:
            event.accept()
