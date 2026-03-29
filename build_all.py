import os
import subprocess

def build_version(name, region, distpath, has_ico):
    print(f"\n=== Building {name} ({region}) ===")
    
    # リージョン情報をテキストファイルとして生成
    with open("_region.txt", "w", encoding="utf-8") as f:
        f.write(region)
    
    cmd = [
        "pyinstaller", "--onefile", "--noconsole",
        "--name", name,
        "--add-data", "Vault.png;.",
        "--add-data", "Vault2.png;.",
        "--add-data", "_region.txt;.",
        "--add-data", "Icon.png;.",
        "main.py",
        "--distpath", distpath,
        "--clean"
    ]
    
    if has_ico:
        cmd.insert(3, "--icon=Icon.ico")
        
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    has_ico = False
    # EXEアイコンのために .ico 変換を試みる（Pillow があれば）
    if os.path.exists("Icon.png"):
        try:
            from PIL import Image
            img = Image.open("Icon.png")
            img.save("Icon.ico")
            has_ico = True
            print("Successfully converted Icon.png to Icon.ico for EXE icon.")
        except Exception as e:
            print(f"Skipping EXE icon generation (Pillow not installed or error): {e}")
            if os.path.exists("Icon.ico"):
                has_ico = True

    # 国内版ビルド
    build_version("Batch_Material_Editor_JP", "JP", "dist/jp", has_ico)
    # 海外版ビルド
    build_version("Batch_Material_Editor_Global", "GLOBAL", "dist/global", has_ico)
    
    # 一時ファイル掃除
    if os.path.exists("_region.txt"):
        os.remove("_region.txt")
    if os.path.exists("Icon.ico"):
        os.remove("Icon.ico")
    
    print("\nDone!")
