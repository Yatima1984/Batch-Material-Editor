import struct
import json
import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


BGSM_SIGNATURE = 0x4D534742  # "BGSM"

# AlphaBlendMode 変換テーブル (a, b, c) → 名前
_ALPHA_BLEND_TABLE = [
    (0, 6, 7, "Unknown"),
    (0, 0, 0, "None"),
    (1, 6, 7, "Standard"),
    (1, 6, 0, "Additive"),
    (1, 4, 1, "Multiplicative"),
]
ALPHA_BLEND_MODES = [row[3] for row in _ALPHA_BLEND_TABLE]


def _decode_alpha_blend(a: int, b: int, c: int) -> str:
    for ra, rb, rc, name in _ALPHA_BLEND_TABLE:
        if a == ra and b == rb and c == rc:
            return name
    return "Unknown"


def _encode_alpha_blend(mode: str):
    for ra, rb, rc, name in _ALPHA_BLEND_TABLE:
        if name == mode:
            return ra, rb, rc
    return 0, 6, 7  # Unknown


def _color_float_to_uint(r: float, g: float, b: float) -> int:
    # 1.0 超 (HDR) や負値は 0〜255 に丸める（& 0xFF だと桁あふれして別の色になる）
    ri = min(max(int(r * 255), 0), 255)
    gi = min(max(int(g * 255), 0), 255)
    bi = min(max(int(b * 255), 0), 255)
    return (ri << 16) | (gi << 8) | bi


def _color_uint_to_float(v: int):
    r = ((v >> 16) & 0xFF) / 255.0
    g = ((v >> 8) & 0xFF) / 255.0
    b = (v & 0xFF) / 255.0
    return r, g, b


def _color_uint_to_hex(v: int) -> str:
    return "#{:06x}".format(v & 0xFFFFFF)


def _color_hex_to_uint(s: str) -> int:
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = s[0]*2 + s[1]*2 + s[2]*2
    return int(s, 16) & 0xFFFFFF


# ---- 読み書きで値を失わないためのヘルパー ----
# 色は UI 上 24bit RGB で扱うため、読み込んだ元の浮動小数値を保持しておき、
# 値が変更されていなければ元の値 (HDR や 8bit に収まらない精度を含む) をそのまま書き戻す。
def _read_color_field(obj, r: "_Reader", attr: str):
    rgb = r.read_color()
    setattr(obj, attr, _color_float_to_uint(*rgb))
    obj._raw_colors[attr] = rgb


def _write_color_field(obj, w: "_Writer", attr: str):
    v = getattr(obj, attr)
    raw = obj._raw_colors.get(attr)
    if raw is not None and _color_float_to_uint(*raw) == v:
        w.write_color(*raw)
    else:
        w.write_color(*_color_uint_to_float(v))


# 未知の組み合わせ ("Unknown") でも元の 3 値をそのまま書き戻す
def _read_alpha_blend(obj, r: "_Reader"):
    raw = (r.read_byte(), r.read_uint32(), r.read_uint32())
    obj.alpha_blend_mode = _decode_alpha_blend(*raw)
    obj._raw_alpha_blend = raw


def _write_alpha_blend(obj, w: "_Writer"):
    raw = obj._raw_alpha_blend
    if raw is not None and _decode_alpha_blend(*raw) == obj.alpha_blend_mode:
        a0, a1, a2 = raw
    else:
        a0, a1, a2 = _encode_alpha_blend(obj.alpha_blend_mode)
    w.write_byte(a0)
    w.write_uint32(a1)
    w.write_uint32(a2)


class _Reader:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read_uint32(self) -> int:
        v, = struct.unpack_from("<I", self._data, self._pos)
        self._pos += 4
        return v

    def read_float(self) -> float:
        v, = struct.unpack_from("<f", self._data, self._pos)
        self._pos += 4
        return v

    def read_byte(self) -> int:
        v = self._data[self._pos]
        self._pos += 1
        return v

    def read_bool(self) -> bool:
        return self.read_byte() != 0

    def read_string(self) -> str:
        length = self.read_uint32()
        raw = self._data[self._pos:self._pos + length]
        self._pos += length
        s = raw.decode("utf-8", errors="replace")
        return s.rstrip("\x00")

    def read_color(self):
        r = self.read_float()
        g = self.read_float()
        b = self.read_float()
        return r, g, b


