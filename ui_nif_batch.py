"""
ui_nif_batch.py — NIF バッチ生成タブ
元の NIF をテンプレートに、BGSM ごとに NIF を自動生成する。
nif_material_batch.py のコア機能を PyQt6 UI に統合。
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QGroupBox, QCheckBox, QProgressBar, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from config import AppConfig, tr


# ── ワーカースレッド ─────────────────────────────────────────────────────────
class NifBatchWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    finished_signal = pyqtSignal(int)

    def __init__(self, nif_path, bgsm_folder, prefix, output_folder, recursive):
        super().__init__()
        self.nif_path = nif_path
        self.bgsm_folder = bgsm_folder
        self.prefix = prefix
        self.output_folder = output_folder
        self.recursive = recursive

    def run(self):
        from nif_core import (
            batch_set_materials, batch_set_materials_recursive
        )
        try:
            def on_progress(current, total, filename):
                self.progress.emit(current, total)
                self.log.emit(f"  ✅ [{current}/{total}] {filename}")

            if self.recursive:
                generated = batch_set_materials_recursive(
                    source_nif_path=self.nif_path,
                    bgsm_root_folder=self.bgsm_folder,
                    material_base_prefix=self.prefix,
                    output_folder=self.output_folder,
                    progress_callback=on_progress
                )
            else:
                generated = batch_set_materials(
                    source_nif_path=self.nif_path,
                    bgsm_folder=self.bgsm_folder,
                    material_prefix=self.prefix,
                    output_folder=self.output_folder,
                    progress_callback=on_progress
                )
            self.log.emit(f"\n🎉 {len(generated)} NIF files generated.")
            self.finished_signal.emit(len(generated))
        except Exception as e:
            self.log.emit(f"\n❌ Error: {e}")
            self.finished_signal.emit(0)


# ── NIF バッチ生成タブ ───────────────────────────────────────────────────────
class NifBatchTab(QWidget):
    def __init__(self, log_callback=None, parent=None):
        super().__init__(parent)
        self._log_cb = log_callback
        self._worker = None
        self.setAcceptDrops(True)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        # ── 入力設定 ────────────────────────────────────
        self.grp_input = QGroupBox(tr("Input Settings", AppConfig.lang))
        gl = QVBoxLayout(self.grp_input)

        # 元 NIF ファイル
        row_nif = QHBoxLayout()
        self.lbl_nif = QLabel(tr("Source NIF File:", AppConfig.lang))
        self.edit_nif = QLineEdit()
        self.edit_nif.setPlaceholderText(tr("Select the template NIF file", AppConfig.lang))
        self.btn_nif = QPushButton(tr("Browse...", AppConfig.lang))
        self.btn_nif.setFixedWidth(80)
        self.btn_nif.clicked.connect(self._browse_nif)
        row_nif.addWidget(self.lbl_nif)
        row_nif.addWidget(self.edit_nif, 1)
        row_nif.addWidget(self.btn_nif)
        gl.addLayout(row_nif)

        # BGSM フォルダ
        row_bgsm = QHBoxLayout()
        self.lbl_bgsm = QLabel(tr("BGSM Folder:", AppConfig.lang))
        self.edit_bgsm = QLineEdit()
        self.edit_bgsm.setPlaceholderText(tr("Folder containing BGSM files", AppConfig.lang))
        
        # パスが手動で入力・ペーストされた際も即座に自動判定する（ログなし）
        self.edit_bgsm.textChanged.connect(self._auto_detect_prefix_silent)
        
        self.btn_bgsm = QPushButton(tr("Browse...", AppConfig.lang))
        self.btn_bgsm.setFixedWidth(80)
        self.btn_bgsm.clicked.connect(self._browse_bgsm)
        row_bgsm.addWidget(self.lbl_bgsm)
        row_bgsm.addWidget(self.edit_bgsm, 1)
        row_bgsm.addWidget(self.btn_bgsm)
        gl.addLayout(row_bgsm)

        # 再帰チェック
        self.chk_recursive = QCheckBox(tr("Scan subfolders recursively", AppConfig.lang))
        self.chk_recursive.setChecked(True)
        gl.addWidget(self.chk_recursive)

        # マテリアルプレフィックス
        row_prefix = QHBoxLayout()
        self.lbl_prefix = QLabel(tr("Material Base Prefix:", AppConfig.lang))
        self.edit_prefix = QLineEdit()
        self.edit_prefix.setPlaceholderText("Materials\\\\...")
        self.btn_auto = QPushButton(tr("Auto Detect", AppConfig.lang))
        self.btn_auto.setFixedWidth(100)
        self.btn_auto.clicked.connect(self._auto_detect_prefix)
        row_prefix.addWidget(self.lbl_prefix)
        row_prefix.addWidget(self.edit_prefix, 1)
        row_prefix.addWidget(self.btn_auto)
        gl.addLayout(row_prefix)

        self.lbl_hint = QLabel(tr("Example: Materials\\Folder\\Folder (subfolder paths are appended automatically)", AppConfig.lang))
        self.lbl_hint.setStyleSheet("color: gray; font-size: 11px;")
        gl.addWidget(self.lbl_hint)

        root.addWidget(self.grp_input)

        # ── 出力設定 ────────────────────────────────────
        self.grp_output = QGroupBox(tr("Output Settings", AppConfig.lang))
        ol = QVBoxLayout(self.grp_output)

        row_out = QHBoxLayout()
        self.lbl_output = QLabel(tr("Output Folder:", AppConfig.lang))
        self.edit_output = QLineEdit()
        self.edit_output.setPlaceholderText(tr("Folder to output NIF files", AppConfig.lang))
        self.btn_output = QPushButton(tr("Browse...", AppConfig.lang))
        self.btn_output.setFixedWidth(80)
        self.btn_output.clicked.connect(self._browse_output)
        row_out.addWidget(self.lbl_output)
        row_out.addWidget(self.edit_output, 1)
        row_out.addWidget(self.btn_output)
        ol.addLayout(row_out)

        root.addWidget(self.grp_output)

        # ── ボタン＋プログレス ──────────────────────────
        row_actions = QHBoxLayout()
        self.btn_preview = QPushButton(tr("Preview", AppConfig.lang))
        self.btn_preview.clicked.connect(self._preview)
        self.btn_run = QPushButton(tr("Run Batch", AppConfig.lang))
        self.btn_run.clicked.connect(self._run_batch)
        self.btn_run.setStyleSheet("font-weight: bold;")
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setValue(0)
        row_actions.addWidget(self.progress, 1)
        row_actions.addWidget(self.btn_preview)
        row_actions.addWidget(self.btn_run)
        root.addLayout(row_actions)

        root.addStretch()

    # ---- ドラッグ＆ドロップ ----
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.edit_bgsm.setText(path)
            elif path.lower().endswith('.nif'):
                self.edit_nif.setText(path)
                # nifファイルをドロップした際、出力先が空なら自動設定
                if not self.edit_output.text():
                    self.edit_output.setText(os.path.join(os.path.dirname(path), "output"))
        event.acceptProposedAction()

    # ---- ブラウズ系 ----
    def _browse_nif(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Select the template NIF file", AppConfig.lang),
            "", "NIF files (*.nif);;All files (*.*)"
        )
        if path:
            self.edit_nif.setText(path)
            if not self.edit_output.text():
                self.edit_output.setText(os.path.join(os.path.dirname(path), "output"))

    def _browse_bgsm(self):
        path = QFileDialog.getExistingDirectory(
            self, tr("BGSM Folder:", AppConfig.lang)
        )
        if path:
            self.edit_bgsm.setText(path)
            self._auto_detect_prefix()

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(
            self, tr("Output Folder:", AppConfig.lang)
        )
        if path:
            self.edit_output.setText(path)

    def _auto_detect_prefix(self):
        from nif_core import auto_detect_material_prefix
        bgsm_path = self.edit_bgsm.text()
        if not bgsm_path:
            return
        prefix = auto_detect_material_prefix(bgsm_path)
        if prefix:
            self.edit_prefix.setText(prefix)
            self._emit_log(f"Auto-detected prefix: {prefix}")
        else:
            self._emit_log("⚠ 'Materials\\' not found in path. Please enter prefix manually.")

    def _auto_detect_prefix_silent(self, text):
        from nif_core import auto_detect_material_prefix
        if not text:
            return
        prefix = auto_detect_material_prefix(text)
        if prefix:
            self.edit_prefix.setText(prefix)

    # ---- プレビュー ----
    def _preview(self):
        from nif_core import NifStringEditor, scan_bgsm_recursive

        nif_path = self.edit_nif.text()
        bgsm_folder = self.edit_bgsm.text()
        prefix = self.edit_prefix.text()
        recursive = self.chk_recursive.isChecked()

        if not nif_path:
            self._emit_log("❌ " + tr("Source NIF File:", AppConfig.lang) + " not specified")
            return
        if not bgsm_folder:
            self._emit_log("❌ " + tr("BGSM Folder:", AppConfig.lang) + " not specified")
            return
        if not prefix:
            self._emit_log("❌ " + tr("Material Base Prefix:", AppConfig.lang) + " not specified")
            return

        self._emit_log(f"📄 Source NIF: {nif_path}")
        if os.path.exists(nif_path):
            with open(nif_path, 'rb') as f:
                nif_data = f.read()
            editor = NifStringEditor()
            try:
                editor.read(nif_data)
                v = editor.version
                self._emit_log(f"   Version: {(v >> 24) & 0xFF}.{(v >> 16) & 0xFF}.{(v >> 8) & 0xFF}.{v & 0xFF}")
                self._emit_log(f"   BS Version: {editor.bs_version}")
                mat_indices = editor.find_bgsm_string_indices(materials_only=True)
                self._emit_log(f"   Replacement targets:")
                for idx in mat_indices:
                    self._emit_log(f"     [{idx}] {editor.strings[idx]} 🔄")
            except Exception as e:
                self._emit_log(f"   ⚠ Header parse error: {e}")

        self._emit_log(f"\n📁 BGSM Folder: {bgsm_folder}")
        self._emit_log(f"   Recursive: {'ON' if recursive else 'OFF'}")
        self._emit_log(f"   Base Prefix: {prefix}")

        if recursive:
            scan_results = scan_bgsm_recursive(bgsm_folder)
            total_files = sum(len(bl) for _, bl in scan_results)
            self._emit_log(f"\n   📊 {len(scan_results)} folders, {total_files} BGSM files:")
            for rel_path, bgsm_files in scan_results:
                display = rel_path if rel_path else "(root)"
                self._emit_log(f"\n   📂 {display} ({len(bgsm_files)} files)")
                for bg in bgsm_files[:3]:
                    nif_name = os.path.splitext(bg)[0] + '.nif'
                    self._emit_log(f"      {bg} → {nif_name}")
                if len(bgsm_files) > 3:
                    self._emit_log(f"      ... +{len(bgsm_files) - 3} more")
        else:
            try:
                bgsm_files = sorted([f for f in os.listdir(bgsm_folder) if f.lower().endswith('.bgsm')])
                if bgsm_files:
                    self._emit_log(f"   {len(bgsm_files)} BGSM files:")
                    for bg in bgsm_files:
                        nif_name = os.path.splitext(bg)[0] + '.nif'
                        self._emit_log(f"   {bg} → {nif_name}")
                else:
                    self._emit_log("   ⚠ No BGSM files found")
            except OSError:
                self._emit_log("   ⚠ Cannot access folder")

        self._emit_log(f"\n📂 Output: {self.edit_output.text()}")

    # ---- バッチ実行 ----
    def _run_batch(self):
        nif_path = self.edit_nif.text()
        bgsm_folder = self.edit_bgsm.text()
        prefix = self.edit_prefix.text()
        output_folder = self.edit_output.text()
        recursive = self.chk_recursive.isChecked()

        errors = []
        if not nif_path or not os.path.isfile(nif_path):
            errors.append(tr("Source NIF File:", AppConfig.lang))
        if not bgsm_folder or not os.path.isdir(bgsm_folder):
            errors.append(tr("BGSM Folder:", AppConfig.lang))
        if not prefix:
            errors.append(tr("Material Base Prefix:", AppConfig.lang))
        if not output_folder:
            errors.append(tr("Output Folder:", AppConfig.lang))

        if errors:
            QMessageBox.warning(self, tr("Warning", AppConfig.lang),
                                tr("Please specify:", AppConfig.lang) + "\n" + "\n".join(f"・{e}" for e in errors))
            return

        self.btn_run.setEnabled(False)
        self.progress.setValue(0)
        self._emit_log("🚀 " + tr("Starting batch process...", AppConfig.lang))

        self._worker = NifBatchWorker(nif_path, bgsm_folder, prefix, output_folder, recursive)
        self._worker.log.connect(self._emit_log)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def _on_finished(self, count):
        self.btn_run.setEnabled(True)
        if count > 0:
            output_folder = self.edit_output.text()
            # 翻訳キー: "{count} NIF files generated.\nOpen output folder?"
            msg = tr("{count} NIF files generated.\nOpen output folder?", AppConfig.lang).replace("{count}", str(count))
            reply = QMessageBox.question(
                self, tr("Done", AppConfig.lang),
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(output_folder)

    def _emit_log(self, msg):
        if self._log_cb:
            self._log_cb(msg)

    # ---- 翻訳 ----
    def retranslate(self, lang):
        self.grp_input.setTitle(tr("Input Settings", lang))
        self.lbl_nif.setText(tr("Source NIF File:", lang))
        self.edit_nif.setPlaceholderText(tr("Select the template NIF file", lang))
        self.lbl_bgsm.setText(tr("BGSM Folder:", lang))
        self.edit_bgsm.setPlaceholderText(tr("Folder containing BGSM files", lang))
        self.chk_recursive.setText(tr("Scan subfolders recursively", lang))
        self.lbl_prefix.setText(tr("Material Base Prefix:", lang))
        self.btn_auto.setText(tr("Auto Detect", lang))
        self.lbl_hint.setText(tr("Example: Materials\\Folder\\Folder (subfolder paths are appended automatically)", lang))
        self.btn_nif.setText(tr("Browse...", lang))
        self.btn_bgsm.setText(tr("Browse...", lang))
        self.btn_output.setText(tr("Browse...", lang))
        self.grp_output.setTitle(tr("Output Settings", lang))
        self.lbl_output.setText(tr("Output Folder:", lang))
        self.edit_output.setPlaceholderText(tr("Folder to output NIF files", lang))
        self.btn_preview.setText(tr("Preview", lang))
        self.btn_run.setText(tr("Run Batch", lang))
