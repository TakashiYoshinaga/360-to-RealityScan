# Getting Started with 360° Image Gaussian Splatting (Quality Improvement Edition)

## Introduction

Gaussian Splatting has been gaining attention as a method for recreating wide outdoor scenes in 3D. While related information is increasingly appearing on social media and blogs, it is scattered across many sources, making it difficult to build an efficient workflow.

In the [previous article (Basic Workflow)](../Basic/article-EN.md), I introduced the minimum viable workflow I use for Gaussian Splatting as a hobby, built entirely around free-to-use tools. This time, I'll explain how to further improve quality with just a **few small tweaks** to that workflow. Additionally, for a workflow using the paid software Agisoft Metashape, please refer to the "[Metashape Edition](../MetaShape/article-EN.md)" if you are interested.

> **💡 Before You Start**  
> This article includes a step that involves running a Python script. If you're new to Gaussian Splatting or unfamiliar with Python, I recommend working through the [Basic Workflow](../Basic/article-EN.md) first to get a feel for the overall process before tackling this one.

### Output Comparison with the Basic Workflow

The image below compares the output from the basic workflow and this article's approach. You can see that tile seams and object outlines are reproduced more clearly.

![Basic vs Quality Improvement Comparison](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/012-BeforeAfter.jpg)

> **📝 Note**  
> This article is written so it can be followed independently, so some sections overlap with the previous article. Please keep this in mind.

---

## Differences from the Basic Workflow

Here's a summary of the main changes for those who have already read the previous article.

**Basic Workflow (previous):**  
Generate SfM and a point cloud from Equirectangular images → Feed the Cube Map split images directly into the Gaussian Splatting GUI tool

**Quality Improvement Edition (this article):**  
After generating SfM and a point cloud from Equirectangular images, the following steps are added:

1.　**Excluding top and bottom images** — When splitting into multiple viewpoints, images showing mostly sky or ground are excluded. This reduces low-texture regions that can cause noise.  
2.　**Point cloud regeneration** — The point cloud is recalculated from the extracted images. By generating a point cloud that matches the **pinhole camera model** used during Gaussian Splatting training (rather than the Equirectangular model used during SfM), noise factors during training are eliminated.  

> **⚠️ Prerequisites**  
> This article assumes that the 360° camera is held **nearly vertical** during shooting.

---

## Environment

### PC Specs

| Item | Spec |
|------|------|
| OS | Windows 11 |
| GPU | NVIDIA GeForce RTX 4070 SUPER |
| CPU | AMD Ryzen7 8700G |
| RAM | 32 GB |

### 360° Camera

- **Insta360 X4 Air**  
  ※ Other manufacturers' cameras such as THETA are also supported. **8K or higher** is recommended.

### Software

