"""
NIF マテリアルバッチ設定コア
=================================
元の NIF ファイルをテンプレートに、指定フォルダ内の BGSM マテリアルファイル
それぞれに対応した NIF ファイルを自動生成する。

BSLightingShaderProperty の Name プロパティにマテリアルパスを設定する。

対象: Fallout 4 NIF (Version 20.2.0.7, User Version 12, BS Version 130)
"""

import struct
import os

# ==============================================================================
# NIF バイナリ操作コア
# ==============================================================================

class NifStringEditor:
    """
    NIF ファイルのヘッダ内文字列テーブルを操作するクラス。
    
    NIF フォーマット (Version 20.2.0.7, BS Version 130) のヘッダ構造:
    - ヘッダ行 (改行終端)
    - Version (uint32)
    - Endian Type (byte)
    - User Version (uint32)
    - Num Blocks (uint32)
    - BS Version (uint32)
    - Export Info (ShortString x 3: author, process_script, export_script)
    - [BS >= 130] Max Filepath (ushort)
    - Num Block Types (ushort)
    - Block Type Names (SizedString[])
    - Block Type Indices (ushort[])
    - Block Sizes (uint32[])
    - Num Strings (uint32)
    - Max String Length (uint32)
    - Strings (SizedString[])
    - Num Groups (uint32)
    - Groups (uint32[])
    """
    
    def __init__(self):
        self.raw_data = b""
        self.pre_strings_data = b""
        self.num_strings = 0
        self.max_string_length = 0
        self.strings = []
        self.post_strings_data = b""
        self.version = 0
        self.bs_version = 0
        self.num_blocks = 0
        self.block_type_names = []
        self.block_type_indices = []
    
    def read(self, data: bytes):
        """NIF バイナリデータからヘッダを読み込む"""
        self.raw_data = data
        
        newline_pos = data.index(b'\x0a')
        pos = newline_pos + 1
        
        self.version = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        pos += 1  # Endian Type
        
        user_version = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        self.num_blocks = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        self.bs_version = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        # Export Info: 3 x ShortString (1byte len + string with null)
        for _ in range(3):
            slen = data[pos]
            pos += 1 + slen
        
        # BS Version >= 130: Max Filepath (ushort)
        if self.bs_version >= 130:
            pos += 2
        
        num_block_types = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        
        self.block_type_names = []
        for _ in range(num_block_types):
            bt_len = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            bt_name = data[pos:pos + bt_len].decode('utf-8', errors='replace')
            pos += bt_len
            self.block_type_names.append(bt_name)
        
        self.block_type_indices = []
        for _ in range(self.num_blocks):
            bti = struct.unpack_from('<H', data, pos)[0]
            pos += 2
            self.block_type_indices.append(bti)
        
        for _ in range(self.num_blocks):
            pos += 4  # Block Sizes
        
        self.pre_strings_data = data[:pos]
        
        self.num_strings = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        self.max_string_length = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        self.strings = []
        for _ in range(self.num_strings):
            s_len = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            s_val = data[pos:pos + s_len].decode('utf-8', errors='replace')
            pos += s_len
            self.strings.append(s_val)
        
        self.post_strings_data = data[pos:]
    
    def write(self) -> bytes:
        """変更した文字列テーブルでNIFバイナリを再構築する"""
        buf = bytearray()
        buf.extend(self.pre_strings_data)
        
        buf.extend(struct.pack('<I', len(self.strings)))
        
        if self.strings:
            max_len = max(len(s.encode('utf-8')) for s in self.strings)
        else:
            max_len = 0
        buf.extend(struct.pack('<I', max_len))
        
        for s in self.strings:
            encoded = s.encode('utf-8')
            buf.extend(struct.pack('<I', len(encoded)))
            buf.extend(encoded)
        
        buf.extend(self.post_strings_data)
        return bytes(buf)
    
    def get_block_type_name(self, block_index: int) -> str:
        if 0 <= block_index < len(self.block_type_indices):
            bti = self.block_type_indices[block_index]
            if 0 <= bti < len(self.block_type_names):
                return self.block_type_names[bti]
        return ""
    
    def find_bgsm_string_indices(self, materials_only: bool = True) -> list:
        """
        文字列テーブルから .bgsm で終わる文字列のインデックスを返す。
        materials_only=True の場合、Materials\\ で始まるパスのみを対象にする。
        """
        indices = []
        for i, s in enumerate(self.strings):
            if s.lower().endswith('.bgsm'):
                if materials_only:
                    if s.lower().startswith('materials\\') or s.lower().startswith('materials/'):
                        indices.append(i)
                else:
                    indices.append(i)
        return indices
    
    def has_bslsp(self) -> bool:
        return "BSLightingShaderProperty" in self.block_type_names


def set_material_path(nif_data: bytes, material_path: str) -> bytes:
    """NIF バイナリデータの文字列テーブル内の .bgsm パスを置き換える"""
    editor = NifStringEditor()
    editor.read(nif_data)
    
    mat_indices = editor.find_bgsm_string_indices(materials_only=True)
    if not mat_indices:
        mat_indices = editor.find_bgsm_string_indices(materials_only=False)
    if not mat_indices:
        raise ValueError("NIF ファイル内に .bgsm マテリアルパスが見つかりません")
    
    for idx in mat_indices:
        editor.strings[idx] = material_path
    
    return editor.write()


