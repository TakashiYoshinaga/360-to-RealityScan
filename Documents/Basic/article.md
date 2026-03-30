# 手軽に始める 360° 画像を用いた Gaussian Splatting（基本手順編）

## はじめに

最近屋外などの比較的広範囲のシーンを **Gaussian Splatting** で再現する手法が注目を集めています。SNS やブログで関連情報を見かける機会も増えてきましたが、情報が各所に散らばっているため、それらをうまくまとめて効率的なワークフローを構築するのは容易ではありません。さらに、複数のアプリケーションを切り替える必要があり、初心者にとってはハードルが高いと考えています。

そこで本記事では、筆者が趣味でのGaussian Splattingで運用している **ワークフローの最小構成** をご紹介します。  
本記事で紹介するツールはすべて**無料で利用可能**（一部オプション機能は有料）なため、これからGaussian Splattingを始めたい方も気軽にスタートできます。  
また、クオリティをさらに引き上げるアレンジについては、別記事「[クオリティ向上編](../Advanced/article.md)」で解説しています。さらに、有償ソフトウェアのAgisoft Metashapeを用いたワークフローについても「[Metashape編](../MetaShape/article.md)」で紹介していますので、興味がある方はこちらも併せてご覧ください。

> **📝 SfM ツールの速度に関する補足**
>
> 「無料ツールは COLMAP の CameraRig アプローチだから遅い」という声を見かけたので補足。本記事で使用している **SphereSfM** は CameraRig とは原理的に異なり、本記事で使用する**Equirectangular 画像を球面カメラモデルで直接処理する**ため、CameraRig のようにキューブマップ 6 面分のマッチングコストが発生せず速度面も改善されています。
>
> 有償ツールにアドバンテージがあることは当然ですが、まず Gaussian Splatting を体験する入口としては本記事のフリーツール構成もぜひ試してみてください。さらなるクオリティを追求したくなったら、別記事の Metashape 編もチャレンジしてみてください。

### 本記事の手順による作例

[![作例動画](https://img.youtube.com/vi/n-NL1UisVF4/0.jpg)](https://www.youtube.com/watch?v=n-NL1UisVF4)

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

---

## 全体の流れ

Gaussian Splatting では、一般的に以下の 4 つのステップを踏みます。

| # | 工程 | 内容 |
|---|------|------|
| 1 | **撮影** | 360° カメラでシーンを撮影する |
| 2 | **SfM**（Structure from Motion） | 各画像がどの位置から撮影されたかを推定する |
| 3 | **点群生成** | SfM で得られたカメラ位置をもとに点群を生成する |
| 4 | **Gaussian Splatting** | 点群をもとに 3D Gaussian Splatting モデルを生成する |

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
- **SfM**：`SphereSFM`

> **⚠️ `SphereSFM GUT` を選ばないようご注意ください**  
> `SphereSFM GUT` を使用したフローは別記事「クオリティ改善編」にて紹介しています。本記事では `SphereSFM`（末尾に GUT のないもの）を選択してください。

![Alignment の設定画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/003-AlignmentSetting-01.jpg)

3.　**Advanced SphereSFM Setting** を開き、**Preset** からカメラの画像サイズを選択します  
   例：8K で撮影している場合は `Ultra (8K)` を選択

![SphereSFM の Preset 設定](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/004-SphreSfM_Setting-01.jpg)

4.　**Matcher** で `exhaustive` を選択します  
   その他の設定はデフォルトのままで問題ありません。

> **💡 Matcher の選択について**  
> `sequential` の代わりに `exhaustive` を選択すると、**Loop Closure** の精度が向上しやすくなります。さらに精度を高めたい場合は、下記画像を参考に条件を厳しめに設定することも可能ですが、処理時間が大幅に増加したり SfM が失敗するリスクもあるためご注意ください。  
> 筆者が試した設定の方針としては、**Iterations・Refinements は高め**（High に分類される値）に設定し、**MinInliers はあまり高くしない**というものです。Iterations と Refinements を高くすると、RANSAC のサンプリング試行と最適化が多く行われるため、共通特徴点が少ない（インライア率が低い）ペアに対しても正しいジオメトリを見つけやすくなります。一方 MinInliers を低めに保つと、特徴点の共通数が少ない「弱いマッチ」もジオメトリ検証を通過しやすくなり、ループ接続の糸口となるペアを取りこぼしにくくなります。つまり「**丁寧に検証して（Iterations/Refinements 高め）、その結果は捨てない（MinInliers 低め）**」という組み合わせで、ループクロージャを最大限に拾いにいく方針です。

![SphereSFM の詳細設定例](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/005-SphreSfM_Setting-02.jpg)

### 2.4 SfM の実行

**Start** をクリックして SfM を実行します。  
処理が完了すると、以下のような画面が表示されます。

![SfM 完了画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/006-Complete.jpg)

カメラの位置情報と点群が正しく生成されていることを確認してください。

```
📁 動画が置かれたフォルダ
  └── 📁 動画名と同じフォルダ
       └── 📁 train_data
            ├── 📁 images
            ├── 📁 masks
            └── 📁 sparse
```

---

## Step 3. Gaussian Splatting

### 3.1 データの読み込み

1.　**LichtFeld Studio** を起動します  
2.　上記で生成された **`train_data`** フォルダをウィンドウにドラッグ＆ドロップします  
3.　**Load DataSet** ダイアログが表示されたら **Load** をクリックします  

![LichtFeld Studio の起動画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/007-LichtFeldStudioUI-01.jpg)
![Load DataSet ダイアログ](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/008-LoadDataset.jpg)

点群と画像が正しく読み込まれたことを確認してください。  
カメラ画像の表示が不要な場合は、画面右側の **Rendering** タブにある **Camera Frustum** のチェックを外します。

![データ読み込み後の画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/009-LichtFeldStudioUI-02.jpg)

### 3.2 トレーニング設定

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

### 3.3 トレーニングの実行

1.　マウス操作で、トレーニングの経過を観察したいエリアにクローズアップしておきます  
   （筆者の例では橋の周辺）   
2.　**Start Training** をクリックしてトレーニングを開始します  
3.　最初はぼんやりとした表示ですが、ステップが進むにつれて徐々にクリアになっていきます  

![トレーニング中の画面](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/011-LichtFeldStudioUI-03.jpg)

トレーニングステップが上限に達すると自動で終了します。  
途中経過を保存しておきたい場合は、**Save Checkpoint** をクリックするとその時点の結果を記録できます。

### 3.4 エクスポート
出力したデータは [SuperSplat Editor](https://superspl.at/editor) などのツールを使って、動画作成やビューワーでの閲覧に活用できます。  
1.　**File → Export** をクリックします  
2.　出力フォーマットを選択します（例：`.ply`）  

---

## まとめ

屋内・屋外のさまざまなシーンで検証を重ねた結果、ある程度安定した品質で再現できるワークフローをご紹介しました。本記事の手順をベースに設定をアレンジすることで、さらに高品質な Gaussian Splatting を作成できるはずです。

また、本記事の手順にもうひと手間加えることで、さらにクオリティを引き上げる方法も確認しています。詳細は別記事「**クオリティ改善編**」にまとめますので、興味のある方はぜひチェックしてみてください。

> **💡 Nightly Build 版について**  
> 本記事ではリリース版の手順を紹介しましたが、LichtFeld Studio の Nightly Build 版には **LFT**（IGS+ と MCMC のハイブリッド）というモードが搭載されています。個人的には MCMC よりもおすすめですので、興味のある方はぜひ試してみてください。