class _Writer:
    def __init__(self):
        self._buf = bytearray()

    def write_uint32(self, v: int):
        self._buf += struct.pack("<I", v & 0xFFFFFFFF)

    def write_float(self, v: float):
        self._buf += struct.pack("<f", v)

    def write_byte(self, v: int):
        self._buf += struct.pack("B", v & 0xFF)

    def write_bool(self, v: bool):
        self.write_byte(1 if v else 0)

    def write_string(self, s: Optional[str]):
        if s is None:
            s = ""
        encoded = (s + "\x00").encode("utf-8")
        self.write_uint32(len(encoded))
        self._buf += encoded

    def write_color(self, r: float, g: float, b: float):
        self.write_float(r)
        self.write_float(g)
        self.write_float(b)

    def getvalue(self) -> bytes:
        return bytes(self._buf)


@dataclass
class BGSM:
    """Fallout 4 BGSMマテリアルファイル (FO4 v1/v2)"""

    # ---- BaseMaterialFile ----
    version: int = 2
    tile_u: bool = True
    tile_v: bool = True
    u_offset: float = 0.0
    v_offset: float = 0.0
    u_scale: float = 1.0
    v_scale: float = 1.0
    alpha: float = 1.0
    alpha_blend_mode: str = "None"
    alpha_test_ref: int = 128
    alpha_test: bool = False
    z_buffer_write: bool = True
    z_buffer_test: bool = True
    screen_space_reflections: bool = False
    wetness_control_ssr: bool = False
    decal: bool = False
    two_sided: bool = False
    decal_no_fade: bool = False
    non_occluder: bool = False
    refraction: bool = False
    refraction_falloff: bool = False
    refraction_power: float = 0.0
    environment_mapping: bool = False          # v<10
    environment_mapping_mask_scale: float = 1.0  # v<10
    depth_bias: bool = False                   # v>=10 (FO76のみ)
    grayscale_to_palette_color: bool = False
    mask_writes: int = 0b00111111  # ALBEDO|NORMAL|SPECULAR|AO|EMISSIVE|GLOSS

    # ---- BGSM 固有 ----
    diffuse_texture: str = ""
    normal_texture: str = ""
    smooth_spec_texture: str = ""
    greyscale_texture: str = ""
    # v<=2 専用
    envmap_texture: str = ""
    glow_texture: str = ""
    inner_layer_texture: str = ""
    wrinkles_texture: str = ""
    displacement_texture: str = ""
    # v>2 専用 (FO76)
    specular_texture: str = ""
    lighting_texture: str = ""
    flow_texture: str = ""
    distance_field_alpha_texture: str = ""  # v>=17

    enable_editor_alpha_ref: bool = False

    # v>=8
    translucency: bool = False
    translucency_thick_object: bool = False
    translucency_mix_albedo_with_subsurface_color: bool = False
    translucency_subsurface_color: int = 0x000000
    translucency_transmissive_scale: float = 0.0
    translucency_turbulence: float = 0.0

    # v<8
    rim_lighting: bool = False
    rim_power: float = 2.0
    back_light_power: float = 0.0
    subsurface_lighting: bool = False
    subsurface_lighting_rolloff: float = 0.3

    specular_enabled: bool = False
    specular_color: int = 0xFFFFFF   # 24bit RGB
    specular_mult: float = 1.0
    smoothness: float = 1.0
    fresnel_power: float = 5.0
    wetness_control_spec_scale: float = -1.0
    wetness_control_spec_power_scale: float = -1.0
    wetness_control_spec_minvar: float = -1.0
    wetness_control_env_map_scale: float = -1.0  # v<10
    wetness_control_fresnel_power: float = -1.0
    wetness_control_metalness: float = -1.0

    # v>2
    pbr: bool = False
    custom_porosity: bool = False   # v>=9
    porosity_value: float = 0.0     # v>=9

    root_material_path: str = ""
    aniso_lighting: bool = False
    emit_enabled: bool = False
    emittance_color: int = 0xFFFFFF  # 24bit RGB (EmitEnabled=True のときのみ読み書き)
    emittance_mult: float = 1.0
    model_space_normals: bool = False
    external_emittance: bool = False
    lum_emittance: float = 0.0        # v>=12
    # v>=13
    use_adaptive_emissive: bool = False
    adaptive_emissive_exposure_offset: float = 0.0
    adaptive_emissive_final_exposure_min: float = 0.0
    adaptive_emissive_final_exposure_max: float = 0.0
    back_lighting: bool = False       # v<8
    receive_shadows: bool = False
    hide_secret: bool = False
    cast_shadows: bool = False
    dissolve_fade: bool = False
    assume_shadowmask: bool = False
    glowmap: bool = False
    environment_mapping_window: bool = False  # v<7
    environment_mapping_eye: bool = False     # v<7
    hair: bool = False
    hair_tint_color: int = 0x808080  # 24bit RGB
    tree: bool = False
    facegen: bool = False
    skin_tint: bool = False
    tessellate: bool = False
    # v<3
    displacement_texture_bias: float = -0.5
    displacement_texture_scale: float = 10.0
    tessellation_pn_scale: float = 1.0
    tessellation_base_factor: float = 1.0
    tessellation_fade_distance: float = 0.0
    grayscale_to_palette_scale: float = 1.0
    skew_specular_alpha: bool = False  # v>=1
    # v>=3
    terrain: bool = False
    terrain_threshold_falloff: float = 0.0
    terrain_tiling_distance: float = 0.0
    terrain_rotation_angle: float = 0.0

    # ---- 内部 ----
    _raw_path: str = field(default="", repr=False)
    _raw_colors: dict = field(default_factory=dict, repr=False, compare=False)
    _raw_alpha_blend: Optional[tuple] = field(default=None, repr=False, compare=False)

    # ===== 読み込み =====
    @classmethod
    def read(cls, path: str) -> "BGSM":
        with open(path, "rb") as f:
            data = f.read()
        obj = cls()
        obj._raw_path = path
        r = _Reader(data)
        obj._deserialize(r)
        return obj

    def _deserialize(self, r: _Reader):
        sig = r.read_uint32()
        if sig != BGSM_SIGNATURE:
            raise ValueError(f"無効なシグネチャ: 0x{sig:08X} (期待値: 0x{BGSM_SIGNATURE:08X})")

        self.version = r.read_uint32()

        tile_flags = r.read_uint32()
        self.tile_u = bool(tile_flags & 2)
        self.tile_v = bool(tile_flags & 1)
        self.u_offset = r.read_float()
        self.v_offset = r.read_float()
        self.u_scale = r.read_float()
        self.v_scale = r.read_float()

        self.alpha = r.read_float()
        _read_alpha_blend(self, r)
        self.alpha_test_ref = r.read_byte()
        self.alpha_test = r.read_bool()

        self.z_buffer_write = r.read_bool()
        self.z_buffer_test = r.read_bool()
        self.screen_space_reflections = r.read_bool()
        self.wetness_control_ssr = r.read_bool()
        self.decal = r.read_bool()
        self.two_sided = r.read_bool()
        self.decal_no_fade = r.read_bool()
        self.non_occluder = r.read_bool()

        self.refraction = r.read_bool()
        self.refraction_falloff = r.read_bool()
        self.refraction_power = r.read_float()

        if self.version < 10:
            self.environment_mapping = r.read_bool()
            self.environment_mapping_mask_scale = r.read_float()
        else:
            self.depth_bias = r.read_bool()

        self.grayscale_to_palette_color = r.read_bool()

        if self.version >= 6:
            self.mask_writes = r.read_byte()

        # ---- BGSM 固有 ----
        self.diffuse_texture = r.read_string()
        self.normal_texture = r.read_string()
        self.smooth_spec_texture = r.read_string()
        self.greyscale_texture = r.read_string()

        if self.version > 2:
            self.glow_texture = r.read_string()
            self.wrinkles_texture = r.read_string()
            # v>2 専用テクスチャ (FO76用)
            self.specular_texture = r.read_string()
            self.lighting_texture = r.read_string()
            self.flow_texture = r.read_string()
            if self.version >= 17:
                self.distance_field_alpha_texture = r.read_string()
        else:
            self.envmap_texture = r.read_string()
            self.glow_texture = r.read_string()
            self.inner_layer_texture = r.read_string()
            self.wrinkles_texture = r.read_string()
            self.displacement_texture = r.read_string()

        self.enable_editor_alpha_ref = r.read_bool()

        if self.version >= 8:
            self.translucency = r.read_bool()
            self.translucency_thick_object = r.read_bool()
            self.translucency_mix_albedo_with_subsurface_color = r.read_bool()
            _read_color_field(self, r, "translucency_subsurface_color")
            self.translucency_transmissive_scale = r.read_float()
            self.translucency_turbulence = r.read_float()
        else:
            self.rim_lighting = r.read_bool()
            self.rim_power = r.read_float()
            self.back_light_power = r.read_float()
            self.subsurface_lighting = r.read_bool()
            self.subsurface_lighting_rolloff = r.read_float()

        self.specular_enabled = r.read_bool()
        _read_color_field(self, r, "specular_color")
        self.specular_mult = r.read_float()
        self.smoothness = r.read_float()

        self.fresnel_power = r.read_float()
        self.wetness_control_spec_scale = r.read_float()
        self.wetness_control_spec_power_scale = r.read_float()
        self.wetness_control_spec_minvar = r.read_float()

        if self.version < 10:
            self.wetness_control_env_map_scale = r.read_float()

        self.wetness_control_fresnel_power = r.read_float()
        self.wetness_control_metalness = r.read_float()

        if self.version > 2:
            self.pbr = r.read_bool()
            if self.version >= 9:
                self.custom_porosity = r.read_bool()
                self.porosity_value = r.read_float()

        self.root_material_path = r.read_string()
        self.aniso_lighting = r.read_bool()
        self.emit_enabled = r.read_bool()

        if self.emit_enabled:
            _read_color_field(self, r, "emittance_color")

        self.emittance_mult = r.read_float()
        self.model_space_normals = r.read_bool()
        self.external_emittance = r.read_bool()

        if self.version >= 12:
            self.lum_emittance = r.read_float()

        if self.version >= 13:
            self.use_adaptive_emissive = r.read_bool()
            self.adaptive_emissive_exposure_offset = r.read_float()
            self.adaptive_emissive_final_exposure_min = r.read_float()
            self.adaptive_emissive_final_exposure_max = r.read_float()

        if self.version < 8:
            self.back_lighting = r.read_bool()

        self.receive_shadows = r.read_bool()
        self.hide_secret = r.read_bool()
        self.cast_shadows = r.read_bool()
        self.dissolve_fade = r.read_bool()
        self.assume_shadowmask = r.read_bool()

        self.glowmap = r.read_bool()

        if self.version < 7:
            self.environment_mapping_window = r.read_bool()
            self.environment_mapping_eye = r.read_bool()

        self.hair = r.read_bool()
        _read_color_field(self, r, "hair_tint_color")

        self.tree = r.read_bool()
        self.facegen = r.read_bool()
        self.skin_tint = r.read_bool()
        self.tessellate = r.read_bool()

        if self.version < 3:
            self.displacement_texture_bias = r.read_float()
            self.displacement_texture_scale = r.read_float()
            self.tessellation_pn_scale = r.read_float()
            self.tessellation_base_factor = r.read_float()
            self.tessellation_fade_distance = r.read_float()

        self.grayscale_to_palette_scale = r.read_float()

        if self.version >= 1:
            self.skew_specular_alpha = r.read_bool()

        if self.version >= 3:
            self.terrain = r.read_bool()
            if self.terrain:
                self.terrain_threshold_falloff = r.read_float()
                self.terrain_tiling_distance = r.read_float()
                self.terrain_rotation_angle = r.read_float()

    # ===== 書き込み =====
    def write(self, path: str):
        w = _Writer()
        self._serialize(w)
        with open(path, "wb") as f:
            f.write(w.getvalue())

    def _serialize(self, w: _Writer):
        w.write_uint32(BGSM_SIGNATURE)
        w.write_uint32(self.version)

        tile_flags = 0
        if self.tile_u:
            tile_flags |= 2
        if self.tile_v:
            tile_flags |= 1
        w.write_uint32(tile_flags)

        w.write_float(self.u_offset)
        w.write_float(self.v_offset)
        w.write_float(self.u_scale)
        w.write_float(self.v_scale)

        w.write_float(self.alpha)
        _write_alpha_blend(self, w)
        w.write_byte(self.alpha_test_ref)
        w.write_bool(self.alpha_test)

        w.write_bool(self.z_buffer_write)
        w.write_bool(self.z_buffer_test)
        w.write_bool(self.screen_space_reflections)
        w.write_bool(self.wetness_control_ssr)
        w.write_bool(self.decal)
        w.write_bool(self.two_sided)
        w.write_bool(self.decal_no_fade)
        w.write_bool(self.non_occluder)

        w.write_bool(self.refraction)
        w.write_bool(self.refraction_falloff)
        w.write_float(self.refraction_power)

        if self.version < 10:
            w.write_bool(self.environment_mapping)
            w.write_float(self.environment_mapping_mask_scale)
        else:
            w.write_bool(self.depth_bias)

        w.write_bool(self.grayscale_to_palette_color)

        if self.version >= 6:
            w.write_byte(self.mask_writes)

        # ---- BGSM 固有 ----
        w.write_string(self.diffuse_texture)
        w.write_string(self.normal_texture)
        w.write_string(self.smooth_spec_texture)
        w.write_string(self.greyscale_texture)

        if self.version > 2:
            w.write_string(self.glow_texture)
            w.write_string(self.wrinkles_texture)
            w.write_string(self.specular_texture)
            w.write_string(self.lighting_texture)
            w.write_string(self.flow_texture)
            if self.version >= 17:
                w.write_string(self.distance_field_alpha_texture)
        else:
            w.write_string(self.envmap_texture)
            w.write_string(self.glow_texture)
            w.write_string(self.inner_layer_texture)
            w.write_string(self.wrinkles_texture)
            w.write_string(self.displacement_texture)

        w.write_bool(self.enable_editor_alpha_ref)

        if self.version >= 8:
            w.write_bool(self.translucency)
            w.write_bool(self.translucency_thick_object)
            w.write_bool(self.translucency_mix_albedo_with_subsurface_color)
            _write_color_field(self, w, "translucency_subsurface_color")
            w.write_float(self.translucency_transmissive_scale)
            w.write_float(self.translucency_turbulence)
        else:
            w.write_bool(self.rim_lighting)
            w.write_float(self.rim_power)
            w.write_float(self.back_light_power)
            w.write_bool(self.subsurface_lighting)
            w.write_float(self.subsurface_lighting_rolloff)

        w.write_bool(self.specular_enabled)
        _write_color_field(self, w, "specular_color")
        w.write_float(self.specular_mult)
        w.write_float(self.smoothness)

        w.write_float(self.fresnel_power)
        w.write_float(self.wetness_control_spec_scale)
        w.write_float(self.wetness_control_spec_power_scale)
        w.write_float(self.wetness_control_spec_minvar)

        if self.version < 10:
            w.write_float(self.wetness_control_env_map_scale)

        w.write_float(self.wetness_control_fresnel_power)
        w.write_float(self.wetness_control_metalness)

        if self.version > 2:
            w.write_bool(self.pbr)
            if self.version >= 9:
                w.write_bool(self.custom_porosity)
                w.write_float(self.porosity_value)

        w.write_string(self.root_material_path)
        w.write_bool(self.aniso_lighting)
        w.write_bool(self.emit_enabled)

        if self.emit_enabled:
            _write_color_field(self, w, "emittance_color")

        w.write_float(self.emittance_mult)
        w.write_bool(self.model_space_normals)
        w.write_bool(self.external_emittance)

        if self.version >= 12:
            w.write_float(self.lum_emittance)

        if self.version >= 13:
            w.write_bool(self.use_adaptive_emissive)
            w.write_float(self.adaptive_emissive_exposure_offset)
            w.write_float(self.adaptive_emissive_final_exposure_min)
            w.write_float(self.adaptive_emissive_final_exposure_max)

        if self.version < 8:
            w.write_bool(self.back_lighting)

        w.write_bool(self.receive_shadows)
        w.write_bool(self.hide_secret)
        w.write_bool(self.cast_shadows)
        w.write_bool(self.dissolve_fade)
        w.write_bool(self.assume_shadowmask)

        w.write_bool(self.glowmap)

        if self.version < 7:
            w.write_bool(self.environment_mapping_window)
            w.write_bool(self.environment_mapping_eye)

        w.write_bool(self.hair)
        _write_color_field(self, w, "hair_tint_color")

        w.write_bool(self.tree)
        w.write_bool(self.facegen)
        w.write_bool(self.skin_tint)
        w.write_bool(self.tessellate)

        if self.version < 3:
            w.write_float(self.displacement_texture_bias)
            w.write_float(self.displacement_texture_scale)
            w.write_float(self.tessellation_pn_scale)
            w.write_float(self.tessellation_base_factor)
            w.write_float(self.tessellation_fade_distance)

        w.write_float(self.grayscale_to_palette_scale)

        if self.version >= 1:
            w.write_bool(self.skew_specular_alpha)

        if self.version >= 3:
            w.write_bool(self.terrain)
            if self.terrain:
                w.write_float(self.terrain_threshold_falloff)
                w.write_float(self.terrain_tiling_distance)
                w.write_float(self.terrain_rotation_angle)

    # ===== JSON プリセット =====
    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            # プリセットにはテクスチャ情報は含めない
            if k.endswith("_texture"):
                continue
            d[k] = v
        return d

    def save_preset(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_preset(cls, path: str) -> "BGSM":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        obj = cls()
        for k, v in d.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        return obj

    # ===== ユーティリティ =====
    @staticmethod
    def extract_game_path(abs_path: str) -> str:
        """
        絶対パスから Textures フォルダ以降を抽出する。
        例: C:\\...\\Textures\\Alluring\\Test.dds → Textures\\Alluring\\Test.dds
        大文字小文字を区別しない。
        見つからない場合はファイル名のみ返す。
        """
        p = Path(abs_path)
        parts = p.parts
        for i, part in enumerate(parts):
            if part.lower() == "textures":
                return str(Path(*parts[i:]))
        return p.name


# =====================================================================
# BGEM — Effect Material
# =====================================================================

BGEM_SIGNATURE = 0x4D454742  # "BGEM"


@dataclass
class BGEM:
    """Fallout 4 BGEMエフェクトマテリアルファイル"""

    # ---- BaseMaterialFile (BGSM と共通) ----
    version: int = 2
    tile_u: bool = True
    tile_v: bool = True
    u_offset: float = 0.0
    v_offset: float = 0.0
    u_scale: float = 1.0
    v_scale: float = 1.0
    alpha: float = 1.0
    alpha_blend_mode: str = "None"
    alpha_test_ref: int = 128
    alpha_test: bool = False
    z_buffer_write: bool = True
    z_buffer_test: bool = True
    screen_space_reflections: bool = False
    wetness_control_ssr: bool = False
    decal: bool = False
    two_sided: bool = False
    decal_no_fade: bool = False
    non_occluder: bool = False
    refraction: bool = False
    refraction_falloff: bool = False
    refraction_power: float = 0.0
    environment_mapping: bool = False
    environment_mapping_mask_scale: float = 1.0
    depth_bias: bool = False
    grayscale_to_palette_color: bool = False
    mask_writes: int = 0b00111111

    # ---- BGEM 固有 ----
    base_texture: str = ""
    grayscale_texture: str = ""
    envmap_texture: str = ""
    normal_texture: str = ""
    envmap_mask_texture: str = ""
    # v>=11
    specular_texture: str = ""
    lighting_texture: str = ""
    glow_texture: str = ""

    blood_enabled: bool = False
    effect_lighting_enabled: bool = False
    falloff_enabled: bool = False
    falloff_color_enabled: bool = False
    grayscale_to_palette_alpha: bool = False
    soft_enabled: bool = False

    base_color: int = 0xFFFFFF
    base_color_scale: float = 1.0

    falloff_start_angle: float = 1.0
    falloff_stop_angle: float = 1.0
    falloff_start_opacity: float = 0.0
    falloff_stop_opacity: float = 0.0

    lighting_influence: float = 1.0
    envmap_min_lod: int = 0
    soft_depth: float = 100.0

    # v>=11
    emittance_color: int = 0xFFFFFF

    # v>=15
    adaptive_emissive_exposure_offset: float = 0.0
    adaptive_emissive_final_exposure_min: float = 0.0
    adaptive_emissive_final_exposure_max: float = 0.0

    # v>=16
    glowmap: bool = False

    # v>=20
    effect_pbr_specular: bool = False

    # ---- 内部 ----
    _raw_path: str = field(default="", repr=False)
    _raw_colors: dict = field(default_factory=dict, repr=False, compare=False)
    _raw_alpha_blend: Optional[tuple] = field(default=None, repr=False, compare=False)

    # ===== 読み込み =====
    @classmethod
    def read(cls, path: str) -> "BGEM":
        with open(path, "rb") as f:
            data = f.read()
        obj = cls()
        obj._raw_path = path
        r = _Reader(data)
        obj._deserialize(r)
        return obj

    def _deserialize(self, r: _Reader):
        sig = r.read_uint32()
        if sig != BGEM_SIGNATURE:
            raise ValueError(f"無効なシグネチャ: 0x{sig:08X} (期待値: 0x{BGEM_SIGNATURE:08X})")

        self.version = r.read_uint32()

        # ---- BaseMaterialFile 共通部分 ----
        tile_flags = r.read_uint32()
        self.tile_u = bool(tile_flags & 2)
        self.tile_v = bool(tile_flags & 1)
        self.u_offset = r.read_float()
        self.v_offset = r.read_float()
        self.u_scale = r.read_float()
        self.v_scale = r.read_float()

        self.alpha = r.read_float()
        _read_alpha_blend(self, r)
        self.alpha_test_ref = r.read_byte()
        self.alpha_test = r.read_bool()

        self.z_buffer_write = r.read_bool()
        self.z_buffer_test = r.read_bool()
        self.screen_space_reflections = r.read_bool()
        self.wetness_control_ssr = r.read_bool()
        self.decal = r.read_bool()
        self.two_sided = r.read_bool()
        self.decal_no_fade = r.read_bool()
        self.non_occluder = r.read_bool()

        self.refraction = r.read_bool()
        self.refraction_falloff = r.read_bool()
        self.refraction_power = r.read_float()

        if self.version < 10:
            self.environment_mapping = r.read_bool()
            self.environment_mapping_mask_scale = r.read_float()
        else:
            self.depth_bias = r.read_bool()

        self.grayscale_to_palette_color = r.read_bool()

        if self.version >= 6:
            self.mask_writes = r.read_byte()

        # ---- BGEM 固有 ----
        self.base_texture = r.read_string()
        self.grayscale_texture = r.read_string()
        self.envmap_texture = r.read_string()
        self.normal_texture = r.read_string()
        self.envmap_mask_texture = r.read_string()

        if self.version >= 11:
            self.specular_texture = r.read_string()
            self.lighting_texture = r.read_string()
            self.glow_texture = r.read_string()

        if self.version >= 10:
            self.environment_mapping = r.read_bool()
            self.environment_mapping_mask_scale = r.read_float()

        self.blood_enabled = r.read_bool()
        self.effect_lighting_enabled = r.read_bool()
        self.falloff_enabled = r.read_bool()
        self.falloff_color_enabled = r.read_bool()
        self.grayscale_to_palette_alpha = r.read_bool()
        self.soft_enabled = r.read_bool()

        _read_color_field(self, r, "base_color")
        self.base_color_scale = r.read_float()

        self.falloff_start_angle = r.read_float()
        self.falloff_stop_angle = r.read_float()
        self.falloff_start_opacity = r.read_float()
        self.falloff_stop_opacity = r.read_float()

        self.lighting_influence = r.read_float()
        self.envmap_min_lod = r.read_byte()
        self.soft_depth = r.read_float()

        if self.version >= 11:
            _read_color_field(self, r, "emittance_color")

        if self.version >= 15:
            self.adaptive_emissive_exposure_offset = r.read_float()
            self.adaptive_emissive_final_exposure_min = r.read_float()
            self.adaptive_emissive_final_exposure_max = r.read_float()

        if self.version >= 16:
            self.glowmap = r.read_bool()

        if self.version >= 20:
            self.effect_pbr_specular = r.read_bool()

    # ===== 書き込み =====
    def write(self, path: str):
        w = _Writer()
        self._serialize(w)
        with open(path, "wb") as f:
            f.write(w.getvalue())

    def _serialize(self, w: _Writer):
        w.write_uint32(BGEM_SIGNATURE)
        w.write_uint32(self.version)

        tile_flags = 0
        if self.tile_u:
            tile_flags |= 2
        if self.tile_v:
            tile_flags |= 1
        w.write_uint32(tile_flags)

        w.write_float(self.u_offset)
        w.write_float(self.v_offset)
        w.write_float(self.u_scale)
        w.write_float(self.v_scale)

        w.write_float(self.alpha)
        _write_alpha_blend(self, w)
        w.write_byte(self.alpha_test_ref)
        w.write_bool(self.alpha_test)

        w.write_bool(self.z_buffer_write)
        w.write_bool(self.z_buffer_test)
        w.write_bool(self.screen_space_reflections)
        w.write_bool(self.wetness_control_ssr)
        w.write_bool(self.decal)
        w.write_bool(self.two_sided)
        w.write_bool(self.decal_no_fade)
        w.write_bool(self.non_occluder)

        w.write_bool(self.refraction)
        w.write_bool(self.refraction_falloff)
        w.write_float(self.refraction_power)

        if self.version < 10:
            w.write_bool(self.environment_mapping)
            w.write_float(self.environment_mapping_mask_scale)
        else:
            w.write_bool(self.depth_bias)

        w.write_bool(self.grayscale_to_palette_color)

        if self.version >= 6:
            w.write_byte(self.mask_writes)

        # ---- BGEM 固有 ----
        w.write_string(self.base_texture)
        w.write_string(self.grayscale_texture)
        w.write_string(self.envmap_texture)
        w.write_string(self.normal_texture)
        w.write_string(self.envmap_mask_texture)

        if self.version >= 11:
            w.write_string(self.specular_texture)
            w.write_string(self.lighting_texture)
            w.write_string(self.glow_texture)

        if self.version >= 10:
            w.write_bool(self.environment_mapping)
            w.write_float(self.environment_mapping_mask_scale)

        w.write_bool(self.blood_enabled)
        w.write_bool(self.effect_lighting_enabled)
        w.write_bool(self.falloff_enabled)
        w.write_bool(self.falloff_color_enabled)
        w.write_bool(self.grayscale_to_palette_alpha)
        w.write_bool(self.soft_enabled)

        _write_color_field(self, w, "base_color")
        w.write_float(self.base_color_scale)

        w.write_float(self.falloff_start_angle)
        w.write_float(self.falloff_stop_angle)
        w.write_float(self.falloff_start_opacity)
        w.write_float(self.falloff_stop_opacity)

        w.write_float(self.lighting_influence)
        w.write_byte(self.envmap_min_lod)
        w.write_float(self.soft_depth)

        if self.version >= 11:
            _write_color_field(self, w, "emittance_color")

        if self.version >= 15:
            w.write_float(self.adaptive_emissive_exposure_offset)
            w.write_float(self.adaptive_emissive_final_exposure_min)
            w.write_float(self.adaptive_emissive_final_exposure_max)

        if self.version >= 16:
            w.write_bool(self.glowmap)

        if self.version >= 20:
            w.write_bool(self.effect_pbr_specular)

    # ===== JSON プリセット =====
    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if k.endswith("_texture"):
                continue
            d[k] = v
        return d


# BGSM / BGEM 共通 (BaseMaterialFile) のフィールド
BASE_FIELDS = (
    "version", "tile_u", "tile_v", "u_offset", "v_offset", "u_scale", "v_scale",
    "alpha", "alpha_blend_mode", "alpha_test_ref", "alpha_test",
    "z_buffer_write", "z_buffer_test", "screen_space_reflections", "wetness_control_ssr",
    "decal", "two_sided", "decal_no_fade", "non_occluder",
    "refraction", "refraction_falloff", "refraction_power",
    "environment_mapping", "environment_mapping_mask_scale", "depth_bias",
    "grayscale_to_palette_color", "mask_writes",
)


def copy_base_fields(src, dst):
    """BGSM ⇔ BGEM の切り替え用に共通フィールドをコピーする"""
    for name in BASE_FIELDS:
        setattr(dst, name, getattr(src, name))
    dst._raw_alpha_blend = src._raw_alpha_blend


def read_material(path: str):
    """ファイル先頭のシグネチャを読んで BGSM/BGEM を自動判別して読み込む"""
    with open(path, "rb") as f:
        sig_bytes = f.read(4)
    if len(sig_bytes) < 4:
        raise ValueError("ファイルが短すぎます")
    sig, = struct.unpack("<I", sig_bytes)
    if sig == BGSM_SIGNATURE:
        return BGSM.read(path)
    elif sig == BGEM_SIGNATURE:
        return BGEM.read(path)
    else:
        raise ValueError(f"不明なシグネチャ: 0x{sig:08X}")

