# Getting Started with 360° Image Gaussian Splatting (Basic Workflow)

## Introduction

Gaussian Splatting has been gaining attention as a method for recreating wide outdoor scenes in 3D. While related information is increasingly appearing on social media and blogs, it is scattered across many sources, making it difficult to piece together an efficient workflow. The process also requires switching between multiple applications, which can feel daunting for beginners.

In this article, I'll introduce the **minimum viable workflow** I personally use for Gaussian Splatting as a hobby.  
 All tools covered here are **free to use** (with some optional paid features), making it easy to get started even if you're new to Gaussian Splatting.  
For techniques to further improve quality, please refer to the companion article "[Quality Improvement Edition](../Advanced/article-EN.md)". Additionally, I have introduced another workflow using the paid software Agisoft Metashape in the "[Metashape Edition](../MetaShape/article-EN.md)". If you are interested, please check that out as well!

### Sample Output from This Workflow

[![Sample Video](https://img.youtube.com/vi/n-NL1UisVF4/0.jpg)](https://www.youtube.com/watch?v=n-NL1UisVF4)

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
| [LichtFeld Studio v0.5.0](https://lichtfeld.io/) | GUI tool for 3D Gaussian Splatting |
| [360° Gaussian v1.3.0](https://laskosvirtuals.gumroad.com/l/360gaussian) | Tool to automate each step of Gaussian Splatting |

---

## Overall Workflow

Gaussian Splatting generally follows these 4 steps:

| # | Process | Description |
|---|---------|-------------|
| 1 | **Capture** | Shoot the scene with a 360° camera |
| 2 | **SfM** (Structure from Motion) | Estimate the position from which each image was taken |
| 3 | **Point Cloud Generation** | Generate a point cloud based on the camera positions from SfM |
| 4 | **Gaussian Splatting** | Generate a 3D Gaussian Splatting model from the point cloud |

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
- **SfM**: `SphereSFM`

> **⚠️ Do not select `SphereSFM GUT`**  
> The workflow using `SphereSFM GUT` is covered in the companion article "Quality Improvement Edition". In this article, select `SphereSFM` (without the GUT suffix).

![Alignment Settings Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/003-AlignmentSetting-01.jpg)

3.　Open **Advanced SphereSFM Setting** and select the camera image size from **Preset**  
   Example: If shooting in 8K, select `Ultra (8K)`

![SphereSFM Preset Settings](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/004-SphreSfM_Setting-01.jpg)

4.　Select `exhaustive` for **Matcher**    
   Other settings can be left at their defaults.

> **💡 About Matcher Selection**  
> Choosing `exhaustive` over `sequential` tends to improve **Loop Closure** accuracy. For even better accuracy, you can tighten the conditions as shown in the image below, but note that this can significantly increase processing time or cause SfM to fail.

![SphereSFM Advanced Settings](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/005-SphreSfM_Setting-02.jpg)

### 2.4 Running SfM

Click **Start** to run SfM.  
When processing is complete, you'll see the following screen:

![SfM Complete Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/006-Complete.jpg)

Verify that the camera positions and point cloud have been generated correctly.

```
📁 Folder containing the video
  └── 📁 Folder with the same name as the video
       └── 📁 train_data
            ├── 📁 images
            ├── 📁 masks
            └── 📁 sparse
```

---

## Step 3. Gaussian Splatting

### 3.1 Loading Data

1.　Launch **LichtFeld Studio**  
2.　Drag and drop the **`train_data`** folder generated above into the window  
3.　When the **Load DataSet** dialog appears, click **Load**  

![LichtFeld Studio Launch Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/007-LichtFeldStudioUI-01.jpg)
![Load DataSet Dialog](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/008-LoadDataset.jpg)

Verify that the point cloud and images have been loaded correctly.  
If you don't need to see the camera images, uncheck **Camera Frustum** in the **Rendering** tab on the right side of the screen.

![After Data Loading](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/009-LichtFeldStudioUI-02.jpg)

### 3.2 Training Configuration

Here is an example training configuration. Feel free to experiment with different settings as you get more familiar.

1.　Click the **Training** tab  
2.　Select `MCMC` for **Strategy**  
3.　Set **Steps Scaler** appropriately  

| Condition | Recommended Value |
|-----------|------------------|
| 300 or fewer images | `1` |
| More than 300 images | `number of images ÷ 300` |

> **⚠️ If Training Doesn't Work**  
> If the Gaussian Splatting training fails to converge and the view whites out, setting Steps Scaler to **2–3x** the value of `number of images ÷ 300` tends to stabilize training.  
> In the author's experience, it's also common practice to start training from the beginning with a value around **1.5–2x** the recommended value.

4.　Set **Max Gaussians** for the maximum number of Gaussians  
   The default value is generally fine, but increase it if the output lacks detail.

**Optional Settings:**  
Only apply the following if you created mask images with AutoMasker.
- **Mask Mode** → Set to `Ignore`
- **Use Alpha as Mask** → Uncheck

![Training Settings Screen](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/010-TrainingSettings.jpg)

For other parameters, start with the above settings and experiment as you become more comfortable.

### 3.3 Running Training

1.　Use the mouse to zoom in on the area you want to observe during training  
   (In my example, around a bridge)  
2.　Click **Start Training** to begin  
3.　The display starts blurry but gradually becomes clearer as steps progress  

![Training in Progress](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/011-LichtFeldStudioUI-03.jpg)

Training stops automatically when the step limit is reached.  
If you want to save intermediate results, click **Save Checkpoint**.

### 3.4 Export

The exported data can be used with tools like [SuperSplat Editor](https://superspl.at/editor) for creating videos or viewing in a viewer.

1.　Click **File → Export**  
2.　Select the output format (e.g., `.ply`)  

---

## Summary

Through testing with various indoor and outdoor scenes, I've found a workflow that produces reasonably stable quality results. By tweaking the settings in this article, you should be able to achieve even higher quality Gaussian Splatting.

For an approach that takes things a step further, details are covered in the companion article "**Quality Improvement Edition**", so please check it out if you're interested.

> **💡 About the Nightly Build**  
> This article covers the release version workflow, but the Nightly Build version of LichtFeld Studio includes a mode called **LFT** (a hybrid of IGS+ and MCMC). Personally, I recommend it over MCMC, so give it a try if you're interested.
