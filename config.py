"""
config.py — 設定管理、翻訳、テーマ管理
"""

import os
import json
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from utils import get_resource_path, get_app_dir

SETTINGS_FILE = os.path.join(get_app_dir(), "settings.json")
CACHE_FILE = os.path.join(get_app_dir(), "settings.cache")

# ── 翻訳辞書 ───────────────────────────────────────────────────────────────
TRANSLATIONS = {
    # Main Window
    "ja": {
        "FO4 BGSM Tool": "FO4 BGSM ツール",
        "View": "表示",
        "Set Background Image...": "背景画像を設定...",
        "Clear Background Image": "背景画像をクリア",
        "Single Editor": "単体編集",
        "Batch Editor": "一括編集",
        "Generator": "生成",
        "Settings": "設定",
        "Log": "ログ",
        "Clear": "クリア",
        "Ready": "準備完了",

        # Editor Tab
        "Please open a file": "ファイルを開いてください",
        "Open": "開く",
        "Save": "上書き保存",
        "Save As": "名前を付けて保存",

        # Batch Editor
        "Target Folder": "対象フォルダ",
        "Folder containing BGSM files": "BGSMファイルが含まれるフォルダ",
        "Browse...": "参照...",
        "Scan": "スキャン",
        "Scan Count:": "スキャン件数:",
        "Texture Paths (Empty = No change)": "テクスチャパス（空欄 = 変更しない）",
        "Can paste absolute paths (auto extracts game path)": "絶対パス可（Textures以降を自動抽出）",
        "Auto Mapping (Auto-set Diffuse to [Base Path\\bgsm_filename.dds])": "オートマッピング (Diffuse設定を[入力したパス\\各bgsmファイル名.dds]に自動設定)",
        "Base Path (e.g. textures\\actor\\)": "ベースパス（例: textures\\actor\\）",
        "Apply Batch": "一括適用",
        "Check the parameters you want to apply on the left": "適用したいパラメータは左側にチェックを入れてください",
        "Advanced Settings": "高度な設定",

        # Generator
        "Template": "テンプレート",
        "Select template BGSM file": "テンプレートBGSMファイルを選択",
        "BGSM File:": "BGSMファイル:",
        "Preset:": "プリセット:",
        "Load": "読み込む",
        "Save Current Settings": "現在の設定を保存",
        "Template not selected": "テンプレート未選択",
        "Source DDS Folder": "DDSソースフォルダ",
        "Folder containing DDS files": "DDSファイルが含まれるフォルダ",
        "Output Folder": "出力フォルダ",
        "Folder to output BGSMs": "BSGMを出力するフォルダ",
        "Common Map Overrides (Optional)": "共通マップ固定（オプション）",
        "Normal path (Empty = Template)": "法線マップパス（空欄=テンプレート値を使用）",
        "Spec path (Empty = Template)": "スペキュラパス（空欄=テンプレート値を使用）",
        "Common Normal:": "共通 Normal:",
        "Common Smooth/Spec:": "共通 Smooth/Spec:",
        "Generate BGSMs": "BGSM生成",
        "Per-Folder Map Overrides": "フォルダ別マップ設定",

        # Settings
        "Language:": "言語:",
        "Theme:": "テーマ:",
        "Show Tooltips": "ツールチップを表示する（ホバー説明）",
        "Auto Build Index on Startup": "起動時にテクスチャインデックスを自動構築する",
        "Enable Periodic Index Build": "テクスチャインデックスの定期的な自動構築を有効にする",
        "Interval (minutes):": "更新間隔（分）:",
        
        # General Dialogs
        "Warning": "警告",
        "Please specify a valid folder": "有効なフォルダを指定してください",
        "Please select a template": "テンプレートを選択してください",
        "Error": "エラー",
        "Done": "完了",
        "Confirm": "確認",
        "Are you sure you want to continue?": "続行しますか？",
        "Saved preset:": "プリセット保存:",
        "Preset Name": "プリセット名",
        "Enter preset name to save:": "保存するプリセット名を入力:",
        # Recent / Data Path
        "File": "ファイル",
        "Recent Files": "最近使ったファイル",
        "No Recent Files": "履歴なし",
        "FO4 Data Folder:": "FO4 Dataフォルダ:",
        "Path to Fallout 4/Data": "Fallout 4/Data のパス",
        "Texture not found": "テクスチャが見つかりません",
        "MO2 Mods Folder:": "MO2 Modsフォルダ:",
        "Path to MO2/mods folder": "MO2のmodsフォルダのパス",
        "Build Texture Index": "テクスチャインデックス構築",
        "Building index...": "インデックス構築中...",
        "Index built: {count} textures found": "インデックス構築完了: {count}件のテクスチャが見つかりました",
        
        # New additions for File Menu
        "New": "新規",
        "Close": "閉じる",
        "Exit": "終了",
        "Unsaved File": "未保存ファイル",
        
        # Unsaved Changes
        "Unsaved Changes": "未保存の変更",
        "There are unsaved changes. Do you want to save them?": "ファイルに変更が加えられています。保存しますか？",
        "Saved: ": "保存しました: ",

        # NIF Batch Tab
        "NIF Generator": "NIF生成",
        "Input Settings": "入力設定",
        "Source NIF File:": "テンプレートNIFファイル:",
        "Select the template NIF file": "テンプレートNIFファイルを選択",
        "BGSM Folder:": "BGSMフォルダ:",
        "Scan subfolders recursively": "サブフォルダも再帰的にスキャンする",
        "Material Base Prefix:": "マテリアルベースプレフィックス:",
        "Auto Detect": "自動検出",
        "Example: Materials\\Folder\\Folder (subfolder paths are appended automatically)": "例: Materials\\Folder\\Folder (サブフォルダ部分は自動付与されます)",
        "Output Settings": "出力設定",
        "Output Folder:": "出力先フォルダ:",
        "Folder to output NIF files": "NIFファイルの出力先フォルダ",
        "Preview": "プレビュー",
        "Run Batch": "▶ 実行",
        "Please specify:": "以下を指定してください:",
        "Starting batch process...": "バッチ処理を開始...",
        "{count} NIF files generated.\nOpen output folder?": "{count} 個の NIF ファイルを生成しました。\n出力フォルダを開きますか？",
    },
    "ko": {
        "FO4 BGSM Tool": "FO4 BGSM 툴",
        "View": "보기",
        "Set Background Image...": "배경 이미지 설정...",
        "Clear Background Image": "배경 이미지 지우기",
        "Single Editor": "단일 편집기",
        "Batch Editor": "일괄 편집기",
        "Generator": "생성기",
        "Settings": "설정",
        "Log": "로그",
        "Clear": "지우기",
        "Ready": "준비 완료",

        # Editor Tab
        "Please open a file": "파일을 열어주세요",
        "Open": "열기",
        "Save": "저장",
        "Save As": "다른 이름으로 저장",

        # Batch Editor
        "Target Folder": "대상 폴더",
        "Folder containing BGSM files": "BGSM 파일이 포함된 폴더",
        "Browse...": "찾아보기...",
        "Scan": "스캔",
        "Scan Count:": "스캔 수:",
        "Texture Paths (Empty = No change)": "텍스쳐 경로 (비워두면 변경 없음)",
        "Can paste absolute paths (auto extracts game path)": "절대 경로 붙여넣기 가능 (게임 경로 자동 추출)",
        "Auto Mapping (Auto-set Diffuse to [Base Path\\bgsm_filename.dds])": "자동 매핑 (Diffuse 설정을 [입력한 경로\\각 bgsm 파일명.dds]에 자동 설정)",
        "Base Path (e.g. textures\\actor\\)": "기본 경로 (예: textures\\actor\\)",
        "Apply Batch": "일괄 적용",
        "Check the parameters you want to apply on the left": "적용할 매개변수를 왼쪽에 체크하세요",
        "Advanced Settings": "고급 설정",

        # Generator
        "Template": "템플릿",
        "Select template BGSM file": "템플릿 BGSM 파일 선택",
        "BGSM File:": "BGSM 파일:",
        "Preset:": "사전 설정:",
        "Load": "불러오기",
        "Save Current Settings": "현재 설정 저장",
        "Template not selected": "템플릿 선택 안 됨",
        "Source DDS Folder": "원본 DDS 폴더",
        "Folder containing DDS files": "DDS 파일이 포함된 폴더",
        "Output Folder": "출력 폴더",
        "Folder to output BGSMs": "BGSM을 출력할 폴더",
        "Common Map Overrides (Optional)": "공통 맵 덮어쓰기 (선택 사항)",
        "Normal path (Empty = Template)": "노멀 맵 경로 (비워두면 템플릿 사용)",
        "Spec path (Empty = Template)": "스펙 맵 경로 (비워두면 템플릿 사용)",
        "Common Normal:": "공통 Normal:",
        "Common Smooth/Spec:": "공통 Smooth/Spec:",
        "Generate BGSMs": "BGSM 생성",
        "Per-Folder Map Overrides": "폴더별 맵 설정",

        # Settings
        "Language:": "언어:",
        "Theme:": "테마:",
        "Show Tooltips": "도구 설명 표시 (포인터 올릴 때 설명)",
        "Auto Build Index on Startup": "시작 시 텍스처 인덱스 자동 구축",
        "Enable Periodic Index Build": "텍스처 인덱스 정기 자동 구축 활성화",
        "Interval (minutes):": "업데이트 간격 (분):",
        
        # General Dialogs
        "Warning": "경고",
        "Please specify a valid folder": "유효한 폴더를 지정해 주세요",
        "Please select a template": "템플릿을 선택해 주세요",
        "Error": "오류",
        "Done": "완료",
        "Confirm": "확인",
        "Are you sure you want to continue?": "계속하시겠습니까?",
        "Saved preset:": "저장된 사전 설정:",
        "Preset Name": "사전 설정 이름",
        "Enter preset name to save:": "저장할 사전 설정 이름 입력:",
        # Recent / Data Path
        "File": "파일",
        "Recent Files": "최근 파일",
        "No Recent Files": "기록 없음",
        "FO4 Data Folder:": "FO4 Data 폴더:",
        "Path to Fallout 4/Data": "Fallout 4/Data 경로",
        "Texture not found": "텍스처를 찾을 수 없습니다",
        "MO2 Mods Folder:": "MO2 Mods 폴더:",
        "Path to MO2/mods folder": "MO2 mods 폴더 경로",
        "Build Texture Index": "텍스처 인덱스 구축",
        "Building index...": "인덱스 구축 중...",
        "Index built: {count} textures found": "인덱스 구축 완료: {count}개 텍스처 발견",
        
        # New additions for File Menu
        "New": "새로 만들기",
        "Close": "닫기",
        "Exit": "끝내기",
        "Unsaved File": "저장되지 않은 파일",
        
        # Unsaved Changes
        "Unsaved Changes": "저장되지 않은 변경 사항",
        "There are unsaved changes. Do you want to save them?": "저장되지 않은 변경 사항이 있습니다. 저장하시겠습니까?",
        "Saved: ": "저장됨: ",

        # NIF Batch Tab
        "NIF Generator": "NIF 생성",
        "Input Settings": "입력 설정",
        "Source NIF File:": "원본 NIF 파일:",
        "Select the template NIF file": "템플릿 NIF 파일 선택",
        "BGSM Folder:": "BGSM 폴더:",
        "Scan subfolders recursively": "하위 폴더도 재귀적으로 스캔",
        "Material Base Prefix:": "머티리얼 기본 접두사:",
        "Auto Detect": "자동 감지",
        "Example: Materials\\Folder\\Folder (subfolder paths are appended automatically)": "예: Materials\\Folder\\Folder (하위 폴더 경로가 자동으로 추가됩니다)",
        "Output Settings": "출력 설정",
        "Output Folder:": "출력 폴더:",
        "Folder to output NIF files": "NIF 파일을 출력할 폴더",
        "Preview": "미리보기",
        "Run Batch": "▶ 실행",
        "Please specify:": "다음을 지정해 주세요:",
        "Starting batch process...": "배치 처리를 시작합니다...",
        "{count} NIF files generated.\nOpen output folder?": "{count}개의 NIF 파일이 생성되었습니다.\n출력 폴더를 여시겠습니까?",
    }
}

