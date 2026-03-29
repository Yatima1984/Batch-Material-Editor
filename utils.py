import os
import re
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> str:
    """内部リソース（画像など）の絶対パスを取得する。
    PyInstallerの一時フォルダ、または実行環境のカレントディレクトリ。
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # 開発時は実行ファイル(main.py)のあるディレクトリ基準
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)


def get_app_dir() -> str:
    """アプリケーションの実行ディレクトリ（書き込み可能）を取得する。
    EXEの場合はEXEのあるフォルダ、Python実行時はスクリプトのあるフォルダ。
    """
    if hasattr(sys, 'frozen'):
        return os.path.dirname(sys.executable)
    # 開発時はbgsm_toolフォルダ
    return os.path.dirname(os.path.abspath(__file__))



def extract_game_path(abs_path: str) -> str:
    """
    絶対パスから Textures フォルダ以降（Textures自体を含めない）を抽出する。
    例: C:\\...\\Textures\\Alluring\\Test.dds → Alluring\\Test.dds
    """
    p = Path(abs_path)
    parts = p.parts
    for i, part in enumerate(parts):
        if part.lower() == "textures":
            if i + 1 < len(parts):
                return str(Path(*parts[i+1:]))
            return part
    return p.name


def scan_bgsm(folder: str) -> list[str]:
    """フォルダを再帰的にスキャンして .bgsm ファイルのリストを返す"""
    result = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".bgsm"):
                result.append(os.path.join(root, f))
    return result


def scan_dds(folder: str) -> list[str]:
    """フォルダを再帰的にスキャンして .dds ファイルのリストを返す"""
    result = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".dds"):
                result.append(os.path.join(root, f))
    return result


def make_auto_path(base_dir: str, original_bgsm_path: str) -> str:
    """
    オートマッピング: base_dir + 元のbgsmファイル名(拡張子を.ddsに) を結合
    例: base_dir=textures\\actor, file=skin.bgsm → textures\\actor\\skin.dds
    """
    stem = Path(original_bgsm_path).stem
    dds_name = stem + ".dds"
    return str(Path(base_dir) / dds_name)

TOOLTIPS = {
    # General
    "Version": "BGSM/BGEM Format Version",
    "Tile U": "Tile the U texture coordinate (wrapping/repeating the texture).",
    "Tile V": "Tile the V texture coordinate (wrapping/repeating the texture).",
    "U Offset": "Offset the U texture coordinate.",
    "V Offset": "Offset the V texture coordinate.",
    "U Scale": "Scale the U texture coordinate.",
    "V Scale": "Scale the V texture coordinate.",
    "Alpha": "Fixed alpha value that applies to the entire mesh (unrelated to texture alpha).",
    "Alpha Blend Mode": "Defines the mode at which alpha is blended into other meshes.",
    "Alpha Test Ref": "Reference value to do alpha testing for. Transparency happens when alpha is below or exceeds the reference value (depending on modes).",
    "Alpha Test": "Toggle alpha testing using the reference value.",
    "Z Buffer Write": "The mesh writes to the z-buffer to make others aware of its depth.",
    "Z Buffer Test": "The mesh tests the z-buffer to take note of other meshes depth.",
    "Screen Space Reflections": "Toggle screen space reflections.",
    "Wetness Control SSR": "Toggle wetness control for screen space reflections.",
    "Decal": "Toggle decal rendering.",
    "Two Sided": "Renders both sides of all faces of the mesh (double sided).",
    "Decal No Fade": "Toggle decal rendering without fade.",
    "Non Occluder": "Don't perform occlusion (line-of-sight).",
    "Refraction": "Toggle refraction of light.",
    "Refraction Falloff": "Toggles refraction falloff.",
    "Refraction Power": "Power of the refraction.",
    "Environment Mapping": "Toggle environment mapping.",
    "Env Mapping Mask Scale": "Scale for the environment mask.",
    "Grayscale To Palette Color": "Toggle mapping of grayscale to palette colors.",
    "Mask Writes": "Masks writing of certain lighting properties.",

    # Textures
    "Diffuse Texture": "Diffuse texture slot.",
    "Normal Texture": "Normal map slot.",
    "Smooth/Spec Texture": "Smoothness/specular mask slot.",
    "Greyscale Texture": "Greyscale (palette/lookup/heightmap) texture slot.",
    "Envmap Texture": "Environment map slot.",
    "Glow Texture": "Glow map or other specialty slot.",
    "Inner Layer Texture": "Inner layer mask slot.",
    "Wrinkles Texture": "Wrinkles texture slot.",
    "Displacement Texture": "Displacement texture slot.",

    # Material
    "Enable Editor Alpha Ref": "Toggle editor alpha testing reference.",
    "Rim Lighting": "Toggle rim lighting effect.",
    "Rim Power": "Power of the rim lighting.",
    "Back Light Power": "Power of the back lighting.",
    "Subsurface Lighting": "Toggle subsurface lighting effect.",
    "Subsurface Lighting Rolloff": "Rolloff of the subsurface lighting.",
    "Specular Enabled": "Toggle specular effect.",
    "Specular Color": "Color for the specular effect.",
    "Specular Mult": "Multiplier for the specular effect.",
    "Smoothness": "Smoothness of the specular effect.",
    "Fresnel Power": "Power of the fresnel reflection and transmission (specular).",
    "Wetness Spec Scale": "Scale of the wetness specular.",
    "Wetness Spec Power Scale": "Power scale of the wetness specular.",
    "Wetness Spec Minvar": "Minimum variance of the wetness specular.",
    "Wetness Env Map Scale": "Environment map scale of the wetness effect.",
    "Wetness Fresnel Power": "Fresnel power of the wetness effect.",
    "Wetness Metalness": "Metalness of the wetness effect.",
    "PBR": "Enables native PBR rendering.",
    "Root Material Path": "Template/root file of the current material.",
    "Aniso Lighting": "Toggle anisotropic lighting.",
    "Emit Enabled": "Toggle emittance effect.",
    "Emittance Color": "Color for the emittance effect.",
    "Emittance Mult": "Multiplier for the emittance effect.",
    "Model Space Normals": "Toggle model space normals rendering.",
    "External Emittance": "Toggle external emittance effect.",
    "Back Lighting": "Toggle back lighting effect.",
    "Receive Shadows": "Toggle if this mesh receives shadows.",
    "Hide Secret": "Toggle hide secret.",
    "Cast Shadows": "Toggle shadow casting for this mesh.",
    "Dissolve Fade": "Toggle dissolve fade.",
    "Assume Shadowmask": "Toggle assuming shadowmask.",
    "Glowmap": "Toggle making use of a glowmap for emittance.",
    "Env Mapping Window": "Toggle environment map window.",
    "Env Mapping Eye": "Toggle environment map eye.",
    "Hair": "Toggle hair rendering.",
    "Hair Tint Color": "Color for the hair tinting.",
    "Tree": "Toggle tree rendering.",
    "Facegen": "Toggle facegen rendering.",
    "Skin Tint": "Toggle skin tint rendering.",
    "Tessellate": "Toggle tessellation effect.",
    "Displacement Bias": "Bias for the displacement texture.",
    "Displacement Scale": "Scale for the displacement texture.",
    "Tessellation Pn Scale": "PN (point normal) scale for the tessellation effect.",
    "Tessellation Base Factor": "Base factor for the tessellation effect.",
    "Tessellation Fade Distance": "Fade distance for the tessellation effect.",
    "Grayscale To Palette Scale": "Scale for the grayscale to palette mapping.",
    "Skew Specular Alpha": "Toggle skew specular alpha.",
    "Terrain": "Toggle terrain rendering.",
    "Terrain Threshold Falloff": "Softness of the terrain blending.",
    "Terrain Tiling Distance": "Tiling distance of the terrain.",
    "Terrain Rotation Angle": "Rotation angle of the terrain.",
}
