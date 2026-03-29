"""
ui_batch_editor.py — 一括編集タブ
General / Material の2セクションでパラメータを整理し、
全パラメータを反映できるよう高度な設定レイヤー（折り畳み）を追加した。
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QDoubleSpinBox, QSpinBox, QComboBox, QFileDialog,
    QGridLayout, QGroupBox, QScrollArea, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from bgsm_core import BGSM, ALPHA_BLEND_MODES
from utils import scan_bgsm, extract_game_path, make_auto_path, TOOLTIPS
from ui_editor import ColorButton
from config import AppConfig, tr


class BatchWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)

    def __init__(self, files, opts):
        super().__init__()
        self.files = files
        self.opts = opts

    def run(self):
        ok = err = 0
        for path in self.files:
            try:
                bgsm = BGSM.read(path)
                self._apply(bgsm, path)
                bgsm.write(path)
                self.log.emit(f"✅ {path}")
                ok += 1
            except Exception as e:
                self.log.emit(f"❌ {path} → {e}")
                err += 1
        self.finished.emit(ok, err)

    def _apply(self, b: BGSM, path: str):
        o = self.opts

        # テクスチャパス
        for attr, key in [
            ("diffuse_texture",      "diffuse"),
            ("normal_texture",       "normal"),
            ("smooth_spec_texture",  "smooth"),
            ("greyscale_texture",    "greyscale"),
            ("envmap_texture",       "envmap"),
            ("glow_texture",         "glow"),
            ("inner_layer_texture",  "inner_layer"),
            ("wrinkles_texture",     "wrinkles"),
            ("displacement_texture", "displacement"),
        ]:
            raw = o.get(key, "")
            if raw:
                setattr(b, attr, extract_game_path(raw))
            elif key == "diffuse" and o.get("auto_mapping") and o.get("auto_base"):
                setattr(b, attr, make_auto_path(o["auto_base"], path))

        # ---- 全パラメータのマッピング ----
        # str/bool/int/float 型のプロパティをすべてループで判定
        all_attrs = [
            # General
            "version", "tile_u", "tile_v", "u_offset", "v_offset", "u_scale", "v_scale",
            "alpha", "alpha_blend_mode", "alpha_test_ref", "alpha_test",
            "z_buffer_write", "z_buffer_test", "screen_space_reflections",
            "wetness_control_ssr", "decal", "two_sided", "decal_no_fade",
            "non_occluder", "refraction", "refraction_falloff", "refraction_power",
            "environment_mapping", "environment_mapping_mask_scale",
            "grayscale_to_palette_color",

            # Material
            "enable_editor_alpha_ref", "rim_lighting", "rim_power", "back_light_power",
            "subsurface_lighting", "subsurface_lighting_rolloff", "specular_enabled",
            "specular_mult", "smoothness", "fresnel_power", "wetness_control_spec_scale",
            "wetness_control_spec_power_scale", "wetness_control_spec_minvar",
            "wetness_control_env_map_scale", "wetness_control_fresnel_power",
            "wetness_control_metalness", "root_material_path", "aniso_lighting",
            "emit_enabled", "emittance_mult", "model_space_normals", "external_emittance",
            "back_lighting", "receive_shadows", "hide_secret", "cast_shadows",
            "dissolve_fade", "assume_shadowmask", "glowmap", "environment_mapping_window",
            "environment_mapping_eye", "hair", "tree", "facegen", "skin_tint",
            "tessellate", "displacement_texture_bias", "displacement_texture_scale",
            "tessellation_pn_scale", "tessellation_base_factor", "tessellation_fade_distance",
            "grayscale_to_palette_scale", "skew_specular_alpha"
        ]

        for attr in all_attrs:
            if attr in o and o[attr] is not None:
                setattr(b, attr, o[attr])

        # カラー型（別枠）
        for attr in ["specular_color", "emittance_color", "hair_tint_color"]:
            if attr in o and o[attr] is not None:
                setattr(b, attr, o[attr])


# ── ヘルパー ──────────────────────────────────────────────────────────────────
def _chk_row(grid: QGridLayout, row: int, label: str, widget: QWidget):
    """チェックボックス + ラベル + ウィジェットを1行に配置する共通関数"""
    chk = QCheckBox()
    lbl = QLabel(label)
    lbl.setProperty("orig_text", label)
    grid.addWidget(chk, row, 0)
    grid.addWidget(lbl, row, 1)
    grid.addWidget(widget, row, 2)

    tip = TOOLTIPS.get(label)
    if tip:
        chk.setProperty("orig_tip", tip)
        lbl.setProperty("orig_tip", tip)
        widget.setProperty("orig_tip", tip)
        if AppConfig.show_tooltips:
            chk.setToolTip(tip)
            lbl.setToolTip(tip)
            widget.setToolTip(tip)
        
    return chk, lbl


class BatchEditorTab(QWidget):
    def __init__(self, log_callback=None, parent=None):
        super().__init__(parent)
        self._log_cb = log_callback
        self._worker = None
        self._files = []
        self._param_widgets = {}
        self._all_params = [] # [(chk, lbl, w), ...]用
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
                self.edit_folder.setText(path)
                event.acceptProposedAction()
                return

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # ── フォルダ選択 ────────────────────────────────────────────────────
        self.grp_folder = QGroupBox(tr("Target Folder", AppConfig.lang))
        fl = QHBoxLayout(self.grp_folder)
        self.edit_folder = QLineEdit()
        self.edit_folder.setPlaceholderText(tr("Folder containing BGSM files", AppConfig.lang))
        self.btn_browse = QPushButton(tr("Browse...", AppConfig.lang))
        self.btn_browse.setFixedWidth(70)
        self.btn_browse.clicked.connect(self._browse_folder)
        self.btn_scan = QPushButton(tr("Scan", AppConfig.lang))
        self.btn_scan.setFixedWidth(70)
        self.btn_scan.clicked.connect(self._scan)
        fl.addWidget(self.edit_folder, 1)
        fl.addWidget(self.btn_browse)
        fl.addWidget(self.btn_scan)
        root.addWidget(self.grp_folder)

        self.lbl_count = QLabel(tr("Scan Count:", AppConfig.lang) + " -")
        root.addWidget(self.lbl_count)

        # ── スクロールエリア ────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        vl = QVBoxLayout(inner)
        vl.setSpacing(10)

        # ---- テクスチャパス ------------------------------------------------
        self.tex_grp = QGroupBox(tr("Texture Paths (Empty = No change)", AppConfig.lang))
        tgl = QGridLayout(self.tex_grp)
        tgl.setColumnStretch(2, 1)
        self.tex_fields = {}
        self.lbl_tex = [] # プレースホルダー更新用など
        for tr_idx, (label, key) in enumerate([
            ("Diffuse:",    "diffuse"),
            ("Normal:",     "normal"),
            ("Smooth/Spec:", "smooth"),
            ("Greyscale:",  "greyscale"),
            ("Envmap:",     "envmap"),
            ("Glow:",       "glow"),
            ("Inner Layer:", "inner_layer"),
            ("Wrinkles:",    "wrinkles"),
            ("Displacement:", "displacement"),
        ]):
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.lbl_tex.append(lbl)
            edit = QLineEdit()
            edit.setPlaceholderText(tr("Can paste absolute paths (auto extracts game path)", AppConfig.lang))
            edit.textChanged.connect(lambda t, e=edit: self._auto_extract(e, t))
            btn = QPushButton("...")
            btn.setFixedWidth(30)
            btn.clicked.connect(lambda _, e=edit: self._browse_tex(e))
            w = QWidget(); rl = QHBoxLayout(w); rl.setContentsMargins(0,0,0,0)
            rl.addWidget(edit, 1); rl.addWidget(btn)
            tgl.addWidget(lbl, tr_idx, 0)
            tgl.addWidget(w, tr_idx, 1, 1, 2)
            self.tex_fields[key] = edit
            self.lbl_tex.append(edit)

        # オートマッピング
        auto_w = QWidget()
        al = QHBoxLayout(auto_w); al.setContentsMargins(0,0,0,0)
        self.chk_auto = QCheckBox(tr("Auto Mapping (Auto-set Diffuse to [Base Path\\bgsm_filename.dds])", AppConfig.lang))
        self.edit_auto_base = QLineEdit()
        self.edit_auto_base.setPlaceholderText(tr("Base Path (e.g. textures\\actor\\)", AppConfig.lang))
        btn_auto = QPushButton("..."); btn_auto.setFixedWidth(30)
        btn_auto.clicked.connect(lambda: self._browse_tex(self.edit_auto_base))
        al.addWidget(self.chk_auto); al.addWidget(self.edit_auto_base, 1); al.addWidget(btn_auto)
        tgl.addWidget(auto_w, len(self.tex_fields), 0, 1, 3)
        vl.addWidget(self.tex_grp)

        # ---- パラメータ（タブ式: General / Material） ----------------------
        self.lbl_desc = QLabel(tr("Check the parameters you want to apply on the left", AppConfig.lang))
        self.lbl_desc.setStyleSheet("font-weight: bold; margin-top: 8px;")
        vl.addWidget(self.lbl_desc)

        self._adv_buttons = []
        self.param_tab = QTabWidget()
        
        # GeneralとMaterialは長くなるため分割して呼び出し
        self.param_tab.addTab(self._build_general_params(), "General")
        self.param_tab.addTab(self._build_material_params(), "Material")
        self.param_tab.setCurrentIndex(1)
        vl.addWidget(self.param_tab)
        vl.addStretch(1)

        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # ── 実行ボタン ───────────────────────────────────────────────────────
        self.btn_run = QPushButton(tr("Apply Batch", AppConfig.lang))
        self.btn_run.setFixedHeight(38)
        self.btn_run.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_run.clicked.connect(self._run)
        root.addWidget(self.btn_run)

    def _create_collapsible(self, title: str) -> tuple[QWidget, QGridLayout]:
        """折り畳みトグルボタンと内部グリッドを持つウィジェットを返す"""
        container = QWidget()
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 4, 0, 0)
        
        toggle_btn = QPushButton(f"▼ {title}")
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(False)
        toggle_btn.setStyleSheet("text-align: left; font-weight: bold; border: none; background: transparent;")
        
        content = QWidget()
        gl = QGridLayout(content)
        gl.setColumnStretch(2, 1)
        content.setVisible(False)
        
        toggle_btn.toggled.connect(content.setVisible)
        # title ではなく常に翻訳関数を通すようにラムダを修正
        toggle_btn.toggled.connect(lambda checked, tb=toggle_btn: tb.setText(f"▲ {tr('Advanced Settings', AppConfig.lang)}" if checked else f"▼ {tr('Advanced Settings', AppConfig.lang)}"))
        
        self._adv_buttons.append(toggle_btn)
        cl.addWidget(toggle_btn)
        cl.addWidget(content)
        return container, gl

    def _build_general_params(self) -> QWidget:
        main_w = QWidget()
        vbox = QVBoxLayout(main_w)
        
        w_basic = QWidget()
        gl = QGridLayout(w_basic)
        gl.setColumnStretch(2, 1)
        row = 0

        def add_spin(key, label, default=0.0, min_v=0, max_v=1e6, decimals=4):
            nonlocal row
            s = QDoubleSpinBox(); s.setRange(min_v, max_v); s.setDecimals(decimals); s.setValue(default)
            chk, lbl = _chk_row(gl, row, label, s)
            self._param_widgets[key] = (chk, s); self._all_params.append((chk, lbl, s)); row += 1

        def add_int(key, label, default=0, min_v=0, max_v=255):
            nonlocal row
            s = QSpinBox(); s.setRange(min_v, max_v); s.setValue(default)
            chk, lbl = _chk_row(gl, row, label, s)
            self._param_widgets[key] = (chk, s); self._all_params.append((chk, lbl, s)); row += 1

        def add_chk(key, label):
            nonlocal row
            cb = QCheckBox()
            chk, lbl = _chk_row(gl, row, label, cb)
            self._param_widgets[key] = (chk, cb); self._all_params.append((chk, lbl, cb)); row += 1

        def add_combo(key, label, items):
            nonlocal row
            c = QComboBox(); c.addItems(items)
            chk, lbl = _chk_row(gl, row, label, c)
            self._param_widgets[key] = (chk, c); self._all_params.append((chk, lbl, c)); row += 1

        # ---- 基本パラメータ (以前のまま表示) ----
        add_spin("alpha", "Alpha", 1.0, 0, 1)
        add_combo("alpha_blend_mode", "Alpha Blend Mode", ALPHA_BLEND_MODES)
        add_int("alpha_test_ref", "Alpha Test Ref", 128)
        add_chk("alpha_test", "Alpha Test")
        add_chk("z_buffer_write", "Z Buffer Write")
        add_chk("z_buffer_test", "Z Buffer Test")
        add_chk("two_sided", "Two Sided")
        add_chk("decal", "Decal")
        add_chk("environment_mapping", "Environment Mapping")
        add_spin("environment_mapping_mask_scale", "Env Mapping Mask Scale", 1.0, 0, 100)

        gl.setRowStretch(row, 1)
        vbox.addWidget(w_basic)
        
        # ---- 詳細（折り畳み）パラメータ ----
        adv_container, gl = self._create_collapsible(tr("Advanced Settings", AppConfig.lang))
        # ここからは gl が Advanced 側のグリッドになる
        row = 0
        
        add_int("version", "Version", 2, 0, 99)
        add_chk("tile_u", "Tile U")
        add_chk("tile_v", "Tile V")
        add_spin("u_offset", "U Offset", 0.0, -1e6, 1e6)
        add_spin("v_offset", "V Offset", 0.0, -1e6, 1e6)
        add_spin("u_scale", "U Scale", 1.0, -1e6, 1e6)
        add_spin("v_scale", "V Scale", 1.0, -1e6, 1e6)
        add_chk("screen_space_reflections", "Screen Space Reflections")
        add_chk("wetness_control_ssr", "Wetness Control SSR")
        add_chk("decal_no_fade", "Decal No Fade")
        add_chk("non_occluder", "Non Occluder")
        add_chk("refraction", "Refraction")
        add_chk("refraction_falloff", "Refraction Falloff")
        add_spin("refraction_power", "Refraction Power", 0.0, -1e6, 1e6)
        add_chk("grayscale_to_palette_color", "Grayscale To Palette Color")
        
        gl.setRowStretch(row, 1)
        vbox.addWidget(adv_container)
        vbox.addStretch(1)

        return main_w

    def _build_material_params(self) -> QWidget:
        main_w = QWidget()
        vbox = QVBoxLayout(main_w)

        w_basic = QWidget()
        gl = QGridLayout(w_basic)
        gl.setColumnStretch(2, 1)
        row = 0

        def add_spin(key, label, default=0.0, min_v=0, max_v=1e6, decimals=4):
            nonlocal row
            s = QDoubleSpinBox(); s.setRange(min_v, max_v); s.setDecimals(decimals); s.setValue(default)
            chk, lbl = _chk_row(gl, row, label, s)
            self._param_widgets[key] = (chk, s); self._all_params.append((chk, lbl, s)); row += 1

        def add_chk(key, label):
            nonlocal row
            cb = QCheckBox()
            chk, lbl = _chk_row(gl, row, label, cb)
            self._param_widgets[key] = (chk, cb); self._all_params.append((chk, lbl, cb)); row += 1

        def add_color(key, label, default=0xFFFFFF):
            nonlocal row
            btn = ColorButton(default)
            chk, lbl = _chk_row(gl, row, label, btn)
            self._param_widgets[key] = (chk, btn); self._all_params.append((chk, lbl, btn)); row += 1

        def add_text(key, label):
            nonlocal row
            t = QLineEdit()
            chk, lbl = _chk_row(gl, row, label, t)
            self._param_widgets[key] = (chk, t); self._all_params.append((chk, lbl, t)); row += 1

        # ---- 基本パラメータ ----
        add_chk("specular_enabled", "Specular Enabled")
        add_color("specular_color", "Specular Color")
        add_spin("specular_mult", "Specular Mult", 1.0)
        add_spin("smoothness", "Smoothness", 1.0, 0, 1)
        add_chk("emit_enabled", "Emit Enabled")
        add_color("emittance_color", "Emittance Color")
        add_spin("emittance_mult", "Emittance Mult", 1.0)
        add_chk("glowmap", "Glowmap")

        gl.setRowStretch(row, 1)
        vbox.addWidget(w_basic)

        # ---- 詳細（折り畳み）パラメータ ----
        adv_container, gl = self._create_collapsible(tr("Advanced Settings", AppConfig.lang))
        row = 0
        
        add_chk("enable_editor_alpha_ref", "Enable Editor Alpha Ref")
        add_chk("rim_lighting", "Rim Lighting")
        add_spin("rim_power", "Rim Power", 2.0)
        add_spin("back_light_power", "Back Light Power", 0.0)
        add_chk("subsurface_lighting", "Subsurface Lighting")
        add_spin("subsurface_lighting_rolloff", "Subsurface Lighting Rolloff", 0.3)
        add_spin("fresnel_power", "Fresnel Power", 5.0)
        add_spin("wetness_control_spec_scale", "Wetness Spec Scale", -1.0, -1e6, 1e6)
        add_spin("wetness_control_spec_power_scale", "Wetness Spec Power Scale", -1.0, -1e6, 1e6)
        add_spin("wetness_control_spec_minvar", "Wetness Spec Minvar", -1.0, -1e6, 1e6)
        add_spin("wetness_control_env_map_scale", "Wetness Env Map Scale", -1.0, -1e6, 1e6)
        add_spin("wetness_control_fresnel_power", "Wetness Fresnel Power", -1.0, -1e6, 1e6)
        add_spin("wetness_control_metalness", "Wetness Metalness", -1.0, -1e6, 1e6)

        add_text("root_material_path", "Root Material Path")
        add_chk("aniso_lighting", "Aniso Lighting")
        add_chk("model_space_normals", "Model Space Normals")
        add_chk("external_emittance", "External Emittance")
        add_chk("back_lighting", "Back Lighting")
        add_chk("receive_shadows", "Receive Shadows")
        add_chk("hide_secret", "Hide Secret")
        add_chk("cast_shadows", "Cast Shadows")
        add_chk("dissolve_fade", "Dissolve Fade")
        add_chk("assume_shadowmask", "Assume Shadowmask")
        add_chk("environment_mapping_window", "Env Mapping Window")
        add_chk("environment_mapping_eye", "Env Mapping Eye")
        add_chk("hair", "Hair")
        add_color("hair_tint_color", "Hair Tint Color", 0x808080)
        add_chk("tree", "Tree")
        add_chk("facegen", "Facegen")
        add_chk("skin_tint", "Skin Tint")
        add_chk("tessellate", "Tessellate")

        add_spin("displacement_texture_bias", "Displacement Bias", -0.5, -1e6, 1e6)
        add_spin("displacement_texture_scale", "Displacement Scale", 10.0, -1e6, 1e6)
        add_spin("tessellation_pn_scale", "Tessellation Pn Scale", 1.0, -1e6, 1e6)
        add_spin("tessellation_base_factor", "Tessellation Base Factor", 1.0, -1e6, 1e6)
        add_spin("tessellation_fade_distance", "Tessellation Fade Distance", 0.0, -1e6, 1e6)
        add_spin("grayscale_to_palette_scale", "Grayscale To Palette Scale", 1.0, -1e6, 1e6)
        add_chk("skew_specular_alpha", "Skew Specular Alpha")

        gl.setRowStretch(row, 1)
        vbox.addWidget(adv_container)
        vbox.addStretch(1)

        return main_w

    # ── ブラウザ / 入力補助 ────────────────────────────────────────────────
    def _browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, tr("Target Folder", AppConfig.lang))
        if d:
            self.edit_folder.setText(d)

    def _browse_tex(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "DDS", "", "DDS (*.dds);;All (*)")
        if path:
            edit.setText(extract_game_path(path))

    def _auto_extract(self, edit: QLineEdit, text: str):
        if ":\\" in text or ":/" in text:
            converted = extract_game_path(text)
            if converted != text:
                edit.blockSignals(True)
                edit.setText(converted)
                edit.blockSignals(False)

    def _scan(self):
        folder = self.edit_folder.text()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, tr("Warning", AppConfig.lang), tr("Please specify a valid folder", AppConfig.lang))
            return
        self._files = scan_bgsm(folder)
        self.lbl_count.setText(f"{tr('Scan Count:', AppConfig.lang)} {len(self._files)}")

    # ── 実行 ──────────────────────────────────────────────────────────────
    def _run(self):
        if not self._files:
            QMessageBox.warning(self, tr("Warning", AppConfig.lang), tr("Please specify a valid folder", AppConfig.lang))
            return

        ret = QMessageBox.question(
            self, tr("Confirm", AppConfig.lang),
            f"{tr('Are you sure you want to continue?', AppConfig.lang)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        opts = {}
        for key, (chk, w) in self._param_widgets.items():
            if not chk.isChecked():
                continue
            if isinstance(w, QCheckBox):
                opts[key] = w.isChecked()
            elif isinstance(w, QDoubleSpinBox):
                opts[key] = w.value()
            elif isinstance(w, QSpinBox):
                opts[key] = w.value()
            elif isinstance(w, QComboBox):
                opts[key] = w.currentText()
            elif isinstance(w, ColorButton):
                opts[key] = w.get_color()
            elif isinstance(w, QLineEdit):
                opts[key] = w.text()

        for key, edit in self.tex_fields.items():
            opts[key] = edit.text()

        opts["auto_mapping"] = self.chk_auto.isChecked()
        opts["auto_base"] = self.edit_auto_base.text()

        self._worker = BatchWorker(self._files, opts)
        self._worker.log.connect(lambda msg: self._log_cb(msg) if self._log_cb else None)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_done(self, ok: int, err: int):
        msg = f"{tr('Done', AppConfig.lang)}: OK {ok} / Error {err}"
        if self._log_cb:
            self._log_cb(msg)
        QMessageBox.information(self, tr("Done", AppConfig.lang), msg)

    # ── 翻訳・ツールチップ制御 ────────────────────────────────────────────────
    def retranslate(self, lang: str):
        self.grp_folder.setTitle(tr("Target Folder", lang))
        self.edit_folder.setPlaceholderText(tr("Folder containing BGSM files", lang))
        self.btn_browse.setText(tr("Browse...", lang))
        self.btn_scan.setText(tr("Scan", lang))
        self.lbl_count.setText(f"{tr('Scan Count:', lang)} {len(self._files) if self._files else '-'}")
        
        self.tex_grp.setTitle(tr("Texture Paths (Empty = No change)", lang))
        for edit in self.lbl_tex:
            if isinstance(edit, QLineEdit):
                edit.setPlaceholderText(tr("Can paste absolute paths (auto extracts game path)", lang))
        
        self.chk_auto.setText(tr("Auto Mapping (Auto-set Diffuse to [Base Path\\bgsm_filename.dds])", lang))
        self.edit_auto_base.setPlaceholderText(tr("Base Path (e.g. textures\\actor\\)", lang))
        self.lbl_desc.setText(tr("Check the parameters you want to apply on the left", lang))
        self.btn_run.setText(tr("Apply Batch", lang))

        for btn in self._adv_buttons:
            title = tr("Advanced Settings", lang)
            prefix = "▲" if btn.isChecked() else "▼"
            btn.setText(f"{prefix} {title}")

    def set_tooltips_enabled(self, show: bool):
        for chk, lbl, w in self._all_params:
            tip = chk.property("orig_tip")
            if tip:
                val = tip if show else ""
                chk.setToolTip(val)
                lbl.setToolTip(val)
                w.setToolTip(val)
