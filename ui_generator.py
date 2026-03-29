"""
ui_generator.py — BGSM生成タブ
テンプレートベース生成 + DDS連動生成
サブフォルダ構造を維持した出力 & フォルダごとの Normal/Spec 設定に対応
"""

import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QFileDialog, QGroupBox, QCheckBox, QMessageBox,
    QScrollArea, QGridLayout, QInputDialog, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from bgsm_core import BGSM
from utils import extract_game_path, get_app_dir
from config import AppConfig, tr

PRESETS_DIR = os.path.join(get_app_dir(), "presets")
os.makedirs(PRESETS_DIR, exist_ok=True)


def scan_dds_grouped(folder: str) -> dict[str, list[str]]:
    """
    フォルダを再帰スキャンし、サブフォルダ別に .dds ファイルをグループ化して返す。
    キーはソースフォルダからの相対パス（ルート直下は ""）。
    """
    result: dict[str, list[str]] = {}
    folder = os.path.normpath(folder)
    for root, _, files in os.walk(folder):
        dds_list = [os.path.join(root, f) for f in files if f.lower().endswith(".dds")]
        if dds_list:
            rel = os.path.relpath(root, folder)
            if rel == ".":
                rel = ""
            result[rel] = sorted(dds_list)
    return result


class GeneratorWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)

    def __init__(self, template: BGSM, grouped_dds: dict[str, list[str]],
                 out_dir: str, folder_maps: dict[str, tuple[str, str]],
                 global_normal: str, global_specular: str):
        super().__init__()
        self.template = template
        self.grouped_dds = grouped_dds
        self.out_dir = out_dir
        self.folder_maps = folder_maps        # { subfolder: (normal, spec) }
        self.global_normal = global_normal
        self.global_specular = global_specular

    def run(self):
        ok = err = 0
        for subfolder, dds_list in self.grouped_dds.items():
            # 出力先 = out_dir / subfolder（構造維持）
            if subfolder:
                out_sub = os.path.join(self.out_dir, subfolder)
            else:
                out_sub = self.out_dir
            os.makedirs(out_sub, exist_ok=True)

            # このフォルダ用の Normal / Spec を決定
            fm = self.folder_maps.get(subfolder, ("", ""))
            normal = fm[0] or self.global_normal
            specular = fm[1] or self.global_specular

            for dds in dds_list:
                try:
                    b = BGSM()
                    for attr in vars(self.template):
                        if not attr.startswith("_"):
                            # テクスチャ情報はテンプレートから引き継がない
                            if attr.endswith("_texture"):
                                continue
                            setattr(b, attr, getattr(self.template, attr))

                    stem = Path(dds).stem
                    game_dds = extract_game_path(dds)
                    b.diffuse_texture = game_dds
                    if normal:
                        b.normal_texture = normal
                    if specular:
                        b.smooth_spec_texture = specular

                    out_path = os.path.join(out_sub, stem + ".bgsm")
                    b.write(out_path)
                    self.log.emit(f"✅ {out_path}")
                    ok += 1
                except Exception as e:
                    self.log.emit(f"❌ {dds} → {e}")
                    err += 1
        self.finished.emit(ok, err)


