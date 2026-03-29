"""
ui_settings.py — 設定タブUIモジュール
言語・テーマ・ツールチップの各種設定
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCheckBox, QGroupBox, QSpacerItem, QSizePolicy,
    QLineEdit, QPushButton, QFileDialog, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from config import AppConfig, tr


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_from_config()
        self._connect_signals()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        grp = QGroupBox()
        # タイトル自体も翻訳が必要だが、初期化時はAppConfig.langを使う
        grp.setTitle(tr("Settings", AppConfig.lang))
        self.grp = grp
        gl = QVBoxLayout(grp)
        gl.setSpacing(16)

        # ── Language ──────────────────────────────────────
        hl_lang = QHBoxLayout()
        self.lbl_lang = QLabel(tr("Language:", AppConfig.lang))
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("日本語", "ja")
        self.combo_lang.addItem("한국어", "ko")
        self.combo_lang.addItem("English", "en")
        hl_lang.addWidget(self.lbl_lang)
        hl_lang.addWidget(self.combo_lang)
        hl_lang.addStretch()
        gl.addLayout(hl_lang)

        # ── Theme ─────────────────────────────────────────
        hl_theme = QHBoxLayout()
        self.lbl_theme = QLabel(tr("Theme:", AppConfig.lang))
        self.combo_theme = QComboBox()
        self.combo_theme.addItem("Dark", "dark")
        self.combo_theme.addItem("Light", "light")
        hl_theme.addWidget(self.lbl_theme)
        hl_theme.addWidget(self.combo_theme)
        hl_theme.addStretch()
        gl.addLayout(hl_theme)

        # ── Tooltips ──────────────────────────────────────────
        self.chk_tooltips = QCheckBox(tr("Show Tooltips", AppConfig.lang))
        gl.addWidget(self.chk_tooltips)

        # ── Auto Build Index ─────────────────────────────────
        self.chk_auto_build = QCheckBox(tr("Auto Build Index on Startup", AppConfig.lang))
        gl.addWidget(self.chk_auto_build)

        # ── Periodic Build Index ─────────────────────────────
        hl_periodic = QHBoxLayout()
        self.chk_periodic = QCheckBox(tr("Enable Periodic Index Build", AppConfig.lang))
        self.lbl_interval = QLabel(tr("Interval (minutes):", AppConfig.lang))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 1440)  # 1分〜24時間
        self.spin_interval.setFixedWidth(60)
        hl_periodic.addWidget(self.chk_periodic)
        hl_periodic.addStretch()
        hl_periodic.addWidget(self.lbl_interval)
        hl_periodic.addWidget(self.spin_interval)
        gl.addLayout(hl_periodic)

        # ── FO4 Data Folder ─────────────────────────────────
        hl_data = QHBoxLayout()
        self.lbl_data = QLabel(tr("FO4 Data Folder:", AppConfig.lang))
        self.edit_data = QLineEdit()
        self.edit_data.setPlaceholderText(tr("Path to Fallout 4/Data", AppConfig.lang))
        self.btn_data = QPushButton("...")
        self.btn_data.setFixedWidth(30)
        self.btn_data.clicked.connect(self._browse_data)
        hl_data.addWidget(self.lbl_data)
        hl_data.addWidget(self.edit_data, 1)
        hl_data.addWidget(self.btn_data)
        gl.addLayout(hl_data)

        # ── MO2 Mods Folder ────────────────────────────────
        hl_mo2 = QHBoxLayout()
        self.lbl_mo2 = QLabel(tr("MO2 Mods Folder:", AppConfig.lang))
        self.edit_mo2 = QLineEdit()
        self.edit_mo2.setPlaceholderText(tr("Path to MO2/mods folder", AppConfig.lang))
        self.btn_mo2 = QPushButton("...")
        self.btn_mo2.setFixedWidth(30)
        self.btn_mo2.clicked.connect(self._browse_mo2)
        hl_mo2.addWidget(self.lbl_mo2)
        hl_mo2.addWidget(self.edit_mo2, 1)
        hl_mo2.addWidget(self.btn_mo2)
        gl.addLayout(hl_mo2)

        # ── Build Index Button ─────────────────────────────
        hl_idx = QHBoxLayout()
        self.btn_build_index = QPushButton(tr("Build Texture Index", AppConfig.lang))
        self.btn_build_index.setFixedWidth(200)
        self.btn_build_index.clicked.connect(self._build_index)
        self.lbl_index_status = QLabel("")
        hl_idx.addWidget(self.btn_build_index)
        hl_idx.addWidget(self.lbl_index_status, 1)
        gl.addLayout(hl_idx)

        root.addWidget(grp)
        root.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def _load_from_config(self):
        # Language
        idx = self.combo_lang.findData(AppConfig.lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        # Theme
        idx = self.combo_theme.findData(AppConfig.theme)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)
        # Tooltips
        self.chk_tooltips.setChecked(AppConfig.show_tooltips)
        # Auto Build
        self.chk_auto_build.setChecked(AppConfig.auto_build_index)
        # Periodic Build
        self.chk_periodic.setChecked(AppConfig.periodic_build_index)
        self.spin_interval.setValue(AppConfig.build_interval_min)
        self.spin_interval.setEnabled(AppConfig.periodic_build_index)
        # Data path
        self.edit_data.setText(AppConfig.fo4_data_path)
        # MO2 path
        self.edit_mo2.setText(AppConfig.mo2_mods_path)


    def _on_lang_changed(self):
        data = self.combo_lang.currentData()
        AppConfig.set_lang(data)

    def _on_theme_changed(self):
        data = self.combo_theme.currentData()
        AppConfig.set_theme(data)

    def _on_tooltips_changed(self, state):
        AppConfig.set_tooltips(state != 0)

    def _on_auto_build_changed(self, state):
        AppConfig.set_auto_build(state != 0)

    def _on_periodic_changed(self, state):
        enabled = (state != 0)
        AppConfig.set_periodic_build(enabled)
        self.spin_interval.setEnabled(enabled)

    def _on_interval_changed(self, val):
        AppConfig.set_build_interval(val)

    def _browse_data(self):
        path = QFileDialog.getExistingDirectory(self, tr("FO4 Data Folder:", AppConfig.lang))
        if path:
            self.edit_data.setText(path)
            AppConfig.set_fo4_data_path(path)

    def _browse_mo2(self):
        path = QFileDialog.getExistingDirectory(self, tr("MO2 Mods Folder:", AppConfig.lang))
        if path:
            self.edit_mo2.setText(path)
            AppConfig.set_mo2_mods_path(path)

    def _on_data_changed(self):
        AppConfig.set_fo4_data_path(self.edit_data.text())

    def _on_mo2_changed(self):
        AppConfig.set_mo2_mods_path(self.edit_mo2.text())

    def _build_index(self, silent=False):
        if hasattr(self, "_idx_thread") and self._idx_thread.isRunning():
            return
        if not silent:
            self.lbl_index_status.setText(tr("Building index...", AppConfig.lang))
        self.btn_build_index.setEnabled(False)
        self._idx_thread = _IndexWorker()
        self._idx_thread.finished_signal.connect(self._on_index_built)
        self._idx_thread.start()

    def _on_index_built(self, count):
        msg = tr("Index built: {count} textures found", AppConfig.lang).replace("{count}", str(count))
        self.lbl_index_status.setText(msg)
        self.btn_build_index.setEnabled(True)
        # MainWindowのログにも出したいので、AppConfig経由か何かで通知したいが
        # ここではシンプルにシグナルなしでMainWindowが直接フックするようにする
        pass

    def _connect_signals(self):
        self.combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        self.chk_tooltips.stateChanged.connect(self._on_tooltips_changed)
        self.chk_auto_build.stateChanged.connect(self._on_auto_build_changed)
        self.chk_periodic.stateChanged.connect(self._on_periodic_changed)
        self.spin_interval.valueChanged.connect(self._on_interval_changed)
        self.edit_data.editingFinished.connect(self._on_data_changed)
        self.edit_mo2.editingFinished.connect(self._on_mo2_changed)
        
        # 外部から言語が変わった場合に自身のUIを更新する
        AppConfig.language_changed.connect(self.retranslate)

    def retranslate(self, lang: str):
        """言語変更時の自身（SettingsTab）の再翻訳"""
        self.grp.setTitle(tr("Settings", lang))
        self.lbl_lang.setText(tr("Language:", lang))
        self.lbl_theme.setText(tr("Theme:", lang))
        self.chk_tooltips.setText(tr("Show Tooltips", lang))
        self.chk_auto_build.setText(tr("Auto Build Index on Startup", lang))
        self.chk_periodic.setText(tr("Enable Periodic Index Build", lang))
        self.lbl_interval.setText(tr("Interval (minutes):", lang))
        self.lbl_data.setText(tr("FO4 Data Folder:", lang))
        self.edit_data.setPlaceholderText(tr("Path to Fallout 4/Data", lang))
        self.lbl_mo2.setText(tr("MO2 Mods Folder:", lang))
        self.edit_mo2.setPlaceholderText(tr("Path to MO2/mods folder", lang))
        self.btn_build_index.setText(tr("Build Texture Index", lang))


class _IndexWorker(QThread):
    finished_signal = pyqtSignal(int)

    def run(self):
        count = AppConfig.build_texture_index()
        self.finished_signal.emit(count)

