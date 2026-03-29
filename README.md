# Batch Material Editor (Fallout 4)

Fallout 4 のマテリアルファイル（`.bgsm` / `.bgem`）を直感的に、かつ一括で操作するための強力なGUIツールです。
単一ファイルの編集だけでなく、複数のファイルに対するテクスチャパスの一括置換や、テクスチャ（DDSフォルダ）および3Dモデル（NIFテンプレート）に基づいた自動バッチ生成機能を備えています。

## 主な機能

### 1. 単体編集 (Single Editor)
Material Editorのように BGSM / BGEM ファイルを開き、各種パラメーター（Normal, Specular, Emissive, Alpha など）やテクスチャパスを編集できます。

### 2. 一括編集 (Batch Editor)
指定したフォルダ内のすべてのマテリアルに対して、パラメーターの変更を一括適用できます。
- 変更したい項目（例：Normalマップパスのみ、Specular Colorのみ）だけにチェックを入れて一括適用。
- **オートマッピング機能**: Diffuse パスを「ベースパス＋各マテリアル名と同名の `.dds`」として自動設定し、大量のリテクスチャ作業を瞬時に終わらせます。

### 3. 生成 (Generator)
1つの「テンプレートBGSM」と「DDSファイル群（フォルダ）」から、**サブフォルダ構造を維持したまま大量のBGSMを自動生成**します。
- 指定したフォルダのサブフォルダごとに固有の Normal/Spec マップを設定可能（髪や肌など部位ごとに異なるノーマルやスペキュラを適用したい場合に便利）。
- テンプレートBGSMを読み込んだ後にプリセット保存(json)することで、次回からはプリセットを読み込むだけで同じ設定を再現できます。
- Material Swapを実装するために大量のBGSMを生成しなければならないときに便利です

### 4. NIF生成 (NIF Generator)
「テンプレートとなるNIFファイル」と「生成済みのBGSMフォルダ」から、**各BGSMを割り当てたNIFファイルを自動生成**します。

## License
This project is licensed under the MIT License.

------------------------------------------------------------------------------------------------------------------------------

# Batch Material Editor (Fallout 4)

A powerful GUI tool designed for intuitive and bulk editing of Fallout 4 material files (`.bgsm` / `.bgem`).  
In addition to editing single files, it supports batch texture path replacement and automatic batch generation based on texture (DDS folders) and 3D models (NIF templates).

## Main Features

### 1. Single Editor
Open and edit BGSM / BGEM files like in the Material Editor.  
You can directly modify parameters such as Normal, Specular, Emissive, Alpha, as well as texture paths.

### 2. Batch Editor
Apply parameter changes to all material files within a specified folder at once.  
- Select only the parameters you want to modify (e.g., Normal map path only, Specular Color only) and apply them in bulk.  
- **Auto-mapping feature**: Automatically sets the Diffuse path using a base path + `.dds` file with the same name as each material, dramatically speeding up large-scale retexturing work.

### 3. Generator
Automatically generate a large number of BGSM files from a single template BGSM and a set of DDS files (folder), **while preserving the subfolder structure**.  
- Allows assigning unique Normal/Spec maps per subfolder (useful for applying different maps to parts like hair or skin).  
- After loading a template BGSM, you can save settings as a preset (JSON) and reuse them later by simply loading the preset.  
- Ideal when you need to generate many BGSM files for implementing Material Swap.

### 4. NIF Generator
Automatically generate NIF files by assigning each BGSM from a generated BGSM folder to a template NIF file.

---

## License
This project is licensed under the MIT License.