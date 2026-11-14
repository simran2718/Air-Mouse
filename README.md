# ⚡ AIR-MOUSE PRO | AI-Powered Touchless HCI System

> **"An ordinary pen. An ordinary webcam. An extraordinary way to control a computer."**

**AIR-MOUSE PRO** is a real-time Computer Vision and Human-Computer Interaction (HCI) desktop application built in Python. It transforms any ordinary colored pen into a wireless touchless computer mouse using only a standard webcam—requiring no external sensors or specialized hardware.

---

## 🚀 Key Features

* **Precision Air Cursor Control:** Tracks pen tip coordinates in real time and maps them smoothly to the full screen using linear interpolation (`np.interp`) and a custom **One Euro Adaptive Filter** (zero lag on fast movements, rock-solid stability when stationary).
* **Smart Dwell Click System:** Hands-free Left-Click, Right-Click, Double-Click, and Drag-and-Drop triggered by holding the pen steady with a live visual progress ring and cooldown safeguard.
* **Multi-Mode Interaction Switcher:**
  * 🖱️ **Air Mouse Mode:** Full cursor navigation and dwell clicking.
  * 🎨 **Air Drawing Studio:** Draw in mid-air with 4 neon brush colors, eraser, canvas clear, and PNG export.
  * 📊 **Presentation Control Mode:** Navigate PowerPoint slides (`Next` / `Previous`) using mid-air swipe gestures.
  * ↕️ **Smart Scroll Mode:** Hands-free vertical scrolling using upper/lower active zones.
* **Futuristic Dark-Mode Dashboard (`PySide6`):** Multi-threaded GUI displaying live webcam tracking, HSV mask toggle, real-time FPS, processing latency (`ms`), confidence score, persistent JSON calibration (`config.json`), and CSV benchmark export.

---

## 🏗️ Modular System Architecture

```text
Air-Mouse/
├── config.json              # Persistent HSV color & filter calibration settings
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
└── modules/
    ├── __init__.py
    ├── filters.py           # OneEuroFilter adaptive signal smoothing
    ├── vision_tracker.py    # HSV segmentation, noise removal & sub-pixel tip detection
    ├── action_handler.py    # OS mouse automation, dwell click, drawing & PPT logic
    ├── engine_thread.py     # Multi-threaded QThread pipeline & latency logger
    └── dashboard_ui.py      # PySide6 dark-mode desktop interface