# 手軽に始める 360° 画像を用いた Gaussian Splatting（クオリティ向上編）

## はじめに

屋外などの広範囲なシーンを **Gaussian Splatting** で再現する手法が注目を集めています。SNS やブログで関連情報を見かける機会も増えてきましたが、情報が各所に散らばっており、効率的なワークフローを構築するのは容易ではありません。

[前回の記事（基本手順編）](../Basic/article.md)では、筆者が趣味でのGaussian Splattingで運用している、基本的に無料で使えるツールだけで構成したワークフローの最小構成をご紹介しました。今回は、その手順にほんの少しの工夫を加えるだけで、クオリティをさらに引き上げる方法を解説します。また、無料ツールだけでなく、有償のソフトウェアであるAgisoft Metashapeを用いたワークフローについては「[Metashape編](../MetaShape/article.md)」で紹介していますので、興味がある方はそちらもご覧ください。

> **💡 本記事を読む前に**  
> 本記事では Python スクリプトを使用するステップが含まれます。Gaussian Splatting が初めての方や Python に不慣れな方は、まず「[基本手順編](../Basic/article.md)」で全体の流れを掴んでから挑戦することをおすすめします。

> **📝 SfM ツールの速度に関する補足**
>
> 「無料ツールは COLMAP の CameraRig アプローチだから遅い」という声を見かけたので補足。本記事で使用している **SphereSfM** は CameraRig とは原理的に異なり、本記事で使用する**Equirectangular 画像を球面カメラモデルで直接処理する**ため、CameraRig のようにキューブマップ 6 面分のマッチングコストが発生せず速度面も改善されています。
>
> 有償ツールにアドバンテージがあることは当然ですが、まず Gaussian Splatting を体験する入口としては本記事のフリーツール構成もぜひ試してみてください。さらなるクオリティを追求したくなったら、別記事の Metashape 編もチャレンジしてみてください。

### 基本手順編との出力比較

下の画像は、基本手順と本記事の手順による出力を比較したものです。タイルの継ぎ目やオブジェクトの輪郭がよりくっきりと再現されていることがわかります。

![基本手順 vs クオリティ改善手順の比較](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/012-BeforeAfter.jpg)

> **📝 注意**  
> 本記事は単独でも手順を追えるよう、前回と重複するセクションが含まれています。ご了承ください。

---

## 基本手順編との違い

前回の記事をすでにお読みいただいた方に向けて、主な変更点をまとめます。

**基本手順編（前回）：**  
Equirectangular 画像で SfM と点群を生成 → Cube マップに分割した画像をそのまま Gaussian Splatting の GUI ツールに投入

**クオリティ改善編（今回）：**  
Equirectangular 画像で SfM と点群を生成した後、以下の処理を追加します。

1.　**上下画像の除外** — 複数の視点に切り出す際、空や地面の割合が多い上下の画像を使用しません。これにより、ノイズの原因となる低テクスチャ領域を削減できます。  
2.　**点群の再生成** — 切り出した画像をもとに点群を再計算します。SfM 時に使用した Equirectangular ではなく Gaussian Splatting のトレーニング時に使用する**ピンホールカメラモデル**にマッチした点群を生成することで、トレーニング中のノイズ要因を排除します。 

