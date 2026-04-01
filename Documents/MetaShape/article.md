# Metashape で始める 360° 画像を用いた Gaussian Splatting

## はじめに

屋外などの広範囲なシーンを **Gaussian Splatting** で再現する手法が注目を集めています。SNS やブログで関連情報を見かける機会も増えてきましたが、情報が各所に散らばっており、適切に統合して効率的なワークフローを構築するのは容易ではありません。

これまでの記事[基本手順編](../Basic/article.md)、[クオリティ向上編](../Advanced/article.md)では、筆者が趣味でのGaussian Splattingで運用している、基本的に無料で使えるツールだけで構成したワークフローをご紹介しました。今回は、比較的人気がある有料のSfMツールであるMetashape(Standard版)とその後の追加手順を用いたワークフローをご紹介します。

> **💡 本記事を読む前に**  
> 本記事では Python スクリプトを使用するステップが含まれます。Gaussian Splatting が初めての方や Python に不慣れな方は、まず無料ツールを使った「[基本手順編](../Basic/article.md)」で全体の流れを掴んでから挑戦することをおすすめします。


> **📝 注意**  
> 本記事は単独でも手順を追えるよう、これまでの記事と重複するセクションが含まれています。ご了承ください。

---
## 動作環境

### PC スペック

| 項目 | 環境 |
|------|------|
| OS | Windows 11 |
| GPU | NVIDIA GeForce RTX 4070 SUPER |
| CPU | AMD Ryzen7 8700G |
| RAM | 32 GB |

### 360° カメラ

- **Insta360 X4 Air**  
  ※ THETA など他メーカーのカメラでも利用可能です。**8K 以上**を推奨します。

### ソフトウェア