def tr(text: str, lang: str) -> str:
    """翻訳を取得する（見つからなければ原文を返す）"""
    return TRANSLATIONS.get(lang, {}).get(text, text)

# ── テーマQSS ─────────────────────────────────────────────────────────────
DARK_THEME = """
QMainWindow { background-color: #1e1e2e; }
QWidget { background-color: transparent; color: #cdd6f4; font-family: "Segoe UI", "Yu Gothic UI", sans-serif; font-size: 12px; }
QTabWidget::pane { border: 1px solid #45475a; background: rgba(30,30,46,220); border-radius: 4px; }
QTabBar::tab { background: #313244; color: #cdd6f4; padding: 6px 16px; border-radius: 4px 4px 0 0; margin-right: 2px; }
QTabBar::tab:selected { background: #89b4fa; color: #1e1e2e; font-weight: bold; }
QTabBar::tab:hover:!selected { background: #45475a; }
QGroupBox { border: 1px solid #45475a; border-radius: 6px; margin-top: 8px; padding: 6px; background: rgba(49,50,68,180); }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px; color: #89b4fa; font-weight: bold; }
QPushButton { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px 12px; }
QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
QPushButton:pressed { background-color: #89b4fa; color: #1e1e2e; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 3px 6px; color: #cdd6f4; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #89b4fa; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background-color: #1e1e2e; color: #cdd6f4; outline: false; selection-background-color: #89b4fa; selection-color: #1e1e2e; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #45475a; background: #313244; }
QCheckBox::indicator:checked { background: #89b4fa; border-color: #89b4fa; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #1e1e2e; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #45475a; border-radius: 4px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #89b4fa; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QLabel { background: transparent; }
QMenuBar { background: #181825; color: #cdd6f4; }
QMenuBar::item:selected { background: #313244; }
QMenu { background: #181825; border: 1px solid #45475a; }
QMenu::item:selected { background: #89b4fa; color: #1e1e2e; }
QSplitter::handle { background: #45475a; }
QStatusBar { background: #181825; color: #6c7086; font-size: 11px; }

/* Disabled states */
QWidget:disabled, QLabel:disabled, QCheckBox:disabled, QPushButton:disabled { color: #585b70; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled { background-color: #1e1e2e; color: #585b70; border-color: #313244; }
"""