> **⚠️ 前提条件**  
> 本記事では、360° カメラを**垂直に近い状態を保って**撮影していることを前提としています。

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
| [LichtFeld Studio v0.5.0](https://lichtfeld.io/) | 3D Gaussian Splatting の GUI ツール |
| [360° Gaussian v1.3.0](https://laskosvirtuals.gumroad.com/l/360gaussian) | Gaussian Splatting の各ステップを自動化するツール |
| [RealityScan](https://www.realityscan.com/) | 点群の再生成に使用 |
| [360-to-RealityScan](https://github.com/TakashiYoshinaga/360-to-RealityScan) | SphereSfM の結果を RealityScan で読み込める形式（.xmp）に変換するツール |

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

本記事では、Step 3 と Step 4 の間に**点群の再生成**ステップを追加します。

---

## Step 1. 撮影・動画のエクスポート

360° カメラでシーンを撮影します。処理時間が長くなる場合があるため、慣れるまでは **1 分以内の短い動画** でテストすることをおすすめします。

撮影した動画は **Equirectangular 形式** で PC にコピーしてください。  
Insta360 を使用している場合は、**Insta360 Studio**（PC 用アプリ）でエクスポートします。

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

LichtFeld を選択すると、SfM・点群生成・Gaussian Splatting まで一括で実行できます。ただし、LichtFeld Studio のウィンドウが開かない状態で処理が進むため、過程を確認できません。

筆者は処理の経過を観察したいため、以下のように設定しています。

- **Training Method**：`No Training`
- **SfM**：`SphereSFM GUT`

> **⚠️ 基本手順編との違い**  
> 基本手順編では `SphereSFM` を選択しましたが、本記事では **`SphereSFM GUT`** を使用します。お間違いのないようご注意ください。

![Alignment の設定画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/013-AlignmentSetting-02.jpg)

3.　**Advanced SphereSFM Setting** を開き、**Preset** からカメラの画像サイズを選択します  
   例：8K で撮影している場合は `Ultra (8K)` を選択

![SphereSFM の Preset 設定](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/004-SphreSfM_Setting-01.jpg)

4.　**Matcher** で `exhaustive` を選択します  
   その他の設定はデフォルトのままで問題ありません。

> **💡 Matcher の選択について**  
> `sequential` の代わりに `exhaustive` を選択すると、撮影の始点と終点付近の画像を正しく繋ぎ直す **Loop Closure** の精度が向上しやすくなります。処理時間の大幅な増加や SfM が失敗するリスクはあるものの、下記画像を参考にパラメータを細かく設定してさらに精度を高めることも可能です。  
> 筆者の推奨する設定方針は、**Iterations・Refinements は高め（High に分類される値）** に設定し、**MinInliers は低め**に保つことです。  
> Iterations と Refinements を高くすると、インライア率が低い難しいペアに対しても正しい位置関係（ジオメトリ）を見つけやすくなります。一方で MinInliers を低めに保つことで、特徴点が少なく「弱いマッチ」と判定されがちなペアも検証を通過しやすくなり、ループ接続のわずかな糸口を取りこぼしにくくなります。  
> つまり、「**丁寧に検証して（Iterations/Refinements 高め）、その結果は捨てない（MinInliers 低め）**」という組み合わせによって、Loop Closure を最大限に引き出す狙いがあります。

![SphereSFM の詳細設定例](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/005-SphreSfM_Setting-02_2.jpg)

### 2.4 SfM の実行

**Start** をクリックして SfM を実行します。  
処理が完了すると、以下のような画面が表示されます。

![SfM 完了画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/006-Complete.jpg)

カメラの位置情報と点群が正しく生成されていることを確認してください。

```
📁 動画が置かれたフォルダ
  └── 📁 動画名と同じフォルダ
       └── 📁 lichtfeld
            ├── 📁 images
            ├── 📁 masks
            ├── 📄 pointcloud.ply
            └── 📄 transforms.json
```

次のステップの準備として、**`lichtfeld`** フォルダと同じ階層に **`RealityScan`** フォルダを作成しておきます。

```
📁 動画が置かれたフォルダ
  └── 📁 動画名と同じフォルダ
       ├── 📁 lichtfeld
       │    ├── 📁 images
       │    ├── 📁 masks
       │    ├── 📄 pointcloud.ply
       │    └── 📄 transforms.json
       └── 📁 RealityScan　← 作成したフォルダ
```

---

## Step 3. 点群の再生成

ここが本記事のポイントとなるステップです。SfM で得られた結果を RealityScan に取り込み、ピンホールカメラモデルに適した点群を再生成します。

### 3.1 入出力ファイルの設定

1.　ターミナル（Python 実行環境）を開き、以下のコマンドを実行して **`spheresfm_to_realityscan.py`** を起動します

```bash
cd C:\path\to\360-to-RealityScan
python spheresfm_to_realityscan.py
```

> **📝 補足**  
> Python スクリプトの取得方法および環境設定方法については、以下のリポジトリの README を参照してください。  
> https://github.com/TakashiYoshinaga/360-to-RealityScan

2.　以下のように各パスを指定します  

| 項目 | 指定先 |
|------|--------|
| transform.json | `lichtfeld` フォルダ内の `transforms.json` |
| PLY file (optional) | `lichtfeld` フォルダ内の `pointcloud.ply` |
| Input folder (equirectangular) | `images` フォルダ |
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

![SphereSfM Converter の変換完了画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/014-SphereSfMConverter.jpg)

SfM の結果を RealityScan に取り込む準備が整いました。

> **📝 補足**  
> `transforms.json` と PLY ファイルを両方指定して実行した場合、カメラ姿勢・点群・画像情報をすべて含む完全な COLMAP 形式のデータが出力されます。  
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

**【点群データのエクスポート】**

1.　**WORKFLOW** タブの **Export** をクリックします
2.　**Export** をクリックします

![Export メニュー](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/019-RealityScanUI-05.jpg)

3.　**Sparse point cloud as Polygon File Format (*.ply)** をクリックします  
4.　`RealityScan` フォルダを選択し、適当なファイル名（例：`pointcloud.ply`）で保存します  
5.　**Exporter Setting** ダイアログの **Export transformation settings → Scene transformation** で以下を設定します  

| 項目 | 設定値 |
|------|--------|
| Rotate X | `90°` |
| Rotate Y | `0°` |
| Rotate Z | `0°` |

6.　**OK** をクリックします

![点群エクスポート設定](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/020-RealityScanUI-06.jpg)

**【カメラの位置姿勢情報を COLMAP 形式でエクスポート】**

1.　**Export** を再度クリックします  
2.　**COLMAP Text Format** をクリックします  
3.　`RealityScan` フォルダに任意のファイル名（例：`colmap`）で保存します  

> **📝 ファイル上書きに関する注意**  
> `spheresfm_to_realityscan.py` で出力された `cameras.txt`・`images.txt`・`points3D.txt` は上書きされます。上書きしても問題はありませんが、点群再生成前の COLMAP ファイルを保存しておきたい場合は、事前に別のフォルダに退避してください。

4.　**Export Dialog** で **Export images** を `No` に設定します  
5.　**Export transformation settings → Scene transformation** を開き、Rotationを以下のように設定します  

| 項目 | 設定値 |
|------|--------|
| Rotate X | `0°` |
| Rotate Y | `0°` |
| Rotate Z | `0°` |

6.　**OK** をクリックします  

![COLMAP エクスポート設定](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/021-RealityScanUI-07.jpg)

---

## Step 4. Gaussian Splatting

### 4.1 データの読み込み

1.　**LichtFeld Studio** を起動します  
2.　動画名フォルダ直下の **`RealityScan`** フォルダをウィンドウにドラッグ＆ドロップします  
3.　**Load DataSet** ダイアログが表示されたら、**Init file** で `RealityScan` フォルダ内の `pointcloud.ply` を選択します  
   ※ RealityScan による点群の再生成をスキップした場合は、Init file は空白のままで構いません  
4.　**Load** をクリックします

![LichtFeld Studio の起動画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/007-LichtFeldStudioUI-01.jpg)
![Load DataSet ダイアログ](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/022-LoadDataset.jpg)

点群と画像が正しく読み込まれたことを確認してください。  
カメラ画像の表示が不要な場合は、画面右側の **Rendering** タブにある **Camera Frustum** のチェックを外します。

![データ読み込み後の画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/009-LichtFeldStudioUI-02.jpg)

### 4.2 トレーニング設定

ここではトレーニング設定の一例を紹介します。慣れてきたらさまざまな設定を試してみてください。

1.　**Training** タブをクリックします  
2.　**Strategy** で `MCMC` を選択します  
3.　**Steps Scaler** を適宜設定します  

| 条件 | 推奨値 |
|------|--------|
| 画像数が 300 枚以下 | `1` |
| 画像数が 300 枚以上 | `画像枚数 ÷ 300` |

> **⚠️ トレーニングがうまくいかない場合**  
> 上記の設定で実行してもGaussian Splattingのトレーニングが進むにつれて収束せずにホワイトアウトしてしまう場合は、Steps Scaler を `画像枚数 ÷ 300` の **2〜3 倍** に設定すると安定しやすいです。  
> なお筆者は経験上、最初から推奨の **1.5〜2 倍**程度の値でトレーニングを始めています。


4.　**Max Gaussians** で最大ガウシアン数を設定します   
   基本的にはデフォルト値で問題ありませんが、ディテールが不足していると感じたら値を増やしてみてください。

**オプション設定：**  
Auto Maskerを使ってマスク画像を作成した場合のみ下記の設定を行います。
- **Mask Mode** → `Ignore` に設定
- **Use Alpha as Mask** → チェックを外す

![トレーニング設定画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/010-TrainingSettings.jpg)

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

屋内・屋外のさまざまなシーンで検証を重ねた結果、基本手順に少し工夫を加えるだけでクオリティを明確に向上できることが確認できました。ポイントは以下の 2 点です。

1.　**低テクスチャ領域（上下画像）の除外** によるノイズ削減  
2.　**ピンホールカメラモデルに合わせた点群の再生成** によるトレーニング精度の向上  

これらに共通する考え方として、**質の高いアウトプットには質の高いインプットが不可欠**という点が挙げられます。

- **SfM** では、高品質な入力画像と適切なマスク情報がカメラ位置推定の精度を左右します。  
- **Gaussian Splatting のトレーニング**では、その SfM の精度に加え、引き続き高品質な画像とマスクがアウトプットの品質を決定づけます。

各ステップでインプットの質を意識して整えていくことが、クオリティ向上への近道だと筆者は考えています。

本記事の手順をベースにさらなるアレンジを加えることで、より高品質な Gaussian Splatting を追求できるはずです。

### 出力サンプル

下の動画は、基本手順編よりも広域を撮影したシーンへの適用結果です。基本手順編ではトレーニングが収束せず奇麗な出力が得られませんでしたが、本記事の手法でうまく処理できました。

[![出力サンプル動画](https://img.youtube.com/vi/92ycchQSTos/0.jpg)](https://www.youtube.com/watch?v=92ycchQSTos)

> **💡 Nightly Build 版について**  
> 本記事ではリリース版の手順を紹介しましたが、LichtFeld Studio の Nightly Build 版には **LFT**（IGS+ と MCMC のハイブリッド）というモードが搭載されています。個人的には MCMC よりもおすすめですので、興味のある方はぜひ試してみてください。