# ==============================================================================
# BGSM スキャン & バッチ処理
# ==============================================================================

def scan_bgsm_recursive(root_folder: str):
    """
    フォルダを再帰的にスキャンし、BGSMファイルを含むサブフォルダを検出する。
    
    Returns:
        list of (subfolder_relative_path, [bgsm_filenames])
        例: [
            ("C_Com\\Type1\\color\\Black", ["B.bgsm", "Gr.bgsm", ...]),
            ("C_Com\\Type1\\color\\Blue", ["B1.bgsm", "B2.bgsm", ...]),
            ("PureEye\\defalt", ["1.bgsm", "2.bgsm", ...]),
        ]
    """
    results = []
    root_folder = os.path.normpath(root_folder)
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        bgsm_files = sorted([f for f in filenames if f.lower().endswith('.bgsm')])
        if bgsm_files:
            # root_folder からの相対パス
            rel_path = os.path.relpath(dirpath, root_folder)
            if rel_path == '.':
                rel_path = ''
            results.append((rel_path, bgsm_files))
    
    return results


def auto_detect_material_prefix(folder_path: str) -> str:
    """
    フォルダパスから Materials\\ 以降のプレフィックスを自動検出する。
    
    例: "C:\\...\\Materials\\Eku_Race\\Eye" → "Materials\\Eku_Race\\Eye"
    """
    normalized = folder_path.replace('/', '\\')
    lower = normalized.lower()
    mat_pos = lower.find('materials\\')
    if mat_pos != -1:
        return normalized[mat_pos:]
    return ""


def batch_set_materials(
    source_nif_path: str,
    bgsm_folder: str,
    material_prefix: str,
    output_folder: str,
    progress_callback=None
):
    """
    単一フォルダ内の BGSM でバッチ処理（従来版）。
    """
    with open(source_nif_path, 'rb') as f:
        original_nif = f.read()
    
    try:
        all_files = os.listdir(bgsm_folder)
    except OSError as e:
        raise FileNotFoundError(f"フォルダにアクセスできません: {bgsm_folder}\n{e}")
    
    bgsm_files = sorted([f for f in all_files if f.lower().endswith('.bgsm')])
    
    if not bgsm_files:
        raise FileNotFoundError(f"BGSM ファイルが見つかりません: {bgsm_folder}")
    
    os.makedirs(output_folder, exist_ok=True)
    
    generated_files = []
    total = len(bgsm_files)
    
    for i, bgsm_name in enumerate(bgsm_files):
        nif_name = os.path.splitext(bgsm_name)[0] + '.nif'
        mat_path = (material_prefix.rstrip('\\') + '\\' + bgsm_name).replace('/', '\\')
        
        new_nif = set_material_path(original_nif, mat_path)
        
        output_path = os.path.join(output_folder, nif_name)
        with open(output_path, 'wb') as f:
            f.write(new_nif)
        
        generated_files.append(output_path)
        
        if progress_callback:
            progress_callback(i + 1, total, nif_name)
    
    return generated_files


def batch_set_materials_recursive(
    source_nif_path: str,
    bgsm_root_folder: str,
    material_base_prefix: str,
    output_folder: str,
    progress_callback=None
):
    """
    サブフォルダを再帰的にスキャンし、各サブフォルダの BGSM に対応する
    NIF ファイルを自動 Prefix 付きでバッチ生成する。
    
    出力フォルダにはサブフォルダ構造が再現される。
    
    Args:
        source_nif_path: 元の NIF ファイルパス
        bgsm_root_folder: BGSM のルートフォルダ（再帰スキャン起点）
        material_base_prefix: マテリアルのベースプレフィックス
                              例: "Materials\\Eku_Race\\Eye"
        output_folder: 出力先ルートフォルダ
        progress_callback: (current, total, message)
    
    Returns:
        list: 生成されたファイルのリスト
    """
    with open(source_nif_path, 'rb') as f:
        original_nif = f.read()
    
    # 再帰スキャン
    scan_results = scan_bgsm_recursive(bgsm_root_folder)
    
    if not scan_results:
        raise FileNotFoundError(f"BGSM ファイルが見つかりません: {bgsm_root_folder}")
    
    # 総数を計算
    total_files = sum(len(bgsm_list) for _, bgsm_list in scan_results)
    
    generated_files = []
    current = 0
    
    for rel_path, bgsm_files in scan_results:
        # このサブフォルダ用のマテリアルプレフィックスを構築
        if rel_path:
            mat_prefix = material_base_prefix.rstrip('\\') + '\\' + rel_path.replace('/', '\\')
            out_subfolder = os.path.join(output_folder, rel_path)
        else:
            mat_prefix = material_base_prefix.rstrip('\\')
            out_subfolder = output_folder
        
        os.makedirs(out_subfolder, exist_ok=True)
        
        for bgsm_name in bgsm_files:
            nif_name = os.path.splitext(bgsm_name)[0] + '.nif'
            mat_path = (mat_prefix + '\\' + bgsm_name).replace('/', '\\')
            
            new_nif = set_material_path(original_nif, mat_path)
            
            output_path = os.path.join(out_subfolder, nif_name)
            with open(output_path, 'wb') as f:
                f.write(new_nif)
            
            generated_files.append(output_path)
            current += 1
            
            if progress_callback:
                display_path = os.path.join(rel_path, nif_name) if rel_path else nif_name
                progress_callback(current, total_files, display_path)
    
    return generated_files