LIGHT_THEME = """
QMainWindow { background-color: #eff1f5; }
QWidget { background-color: transparent; color: #4c4f69; font-family: "Segoe UI", "Yu Gothic UI", sans-serif; font-size: 12px; }
QTabWidget::pane { border: 1px solid #bcc0cc; background: rgba(239,241,245,220); border-radius: 4px; }
QTabBar::tab { background: #e6e9ef; color: #4c4f69; padding: 6px 16px; border-radius: 4px 4px 0 0; margin-right: 2px; border: 1px solid #bcc0cc; border-bottom: none; }
QTabBar::tab:selected { background: #1e66f5; color: #eff1f5; font-weight: bold; border-color: #1e66f5; }
QTabBar::tab:hover:!selected { background: #ccd0da; }
QGroupBox { border: 1px solid #bcc0cc; border-radius: 6px; margin-top: 8px; padding: 6px; background: rgba(230,233,239,180); }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px; color: #1e66f5; font-weight: bold; }
QPushButton { background-color: #e6e9ef; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 4px; padding: 4px 12px; }
QPushButton:hover { background-color: #ccd0da; border-color: #1e66f5; }
QPushButton:pressed { background-color: #1e66f5; color: #eff1f5; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #e6e9ef; border: 1px solid #bcc0cc; border-radius: 4px; padding: 3px 6px; color: #4c4f69; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #1e66f5; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background-color: #eff1f5; color: #4c4f69; outline: false; selection-background-color: #1e66f5; selection-color: #eff1f5; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #bcc0cc; background: #e6e9ef; }
QCheckBox::indicator:checked { background: #1e66f5; border-color: #1e66f5; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #e6e9ef; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #bcc0cc; border-radius: 4px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #1e66f5; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QLabel { background: transparent; }
QMenuBar { background: #e6e9ef; color: #4c4f69; }
QMenuBar::item:selected { background: #ccd0da; }
QMenu { background: #e6e9ef; border: 1px solid #bcc0cc; color: #4c4f69; }
QMenu::item:selected { background: #1e66f5; color: #eff1f5; }
QSplitter::handle { background: #bcc0cc; }
QStatusBar { background: #e6e9ef; color: #8c8fa1; font-size: 11px; }

/* Disabled states */
QWidget:disabled, QLabel:disabled, QCheckBox:disabled, QPushButton:disabled { color: #6c7086; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled { background-color: #ccd0da; color: #6c7086; border-color: #bcc0cc; }
"""

