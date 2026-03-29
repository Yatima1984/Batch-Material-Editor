"""
ui_editor.py — 単体BGSM編集タブ
General / Material の2サブタブ構成。
依存する子項目はトグル式で親がONのときのみ展開される。
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QDoubleSpinBox, QSpinBox, QComboBox, QTabWidget,
    QScrollArea, QFileDialog, QGridLayout, QFrame, QColorDialog,
    QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from bgsm_core import BGSM, BGEM, ALPHA_BLEND_MODES, read_material
from utils import TOOLTIPS
from config import AppConfig, tr


# ─────────────────────────────────────────────────────────────────────────────
# 共通ヘルパーウィジェット
# ─────────────────────────────────────────────────────────────────────────────

class ColorButton(QPushButton):
    """カラーピッカーを開くボタン"""
    color_changed = pyqtSignal(int)

    def __init__(self, color_int: int = 0xFFFFFF, parent=None):
        super().__init__(parent)
        self._color = color_int
        self._update_style()
        self.clicked.connect(self._pick)
        self.setFixedHeight(28)
        self.setMinimumWidth(80)

    def _update_style(self):
        r = (self._color >> 16) & 0xFF
        g = (self._color >> 8) & 0xFF
        b = self._color & 0xFF
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        fg = "#000000" if lum > 128 else "#FFFFFF"
        self.setStyleSheet(
            f"background-color: #{self._color:06x}; color: {fg}; "
            f"border: 1px solid #555; border-radius: 4px;"
        )
        self.setText(f"#{self._color:06X}")

    def _pick(self):
        init = QColor((self._color >> 16) & 0xFF,
                      (self._color >> 8) & 0xFF,
                      self._color & 0xFF)
        c = QColorDialog.getColor(init, self)
        if c.isValid():
            self._color = (c.red() << 16) | (c.green() << 8) | c.blue()
            self._update_style()
            self.color_changed.emit(self._color)

    def get_color(self) -> int:
        return self._color

    def set_color(self, v: int):
        self._color = v & 0xFFFFFF
        self._update_style()


class TextureRow(QWidget):
    """テクスチャパス入力行（テキスト + 参照ボタン + パス存在チェック）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.textChanged.connect(self._check_path)
        btn = QPushButton("...")
        btn.setFixedWidth(30)
        btn.clicked.connect(self._browse)
        lay.addWidget(self.edit)
        lay.addWidget(btn)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "テクスチャ選択", "", "DDS (*.dds);;All (*)")
        if path:
            self.edit.setText(BGSM.extract_game_path(path))

    def _check_path(self, text: str):
        """テクスチャインデックスが構築済みなら O(1) で存在チェック"""
        if not text.strip():
            self.edit.setStyleSheet("")
            self.edit.setToolTip("")
            return
        if AppConfig.check_texture_exists(text):
            self.edit.setStyleSheet("")
            self.edit.setToolTip("")
        else:
            self.edit.setStyleSheet("border: 2px solid #e64553;")
            self.edit.setToolTip(tr("Texture not found", AppConfig.lang))

    def text(self) -> str:
        return self.edit.text()

    def setText(self, t: str):
        self.edit.setText(t)


# ─────────────────────────────────────────────────────────────────────────────
# 依存折り畳みウィジェット
# ─────────────────────────────────────────────────────────────────────────────

