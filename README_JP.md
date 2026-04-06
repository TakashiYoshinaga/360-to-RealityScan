# 360-to-RealityScan
A tool for converting 360° equirectangular image-based SfM/NeRF results into RealityScan compatible images/XMP and COLMAP format for verification. Features automatic splitting, pose calculation, and mask support.

[English](README.md)

---

## ダウンロード

本リポジトリを取得するには、以下のいずれかの方法を使用してください。

- **ZIP でダウンロード**：GitHub ページ上部の **Code → Download ZIP** をクリックし、任意のフォルダに展開します。  
  or  
- **Git でクローン**：GitHub クライアントアプリや以下のコマンドでリポジトリをクローンします。

```
git clone https://github.com/TakashiYoshinaga/360-to-RealityScan.git
```

---

## セットアップ

### 1. Anaconda のインストール

以下のページから Anaconda をダウンロードしてインストールします。

https://www.anaconda.com/download

### 2. 仮想環境の作成

1. **Anaconda Navigator** を起動します
2. 左メニューの **Environments** をクリックします
3. 下部の **Create** をクリックします

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/023-Anaconda.jpg)

4. **Create new environment** ダイアログで以下を設定します
   - **Name**：任意の環境名（例：`gs_env`）
   - **Python**：バージョン 3.10 以上を選択
5. **Create** をクリックします

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/024-CreateNewEnvironment.jpg)

### 3. 関連ライブラリのインストール

#### NumPy のインストール

1. 作成した環境（例：`gs_env`）をクリックします
2. ドロップダウンメニューから **Not installed** を選択します

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/025-LibInstall.jpg)

3. 検索欄に `numpy` と入力します
4. リスト内の **numpy** にチェックを入れます
5. **Apply** をクリックします

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/026-NumPyInstall.jpg)

#### FFmpeg のインストール

1. 同様に検索欄に `ffmpeg` と入力します
2. リスト内の **ffmpeg** にチェックを入れます
3. **Apply** をクリックします

---

## 実行

### ターミナルの起動

1. Anaconda Navigator で環境名（例：`gs_env`）の横にある実行ボタンをクリックします
2. **Open Terminal** をクリックします

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/027-RunTerminal.jpg)

### スクリプトの実行

1. スクリプトのあるフォルダに移動します

```
cd C:\path\to\360-to-RealityScan
```

> **💡 ヒント**  
> `cd`（スペースあり）と入力した後、`360-to-RealityScan` フォルダをターミナル画面にドラッグ＆ドロップしても、パスを自動入力できます。

2. スクリプトを実行します

```
python spheresfm_to_realityscan.py
```

GUI が起動します。

---

## スクリプトの使い方

### 入出力ファイルの設定

GUI が起動したら、以下のように各パスを指定します。

| 項目 | 指定先 |
|------|--------|
| transform.json | `lichtfeld` フォルダ内の `transforms.json` |
| PLY file (optional) | `lichtfeld` フォルダ内の `pointcloud.ply` |
| Input folder (equirectangular) | Equirectangular 画像が入った `images` フォルダ |
| Mask folder (equirectangular, optional) | マスク画像が入った `masks` フォルダ |
| Output folder | 出力先フォルダ（例：`RealityScan` フォルダ） |

### 分割設定

基本的にはデフォルトのままで問題ありません。

| パラメータ | 説明 |
|-----------|------|
| Additional Pitch Angles | 赤道（画面上下中央 = 0°）は常に自動で含まれます。Equirectangular 画像の中央から上下に何度傾けた方向も切り出したい場合は、カンマ区切りで角度を入力します（例：`-45,45` で中央から上45°・下45°を追加）。空欄のままにすると赤道方向のみが切り出されます |
| Overlap Rate | 画像間のオーバーラップ率（赤道基準）。デフォルトで OK ですが、`0` にすると Cube マップの側面のみになります |

### 変換の実行

**Start Conversion** をクリックして変換を実行します。

変換が完了すると、出力フォルダ（例：`RealityScan`）に以下のファイル・フォルダが生成されます。

```
RealityScan/
├── all/
├── images/
├── masks/
├── cameras.txt
├── images.txt
└── points3D.txt  ← PLY ファイルを指定した場合のみ生成
```

> **📝 補足**  
> `transforms.json` と PLY ファイルを両方指定して実行した場合、カメラ姿勢・点群・画像情報をすべて含む完全な COLMAP 形式のデータが出力されます。

---

## 詳細な使い方

Gaussian Splatting のワークフロー全体への組み込み方については、以下の記事を参照してください。

- [SphereSfM](Documents/Advanced/article.md)
- [MetaShape](Documents/MetaShape/article.md)