# ── 設定マネージャ ───────────────────────────────────────────────────────────
class _SettingsManager(QObject):
    # 値変更シグナル
    language_changed = pyqtSignal(str)
    theme_changed = pyqtSignal(str)
    tooltips_changed = pyqtSignal(bool)
    periodic_settings_changed = pyqtSignal()

    def _resolve_default_bg(self):
        """リージョンに基づいてデフォルト背景画像を決定する"""
        region_file = get_resource_path("_region.txt")
        region = ""
        try:
            with open(region_file, "r", encoding="utf-8") as rf:
                region = rf.read().strip()
        except Exception:
            pass
        
        if region == "GLOBAL":
            return "Vault2.png"
        else:
            return "Vault.png"

    def __init__(self):
        super().__init__()
        self.lang = "ja"
        self.theme = "dark"
        self.show_tooltips = True
        # リージョンに基づいたデフォルト背景を設定（settings.json の有無に関係なく）
        default_name = self._resolve_default_bg()
        self.bg_path = get_resource_path(default_name)
        self.recent_files: list[str] = []
        self.fo4_data_path: str = ""
        self.mo2_mods_path: str = ""
        self.auto_build_index: bool = False
        self.periodic_build_index: bool = False
        self.build_interval_min: int = 60
        self._texture_index: set[str] | None = None  # キャッシュ済みインデックス
        self.load()

    def load(self):
        try:
            if os.path.isfile(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.lang = d.get("lang", "ja")
                self.theme = d.get("theme", "dark")
                self.show_tooltips = d.get("show_tooltips", True)
                
                # リージョンに基づいたデフォルト背景名を取得
                default_name = self._resolve_default_bg()
                
                # 保存されたパスを取得
                saved_bg = d.get("bg_path", "")
                
                # 特殊処理: 保存された背景が「プリセットデフォルト」に含まれる場合、
                # 現在のリージョン設定に合わせて強制的にデフォルトを適用する
                internal_defaults = ["Vault.png", "Vault2.png", "Vault_Censored.png", "Internal_BG.png"]
                saved_bg_name = os.path.basename(saved_bg) if saved_bg else ""
                
                if saved_bg_name in internal_defaults or not saved_bg:
                    # システムデフォルトとして扱う
                    self.bg_path = get_resource_path(default_name)
                elif os.path.isfile(saved_bg):
                    # ユーザー指定の絶対パスの外部ファイルが存在する場合
                    self.bg_path = saved_bg
                elif not os.path.isabs(saved_bg) and os.path.isfile(get_resource_path(saved_bg)):
                    # ユーザー指定の相対パス（内部リソース等）が存在する場合
                    self.bg_path = get_resource_path(saved_bg)
                else:
                    # ファイルが見つからない場合は現在のデフォルトを適用
                    self.bg_path = get_resource_path(default_name)
                
                self.recent_files = d.get("recent_files", [])
                self.fo4_data_path = d.get("fo4_data_path", "")
                self.mo2_mods_path = d.get("mo2_mods_path", "")
                self.auto_build_index = d.get("auto_build_index", False)
                self.periodic_build_index = d.get("periodic_build_index", False)
                self.build_interval_min = d.get("build_interval_min", 60)
            
            # キャッシュファイルからインデックスを読み込み
            if os.path.isfile(CACHE_FILE):
                try:
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        self._texture_index = set(line.strip() for line in f if line.strip())
                except Exception:
                    self._texture_index = None
        except Exception:
            pass

    def save(self):
        d = {
            "lang": self.lang,
            "theme": self.theme,
            "show_tooltips": self.show_tooltips,
            "bg_path": self.bg_path,
            "recent_files": self.recent_files[:10],
            "fo4_data_path": self.fo4_data_path,
            "mo2_mods_path": self.mo2_mods_path,
            "auto_build_index": self.auto_build_index,
            "periodic_build_index": self.periodic_build_index,
            "build_interval_min": self.build_interval_min
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(d, f)
        except Exception:
            pass

    def apply_theme(self, app: QApplication = None):
        qss = DARK_THEME if self.theme == "dark" else LIGHT_THEME
        if app is None:
            app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)

    def set_lang(self, lang: str):
        if self.lang != lang:
            self.lang = lang
            self.save()
            self.language_changed.emit(lang)

    def set_theme(self, theme: str):
        if self.theme != theme:
            self.theme = theme
            self.save()
            self.apply_theme()
            self.theme_changed.emit(theme)

    def set_tooltips(self, show: bool):
        if self.show_tooltips != show:
            self.show_tooltips = show
            self.save()
            self.tooltips_changed.emit(show)

    def set_auto_build(self, auto: bool):
        if self.auto_build_index != auto:
            self.auto_build_index = auto
            self.save()

    def set_periodic_build(self, enabled: bool):
        if self.periodic_build_index != enabled:
            self.periodic_build_index = enabled
            self.save()
            self.periodic_settings_changed.emit()

    def set_build_interval(self, minutes: int):
        if self.build_interval_min != minutes:
            self.build_interval_min = minutes
            self.save()
            self.periodic_settings_changed.emit()

    def set_bg_path(self, path: str):
        self.bg_path = path
        self.save()

    def add_recent_file(self, path: str):
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:10]
        self.save()

    def get_recent_files(self) -> list[str]:
        return self.recent_files

    def set_fo4_data_path(self, path: str):
        self.fo4_data_path = path
        self._clear_cache()
        self.save()

    def set_mo2_mods_path(self, path: str):
        self.mo2_mods_path = path
        self._clear_cache()
        self.save()

    def _clear_cache(self):
        self._texture_index = None
        if os.path.isfile(CACHE_FILE):
            try:
                os.remove(CACHE_FILE)
            except Exception:
                pass

    def build_texture_index(self):
        """テクスチャパスのインデックスを事前構築する。
        Data/Textures と MO2 mods/*/Textures の両方をスキャン。
        結果は lowercase の相対パスの set でキャッシュされる。"""
        index = set()

        # Data/Textures フォルダ
        if self.fo4_data_path:
            tex_root = os.path.join(self.fo4_data_path, "Textures")
            if os.path.isdir(tex_root):
                for dirpath, _, filenames in os.walk(tex_root):
                    for fn in filenames:
                        rel = os.path.relpath(os.path.join(dirpath, fn), tex_root)
                        index.add(rel.lower())

        # MO2 mods フォルダ
        if self.mo2_mods_path and os.path.isdir(self.mo2_mods_path):
            for mod_name in os.listdir(self.mo2_mods_path):
                tex_root = os.path.join(self.mo2_mods_path, mod_name, "Textures")
                if not os.path.isdir(tex_root):
                    continue
                for dirpath, _, filenames in os.walk(tex_root):
                    for fn in filenames:
                        rel = os.path.relpath(os.path.join(dirpath, fn), tex_root)
                        index.add(rel.lower())

        self._texture_index = index
        
        # ファイルにキャッシュを保存
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                for path in sorted(index):
                    f.write(path + "\n")
        except Exception:
            pass
            
        return len(index)

    def check_texture_exists(self, texture_path: str) -> bool:
        """テクスチャパスがインデックスに存在するかチェック。
        インデックスが構築済みなら O(1) で検索。未構築ならチェックしない。"""
        if self._texture_index is None:
            return True  # インデックス未構築時は全てOK扱い
        # Textures\ プレフィックスがある場合は除去
        p = texture_path.strip()
        lower = p.lower().replace("/", "\\")
        if lower.startswith("textures\\"):
            lower = lower[len("textures\\"):]
        return lower in self._texture_index

# グローバルインスタンス
AppConfig = _SettingsManager()