# ── フォルダ別 Normal/Spec 設定行ウィジェット ─────────────────────────────────
class _FolderMapRow(QWidget):
    """サブフォルダ1つ分の Normal / Smooth-Spec 入力行"""
    def __init__(self, folder_name: str, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        lay = QGridLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setColumnStretch(1, 1)

        lbl = QLabel(f"{folder_name}")
        lbl.setStyleSheet("font-weight: bold;")
        lay.addWidget(lbl, 0, 0, 1, 2)

        self.edit_normal = QLineEdit()
        self.edit_normal.setPlaceholderText(tr("Normal path (Empty = Template)", AppConfig.lang))
        btn_n = QPushButton("..."); btn_n.setFixedWidth(30)
        btn_n.clicked.connect(lambda: self._browse(self.edit_normal))
        w_n = QWidget(); hl_n = QHBoxLayout(w_n); hl_n.setContentsMargins(0,0,0,0)
        hl_n.addWidget(self.edit_normal, 1); hl_n.addWidget(btn_n)
        lay.addWidget(QLabel("Normal:"), 1, 0)
        lay.addWidget(w_n, 1, 1)

        self.edit_spec = QLineEdit()
        self.edit_spec.setPlaceholderText(tr("Spec path (Empty = Template)", AppConfig.lang))
        btn_s = QPushButton("..."); btn_s.setFixedWidth(30)
        btn_s.clicked.connect(lambda: self._browse(self.edit_spec))
        w_s = QWidget(); hl_s = QHBoxLayout(w_s); hl_s.setContentsMargins(0,0,0,0)
        hl_s.addWidget(self.edit_spec, 1); hl_s.addWidget(btn_s)
        lay.addWidget(QLabel("Smooth/Spec:"), 2, 0)
        lay.addWidget(w_s, 2, 1)

    def _browse(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "DDS選択", "", "DDS (*.dds);;All (*)")
        if path:
            edit.setText(extract_game_path(path))

    def get_maps(self) -> tuple[str, str]:
        return self.edit_normal.text(), self.edit_spec.text()


class GeneratorTab(QWidget):
    def __init__(self, log_callback=None, parent=None):
        super().__init__(parent)
        self._log_cb = log_callback
        self._template: BGSM | None = None
        self._worker = None
        self._grouped_dds: dict[str, list[str]] = {}
        self._folder_rows: list[_FolderMapRow] = []
        os.makedirs(PRESETS_DIR, exist_ok=True)
        self.setAcceptDrops(True)
        self._build_ui()

    # ── フォルダ D&D 対応 ─────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if os.path.isdir(url.toLocalFile()):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.edit_src.setText(path)
                event.acceptProposedAction()
                return

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # ---- テンプレート選択 ----
        self.grp_tmpl = QGroupBox(tr("Template", AppConfig.lang))
        tl = QVBoxLayout(self.grp_tmpl)

        r1 = QHBoxLayout()
        self.edit_tmpl = QLineEdit()
        self.edit_tmpl.setPlaceholderText(tr("Select template BGSM file", AppConfig.lang))
        self.btn_tmpl = QPushButton(tr("Browse...", AppConfig.lang))
        self.btn_tmpl.setFixedWidth(70)
        self.btn_tmpl.clicked.connect(self._browse_template)
        self.lbl_tmpl_title = QLabel(tr("BGSM File:", AppConfig.lang))
        r1.addWidget(self.lbl_tmpl_title)
        r1.addWidget(self.edit_tmpl, 1)
        r1.addWidget(self.btn_tmpl)
        tl.addLayout(r1)

        r2 = QHBoxLayout()
        self.combo_preset = QComboBox()
        self.combo_preset.setMinimumWidth(200)
        btn_reload = QPushButton("⟳"); btn_reload.setFixedWidth(30)
        btn_reload.clicked.connect(self._reload_presets)
        self.btn_load_preset = QPushButton(tr("Load", AppConfig.lang))
        self.btn_load_preset.setFixedWidth(80)
        self.btn_load_preset.clicked.connect(self._load_preset)
        self.btn_save_preset = QPushButton(tr("Save Current Settings", AppConfig.lang))
        self.btn_save_preset.clicked.connect(self._save_preset)
        self.lbl_preset_title = QLabel(tr("Preset:", AppConfig.lang))
        r2.addWidget(self.lbl_preset_title)
        r2.addWidget(self.combo_preset, 1)
        r2.addWidget(btn_reload)
        r2.addWidget(self.btn_load_preset)
        r2.addWidget(self.btn_save_preset)
        tl.addLayout(r2)

        self.lbl_tmpl_status = QLabel(tr("Template not selected", AppConfig.lang))
        self.lbl_tmpl_status.setStyleSheet("font-style: italic;")
        tl.addWidget(self.lbl_tmpl_status)
        root.addWidget(self.grp_tmpl)

        # ---- ソース DDS フォルダ ----
        self.grp_src = QGroupBox(tr("Source DDS Folder", AppConfig.lang))
        sl = QHBoxLayout(self.grp_src)
        self.edit_src = QLineEdit()
        self.edit_src.setPlaceholderText(tr("Folder containing DDS files", AppConfig.lang))
        self.btn_src = QPushButton(tr("Browse...", AppConfig.lang))
        self.btn_src.setFixedWidth(70)
        self.btn_src.clicked.connect(self._browse_src)
        self.btn_scan = QPushButton(tr("Scan", AppConfig.lang))
        self.btn_scan.setFixedWidth(70)
        self.btn_scan.clicked.connect(self._scan_src)
        sl.addWidget(self.edit_src, 1)
        sl.addWidget(self.btn_src)
        sl.addWidget(self.btn_scan)
        root.addWidget(self.grp_src)

        self.lbl_scan_info = QLabel("")
        self.lbl_scan_info.setStyleSheet("font-weight: bold;")
        root.addWidget(self.lbl_scan_info)

        # ---- 出力フォルダ ----
        self.grp_out = QGroupBox(tr("Output Folder", AppConfig.lang))
        ol = QHBoxLayout(self.grp_out)
        self.edit_out = QLineEdit()
        self.edit_out.setPlaceholderText(tr("Folder to output BGSMs", AppConfig.lang))
        self.btn_out = QPushButton(tr("Browse...", AppConfig.lang))
        self.btn_out.setFixedWidth(70)
        self.btn_out.clicked.connect(self._browse_out)
        ol.addWidget(self.edit_out, 1)
        ol.addWidget(self.btn_out)
        root.addWidget(self.grp_out)

        # ---- 共通マップ（グローバルフォールバック） ----
        self.grp_common = QGroupBox(tr("Common Map Overrides (Optional)", AppConfig.lang))
        cl = QGridLayout(self.grp_common)
        cl.setColumnStretch(1, 1)

        self.edit_common_normal = QLineEdit()
        self.edit_common_normal.setPlaceholderText(tr("Normal path (Empty = Template)", AppConfig.lang))
        btn_cn = QPushButton("..."); btn_cn.setFixedWidth(30)
        btn_cn.clicked.connect(lambda: self._browse_dds(self.edit_common_normal))

        self.edit_common_specular = QLineEdit()
        self.edit_common_specular.setPlaceholderText(tr("Spec path (Empty = Template)", AppConfig.lang))
        btn_cs = QPushButton("..."); btn_cs.setFixedWidth(30)
        btn_cs.clicked.connect(lambda: self._browse_dds(self.edit_common_specular))

        self.lbl_cn = QLabel(tr("Common Normal:", AppConfig.lang))
        cl.addWidget(self.lbl_cn, 0, 0)
        w1 = QWidget(); hl1 = QHBoxLayout(w1); hl1.setContentsMargins(0,0,0,0)
        hl1.addWidget(self.edit_common_normal, 1); hl1.addWidget(btn_cn)
        cl.addWidget(w1, 0, 1)
        self.lbl_cs = QLabel(tr("Common Smooth/Spec:", AppConfig.lang))
        cl.addWidget(self.lbl_cs, 1, 0)
        w2 = QWidget(); hl2 = QHBoxLayout(w2); hl2.setContentsMargins(0,0,0,0)
        hl2.addWidget(self.edit_common_specular, 1); hl2.addWidget(btn_cs)
        cl.addWidget(w2, 1, 1)
        root.addWidget(self.grp_common)

        # ---- フォルダ別 Normal/Spec 設定エリア（スキャン後に動的生成） ----
        self.grp_per_folder = QGroupBox(tr("Per-Folder Map Overrides", AppConfig.lang))
        self.grp_per_folder.setVisible(False)
        self._per_folder_layout = QVBoxLayout(self.grp_per_folder)
        self._per_folder_layout.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.grp_per_folder)
        scroll.setMinimumHeight(120)
        root.addWidget(scroll, 1)

        # 実行ボタン
        self.btn_gen = QPushButton(tr("Generate BGSMs", AppConfig.lang))
        self.btn_gen.setFixedHeight(38)
        self.btn_gen.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_gen.clicked.connect(self._run)
        root.addWidget(self.btn_gen)

        self._reload_presets()

    # ── スキャン ────────────────────────────────────────────────────────────
    def _scan_src(self):
        src = self.edit_src.text()
        if not src or not os.path.isdir(src):
            QMessageBox.warning(self, tr("Warning", AppConfig.lang),
                                tr("Please specify a valid folder", AppConfig.lang))
            return

        self._grouped_dds = scan_dds_grouped(src)
        total = sum(len(v) for v in self._grouped_dds.values())
        n_folders = len(self._grouped_dds)

        self.lbl_scan_info.setText(
            f"{n_folders} folder(s) / {total} DDS file(s)")

        # フォルダ別 UI を再構築
        self._rebuild_per_folder_ui()

    def _rebuild_per_folder_ui(self):
        """スキャン結果に基づいてフォルダ別 Normal/Spec 設定行を動的に生成する。"""
        # 既存ウィジェットをクリア
        for row in self._folder_rows:
            row.setParent(None)
            row.deleteLater()
        self._folder_rows.clear()

        subfolders = sorted(k for k in self._grouped_dds if k)  # "" を除外
        if len(subfolders) < 2:
            # サブフォルダが1つ以下なら共通設定のみで十分
            self.grp_per_folder.setVisible(False)
            return

        self.grp_per_folder.setVisible(True)
        for sf in subfolders:
            count = len(self._grouped_dds[sf])
            row = _FolderMapRow(f"{sf}  ({count} files)")
            row.folder_name = sf
            self._per_folder_layout.addWidget(row)
            self._folder_rows.append(row)

            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #45475a;")
            self._per_folder_layout.addWidget(sep)

        self._per_folder_layout.addStretch(1)

    # ── プリセット管理 ──────────────────────────────────────────────────────
    def _reload_presets(self):
        self.combo_preset.clear()
        if os.path.isdir(PRESETS_DIR):
            for f in sorted(os.listdir(PRESETS_DIR)):
                if f.endswith(".json"):
                    self.combo_preset.addItem(f[:-5], f)

    def _browse_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "テンプレートBGSM選択", "", "BGSM (*.bgsm)")
        if path:
            try:
                self._template = BGSM.read(path)
                self.edit_tmpl.setText(path)
                self.lbl_tmpl_status.setText(f"✅ 読み込み完了: v{self._template.version}")
                self.lbl_tmpl_status.setStyleSheet("color: #7de87d;")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"読み込み失敗:\n{e}")

    def _load_preset(self):
        name = self.combo_preset.currentData()
        if not name:
            return
        path = os.path.join(PRESETS_DIR, name)
        try:
            self._template = BGSM.load_preset(path)
            self.edit_tmpl.clear()
            self.lbl_tmpl_status.setText(f"✅ プリセット読み込み: {name}")
            self.lbl_tmpl_status.setStyleSheet("color: #7de87d;")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"プリセット読み込み失敗:\n{e}")

    def _save_preset(self):
        if self._template is None:
            QMessageBox.warning(self, tr("Warning", AppConfig.lang),
                                tr("Please select a template", AppConfig.lang))
            return
        name, ok = QInputDialog.getText(
            self, tr("Preset Name", AppConfig.lang),
            tr("Enter preset name to save:", AppConfig.lang))
        if ok and name:
            path = os.path.join(PRESETS_DIR, name + ".json")
            self._template.save_preset(path)
            if self._log_cb:
                self._log_cb(f"{tr('Saved preset:', AppConfig.lang)} {path}")
            self._reload_presets()

    # ── フォルダ選択 ────────────────────────────────────────────────────────
    def _browse_src(self):
        d = QFileDialog.getExistingDirectory(self, "DDSソースフォルダ")
        if d:
            self.edit_src.setText(d)

    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "出力フォルダ")
        if d:
            self.edit_out.setText(d)

    def _browse_dds(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "DDS選択", "", "DDS (*.dds);;All (*)")
        if path:
            edit.setText(extract_game_path(path))

    # ── 生成実行 ────────────────────────────────────────────────────────────
    def _run(self):
        if self._template is None:
            QMessageBox.warning(self, tr("Warning", AppConfig.lang),
                                tr("Please select a template", AppConfig.lang))
            return

        # スキャンがまだなら自動実行
        if not self._grouped_dds:
            self._scan_src()
        if not self._grouped_dds:
            return

        out = self.edit_out.text()
        if not out:
            QMessageBox.warning(self, tr("Warning", AppConfig.lang),
                                tr("Please specify a valid folder", AppConfig.lang))
            return

        total = sum(len(v) for v in self._grouped_dds.values())
        ret = QMessageBox.question(
            self, tr("Confirm", AppConfig.lang),
            f"{total} DDS → BGSM\n{tr('Are you sure you want to continue?', AppConfig.lang)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        # フォルダ別マップを収集
        folder_maps: dict[str, tuple[str, str]] = {}
        for row in self._folder_rows:
            n, s = row.get_maps()
            if n or s:
                folder_maps[row.folder_name] = (n, s)

        self._worker = GeneratorWorker(
            self._template, self._grouped_dds, out, folder_maps,
            self.edit_common_normal.text(),
            self.edit_common_specular.text()
        )
        self._worker.log.connect(lambda msg: self._log_cb(msg) if self._log_cb else None)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_done(self, ok: int, err: int):
        msg = f"{tr('Done', AppConfig.lang)}: {ok} / Error {err}"
        if self._log_cb:
            self._log_cb(msg)
        QMessageBox.information(self, tr("Done", AppConfig.lang), msg)

    # ── 翻訳対応 ────────────────────────────────────────────────────────────
    def retranslate(self, lang: str):
        self.grp_tmpl.setTitle(tr("Template", lang))
        self.edit_tmpl.setPlaceholderText(tr("Select template BGSM file", lang))
        self.btn_tmpl.setText(tr("Browse...", lang))
        self.lbl_tmpl_title.setText(tr("BGSM File:", lang))
        self.btn_load_preset.setText(tr("Load", lang))
        self.btn_save_preset.setText(tr("Save Current Settings", lang))
        self.lbl_preset_title.setText(tr("Preset:", lang))
        if self._template is None:
            self.lbl_tmpl_status.setText(tr("Template not selected", lang))

        self.grp_src.setTitle(tr("Source DDS Folder", lang))
        self.edit_src.setPlaceholderText(tr("Folder containing DDS files", lang))
        self.btn_src.setText(tr("Browse...", lang))
        self.btn_scan.setText(tr("Scan", lang))

        self.grp_out.setTitle(tr("Output Folder", lang))
        self.edit_out.setPlaceholderText(tr("Folder to output BGSMs", lang))
        self.btn_out.setText(tr("Browse...", lang))

        self.grp_common.setTitle(tr("Common Map Overrides (Optional)", lang))
        self.edit_common_normal.setPlaceholderText(tr("Normal path (Empty = Template)", lang))
        self.edit_common_specular.setPlaceholderText(tr("Spec path (Empty = Template)", lang))
        self.lbl_cn.setText(tr("Common Normal:", lang))
        self.lbl_cs.setText(tr("Common Smooth/Spec:", lang))

        self.grp_per_folder.setTitle(tr("Per-Folder Map Overrides", lang))
        self.btn_gen.setText("▶ " + tr("Generate BGSMs", lang))