class DependentSection(QWidget):
    """
    親チェックボックスがONのときのみ子ウィジェット群を表示するコンテナ。
    子は QGridLayout に _row() で追加する。
    """
    def __init__(self, parent_check: QCheckBox, parent=None):
        super().__init__(parent)
        self._parent_check = parent_check
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 0, 0, 0)  # インデント
        self._layout.setSpacing(2)
        parent_check.stateChanged.connect(self._on_toggle)
        self.setVisible(parent_check.isChecked())

    def _on_toggle(self, state):
        self.setVisible(state != 0)

    def add_row(self, label: str, widget: QWidget, target_list: list = None):
        row_w = QWidget()
        hl = QHBoxLayout(row_w)
        hl.setContentsMargins(0, 0, 0, 0)
        lbl_text = label.replace(":", "")
        lbl = QLabel(label)
        lbl.setProperty("orig_text", lbl_text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setFixedWidth(180)
        lbl.setStyleSheet("color: #89b4fa;")
        
        tip = TOOLTIPS.get(lbl_text)
        if tip:
            lbl.setProperty("orig_tip", tip)
            widget.setProperty("orig_tip", tip)
            if AppConfig.show_tooltips:
                lbl.setToolTip(tip)
                widget.setToolTip(tip)
            
        hl.addWidget(lbl)
        hl.addWidget(widget, 1)
        self._layout.addWidget(row_w)
        if target_list is not None:
            target_list.append((lbl, widget))


def _scroll(inner: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(inner)
    return sa


def _row(layout: QGridLayout, row: int, label: str, widget: QWidget, target_list: list = None):
    lbl_text = label.replace(":", "")
    lbl = QLabel(label)
    lbl.setProperty("orig_text", lbl_text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    tip = TOOLTIPS.get(lbl_text)
    if tip:
        lbl.setProperty("orig_tip", tip)
        widget.setProperty("orig_tip", tip)
        if AppConfig.show_tooltips:
            lbl.setToolTip(tip)
            widget.setToolTip(tip)
    layout.addWidget(lbl, row, 0)
    layout.addWidget(widget, row, 1)
    if target_list is not None:
        target_list.append((lbl, widget))


def _check(val: bool) -> QCheckBox:
    cb = QCheckBox()
    cb.setChecked(val)
    return cb


def _spin(val: float, mn=-1e6, mx=1e6, decimals=4) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(mn, mx)
    sb.setDecimals(decimals)
    sb.setValue(val)
    return sb


def _int_spin(val: int, mn=0, mx=255) -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(mn, mx)
    sb.setValue(val)
    return sb


def _sep(layout: QGridLayout, row: int):
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("color: #45475a;")
    layout.addWidget(sep, row, 0, 1, 2)


# ─────────────────────────────────────────────────────────────────────────────
# メイン編集タブ
# ─────────────────────────────────────────────────────────────────────────────

class EditorTab(QWidget):
    """単体 BGSM/BGEM 編集タブ（General / Material の2サブタブ)"""
    file_opened = pyqtSignal(str)
    file_saved = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bgsm: BGSM | None = None
        self._bgem: BGEM | None = None
        self._is_bgem: bool = False
        self.setAcceptDrops(True)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # ファイル操作バー
        bar = QHBoxLayout()
        self.lbl_path = QLabel(tr("Please open a file", AppConfig.lang))
        self.lbl_path.setStyleSheet("color: #aaa;")
        bar.addWidget(self.lbl_path, 1)
        root.addLayout(bar)

        self.tab = QTabWidget()
        self.tab.addTab(self._build_general_tab(), "General")
        self._bgsm_material_tab = self._build_material_tab()
        self._bgem_material_tab = self._build_bgem_material_tab()

        # BGSM/BGEM モード切り替えバー
        mode_bar = QHBoxLayout()
        mode_bar.setContentsMargins(0, 4, 0, 0)
        mode_lbl = QLabel("Mode:")
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("BGSM (Material)", "bgsm")
        self.combo_mode.addItem("BGEM (Effect)", "bgem")
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        mode_bar.addWidget(mode_lbl)
        mode_bar.addWidget(self.combo_mode)
        mode_bar.addStretch()
        root.addLayout(mode_bar)

        self.tab.addTab(self._bgsm_material_tab, "Material")
        self.tab.setCurrentIndex(1)
        root.addWidget(self.tab)

    def _on_mode_changed(self, index):
        mode = self.combo_mode.currentData()
        is_bgem = (mode == "bgem")
        self._is_bgem = is_bgem
        self._switch_material_tab(is_bgem=is_bgem)

    # ── General タブ ─────────────────────────────────────────────────────────
    def _build_general_tab(self) -> QWidget:
        inner = QWidget()
        gl = QGridLayout(inner)
        gl.setColumnStretch(1, 1)
        r = 0

        self._all_labels = []

        self.w_version = _int_spin(2, 1, 22)
        _row(gl, r, "Version:", self.w_version, self._all_labels); r += 1
        self.w_tile_u = _check(True)
        self.w_tile_v = _check(True)
        _row(gl, r, "Tile U:", self.w_tile_u, self._all_labels); r += 1
        _row(gl, r, "Tile V:", self.w_tile_v, self._all_labels); r += 1
        self.w_u_offset = _spin(0.0);  self.w_v_offset = _spin(0.0)
        self.w_u_scale  = _spin(1.0);  self.w_v_scale  = _spin(1.0)
        _row(gl, r, "U Offset:", self.w_u_offset, self._all_labels); r += 1
        _row(gl, r, "V Offset:", self.w_v_offset, self._all_labels); r += 1
        _row(gl, r, "U Scale:",  self.w_u_scale, self._all_labels);  r += 1
        _row(gl, r, "V Scale:",  self.w_v_scale, self._all_labels);  r += 1

        self.w_alpha = _spin(1.0, 0, 1)
        _row(gl, r, "Alpha:", self.w_alpha, self._all_labels); r += 1

        self.w_alpha_blend = QComboBox()
        self.w_alpha_blend.addItems(ALPHA_BLEND_MODES)
        _row(gl, r, "Alpha Blend Mode:", self.w_alpha_blend, self._all_labels); r += 1

        self.w_alpha_test_ref = _int_spin(128)
        _row(gl, r, "Alpha Test Ref:", self.w_alpha_test_ref, self._all_labels); r += 1
        self.w_alpha_test = _check(False)
        _row(gl, r, "Alpha Test:", self.w_alpha_test, self._all_labels); r += 1

        self.w_zbuf_write = _check(True);  self.w_zbuf_test = _check(True)
        _row(gl, r, "Z Buffer Write:", self.w_zbuf_write, self._all_labels); r += 1
        _row(gl, r, "Z Buffer Test:",  self.w_zbuf_test, self._all_labels);  r += 1

        for label, attr in [
            ("Screen Space Reflections:", "w_ssr"),
            ("Wetness Control SSR:",       "w_wet_ssr"),
            ("Decal:",                     "w_decal"),
            ("Two Sided:",                 "w_two_sided"),
            ("Decal No Fade:",             "w_decal_no_fade"),
            ("Non Occluder:",              "w_non_occluder"),
        ]:
            w = _check(False); setattr(self, attr, w)
            _row(gl, r, label, w, self._all_labels); r += 1

        # Refraction → 子項目 折り畳み
        self.w_refraction = _check(False)
        _row(gl, r, "Refraction:", self.w_refraction, self._all_labels); r += 1
        self._sec_refraction = DependentSection(self.w_refraction)
        self.w_refraction_falloff = _check(False)
        self.w_refraction_power   = _spin(0.0)
        self._sec_refraction.add_row("Refraction Falloff:", self.w_refraction_falloff, self._all_labels)
        self._sec_refraction.add_row("Refraction Power:",   self.w_refraction_power, self._all_labels)
        gl.addWidget(self._sec_refraction, r, 0, 1, 2); r += 1

        # Environment Mapping → 子項目 折り畳み
        self.w_env_mapping = _check(False)
        _row(gl, r, "Environment Mapping:", self.w_env_mapping, self._all_labels); r += 1
        self._sec_env = DependentSection(self.w_env_mapping)
        self.w_env_mask_scale = _spin(1.0)
        self._sec_env.add_row("Env Mapping Mask Scale:", self.w_env_mask_scale, self._all_labels)
        gl.addWidget(self._sec_env, r, 0, 1, 2); r += 1

        self.w_grayscale_palette = _check(False)
        _row(gl, r, "Grayscale To Palette Color:", self.w_grayscale_palette, self._all_labels); r += 1

        gl.setRowStretch(r, 1)
        return _scroll(inner)

    # ── Material タブ ────────────────────────────────────────────────────────
    def _build_material_tab(self) -> QWidget:
        inner = QWidget()
        gl = QGridLayout(inner)
        gl.setColumnStretch(1, 1)
        r = 0

        # テクスチャパス
        for label, attr in [
            ("Diffuse Texture:",       "w_diffuse"),
            ("Normal Texture:",        "w_normal"),
            ("Smooth/Spec Texture:",   "w_smooth_spec"),
            ("Greyscale Texture:",     "w_greyscale"),
            ("Envmap Texture:",        "w_envmap"),
            ("Glow Texture:",          "w_glow"),
            ("Inner Layer Texture:",   "w_inner_layer"),
            ("Wrinkles Texture:",      "w_wrinkles"),
            ("Displacement Texture:",  "w_displacement"),
        ]:
            w = TextureRow(); setattr(self, attr, w)
            _row(gl, r, label, w, self._all_labels); r += 1

        _sep(gl, r); r += 1

        self.w_enable_editor_alpha = _check(False)
        _row(gl, r, "Enable Editor Alpha Ref:", self.w_enable_editor_alpha, self._all_labels); r += 1

        # RimLighting → RimPower 折り畳み（v<8）
        self.w_rim_lighting = _check(False)
        _row(gl, r, "Rim Lighting:", self.w_rim_lighting, self._all_labels); r += 1
        self._sec_rim = DependentSection(self.w_rim_lighting)
        self.w_rim_power = _spin(2.0)
        self._sec_rim.add_row("Rim Power:", self.w_rim_power, self._all_labels)
        gl.addWidget(self._sec_rim, r, 0, 1, 2); r += 1

        self.w_back_light_power = _spin(0.0)
        _row(gl, r, "Back Light Power:", self.w_back_light_power, self._all_labels); r += 1

        # SubsurfaceLighting → Rolloff 折り畳み
        self.w_subsurface = _check(False)
        _row(gl, r, "Subsurface Lighting:", self.w_subsurface, self._all_labels); r += 1
        self._sec_subsurface = DependentSection(self.w_subsurface)
        self.w_subsurface_rolloff = _spin(0.3)
        self._sec_subsurface.add_row("Subsurface Lighting Rolloff:", self.w_subsurface_rolloff, self._all_labels)
        gl.addWidget(self._sec_subsurface, r, 0, 1, 2); r += 1

        _sep(gl, r); r += 1

        # SpecularEnabled → Color / Mult 折り畳み
        self.w_specular_enabled = _check(False)
        _row(gl, r, "Specular Enabled:", self.w_specular_enabled, self._all_labels); r += 1
        self._sec_specular = DependentSection(self.w_specular_enabled)
        self.w_specular_color = ColorButton(0xFFFFFF)
        self.w_specular_mult  = _spin(1.0)
        self._sec_specular.add_row("Specular Color:", self.w_specular_color, self._all_labels)
        self._sec_specular.add_row("Specular Mult:",  self.w_specular_mult, self._all_labels)
        gl.addWidget(self._sec_specular, r, 0, 1, 2); r += 1

        self.w_smoothness = _spin(1.0, 0, 1)
        _row(gl, r, "Smoothness:", self.w_smoothness, self._all_labels); r += 1
        self.w_fresnel = _spin(5.0)
        _row(gl, r, "Fresnel Power:", self.w_fresnel, self._all_labels); r += 1

        for label, attr, default in [
            ("Wetness Spec Scale:",       "w_wet_spec_scale",  -1.0),
            ("Wetness Spec Power Scale:",  "w_wet_spec_power",  -1.0),
            ("Wetness Spec Minvar:",       "w_wet_spec_minvar", -1.0),
            ("Wetness Env Map Scale:",     "w_wet_env_scale",   -1.0),
            ("Wetness Fresnel Power:",     "w_wet_fresnel",     -1.0),
            ("Wetness Metalness:",         "w_wet_metalness",   -1.0),
        ]:
            w = _spin(default); setattr(self, attr, w)
            _row(gl, r, label, w, self._all_labels); r += 1

        _sep(gl, r); r += 1

        self.w_root_material = QLineEdit()
        _row(gl, r, "Root Material Path:", self.w_root_material, self._all_labels); r += 1

        self.w_aniso = _check(False)
        _row(gl, r, "Aniso Lighting:", self.w_aniso, self._all_labels); r += 1

        # EmitEnabled → Color / Mult 折り畳み
        self.w_emit_enabled = _check(False)
        _row(gl, r, "Emit Enabled:", self.w_emit_enabled, self._all_labels); r += 1
        self._sec_emit = DependentSection(self.w_emit_enabled)
        self.w_emittance_color = ColorButton(0xFFFFFF)
        self.w_emittance_mult  = _spin(1.0)
        self._sec_emit.add_row("Emittance Color:", self.w_emittance_color, self._all_labels)
        self._sec_emit.add_row("Emittance Mult:",  self.w_emittance_mult, self._all_labels)
        gl.addWidget(self._sec_emit, r, 0, 1, 2); r += 1

        for label, attr in [
            ("Model Space Normals:",  "w_msn"),
            ("External Emittance:",   "w_ext_emit"),
            ("Back Lighting:",        "w_back_lighting"),
            ("Receive Shadows:",      "w_recv_shadow"),
            ("Hide Secret:",          "w_hide_secret"),
            ("Cast Shadows:",         "w_cast_shadow"),
            ("Dissolve Fade:",        "w_dissolve"),
            ("Assume Shadowmask:",    "w_shadowmask"),
            ("Glowmap:",              "w_glowmap"),
            ("Env Mapping Window:",   "w_env_window"),
            ("Env Mapping Eye:",      "w_env_eye"),
        ]:
            w = _check(False); setattr(self, attr, w)
            _row(gl, r, label, w, self._all_labels); r += 1

        # Hair → HairTintColor 折り畳み
        self.w_hair = _check(False)
        _row(gl, r, "Hair:", self.w_hair, self._all_labels); r += 1
        self._sec_hair = DependentSection(self.w_hair)
        self.w_hair_tint = ColorButton(0x808080)
        self._sec_hair.add_row("Hair Tint Color:", self.w_hair_tint, self._all_labels)
        gl.addWidget(self._sec_hair, r, 0, 1, 2); r += 1

        for label, attr in [
            ("Tree:",     "w_tree"),
            ("Facegen:",  "w_facegen"),
            ("Skin Tint:", "w_skin_tint"),
        ]:
            w = _check(False); setattr(self, attr, w)
            _row(gl, r, label, w, self._all_labels); r += 1

        # Tessellate → Displacement/Tessellation 系 折り畳み（v<3）
        self.w_tessellate = _check(False)
        _row(gl, r, "Tessellate:", self.w_tessellate, self._all_labels); r += 1
        self._sec_tessellate = DependentSection(self.w_tessellate)
        self.w_disp_bias   = _spin(-0.5)
        self.w_disp_scale  = _spin(10.0)
        self.w_tess_pn     = _spin(1.0)
        self.w_tess_base   = _spin(1.0)
        self.w_tess_fade   = _spin(0.0)
        self._sec_tessellate.add_row("Displacement Bias:",         self.w_disp_bias, self._all_labels)
        self._sec_tessellate.add_row("Displacement Scale:",        self.w_disp_scale, self._all_labels)
        self._sec_tessellate.add_row("Tessellation Pn Scale:",     self.w_tess_pn, self._all_labels)
        self._sec_tessellate.add_row("Tessellation Base Factor:",  self.w_tess_base, self._all_labels)
        self._sec_tessellate.add_row("Tessellation Fade Distance:", self.w_tess_fade, self._all_labels)
        gl.addWidget(self._sec_tessellate, r, 0, 1, 2); r += 1

        self.w_gs_palette_scale = _spin(1.0)
        _row(gl, r, "Grayscale To Palette Scale:", self.w_gs_palette_scale, self._all_labels); r += 1
        self.w_skew_specular = _check(False)
        _row(gl, r, "Skew Specular Alpha:", self.w_skew_specular, self._all_labels); r += 1

        gl.setRowStretch(r, 1)
        return _scroll(inner)

    # ── データ ↔ UI ───────────────────────────────────────────────────────────
    def load_bgsm(self, bgsm: BGSM):
        self._bgsm = bgsm
        b = bgsm

        # General
        self.w_version.setValue(b.version)
        self.w_tile_u.setChecked(b.tile_u)
        self.w_tile_v.setChecked(b.tile_v)
        self.w_u_offset.setValue(b.u_offset)
        self.w_v_offset.setValue(b.v_offset)
        self.w_u_scale.setValue(b.u_scale)
        self.w_v_scale.setValue(b.v_scale)
        self.w_alpha.setValue(b.alpha)
        idx = ALPHA_BLEND_MODES.index(b.alpha_blend_mode) if b.alpha_blend_mode in ALPHA_BLEND_MODES else 0
        self.w_alpha_blend.setCurrentIndex(idx)
        self.w_alpha_test_ref.setValue(b.alpha_test_ref)
        self.w_alpha_test.setChecked(b.alpha_test)
        self.w_zbuf_write.setChecked(b.z_buffer_write)
        self.w_zbuf_test.setChecked(b.z_buffer_test)
        self.w_ssr.setChecked(b.screen_space_reflections)
        self.w_wet_ssr.setChecked(b.wetness_control_ssr)
        self.w_decal.setChecked(b.decal)
        self.w_two_sided.setChecked(b.two_sided)
        self.w_decal_no_fade.setChecked(b.decal_no_fade)
        self.w_non_occluder.setChecked(b.non_occluder)
        self.w_refraction.setChecked(b.refraction)
        self.w_refraction_falloff.setChecked(b.refraction_falloff)
        self.w_refraction_power.setValue(b.refraction_power)
        self.w_env_mapping.setChecked(b.environment_mapping)
        self.w_env_mask_scale.setValue(b.environment_mapping_mask_scale)
        self.w_grayscale_palette.setChecked(b.grayscale_to_palette_color)

        # Material
        self.w_diffuse.setText(b.diffuse_texture)
        self.w_normal.setText(b.normal_texture)
        self.w_smooth_spec.setText(b.smooth_spec_texture)
        self.w_greyscale.setText(b.greyscale_texture)
        self.w_envmap.setText(b.envmap_texture)
        self.w_glow.setText(b.glow_texture)
        self.w_inner_layer.setText(b.inner_layer_texture)
        self.w_wrinkles.setText(b.wrinkles_texture)
        self.w_displacement.setText(b.displacement_texture)
        self.w_enable_editor_alpha.setChecked(b.enable_editor_alpha_ref)
        self.w_rim_lighting.setChecked(b.rim_lighting)
        self.w_rim_power.setValue(b.rim_power)
        self.w_back_light_power.setValue(b.back_light_power)
        self.w_subsurface.setChecked(b.subsurface_lighting)
        self.w_subsurface_rolloff.setValue(b.subsurface_lighting_rolloff)
        self.w_specular_enabled.setChecked(b.specular_enabled)
        self.w_specular_color.set_color(b.specular_color)
        self.w_specular_mult.setValue(b.specular_mult)
        self.w_smoothness.setValue(b.smoothness)
        self.w_fresnel.setValue(b.fresnel_power)
        self.w_wet_spec_scale.setValue(b.wetness_control_spec_scale)
        self.w_wet_spec_power.setValue(b.wetness_control_spec_power_scale)
        self.w_wet_spec_minvar.setValue(b.wetness_control_spec_minvar)
        self.w_wet_env_scale.setValue(b.wetness_control_env_map_scale)
        self.w_wet_fresnel.setValue(b.wetness_control_fresnel_power)
        self.w_wet_metalness.setValue(b.wetness_control_metalness)
        self.w_root_material.setText(b.root_material_path)
        self.w_aniso.setChecked(b.aniso_lighting)
        self.w_emit_enabled.setChecked(b.emit_enabled)
        self.w_emittance_color.set_color(b.emittance_color)
        self.w_emittance_mult.setValue(b.emittance_mult)
        self.w_msn.setChecked(b.model_space_normals)
        self.w_ext_emit.setChecked(b.external_emittance)
        self.w_back_lighting.setChecked(b.back_lighting)
        self.w_recv_shadow.setChecked(b.receive_shadows)
        self.w_hide_secret.setChecked(b.hide_secret)
        self.w_cast_shadow.setChecked(b.cast_shadows)
        self.w_dissolve.setChecked(b.dissolve_fade)
        self.w_shadowmask.setChecked(b.assume_shadowmask)
        self.w_glowmap.setChecked(b.glowmap)
        self.w_env_window.setChecked(b.environment_mapping_window)
        self.w_env_eye.setChecked(b.environment_mapping_eye)
        self.w_hair.setChecked(b.hair)
        self.w_hair_tint.set_color(b.hair_tint_color)
        self.w_tree.setChecked(b.tree)
        self.w_facegen.setChecked(b.facegen)
        self.w_skin_tint.setChecked(b.skin_tint)
        self.w_tessellate.setChecked(b.tessellate)
        self.w_disp_bias.setValue(b.displacement_texture_bias)
        self.w_disp_scale.setValue(b.displacement_texture_scale)
        self.w_tess_pn.setValue(b.tessellation_pn_scale)
        self.w_tess_base.setValue(b.tessellation_base_factor)
        self.w_tess_fade.setValue(b.tessellation_fade_distance)
        self.w_gs_palette_scale.setValue(b.grayscale_to_palette_scale)
        self.w_skew_specular.setChecked(b.skew_specular_alpha)
        
        # GUIの仕様（小数の丸め等）に合わせた正規化済みの状態を基準データ（保存済み）として格納する
        self._bgsm = self.collect_bgsm()

    def collect_bgsm(self, target: BGSM = None) -> BGSM:
        import copy
        b = target or (copy.deepcopy(self._bgsm) if self._bgsm else BGSM())
        if self._bgsm and hasattr(self._bgsm, '_raw_path'):
            b._raw_path = self._bgsm._raw_path
        # General
        b.version = self.w_version.value()
        b.tile_u = self.w_tile_u.isChecked()
        b.tile_v = self.w_tile_v.isChecked()
        b.u_offset = self.w_u_offset.value()
        b.v_offset = self.w_v_offset.value()
        b.u_scale = self.w_u_scale.value()
        b.v_scale = self.w_v_scale.value()
        b.alpha = self.w_alpha.value()
        b.alpha_blend_mode = self.w_alpha_blend.currentText()
        b.alpha_test_ref = self.w_alpha_test_ref.value()
        b.alpha_test = self.w_alpha_test.isChecked()
        b.z_buffer_write = self.w_zbuf_write.isChecked()
        b.z_buffer_test = self.w_zbuf_test.isChecked()
        b.screen_space_reflections = self.w_ssr.isChecked()
        b.wetness_control_ssr = self.w_wet_ssr.isChecked()
        b.decal = self.w_decal.isChecked()
        b.two_sided = self.w_two_sided.isChecked()
        b.decal_no_fade = self.w_decal_no_fade.isChecked()
        b.non_occluder = self.w_non_occluder.isChecked()
        b.refraction = self.w_refraction.isChecked()
        b.refraction_falloff = self.w_refraction_falloff.isChecked()
        b.refraction_power = self.w_refraction_power.value()
        b.environment_mapping = self.w_env_mapping.isChecked()
        b.environment_mapping_mask_scale = self.w_env_mask_scale.value()
        b.grayscale_to_palette_color = self.w_grayscale_palette.isChecked()
        # Material
        b.diffuse_texture = self.w_diffuse.text()
        b.normal_texture = self.w_normal.text()
        b.smooth_spec_texture = self.w_smooth_spec.text()
        b.greyscale_texture = self.w_greyscale.text()
        b.envmap_texture = self.w_envmap.text()
        b.glow_texture = self.w_glow.text()
        b.inner_layer_texture = self.w_inner_layer.text()
        b.wrinkles_texture = self.w_wrinkles.text()
        b.displacement_texture = self.w_displacement.text()
        b.enable_editor_alpha_ref = self.w_enable_editor_alpha.isChecked()
        b.rim_lighting = self.w_rim_lighting.isChecked()
        b.rim_power = self.w_rim_power.value()
        b.back_light_power = self.w_back_light_power.value()
        b.subsurface_lighting = self.w_subsurface.isChecked()
        b.subsurface_lighting_rolloff = self.w_subsurface_rolloff.value()
        b.specular_enabled = self.w_specular_enabled.isChecked()
        b.specular_color = self.w_specular_color.get_color()
        b.specular_mult = self.w_specular_mult.value()
        b.smoothness = self.w_smoothness.value()
        b.fresnel_power = self.w_fresnel.value()
        b.wetness_control_spec_scale = self.w_wet_spec_scale.value()
        b.wetness_control_spec_power_scale = self.w_wet_spec_power.value()
        b.wetness_control_spec_minvar = self.w_wet_spec_minvar.value()
        b.wetness_control_env_map_scale = self.w_wet_env_scale.value()
        b.wetness_control_fresnel_power = self.w_wet_fresnel.value()
        b.wetness_control_metalness = self.w_wet_metalness.value()
        b.root_material_path = self.w_root_material.text()
        b.aniso_lighting = self.w_aniso.isChecked()
        b.emit_enabled = self.w_emit_enabled.isChecked()
        b.emittance_color = self.w_emittance_color.get_color()
        b.emittance_mult = self.w_emittance_mult.value()
        b.model_space_normals = self.w_msn.isChecked()
        b.external_emittance = self.w_ext_emit.isChecked()
        b.back_lighting = self.w_back_lighting.isChecked()
        b.receive_shadows = self.w_recv_shadow.isChecked()
        b.hide_secret = self.w_hide_secret.isChecked()
        b.cast_shadows = self.w_cast_shadow.isChecked()
        b.dissolve_fade = self.w_dissolve.isChecked()
        b.assume_shadowmask = self.w_shadowmask.isChecked()
        b.glowmap = self.w_glowmap.isChecked()
        b.environment_mapping_window = self.w_env_window.isChecked()
        b.environment_mapping_eye = self.w_env_eye.isChecked()
        b.hair = self.w_hair.isChecked()
        b.hair_tint_color = self.w_hair_tint.get_color()
        b.tree = self.w_tree.isChecked()
        b.facegen = self.w_facegen.isChecked()
        b.skin_tint = self.w_skin_tint.isChecked()
        b.tessellate = self.w_tessellate.isChecked()
        b.displacement_texture_bias = self.w_disp_bias.value()
        b.displacement_texture_scale = self.w_disp_scale.value()
        b.tessellation_pn_scale = self.w_tess_pn.value()
        b.tessellation_base_factor = self.w_tess_base.value()
        b.tessellation_fade_distance = self.w_tess_fade.value()
        b.grayscale_to_palette_scale = self.w_gs_palette_scale.value()
        b.skew_specular_alpha = self.w_skew_specular.isChecked()
        return b

    # ── BGEM Material タブ ──────────────────────────────────────────────────
    def _build_bgem_material_tab(self) -> QWidget:
        inner = QWidget()
        gl = QGridLayout(inner)
        gl.setColumnStretch(1, 1)
        r = 0

        if not hasattr(self, '_all_labels'):
            self._all_labels = []

        # テクスチャ
        self.w_bgem_base = TextureRow();     _row(gl, r, "Base Texture:",       self.w_bgem_base,       self._all_labels); r += 1
        self.w_bgem_grayscale = TextureRow(); _row(gl, r, "Grayscale Texture:", self.w_bgem_grayscale,  self._all_labels); r += 1
        self.w_bgem_envmap = TextureRow();    _row(gl, r, "Envmap Texture:",    self.w_bgem_envmap,     self._all_labels); r += 1
        self.w_bgem_normal = TextureRow();   _row(gl, r, "Normal Texture:",    self.w_bgem_normal,     self._all_labels); r += 1
        self.w_bgem_envmap_mask = TextureRow(); _row(gl, r, "Envmap Mask Texture:", self.w_bgem_envmap_mask, self._all_labels); r += 1
        self.w_bgem_specular = TextureRow(); _row(gl, r, "Specular Texture:",  self.w_bgem_specular,   self._all_labels); r += 1
        self.w_bgem_lighting = TextureRow(); _row(gl, r, "Lighting Texture:",  self.w_bgem_lighting,   self._all_labels); r += 1
        self.w_bgem_glow = TextureRow();     _row(gl, r, "Glow Texture:",      self.w_bgem_glow,       self._all_labels); r += 1

        # Effect パラメータ
        self.w_bgem_blood = _check(False);   _row(gl, r, "Blood Enabled:",     self.w_bgem_blood,      self._all_labels); r += 1
        self.w_bgem_effect_lighting = _check(False); _row(gl, r, "Effect Lighting Enabled:", self.w_bgem_effect_lighting, self._all_labels); r += 1
        self.w_bgem_falloff = _check(False); _row(gl, r, "Falloff Enabled:",   self.w_bgem_falloff,    self._all_labels); r += 1
        self.w_bgem_falloff_color = _check(False); _row(gl, r, "Falloff Color Enabled:", self.w_bgem_falloff_color, self._all_labels); r += 1
        self.w_bgem_gs_palette_alpha = _check(False); _row(gl, r, "Grayscale To Palette Alpha:", self.w_bgem_gs_palette_alpha, self._all_labels); r += 1
        self.w_bgem_soft = _check(False);    _row(gl, r, "Soft Enabled:",      self.w_bgem_soft,       self._all_labels); r += 1

        self.w_bgem_base_color = ColorButton(0xFFFFFF); _row(gl, r, "Base Color:", self.w_bgem_base_color, self._all_labels); r += 1
        self.w_bgem_base_color_scale = _spin(1.0, 0, 100); _row(gl, r, "Base Color Scale:", self.w_bgem_base_color_scale, self._all_labels); r += 1

        self.w_bgem_falloff_start_angle = _spin(1.0, 0, 360); _row(gl, r, "Falloff Start Angle:", self.w_bgem_falloff_start_angle, self._all_labels); r += 1
        self.w_bgem_falloff_stop_angle = _spin(1.0, 0, 360);  _row(gl, r, "Falloff Stop Angle:",  self.w_bgem_falloff_stop_angle, self._all_labels); r += 1
        self.w_bgem_falloff_start_opacity = _spin(0.0, 0, 1); _row(gl, r, "Falloff Start Opacity:", self.w_bgem_falloff_start_opacity, self._all_labels); r += 1
        self.w_bgem_falloff_stop_opacity = _spin(0.0, 0, 1);  _row(gl, r, "Falloff Stop Opacity:",  self.w_bgem_falloff_stop_opacity, self._all_labels); r += 1

        self.w_bgem_lighting_influence = _spin(1.0, 0, 1); _row(gl, r, "Lighting Influence:", self.w_bgem_lighting_influence, self._all_labels); r += 1
        self.w_bgem_envmap_min_lod = _int_spin(0, 0, 255); _row(gl, r, "Envmap Min LOD:", self.w_bgem_envmap_min_lod, self._all_labels); r += 1
        self.w_bgem_soft_depth = _spin(100.0, 0, 10000); _row(gl, r, "Soft Depth:", self.w_bgem_soft_depth, self._all_labels); r += 1

        self.w_bgem_emittance_color = ColorButton(0xFFFFFF); _row(gl, r, "Emittance Color:", self.w_bgem_emittance_color, self._all_labels); r += 1
        self.w_bgem_glowmap = _check(False); _row(gl, r, "Glowmap:", self.w_bgem_glowmap, self._all_labels); r += 1
        self.w_bgem_effect_pbr = _check(False); _row(gl, r, "Effect PBR Specular:", self.w_bgem_effect_pbr, self._all_labels); r += 1

        gl.setRowStretch(r, 1)

        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(inner)
        return sa

    def load_bgem(self, em: BGEM):
        self._bgem = em
        self._is_bgem = True
        # General tab (shared)
        self.w_version.setValue(em.version)
        self.w_tile_u.setChecked(em.tile_u)
        self.w_tile_v.setChecked(em.tile_v)
        self.w_u_offset.setValue(em.u_offset)
        self.w_v_offset.setValue(em.v_offset)
        self.w_u_scale.setValue(em.u_scale)
        self.w_v_scale.setValue(em.v_scale)
        self.w_alpha.setValue(em.alpha)
        idx = ALPHA_BLEND_MODES.index(em.alpha_blend_mode) if em.alpha_blend_mode in ALPHA_BLEND_MODES else 0
        self.w_alpha_blend.setCurrentIndex(idx)
        self.w_alpha_test_ref.setValue(em.alpha_test_ref)
        self.w_alpha_test.setChecked(em.alpha_test)
        self.w_zbuf_write.setChecked(em.z_buffer_write)
        self.w_zbuf_test.setChecked(em.z_buffer_test)
        self.w_ssr.setChecked(em.screen_space_reflections)
        self.w_wet_ssr.setChecked(em.wetness_control_ssr)
        self.w_decal.setChecked(em.decal)
        self.w_two_sided.setChecked(em.two_sided)
        self.w_decal_no_fade.setChecked(em.decal_no_fade)
        self.w_non_occluder.setChecked(em.non_occluder)
        self.w_refraction.setChecked(em.refraction)
        self.w_refraction_falloff.setChecked(em.refraction_falloff)
        self.w_refraction_power.setValue(em.refraction_power)
        self.w_env_mapping.setChecked(em.environment_mapping)
        self.w_env_mask_scale.setValue(em.environment_mapping_mask_scale)
        self.w_grayscale_palette.setChecked(em.grayscale_to_palette_color)

        # BGEM Material tab
        self.w_bgem_base.setText(em.base_texture)
        self.w_bgem_grayscale.setText(em.grayscale_texture)
        self.w_bgem_envmap.setText(em.envmap_texture)
        self.w_bgem_normal.setText(em.normal_texture)
        self.w_bgem_envmap_mask.setText(em.envmap_mask_texture)
        self.w_bgem_specular.setText(em.specular_texture)
        self.w_bgem_lighting.setText(em.lighting_texture)
        self.w_bgem_glow.setText(em.glow_texture)

        self.w_bgem_blood.setChecked(em.blood_enabled)
        self.w_bgem_effect_lighting.setChecked(em.effect_lighting_enabled)
        self.w_bgem_falloff.setChecked(em.falloff_enabled)
        self.w_bgem_falloff_color.setChecked(em.falloff_color_enabled)
        self.w_bgem_gs_palette_alpha.setChecked(em.grayscale_to_palette_alpha)
        self.w_bgem_soft.setChecked(em.soft_enabled)

        self.w_bgem_base_color.set_color(em.base_color)
        self.w_bgem_base_color_scale.setValue(em.base_color_scale)
        self.w_bgem_falloff_start_angle.setValue(em.falloff_start_angle)
        self.w_bgem_falloff_stop_angle.setValue(em.falloff_stop_angle)
        self.w_bgem_falloff_start_opacity.setValue(em.falloff_start_opacity)
        self.w_bgem_falloff_stop_opacity.setValue(em.falloff_stop_opacity)
        self.w_bgem_lighting_influence.setValue(em.lighting_influence)
        self.w_bgem_envmap_min_lod.setValue(em.envmap_min_lod)
        self.w_bgem_soft_depth.setValue(em.soft_depth)
        self.w_bgem_emittance_color.set_color(em.emittance_color)
        self.w_bgem_glowmap.setChecked(em.glowmap)
        self.w_bgem_effect_pbr.setChecked(em.effect_pbr_specular)

        # GUIの仕様（小数の丸め等）に合わせた正規化済みの状態を基準データ（保存済み）として格納する
        self._bgem = self.collect_bgem()

    def collect_bgem(self) -> BGEM:
        import copy
        em = copy.deepcopy(self._bgem) if self._bgem else BGEM()
        if self._bgem and hasattr(self._bgem, '_raw_path'):
            em._raw_path = self._bgem._raw_path
        # General
        em.version = self.w_version.value()
        em.tile_u = self.w_tile_u.isChecked()
        em.tile_v = self.w_tile_v.isChecked()
        em.u_offset = self.w_u_offset.value()
        em.v_offset = self.w_v_offset.value()
        em.u_scale = self.w_u_scale.value()
        em.v_scale = self.w_v_scale.value()
        em.alpha = self.w_alpha.value()
        em.alpha_blend_mode = ALPHA_BLEND_MODES[self.w_alpha_blend.currentIndex()]
        em.alpha_test_ref = self.w_alpha_test_ref.value()
        em.alpha_test = self.w_alpha_test.isChecked()
        em.z_buffer_write = self.w_zbuf_write.isChecked()
        em.z_buffer_test = self.w_zbuf_test.isChecked()
        em.screen_space_reflections = self.w_ssr.isChecked()
        em.wetness_control_ssr = self.w_wet_ssr.isChecked()
        em.decal = self.w_decal.isChecked()
        em.two_sided = self.w_two_sided.isChecked()
        em.decal_no_fade = self.w_decal_no_fade.isChecked()
        em.non_occluder = self.w_non_occluder.isChecked()
        em.refraction = self.w_refraction.isChecked()
        em.refraction_falloff = self.w_refraction_falloff.isChecked()
        em.refraction_power = self.w_refraction_power.value()
        em.environment_mapping = self.w_env_mapping.isChecked()
        em.environment_mapping_mask_scale = self.w_env_mask_scale.value()
        em.grayscale_to_palette_color = self.w_grayscale_palette.isChecked()
        # BGEM Material
        em.base_texture = self.w_bgem_base.text()
        em.grayscale_texture = self.w_bgem_grayscale.text()
        em.envmap_texture = self.w_bgem_envmap.text()
        em.normal_texture = self.w_bgem_normal.text()
        em.envmap_mask_texture = self.w_bgem_envmap_mask.text()
        em.specular_texture = self.w_bgem_specular.text()
        em.lighting_texture = self.w_bgem_lighting.text()
        em.glow_texture = self.w_bgem_glow.text()
        em.blood_enabled = self.w_bgem_blood.isChecked()
        em.effect_lighting_enabled = self.w_bgem_effect_lighting.isChecked()
        em.falloff_enabled = self.w_bgem_falloff.isChecked()
        em.falloff_color_enabled = self.w_bgem_falloff_color.isChecked()
        em.grayscale_to_palette_alpha = self.w_bgem_gs_palette_alpha.isChecked()
        em.soft_enabled = self.w_bgem_soft.isChecked()
        em.base_color = self.w_bgem_base_color.get_color()
        em.base_color_scale = self.w_bgem_base_color_scale.value()
        em.falloff_start_angle = self.w_bgem_falloff_start_angle.value()
        em.falloff_stop_angle = self.w_bgem_falloff_stop_angle.value()
        em.falloff_start_opacity = self.w_bgem_falloff_start_opacity.value()
        em.falloff_stop_opacity = self.w_bgem_falloff_stop_opacity.value()
        em.lighting_influence = self.w_bgem_lighting_influence.value()
        em.envmap_min_lod = self.w_bgem_envmap_min_lod.value()
        em.soft_depth = self.w_bgem_soft_depth.value()
        em.emittance_color = self.w_bgem_emittance_color.get_color()
        em.glowmap = self.w_bgem_glowmap.isChecked()
        em.effect_pbr_specular = self.w_bgem_effect_pbr.isChecked()
        return em

    # ── ファイル操作 ──────────────────────────────────────────────────────────
    def has_unsaved_changes(self) -> bool:
        try:
            if self._is_bgem:
                if not self._bgem: return False
                return self.collect_bgem() != self._bgem
            else:
                if not self._bgsm: return False
                return self.collect_bgsm() != self._bgsm
        except Exception:
            return True

    def confirm_discard_changes(self) -> bool:
        """未保存の変更がある場合、ユーザーに破棄してよいか尋ねる。
        戻り値が True なら続行、False ならキャンセル。"""
        if not self.has_unsaved_changes():
            return True
        from PyQt6.QtWidgets import QMessageBox
        ans = QMessageBox.warning(
            self,
            tr("Unsaved Changes", AppConfig.lang),
            tr("There are unsaved changes. Do you want to save them?", AppConfig.lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.save_file()
            return not self.has_unsaved_changes()
        elif ans == QMessageBox.StandardButton.Cancel:
            return False
        return True

    def new_file(self):
        if not self.confirm_discard_changes(): return
        self._is_bgem = False
        self._bgsm = BGSM()
        self._bgsm._raw_path = ""
        self._bgem = None
        self.combo_mode.blockSignals(True)
        self.combo_mode.setCurrentIndex(0)
        self.combo_mode.blockSignals(False)
        self._switch_material_tab(is_bgem=False)
        self.load_bgsm(self._bgsm)
        self.lbl_path.setText(tr("Unsaved File", AppConfig.lang))
        self.lbl_path.setStyleSheet("color: #aaa;")

    def close_file(self):
        if not self.confirm_discard_changes(): return
        self._is_bgem = False
        self._bgsm = None
        self._bgem = None
        self.combo_mode.blockSignals(True)
        self.combo_mode.setCurrentIndex(0)
        self.combo_mode.blockSignals(False)
        self._switch_material_tab(is_bgem=False)
        self.load_bgsm(BGSM())  # 初期状態リセット
        self.lbl_path.setText(tr("Please open a file", AppConfig.lang))
        self.lbl_path.setStyleSheet("color: #aaa;")

    def open_file(self):
        if not self.confirm_discard_changes(): return
        path, _ = QFileDialog.getOpenFileName(self, "マテリアルを開く", "", "Material (*.bgsm *.bgem);;All (*)")
        if path:
            self.open_by_path(path)
            
    def open_by_path(self, path: str):
        if not self.confirm_discard_changes(): return
        try:
            mat = read_material(path)
            if isinstance(mat, BGEM):
                self._is_bgem = True
                self._bgem = mat
                self._bgsm = None
                self.combo_mode.blockSignals(True)
                self.combo_mode.setCurrentIndex(1)  # BGEM
                self.combo_mode.blockSignals(False)
                self._switch_material_tab(is_bgem=True)
                self.load_bgem(mat)
            else:
                self._is_bgem = False
                self._bgsm = mat
                self._bgem = None
                self.combo_mode.blockSignals(True)
                self.combo_mode.setCurrentIndex(0)  # BGSM
                self.combo_mode.blockSignals(False)
                self._switch_material_tab(is_bgem=False)
                self.load_bgsm(mat)
            self.lbl_path.setText(path)
            self.lbl_path.setStyleSheet("color: #eee;")
            self.file_opened.emit(path)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "エラー", f"読み込み失敗:\n{e}")

    def _switch_material_tab(self, is_bgem: bool):
        """Material タブを BGSM 用と BGEM 用で切り替える"""
        if self.tab.count() > 1:
            self.tab.removeTab(1)
        if is_bgem:
            self.tab.addTab(self._bgem_material_tab, "Effect Material")
        else:
            self.tab.addTab(self._bgsm_material_tab, "Material")
        self.tab.setCurrentIndex(1)

    def save_file(self):
        if self._is_bgem:
            if self._bgem is None:
                self.save_as(); return
            path = getattr(self._bgem, '_raw_path', None)
            if not path:
                self.save_as(); return
            try:
                mat = self.collect_bgem()
                mat.write(path)
                mat._raw_path = path
                self._bgem = mat
                self.file_saved.emit(path)
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "エラー", f"保存失敗:\n{e}")
        else:
            if self._bgsm is None:
                self.save_as(); return
            path = getattr(self._bgsm, '_raw_path', None)
            if not path:
                self.save_as(); return
            try:
                mat = self.collect_bgsm()
                mat.write(path)
                mat._raw_path = path
                self._bgsm = mat
                self.file_saved.emit(path)
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "エラー", f"保存失敗:\n{e}")

    def save_as(self):
        if self._is_bgem:
            ext_filter = "BGEM (*.bgem)"
        else:
            ext_filter = "BGSM (*.bgsm)"
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(self, "名前を付けて保存", "", ext_filter)
        if path:
            try:
                if self._is_bgem:
                    mat = self.collect_bgem()
                    mat.write(path)
                    mat._raw_path = path
                    self._bgem = mat
                else:
                    mat = self.collect_bgsm()
                    mat.write(path)
                    mat._raw_path = path
                    self._bgsm = mat
                self.lbl_path.setText(path)
                self.file_saved.emit(path)
            except Exception as e:
                QMessageBox.critical(self, tr("Error", AppConfig.lang), f"{tr('Failed to save', AppConfig.lang)}:\n{e}")

    # ── 翻訳・ツールチップ対応 ──────────────────────────────────────────────────
    def retranslate(self, lang: str):
        if self._bgsm is None and self._bgem is None:
            self.lbl_path.setText(tr("Please open a file", lang))

        # すべてのラベルを翻訳
        for lbl, w in getattr(self, "_all_labels", []):
            orig = lbl.property("orig_text")
            if orig:
                lbl.setText(f"{tr(orig, lang)}:")

    def set_tooltips_enabled(self, show: bool):
        for lbl, w in getattr(self, "_all_labels", []):
            tip = lbl.property("orig_tip")
            if tip:
                val = tip if show else ""
                lbl.setToolTip(val)
                w.setToolTip(val)

    # ── ドラッグ＆ドロップ ──────────────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                f = urls[0].toLocalFile().lower()
                if f.endswith(".bgsm") or f.endswith(".bgem"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            f = path.lower()
            if f.endswith(".bgsm") or f.endswith(".bgem"):
                self.open_by_path(path)
                event.acceptProposedAction()