| Software | Purpose |
|----------|---------|
| [LichtFeld Studio v0.5.1](https://lichtfeld.io/) | GUI tool for 3D Gaussian Splatting |
| [360° Gaussian v1.4.2](https://laskosvirtuals.gumroad.com/l/360gaussian) | Tool to automate each step of Gaussian Splatting (Updated: April 8, 2026) |
| [RealityScan](https://www.realityscan.com/) | Used for point cloud regeneration |
| [360-to-RealityScan](https://github.com/TakashiYoshinaga/360-to-RealityScan) | Converts SphereSfM results into a format readable by RealityScan (.xmp) |

### Other

- **Python environment** (for 360-to-RealityScan)  
  e.g., Anaconda

---

## Overall Workflow

Gaussian Splatting generally follows these steps:

| # | Process | Description |
|---|---------|-------------|
| 1 | **Capture** | Shoot the scene with a 360° camera |
| 2 | **SfM** (Structure from Motion) | Estimate the position from which each image was taken |
| 3 | **Point Cloud Generation** | Generate a point cloud based on the camera positions from SfM |
| 4 | **Gaussian Splatting** | Generate a 3D Gaussian Splatting model from the point cloud |

In this article, a **point cloud regeneration** step is added between Step 3 and Step 4.

---

## Step 1. Capturing & Exporting the Video

Capture the scene with your 360° camera. Since processing can take a long time, it's recommended to start with **videos under 1 minute** until you get familiar with the workflow.

Export the captured video in **Equirectangular format** and copy it to your PC.  
If you're using an Insta360, export it using **Insta360 Studio** (the PC application).

> **⚠️ Note on Stabilization**  
> Stabilization can be ON or OFF, but if you turn it **ON**, make sure to disable the following:  
> - Horizon Leveling  
> - Tilt Recovery  
> - Vibration Reduction  

> **💡 Tip**  
> With stabilization ON, the camera automatically corrects for tilt. Strictly speaking, the slight distortion introduced by this correction can become a source of noise in later processing — but if you just want to get started without worrying about that, turning stabilization ON is totally fine.

![Stabilization Settings Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/000-stabilization.jpg)

---

## Step 2. SfM and Point Cloud Generation

This step uses **360° Gaussian**.  
Because 360° Gaussian supports multiple tools for both SfM and Gaussian Splatting, it makes it easy to compare and test different combinations of tools and methods.  
For detailed usage, refer to the following videos:

- 📺 [Basic Tutorial](https://www.youtube.com/watch?v=XcmmxKbjESQ)  
- 📺 [Additional Features Tutorial](https://www.youtube.com/watch?v=FDEUAn8FjSk)

### 2.1 Image Extraction

1.　Launch **360° Gaussian**  
2.　Click **Add Video(s)** and select the Equirectangular video  
3.　Select **Splitting** and configure the extraction settings  

| Parameter | Description |
|-----------|-------------|
| Extra frame every | Extract images at the specified interval (seconds or frames) |
| Sharp frame extraction | Whether to prioritize less blurry images compared to adjacent frames |
| Sharpness check range | E.g., `10` compares ±5 frames to select the sharpest image |

![360° Gaussian Splitting Settings](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/001-360GaussianUI-01.jpg)

### 2.2 Image Masking (Optional)

**AutoMasker** is a tool that automatically masks regions that are unnecessary for Gaussian Splatting.

> **ℹ️ This step is optional**  
> If you are not using AutoMasker, skip ahead to [2.3 SfM Configuration](#23-sfm-configuration).

1.　Click **AutoMasker**  
2.　Enable **Use AutoMasker**  
3.　Enter keywords in **Detection Keywords** separated by periods (`.`)  
   Example: `person.sky`

![AutoMasker Result](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/002-MaskImage.jpg)

> **💡 Two Reasons Why Masking Matters**  
> First, subjects that move or lack distinct features — such as people, vehicles, and low-texture objects — introduce **noise into the SfM process**, reducing the accuracy of camera pose estimation. Since SfM accuracy directly impacts the quality of the Gaussian Splatting output, masking these subjects out is essential.  
> Second, **the same noise degrades quality during the training stage as well**. When the same subject appears with a different appearance across frames, the Gaussians struggle to converge to the correct shape and color. Masking protects quality at both stages of the pipeline.  
> 📺 [Reference Video](https://youtu.be/XcmmxKbjESQ?si=wPF74IBWmgV6mpxk&t=59)

> **📝 About AutoMasker**  
> AutoMasker is a paid tool (46€), but since it runs as a standalone application, it can be used not only within the 360° Gaussian Splatting automation workflow, but also for general 360° image masking tasks outside of Gaussian Splatting.  
> It offers better value than purchasing a similar tool, and is well worth considering.  
> For setup instructions to integrate it with 360° Gaussian after purchase, refer to [this video](https://youtu.be/9g8wO_8jdKs?si=wNln9pvP2_7A2DSE&t=99).

### 2.3 SfM Configuration

1.　Click **Alignment**  
2.　Configure **Training Method**  

Selecting LichtFeld will run SfM, point cloud generation, and Gaussian Splatting all at once, but the LichtFeld Studio window won't open during processing, so you cannot observe the progress.

My preferred settings are:

- **Training Method**: `No Training`
- **SfM**: `SphereSFM GUT`

> **⚠️ Difference from the Basic Workflow**  
> The Basic Workflow uses `SphereSFM`, but this article uses **`SphereSFM GUT`**. Please make sure to select the correct one.

![Alignment Settings Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/013-AlignmentSetting-02.jpg)

3.　Open **Advanced SphereSFM Setting** and select the camera image size from **Preset**  
   Example: If shooting in 8K, select `Ultra (8K)`

![SphereSFM Preset Settings](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/004-SphreSfM_Setting-01.jpg)

4.　Select `sequential` for **Matcher**  
Since v1.4.0, Loop detection with vocabulary tree is now supported, significantly improving loop closing performance.  
Other settings can be left at their defaults.  
As a reference, below is a practical settings example that the author often uses:

![SphereSFM Settings Example (v1.4.0)](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/037-SphereSfM_Setting_140_3.jpg)

<br>
<details>
<summary>💡 If sequential doesn't work: Try exhaustive as a last resort (Click to expand)</summary>

If `sequential` doesn't produce good results, `exhaustive` is an option to try as a last resort. It matches all image pairs exhaustively, which significantly increases processing time, but may cover pairs that `sequential` failed to connect.

As an example, here are the settings the author typically uses for shooting relatively large areas:  
![SphereSFM Advanced Settings](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/005-SphreSfM_Setting-02_5.jpg)  
Note: This configuration increases the number of computation iterations compared to the default settings and may take more time. We recommend starting with the default settings first.  

The author's recommended configuration strategy is as follows:

1. **Iterations(Global) and Refinements (Always High)**
   - Setting these high makes it easier to find the correct geometry even for difficult image pairs with a low inlier ratio.
2. **MinInliers (Minimum Inlier Count)**
   - **Large-scale areas (Low)**: Keep this low. This allows pairs with few feature points—often judged as "weak matches"—to pass verification more easily, ensuring you don't miss the slight clues needed for loop connections.
   - **(Note) Small areas (High)**: Since feature points match consistently across images, setting this intentionally higher ensures only "reliable matches" are adopted. This eliminates erroneous matches and results in higher accuracy.
3. **Reprojection threshold**
   - **Large-scale areas (Loose)**: Changes in lighting, weather, and perspective can cause major viewpoint differences between the start and end of a loop. If the threshold is strict here, sparse matches will be rejected, preventing the loop from closing (connecting). Therefore, easing the tolerance to match the scene's variability is the standard approach.
   - **(Note) Small areas (Strict)**: Because viewpoint changes are minor and feature points are stable, you can afford to use a **stricter (tighter)** threshold. This helps eliminate noise and allows for higher precision camera pose estimation.

In short, for large-scale scans, the combination of "**verify thoroughly (High Iterations(Global)/Refinements), don't discard the results (Low MinInliers), and ease the tolerance in response to spatial diversity (Loose Reprojection threshold)**" is designed to maximize the success rate of SfM.

</details>
<br>  


### 2.4 Running SfM

Click **Start** to run SfM.  
When processing is complete, you'll see the following screen:

![SfM Complete Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/006-Complete.jpg)

Verify that the camera positions and point cloud have been generated correctly.

```
📁 Folder containing the video
  └── 📁 Folder with the same name as the video
       └── 📁 lichtfeld
            ├── 📁 images
            ├── 📁 masks
            ├── 📄 pointcloud.ply
            └── 📄 transforms.json
```

In preparation for the next step, create a **`RealityScan`** folder at the same level as the **`lichtfeld`** folder.

```
📁 Folder containing the video
  └── 📁 Folder with the same name as the video
       ├── 📁 lichtfeld
       │    ├── 📁 images
       │    ├── 📁 masks
       │    ├── 📄 pointcloud.ply
       │    └── 📄 transforms.json
       └── 📁 RealityScan　← folder you just created
```

---

## Step 3. Point Cloud Regeneration

This is the key step in this article. The SfM results are imported into RealityScan to regenerate a point cloud suited to the pinhole camera model.

### 3.1 Input/Output File Configuration

1.　Open a terminal (Python environment) and run the following command to launch **`spheresfm_to_realityscan.py`**:

```bash
cd C:\path\to\360-to-RealityScan
python spheresfm_to_realityscan.py
```

> **📝 Note**  
> For instructions on how to obtain the script and set up the environment, refer to the README in the repository below.  
> https://github.com/TakashiYoshinaga/360-to-RealityScan

2.　Specify each path as follows:  

| Item | Target |
|------|--------|
| transform.json | `transforms.json` inside the `lichtfeld` folder |
| PLY file (optional) | `pointcloud.ply` inside the `lichtfeld` folder |
| Input folder (equirectangular) | `images` folder |
| Mask folder (equirectangular, optional) | `masks` folder |
| Output folder | the `RealityScan` folder you created |

### 3.2 Split Settings

The default settings are generally fine.

| Parameter | Description |
|-----------|-------------|
| Additional Pitch Angles | The equator (vertical center of the image = 0°) is always included automatically. To also crop directions tilted up or down from the center of the equirectangular image, enter angles as comma-separated values (e.g. `-45,45` adds 45° above and 45° below center). Leave blank to crop the equatorial direction only |
| Split Count (Equator) | Number of splits along the equator. Default is `6`; setting to `4` extracts only the side faces of the Cube Map |

> **💡 Note on Additional Pitch Angles**  
> Depending on the scene, adding upward and downward views can improve the quality of the Gaussian Splatting output. For example, if the floor or ceiling has distinctive textures or patterns, try adding `-45,45` to include tilted angles.

### 3.3 Running the Conversion

Click **Start Conversion** to start the conversion.  
When complete, you'll see the following screen:

![SphereSfM Converter Completion Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/014-SphereSfMConverter_3.jpg)

The SfM results are now ready to be imported into RealityScan.

> **📝 Note**  
> If you specify both `transforms.json` and the PLY file, the output will include complete COLMAP-format data containing camera poses, a point cloud, and image information.  
> If you prefer to skip point cloud regeneration in RealityScan and use the images split by this tool directly for Gaussian Splatting, proceed to **Step 4. Gaussian Splatting**.

### 3.4 Point Cloud Generation in RealityScan

1.　Launch **RealityScan**  
2.　Click the **WORKFLOW** tab  
3.　Click **Folder** and select the **`all`** folder inside the `RealityScan` folder  
4.　Open **Inputs** and press `Ctrl + A` to select all images  

![RealityScan Inputs Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/015-RealityScanUI-01.jpg)

5.　Configure the detail settings as follows:  

| Category | Item | Value |
|----------|------|-------|
| **Prior pose** | Absolute pose | `Locked` |
| **Prior calibration** | Calibration group | `0` (same settings for all cameras) |
| | Prior | `Fixed` (fixed field of view) |
| **Prior lens distortion** | Lens group | `0` (same settings for all cameras) |
| | Prior | `Fixed` (fixed distortion) |

![RealityScan Detail Settings](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/016-RealityScanUI-02.jpg)

6.　Click the **ALIGNMENT** tab  
7.　Click **Align Images**  

![Align Images Execution](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/017-RealityScanUI-03.jpg)

When processing is complete, the regenerated point cloud will be displayed.

![Regenerated Point Cloud](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/018-RealityScanUI-04.jpg)

### 3.5 Export

**[Export Camera Pose Information and Point Cloud in COLMAP Format]**

1.　Click the **WORKFLOW** tab  
2.　Click **Export**  
3.　Click **COLMAP**  
4.　Save to the `RealityScan` folder with any file name (e.g., `colmap`)  

> **📝 Note on File Overwriting**  
> The `cameras.txt`, `images.txt`, and `points3D.txt` output by `spheresfm_to_realityscan.py` will be overwritten. This is fine, but if you want to keep the COLMAP files from before regeneration, move them to a separate folder beforehand.

5.　In the **Export Dialog**, set **Directory structure** to `Flat`  
6.　Set **Export masks** to `No`  
7.　Temporarily set **Export images** to `Yes`  
8.　The **Export image setting** will appear  
9.　Set **Image format** to `jpg`  
10.　Set **Naming convention** to `original file name`  
11.　Set **Export images** back to `No`  
12.　Click **OK**  

![COLMAP Export Settings](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/021-RealityScanUI-07_2.jpg)

> **💡 Hint**  
> The `all` folder and its images are used exclusively for processing within RealityScan. Therefore, you can safely delete them once the export is complete and they are no longer needed. If you ever need them again, you can always regenerate them by re-running `spheresfm_to_realityscan.py`.

---

## Step 4. Gaussian Splatting

### 4.1 Loading Data

1.　Launch **LichtFeld Studio**  
2.　Drag and drop the **`RealityScan`** folder (directly under the video name folder) into the window  
3.　When the **Load DataSet** dialog appears, click **Load**  

![LichtFeld Studio Launch Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/007-LichtFeldStudioUI-01.jpg)
![Load DataSet Dialog](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/008-LoadDataset_2.jpg)

Verify that the point cloud and images have been loaded correctly.  
If you don't need to see the camera images, uncheck **Camera Frustum** in the **Rendering** tab on the right side of the screen.

![After Data Loading](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/009-LichtFeldStudioUI-02.jpg)

### 4.2 Training Configuration

Here is an example training configuration. Feel free to experiment with different settings as you get more familiar.

1.　Click the **Training** tab  
2.　Select `MRNF` for **Strategy**  
3.　Set **Steps Scaler** appropriately  

| Condition | Recommended Value |
|-----------|------------------|
| 300 or fewer images | `1` |
| More than 300 images | `number of images / 300` |

> **⚠️ If Training Doesn't Work**  
> If the Gaussian Splatting training fails to converge and the view whites out, setting Steps Scaler to **2–3x** the value of `number of images / 300` tends to stabilize training.

4.　Set **Max Gaussians** for the maximum number of Gaussians  
   The default value is generally fine, but increase it if the output lacks detail.

**Optional Settings:**  
Only apply the following if you created mask images with AutoMasker.
- **Mask Mode** → Set to `Ignore`
- **Use Alpha as Mask** → Uncheck

![Training Settings Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/010-TrainingSettings_2.jpg)

For other parameters, start with the above settings and experiment as you become more comfortable.

### 4.3 Running Training

1.　Use the mouse to zoom in on the area you want to observe during training  
   (In my example, around a bridge)  
2.　Click **Start Training** to begin  
3.　The display starts blurry but gradually becomes clearer as steps progress  

![Training in Progress](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/011-LichtFeldStudioUI-03.jpg)

Training stops automatically when the step limit is reached.  
If you want to save intermediate results, click **Save Checkpoint**.

### 4.4 Export

The exported data can be used with tools like [SuperSplat Editor](https://superspl.at/editor) for creating videos or viewing in a viewer.

1.　Click **File → Export**  
2.　Select the output format (e.g., `.ply`)  

---

## Summary

Through testing with various indoor and outdoor scenes, I've confirmed that adding just a few steps to the basic workflow can produce a clear improvement in quality. The key points are:

1.　**Reducing noise by excluding low-texture regions** (top and bottom images)  
2.　**Improving training accuracy by regenerating a point cloud matched to the pinhole camera model**  

Underlying both of these is a fundamental principle: **high-quality output requires high-quality input**.

- **In SfM**, the quality of the input images and the accuracy of the mask information directly determine how well camera poses can be estimated.  
- **In Gaussian Splatting training**, the accuracy of the SfM results — along with continued use of high-quality images and masks — determines the quality of the final output.

Being mindful of input quality at each step is, in my view, the most reliable path to better results.

By building on this article's workflow with further adjustments, you should be able to pursue even higher quality Gaussian Splatting results.

### Sample Output

The video below shows the result of applying this workflow to a wider area than covered in the Basic Workflow edition. The Basic Workflow approach failed to converge during training and did not produce a clean output, but this quality improvement method succeeded.

[![Sample Output Video](https://img.youtube.com/vi/92ycchQSTos/0.jpg)](https://www.youtube.com/watch?v=92ycchQSTos)

