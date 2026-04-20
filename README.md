# 360-to-RealityScan
A tool for converting SfM results from [360° Gaussian](https://laskosvirtuals.gumroad.com/l/360gaussian) into RealityScan compatible images/XMP and COLMAP format for verification. Features automatic splitting, pose calculation, and mask support.

[日本語版はこちら](README_JP.md)

---

## Download

Choose one of the following methods to get this repository:

- **Download ZIP**: Click **Code → Download ZIP** at the top of the GitHub page and extract it to any folder.  
  or
- **Clone with Git**: Use the GitHub desktop app or run the following command:

```
git clone https://github.com/TakashiYoshinaga/360-to-RealityScan.git
```

---

## Setup

### 1. Install Anaconda

Download and install Anaconda from the page below.

https://www.anaconda.com/download

### 2. Create a Virtual Environment

1. Launch **Anaconda Navigator**
2. Click **Environments** in the left menu
3. Click **Create** at the bottom

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/023-Anaconda.jpg)

4. In the **Create new environment** dialog, configure the following:
   - **Name**: Any name (e.g. `gs_env`)
   - **Python**: Select version 3.10 or higher
5. Click **Create**

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/024-CreateNewEnvironment.jpg)

### 3. Install Required Libraries

#### Install NumPy

1. Click the environment you just created (e.g. `gs_env`)
2. Select **Not installed** from the dropdown menu

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/025-LibInstall.jpg)

3. Search for `numpy`
4. Check the **numpy** entry in the list
5. Click **Apply**

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/026-NumPyInstall.jpg)

#### Install FFmpeg

1. Search for `ffmpeg` in the same way
2. Check the **ffmpeg** entry in the list
3. Click **Apply**

---

## Running the Script

### Open a Terminal

1. Click the play button next to the environment name (e.g. `gs_env`) in Anaconda Navigator
2. Click **Open Terminal**

![](https://raw.githubusercontent.com/TakashiYoshinaga/360-to-RealityScan/main/Documents/Images/027-RunTerminal.jpg)

### Run the Script

1. Navigate to the folder containing the script

```
cd C:\path\to\360-to-RealityScan
```

> **💡 Tip**  
> You can also type `cd` followed by a space and then drag and drop the `360-to-RealityScan` folder into the terminal window to fill in the path automatically.

2. Run the script

```
python spheresfm_to_realityscan.py
```

The GUI will launch.

---

## How to Use the Script

### Configure Input / Output Paths

Once the GUI launches, specify each path as follows:

| Field | Target |
|-------|--------|
| transform.json | `transforms.json` inside the `lichtfeld` folder |
| PLY file (optional) | `pointcloud.ply` inside the `lichtfeld` folder |
| Input folder (equirectangular) | `images` folder containing equirectangular images |
| Mask folder (equirectangular, optional) | `masks` folder containing mask images |
| Output folder | Destination folder (e.g. `RealityScan`) |

### Split Settings

The defaults work fine in most cases.

| Parameter | Description |
|-----------|-------------|
| Additional Pitch Angles | The equator (vertical center of the image = 0°) is always included automatically. To also crop directions tilted up or down from the center of the equirectangular image, enter angles as comma-separated values (e.g. `-45,45` adds 45° above and 45° below center). Leave blank to crop the equatorial direction only |
| Split Count (Equator) | Number of splits along the equator. Default is `6`; set to `4` for cube map sides only |

### Run Conversion

Click **Start Conversion** to begin.

When conversion completes, the following files and folders will be created in the output folder (e.g. `RealityScan`):

```
RealityScan/
├── all/
├── images/
├── masks/
├── cameras.txt
├── images.txt
└── points3D.txt  ← Generated only when a PLY file is specified
```

> **📝 Note**  
> When both `transforms.json` and a PLY file are specified, a complete COLMAP-format dataset including camera poses, point cloud, and image information will be output.

---

## Advanced Usage

For instructions on integrating this tool into a full Gaussian Splatting workflow, refer to the articles below:

- [SphereSfM](Documents/Advanced/article-EN.md)
- [MetaShape](Documents/MetaShape/article-EN.md)

---

## Building Executables (for Developers)

You can build Windows executables from source using the provided PowerShell script.

### Prerequisites

- [Anaconda](https://www.anaconda.com/download) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- A conda environment with **Python 3.10+** and **NumPy** installed (see [Setup](#setup) above)
- **ffmpeg is NOT bundled** in the exe (license reasons). Users set the path manually in the GUI.  
  Download ffmpeg for Windows from: https://github.com/BtbN/FFmpeg-Builds/releases

### Build

Open PowerShell and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\Build\build.ps1
```

If your conda environment name is not `gs_env`, specify it with `-CondaEnv`:

```powershell
.\Build\build.ps1 -CondaEnv myenv
```

You can also build only one tool at a time:

```powershell
.\Build\build.ps1 -Target metashape   # MetashapeToRS.exe only
.\Build\build.ps1 -Target spheresfm   # SphereSfMToRS.exe only
```

Output files are placed in `Build\dist\`:

| File | Source |
|------|--------|
| `MetashapeToRS.exe` | `Build\metashape_to_realityscan.py` |
| `SphereSfMToRS.exe` | `Build\spheresfm_to_realityscan.py` |

> conda is detected automatically from PATH or common installation locations.  
> PyInstaller is installed automatically if not already present.