| ソフトウェア | 用途 |
|------------|------|
| [LichtFeld Studio v0.5.1](https://lichtfeld.io/) | 3D Gaussian Splatting の GUI ツール |
| [360° Gaussian v1.3.0](https://laskosvirtuals.gumroad.com/l/360gaussian) | Gaussian Splatting の各ステップを自動化するツール |
| [Metashape(Standard版)](https://oakcorp.net/agisoft/standard/) | SfMと点群の生成に使用 |
| [RealityScan](https://www.realityscan.com/) | 点群の再生成に使用 |
| [360-to-RealityScan](https://github.com/TakashiYoshinaga/360-to-RealityScan) | Metashape の結果を RealityScan で読み込める形式（.xmp）に変換するツール |

### その他

- **Python 実行環境**（360-to-RealityScan 用）  
  例：Anaconda

---

## 全体の流れ

Gaussian Splatting では、一般的に以下のステップを踏みます。

| # | 工程 | 内容 |
|---|------|------|
| 1 | **撮影** | 360° カメラでシーンを撮影する |
| 2 | **SfM**（Structure from Motion） | 各画像がどの位置から撮影されたかを推定する |
| 3 | **点群生成** | SfM で得られたカメラ位置をもとに点群を生成する |
| 4 | **Gaussian Splatting** | 点群をもとに 3D Gaussian Splatting モデルを生成する |

本記事では、Step 2とStep3にMetashapeを使用します。
さらに、Step 4の前にMetashapeの結果をLichtFeld StudioやRealityCaptureなどの連携ツールで読める形式に変換し、点群の再生成を行います。

---

## Step 1. 撮影・動画のエクスポート

360° カメラでシーンを撮影します。処理時間が長くなる場合があるため、慣れるまでは **1 分以内の短い動画** でテストすることをおすすめします。

撮影した動画は **Equirectangular 形式** で PC にコピーしてください。  
Insta360 を使用している場合は、**Insta360 Studio**（PC 用アプリ）でエクスポートします。

> **⚠️ 前提条件**  
> 本記事では、360° カメラを**垂直に近い状態を保って**撮影していることを前提としています。

> **⚠️ 手ぶれ補正に関する注意**  
> 手ぶれ補正は ON / OFF どちらでも構いませんが、**ON にする場合**は以下の項目を必ず**オフ**にしてください。
> - 方向ロック
> - ティルトリカバリー
> - 微振動補正

> **💡 ヒント**  
> 手ぶれ補正を ON にしておくと、カメラが傾いても自動で垂直補正がかかります。厳密に言えば、この補正によって生じるわずかな歪みが後続の処理でノイズの原因となるケースもありますが、まずは手ぶれなどの細かいことを気にせず手軽に試してみたいという場合は「手ぶれ補正 ON」の設定で進めるのもありです。

![手ぶれ補正の設定画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/000-stabilization.jpg)

---

## Step 2. SfM と点群生成

この手順では **360° Gaussian** を使用します。  
360° Gaussianは、SfMやGaussian Splattingにおいてそれぞれ複数のツールをサポートしているため、ツールや手法の組み合わせを容易に比較検証できるのが特徴です。  
詳しい使い方を知りたい方は以下の動画を参考にしてください。

- 📺 [基本解説](https://www.youtube.com/watch?v=XcmmxKbjESQ)  
- 📺 [上記動画以降の追加要素の解説](https://www.youtube.com/watch?v=FDEUAn8FjSk)

### 2.1 画像の切り出し

1.　**360° Gaussian** を起動します  
2.　**Add Video(s)** をクリックし、Equirectangular 形式の動画を選択します  
3.　**Splitting** を選択し、画像の切り出し条件を設定します  

| パラメータ | 説明 |
|-----------|------|
| Extra frame every | 指定した秒数（またはフレーム数）のインターバルで画像を切り出す |
| Sharp frame extraction | 前後のフレームと比較して、ボケの少ない画像を優先的に選択するかどうか |
| Sharpness check range | 例えば `10` の場合、前後 5 フレームを比較して最もシャープな画像を選択する |

![360° Gaussian の Splitting 設定画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/001-360GaussianUI-01.jpg)

### 2.2 画像のマスク（オプション）

**AutoMasker** は、Gaussian Splatting の処理に不要な領域を自動でマスクしてくれるツールです。

1.　**AutoMasker** をクリックします  
2.　**Use AutoMasker** をオンにします  
3.　**Detection Keywords** にピリオド（`.`）区切りでキーワードを入力します  
   例：`person.sky`

![AutoMasker のマスク結果](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/002-MaskImage.jpg)

> **💡 マスクが重要な 2 つの理由**  
> まず、人・車・低テクスチャオブジェクトなど動いたり特徴点の少ない被写体は **SfM のノイズ**になりやすく、カメラ位置の推定精度を下げます。SfM の精度はその後の Gaussian Splatting の出力品質に直結するため、これらをマスクで除外することが重要です。  
> さらに、**トレーニング段階でも同様のノイズが品質を低下させます**。同じ被写体が場所によって異なる見た目で映り込むと、Gaussian が正しい形状・色に収束しにくくなります。マスクはこの両方の工程でクオリティを守る役割を果たします。  
> 📺 [参考動画](https://youtu.be/XcmmxKbjESQ?si=wPF74IBWmgV6mpxk&t=59)

> **📝 AutoMasker について**  
> AutoMasker は有償（46€）ですが、独立したアプリとして単独で動作するため、360° Gaussian を使った Gaussian Splatting の自動化ワークフローだけでなく、Gaussian Splatting 以外の用途（360° 画像へのマスク処理全般）にも幅広く活用できます。  
> 類似ツールを購入するよりもこれを利用・導入する方を検討することをお勧めします。    
> 購入後の 360° Gaussian との連携設定については、[こちらの動画](https://youtu.be/9g8wO_8jdKs?si=wNln9pvP2_7A2DSE&t=99) を参考にしてください。

### 2.3 SfM の設定

1.　**Alignment** をクリックします  
2.　**Training Method** を設定します  
本記事では最終的な処理にLichtFeld Studioを使用するため下記の通り設定します。
- **Training Method**：`Lichtfeld`
- **SfM(ドロップダウンメニュー)**：`Metashape Standard GUT`

> **⚠️ これまでの記事との違い**  
> これまでの記事では `SphereSFM` をベースとしたSfMツールを選択しましたが、本記事では **`Metashape Standard GUT`** を使用します。お間違いのないようご注意ください。

![Alignment の設定画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/029-AlignmentSetting-03.jpg)



### 2.4 フレーム抽出

**Start** をクリックして先ほど設定した間隔でのフレーム抽出を行います。 
抽出が完了すると、以下のようなMetashapeでのアライメント手順を解説する画面が表示されます。作業手順の参考になると思いますので現時点ではまだ閉じる必要はありません。 

![抽出完了画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/030-MetaShapeALignmentGuide.jpg)



カメラの位置情報と点群が正しく生成されていることを確認してください。

```
📁 動画が置かれたフォルダ
  └── 📁 動画名と同じフォルダ
       ├── 📁 final
       ├── 📁 frames
       ├── 📁 lichtfeld
       ├── 📁 masks
       └── 📁 metashape
```

次のステップの準備として、**`lichtfeld`** フォルダと同じ階層に **`RealityScan`** フォルダを作成しておきます。

```
📁 動画が置かれたフォルダ
  └── 📁 動画名と同じフォルダ
       ├── 📁 final
       ├── 📁 frames
       ├── 📁 lichtfeld
       ├── 📁 masks
       ├── 📁 metashape
       └── 📁 RealityScan　← 作成したフォルダ
```

### 2.5 Metashapeへのデータ取り込み

1.　**Metashape** を起動します  
2.　メニューバーの **Workflow** をクリックし、**Add Folder** を選択します  
3.　先ほど生成されたフォルダ内の **`frames`** フォルダを選択します  
4.　メニューバーの **Tools** をクリックし、**Camera Calibration** を選択します  
5.　**General** タブを開き、**Camera type** を `Spherical` に変更します  
6.　**OK** をクリックします

> **⚠️ 重要な設定**  
> Camera type を `Spherical` に変更し忘れると、360° 画像として正しく処理されません。必ず設定してください。

![キャリブレーション設定](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/031-CameraCalibrationForMetaShape.jpg)

**【オプション：マスク画像を作成した場合】**

マスク画像を生成した場合は、以下の手順でインポートします。

1.　メニューバーの **File** をクリックし、**Import → Import Masks** を選択します  
2.　**File name template** を `{filename}.mask.png` に変更します  
3.　**OK** をクリックし、先ほど生成されたフォルダ内の **`masks`** フォルダを選択します

> **📝 テンプレート指定の注意点**  
> デフォルトでは `{filename}_mask.png` のようになっている場合があります。アンダースコア（`_`）をピリオド（`.`）に変更するのを忘れないようにしてください。

![マスク画像のインポート](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/032-ImportMasksForMetaShape.jpg)

### 2.6 SfM の実行

1.　メニューバーの **Workflow** をクリックし、**Align Photos** を選択します  
2.　設定ダイアログが表示されたら各種設定を行い、**OK** をクリックします  

> **💡 アライメントの設定について**  
> 筆者は推定方法（Reference preselection）を `Sequential` ではなく `Estimated` を選択して実行しています。その他の詳細な設定については、以下のスクリーンショットを参考にしてください。

![SfMの実行](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/033-AlignmentSettingsForMetaShape.jpg)

処理が完了すると、以下のような結果が表示されます。正しくカメラ位置と点群が推定されていることを確認してください。

![SfMの実行結果](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/034-AlignmentResultForMetaShape.jpg)

**【データのエクスポート】**

問題がなければ、生成されたデータを保存します。

1.　メニューバーの **File** をクリックし、**Export → Export Cameras** を選択します  
2.　先ほど生成されたフォルダ内の **`metashape`** フォルダを選択し、任意の名前で XML ファイルとして保存します（例：`metashape.xml`）  
3.　続いて **File → Export → Export Point Cloud** を選択します  
4.　同じく **`metashape`** フォルダに任意の名前で PLY ファイルとして保存します（例：`points.ply`）  
5.　**Export Points** ダイアログが表示されたら、設定を確認して **OK** をクリックします  

![Export Points](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/035-ExportPoints.jpg)

出力が終了したら、Metashape を終了します。  
また、本記事ではここで 360° Gaussian 側の処理も完了となるため、Metashape 使用ガイドのウィンドウの **Abort** をクリックして閉じます。  
さらに、360° Gaussian のメイン画面の **Stop** もクリックして処理を終了させてください。



---

## Step 3. 画像の分割と点群の再生成

ここでは、Metashape で得られた SfM の結果を複数視点のピンホールカメラモデルの画像に分割します。さらに、そのデータを RealityScan に取り込み、分割後の画像をもとにした点群の再生成を実行します。

### 3.1 入出力ファイルの設定

1.　ターミナル（Python 実行環境）を開き、以下のコマンドを実行して **`metashape_to_realityscan.py`** を起動します

```bash
cd C:\path\to\360-to-RealityScan
python metashape_to_realityscan.py
```

> **📝 補足**  
> Python スクリプトの取得方法および環境設定方法については、以下のリポジトリの README を参照してください。  
> https://github.com/TakashiYoshinaga/360-to-RealityScan

2.　以下のように各パスを指定します  

| 項目 | 指定先 |
|------|--------|
| Metashape XML | `metashape` フォルダ内の `metashape.xml` |
| PLY file (optional) | `metashape` フォルダ内の `points.ply` |
| Input folder (equirectangular) | `frames` フォルダ |
| Mask folder (equirectangular, optional) | `masks` フォルダ |
| Output folder | 作成した `RealityScan` フォルダ |

### 3.2 分割設定

基本的にはデフォルトのままで問題ありません。

| パラメータ | 説明 |
|-----------|------|
| Pitch Angles | `0` に設定すると、Equirectangular 画像の上下中央の領域のみを切り出します |
| Overlap Rate | 画像間のオーバーラップ率。デフォルトで OK ですが、`0` にすると Cube マップの側面のみになります |

> **💡 Pitch Angles の補足**  
> `0` のみ（水平方向だけ）に限定する必要は必ずしもありません。撮影シーンによっては、上下方向の画像を加えることで Gaussian Splatting の出力品質が向上する場合があります。たとえば床や天井にタイルや模様など特徴的なテクスチャがある場合などは、`-30,0,30` のように仰角・俯角を加えた設定を試してみてください。

### 3.3 変換の実行

**Start Conversion** をクリックして変換を実行します。  
完了すると以下のような画面が表示されます。

![Metashape to RealityScan](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/036-MetaShapeConverter.jpg)

SfM の結果を RealityScan に取り込む準備が整いました。

> **📝 補足**  
> XML と PLY ファイルを両方指定して実行した場合、カメラ姿勢・点群・画像情報をすべて含む完全な COLMAP 形式のデータが出力されます。  
> RealityScan による点群の再生成は不要で、このツールで分割した画像をそのまま Gaussian Splatting に使用したい場合は、**Step 4. Gaussian Splatting** に進んでください。

### 3.4 RealityScan での点群生成

1.　**RealityScan** を起動します  
2.　**WORKFLOW** タブをクリックします  
3.　**Folder** をクリックし、`RealityScan` フォルダ内の **`all`** フォルダを指定します  
4.　**Inputs** を開き、`Ctrl + A` ですべての画像を選択します  

![RealityScan の Inputs 画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/015-RealityScanUI-01.jpg)

5.　以下のように詳細情報を設定します

| カテゴリ | 項目 | 設定値 |
|---------|------|--------|
| **Prior pose** | Absolute pose | `Locked` |
| **Prior calibration** | Calibration group | `0`（すべてのカメラを同じ設定にする） |
| | Prior | `Fixed`（画角固定） |
| **Prior lens distortion** | Lens group | `0`（すべてのカメラを同じ設定にする） |
| | Prior | `Fixed`（歪み固定） |

![RealityScan の詳細設定](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/016-RealityScanUI-02.jpg)

6.　**ALIGNMENT** タブをクリックします
7.　**Align Images** をクリックします

![Align Images の実行](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/017-RealityScanUI-03.jpg)

処理が完了すると、点群が再生成されます。

![再生成された点群](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/018-RealityScanUI-04.jpg)

### 3.5 エクスポート

**【カメラの位置姿勢情報と点群を COLMAP 形式でエクスポート】**

1.　**WORKFLOW**タブをクリックします  
2.　**Export** をクリックします  
3.　**COLMAP** をクリックします  
4.　`RealityScan` フォルダに任意のファイル名（例：`colmap`）で保存します  

> **📝 ファイル上書きに関する注意**  
> `metashape_to_realityscan.py` で出力された `cameras.txt`・`images.txt`・`points3D.txt` は上書きされます。上書きしても問題はありませんが、点群再生成前の COLMAP ファイルを保存しておきたい場合は、事前に別のフォルダに退避してください。

5.　**Export Dialog** で **Directory structure**を`Flat`にします  
6.　**Export masks** を `No` に設定します  
7.　**Export images** を一旦 `Yes` に設定します  
8.　**Export image setting** が表示されます  
9.　**Image format** を `jpg` に設定  
10.　**Naming convention** を `original file name`に設定  
11.　**Export images** を一旦 `No` に設定します  
12.　**OK** をクリックします  

![COLMAP エクスポート設定](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/021-RealityScanUI-07_2.jpg)

> **💡 ヒント**  
> `all` フォルダとその中の画像は RealityScan での処理（点群生成など）のためだけに使用されます。そのため、エクスポート完了後に不要になれば削除して構いません。もし再度必要になった場合は、`metashape_to_realityscan.py` を実行することでいつでも再生成できます。

---

## Step 4. Gaussian Splatting

### 4.1 データの読み込み

1.　**LichtFeld Studio** を起動します  
2.　動画名フォルダ直下の **`RealityScan`** フォルダをウィンドウにドラッグ＆ドロップします  
3.　**Load DataSet** ダイアログが表示されたら、そのまま**Load** をクリックします

![LichtFeld Studio の起動画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/007-LichtFeldStudioUI-01.jpg)
![Load DataSet ダイアログ](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/008-LoadDataset_2.jpg)

点群と画像が正しく読み込まれたことを確認してください。  
カメラ画像の表示が不要な場合は、画面右側の **Rendering** タブにある **Camera Frustum** のチェックを外します。

![データ読み込み後の画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/009-LichtFeldStudioUI-02.jpg)

### 4.2 トレーニング設定

ここではトレーニング設定の一例を紹介します。慣れてきたらさまざまな設定を試してみてください。

1.　**Training** タブをクリックします  
2.　**Strategy** で `MRNF` を選択します  
3.　**Steps Scaler** を適宜設定します  

| 条件 | 推奨値 |
|------|--------|
| 画像数が 300 枚以下 | `1` |
| 画像数が 300 枚以上 | `画像枚数 / 300` |

> **⚠️ トレーニングがうまくいかない場合**  
> 上記の設定で実行してもGaussian Splattingのトレーニングが進むにつれて収束せずにホワイトアウトしてしまう場合は、Steps Scaler を `画像枚数 / 300` の **2〜3 倍** に設定すると安定しやすいです。  
> なお筆者は経験上、最初から推奨の **1.5〜2 倍**程度の値でトレーニングを始めています。


4.　**Max Gaussians** で最大ガウシアン数を設定します   
   基本的にはデフォルト値で問題ありませんが、ディテールが不足していると感じたら値を増やしてみてください。

**オプション設定：**  
Auto Maskerを使ってマスク画像を作成した場合のみ下記の設定を行います。
- **Mask Mode** → `Ignore` に設定
- **Use Alpha as Mask** → チェックを外す

![トレーニング設定画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/010-TrainingSettings_2.jpg)

他のパラメータについては、まずは上記の設定で進め、慣れてきてから試行錯誤してみてください。

### 4.3 トレーニングの実行

1.　マウス操作で、トレーニングの経過を観察したいエリアにクローズアップしておきます  
   (筆者の例では橋の周辺)  
2.　**Start Training** をクリックしてトレーニングを開始します  
3.　最初はぼんやりとした表示ですが、ステップが進むにつれて徐々にクリアになっていきます  

![トレーニング中の画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/011-LichtFeldStudioUI-03.jpg)

トレーニングステップが上限に達すると自動で終了します。  
途中経過を保存しておきたい場合は、**Save Checkpoint** をクリックするとその時点の結果を記録できます。

### 4.4 エクスポート
出力したデータは [SuperSplat Editor](https://superspl.at/editor) などのツールを使って、動画作成やビューワーでの閲覧に活用できます。  
1.　**File → Export** をクリックします  
2.　出力フォーマットを選択します（例：`.ply`）

---

## まとめ

本記事では、商用の SfM ソフトウェアである **Metashape** を用いたワークフローをご紹介しました。  
Metashape は有償ツールですが、30 日間の無料トライアル期間も用意されているため、ご興味のある方はぜひ一度試してみてください。

これまで紹介してきた **SphereSfM** は、アライメントのイテレーション回数など SfM の細かいパラメータ設定に関して非常に充実しています。一方で **Metashape** はウィンドウ操作で簡単に扱え、手軽さや処理速度の面で分があります。どちらが絶対に優れていると断定することは難しく、用途や目的、求める精度に合わせて柔軟に使い分けるのがベストな選択と言えるでしょう。

その点、今回使用した **360° Gaussian** は、同じアプリ内で目的に応じて処理ツールを簡単に切り替えられます。様々な手法を比較・検証するうえで大変強力なツールだと実感しています。

本記事の手順をベースに、さらにご自身なりのアレンジを加えることで、より高品質な Gaussian Splatting の表現を追求していただければ幸いです。

### 作例（比較用）

参考までに、異なるSfMツールを使用して生成された3Dシーンの比較です。ブラウザ上で実際の3Dモデルをご覧いただけます：

- **[SphereSfM（前回の記事）で処理](https://superspl.at/scene/c28be98f)**
- **[Metashape（本記事）で処理](https://superspl.at/scene/adaae718)**

<br>

