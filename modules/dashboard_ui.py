import json
import cv2
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QGroupBox, QGridLayout, QFileDialog
)
from modules.engine_thread import VisionEngine


class AirMouseDashboard(QMainWindow):
    def __init__(self, config_path="config.json"):
        super().__init__()
        self.config_path = config_path
        self.config = self.load_config()

        self.setWindowTitle("AIR-MOUSE PRO v2.0 | Modular Touchless HCI System")
        self.setMinimumSize(1220, 740)

        self.engine = VisionEngine(self.config)
        self.engine.frame_ready.connect(self.update_video)
        self.engine.telemetry_ready.connect(self.update_telemetry)

        self.init_ui()
        self.engine.start()

    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_config(self):
        updated = {
            "h_min": self.engine.h_min,
            "s_min": self.engine.s_min,
            "v_min": self.engine.v_min,
            "h_max": self.engine.h_max,
            "s_max": self.engine.s_max,
            "v_max": self.engine.v_max,
            "smoothening": self.engine.smoothening,
            "frame_margin": self.engine.frame_margin,
            "dwell_time_req": self.engine.dwell_time_req
        }
        with open(self.config_path, "w") as f:
            json.dump(updated, f, indent=4)
        self.engine.last_event_text = "Calibration Saved to config.json!"

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0d1117;
                color: #e6edf3;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: bold;
                color: #58a6ff;
                background-color: #161b22;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #c9d1d9;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #58a6ff;
            }
            QPushButton:checked {
                background-color: #1f6feb;
                color: #ffffff;
                border-color: #58a6ff;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #30363d;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #58a6ff;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # LEFT PANEL
        left_layout = QVBoxLayout()
        header = QLabel("⚡ AIR-MOUSE PRO : MODULAR HCI COMMAND CENTER")
        header.setFont(QFont("Segoe UI", 15, QFont.Bold))
        header.setStyleSheet("color: #58a6ff; padding: 4px;")
        left_layout.addWidget(header)

        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)
        self.video_label.setStyleSheet("border: 2px solid #58a6ff; border-radius: 10px; background-color: #000;")
        self.video_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.video_label)

        perf_box = QGroupBox("📊 Live Performance & Latency Telemetry")
        perf_grid = QGridLayout()

        self.lbl_fps = QLabel("FPS: 0 | Latency: 0 ms")
        self.lbl_coords = QLabel("Pen Coords: X: 0, Y: 0")
        self.lbl_conf = QLabel("Confidence: 0%")
        self.lbl_status = QLabel("Status: INITIALIZING")
        self.lbl_mode = QLabel("Active Mode: MOUSE")
        self.lbl_event = QLabel("Last Event: None")

        for lbl in [self.lbl_fps, self.lbl_coords, self.lbl_conf, self.lbl_status, self.lbl_mode, self.lbl_event]:
            lbl.setFont(QFont("Consolas", 9, QFont.Bold))
            lbl.setStyleSheet("color: #3fb950; background-color: #0d1117; padding: 6px; border-radius: 4px;")

        perf_grid.addWidget(self.lbl_fps, 0, 0)
        perf_grid.addWidget(self.lbl_coords, 0, 1)
        perf_grid.addWidget(self.lbl_conf, 0, 2)
        perf_grid.addWidget(self.lbl_status, 1, 0)
        perf_grid.addWidget(self.lbl_mode, 1, 1)
        perf_grid.addWidget(self.lbl_event, 1, 2)
        perf_box.setLayout(perf_grid)
        left_layout.addWidget(perf_box)

        main_layout.addLayout(left_layout)

        # RIGHT PANEL
        right_layout = QVBoxLayout()

        # 1. Interaction Mode Switcher
        mode_box = QGroupBox("🎮 Multi-Mode Interaction Switcher")
        mode_grid = QGridLayout()

        self.btn_mouse = QPushButton("🖱️ Air Mouse")
        self.btn_draw = QPushButton("🎨 Air Drawing")
        self.btn_ppt = QPushButton("📊 PPT Control")
        self.btn_scroll = QPushButton("↕️ Smart Scroll")
        self.btn_pause = QPushButton("⏸️ Pause / Override")

        self.mode_buttons = [self.btn_mouse, self.btn_draw, self.btn_ppt, self.btn_scroll, self.btn_pause]
        for btn in self.mode_buttons:
            btn.setCheckable(True)
        self.btn_mouse.setChecked(True)

        self.btn_mouse.clicked.connect(lambda: self.change_mode("MOUSE", self.btn_mouse))
        self.btn_draw.clicked.connect(lambda: self.change_mode("DRAW", self.btn_draw))
        self.btn_ppt.clicked.connect(lambda: self.change_mode("PPT", self.btn_ppt))
        self.btn_scroll.clicked.connect(lambda: self.change_mode("SCROLL", self.btn_scroll))
        self.btn_pause.clicked.connect(lambda: self.change_mode("PAUSED", self.btn_pause))

        mode_grid.addWidget(self.btn_mouse, 0, 0)
        mode_grid.addWidget(self.btn_draw, 0, 1)
        mode_grid.addWidget(self.btn_ppt, 1, 0)
        mode_grid.addWidget(self.btn_scroll, 1, 1)
        mode_grid.addWidget(self.btn_pause, 2, 0, 1, 2)
        mode_box.setLayout(mode_grid)
        right_layout.addWidget(mode_box)

        # 2. Dwell Click Actions
        click_box = QGroupBox("👆 Smart Dwell Click Action")
        click_layout = QHBoxLayout()

        self.btn_left = QPushButton("Left Click")
        self.btn_right = QPushButton("Right Click")
        self.btn_double = QPushButton("Double Click")
        self.btn_drag = QPushButton("Drag & Drop")

        self.click_buttons = [self.btn_left, self.btn_right, self.btn_double, self.btn_drag]
        for btn in self.click_buttons:
            btn.setCheckable(True)
            click_layout.addWidget(btn)
        self.btn_left.setChecked(True)

        self.btn_left.clicked.connect(lambda: self.change_click("LEFT", self.btn_left))
        self.btn_right.clicked.connect(lambda: self.change_click("RIGHT", self.btn_right))
        self.btn_double.clicked.connect(lambda: self.change_click("DOUBLE", self.btn_double))
        self.btn_drag.clicked.connect(lambda: self.change_click("DRAG", self.btn_drag))

        click_box.setLayout(click_layout)
        right_layout.addWidget(click_box)

        # 3. Air Drawing Studio
        draw_box = QGroupBox("🖌️ Air Drawing Studio Controls")
        draw_grid = QGridLayout()

        btn_yellow = QPushButton("🟡 Yellow")
        btn_green = QPushButton("🟢 Green")
        btn_red = QPushButton("🔴 Red")
        btn_cyan = QPushButton("🔵 Cyan")
        btn_eraser = QPushButton("🧽 Eraser")
        btn_clear = QPushButton("🗑️ Clear")
        btn_save = QPushButton("💾 Save PNG")

        btn_yellow.clicked.connect(lambda: self.set_brush((0, 255, 255), False))
        btn_green.clicked.connect(lambda: self.set_brush((0, 255, 0), False))
        btn_red.clicked.connect(lambda: self.set_brush((0, 0, 255), False))
        btn_cyan.clicked.connect(lambda: self.set_brush((255, 255, 0), False))
        btn_eraser.clicked.connect(lambda: self.set_brush((0, 0, 0), True))
        btn_clear.clicked.connect(self.clear_drawing)
        btn_save.clicked.connect(self.save_drawing)

        draw_grid.addWidget(btn_yellow, 0, 0)
        draw_grid.addWidget(btn_green, 0, 1)
        draw_grid.addWidget(btn_red, 0, 2)
        draw_grid.addWidget(btn_cyan, 0, 3)
        draw_grid.addWidget(btn_eraser, 1, 0)
        draw_grid.addWidget(btn_clear, 1, 1)
        draw_grid.addWidget(btn_save, 1, 2, 1, 2)
        draw_box.setLayout(draw_grid)
        right_layout.addWidget(draw_box)

        # 4. Calibration & Evaluation Controls
        tune_box = QGroupBox("⚙️ Precision Filter, Calibration & Evaluation")
        tune_grid = QGridLayout()

        tune_grid.addWidget(QLabel("Adaptive Stability:"), 0, 0)
        s_smooth = QSlider(Qt.Horizontal)
        s_smooth.setRange(1, 15)
        s_smooth.setValue(self.engine.smoothening)
        s_smooth.valueChanged.connect(lambda v: setattr(self.engine, 'smoothening', v))
        tune_grid.addWidget(s_smooth, 0, 1)

        tune_grid.addWidget(QLabel("Active Box Size:"), 1, 0)
        s_margin = QSlider(Qt.Horizontal)
        s_margin.setRange(40, 160)
        s_margin.setValue(self.engine.frame_margin)
        s_margin.valueChanged.connect(lambda v: setattr(self.engine, 'frame_margin', v))
        tune_grid.addWidget(s_margin, 1, 1)

        tune_grid.addWidget(QLabel("Pen Hue Min:"), 2, 0)
        s_hmin = QSlider(Qt.Horizontal)
        s_hmin.setRange(0, 179)
        s_hmin.setValue(self.engine.h_min)
        s_hmin.valueChanged.connect(lambda v: setattr(self.engine, 'h_min', v))
        tune_grid.addWidget(s_hmin, 2, 1)

        tune_grid.addWidget(QLabel("Pen Hue Max:"), 3, 0)
        s_hmax = QSlider(Qt.Horizontal)
        s_hmax.setRange(0, 179)
        s_hmax.setValue(self.engine.h_max)
        s_hmax.valueChanged.connect(lambda v: setattr(self.engine, 'h_max', v))
        tune_grid.addWidget(s_hmax, 3, 1)

        self.btn_mask = QPushButton("👁️ Mask View")
        self.btn_mask.setCheckable(True)
        self.btn_mask.clicked.connect(lambda checked: setattr(self.engine, 'show_mask', checked))

        btn_save_cfg = QPushButton("💾 Save Calibration")
        btn_save_cfg.clicked.connect(self.save_config)

        btn_export_csv = QPushButton("📊 Export Benchmark CSV")
        btn_export_csv.clicked.connect(self.export_csv)

        tune_grid.addWidget(self.btn_mask, 4, 0)
        tune_grid.addWidget(btn_save_cfg, 4, 1)
        tune_grid.addWidget(btn_export_csv, 5, 0, 1, 2)

        tune_box.setLayout(tune_grid)
        right_layout.addWidget(tune_box)

        # 5. Emergency Stop
        btn_stop = QPushButton("🛑 EMERGENCY STOP / EXIT APPLICATION")
        btn_stop.setStyleSheet("background-color: #da3633; color: white; padding: 10px; font-size: 13px;")
        btn_stop.clicked.connect(self.close)
        right_layout.addWidget(btn_stop)

        main_layout.addLayout(right_layout)

    def change_mode(self, new_mode, active_btn):
        for btn in self.mode_buttons:
            btn.setChecked(btn == active_btn)
        self.engine.mode = new_mode
        self.engine.last_event_text = f"Switched to {new_mode}"

    def change_click(self, c_type, active_btn):
        for btn in self.click_buttons:
            btn.setChecked(btn == active_btn)
        self.engine.click_type = c_type
        self.engine.last_event_text = f"Click Mode: {c_type}"

    def set_brush(self, color, is_eraser):
        self.engine.controller.brush_color = color
        self.engine.controller.eraser_on = is_eraser
        self.engine.last_event_text = "Eraser Active" if is_eraser else "Brush Changed"

    def clear_drawing(self):
        self.engine.controller.clear_canvas()
        self.engine.last_event_text = "Canvas Cleared"

    def save_drawing(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Air Drawing", "air_drawing.png", "PNG Files (*.png)")
        if file_path:
            cv2.imwrite(file_path, self.engine.controller.canvas)
            self.engine.last_event_text = "Drawing Saved!"

    def export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Performance Benchmark", "air_mouse_benchmark.csv", "CSV Files (*.csv)")
        if file_path:
            self.engine.export_benchmarks(file_path)
            self.engine.last_event_text = "Benchmark CSV Exported!"

    @Slot(QImage)
    def update_video(self, qt_img):
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    @Slot(int, float, int, int, int, str, str)
    def update_telemetry(self, fps, latency, x, y, conf, status, event):
        self.lbl_fps.setText(f"FPS: {fps} | {latency} ms")
        self.lbl_coords.setText(f"Pen: X:{x} Y:{y}")
        self.lbl_conf.setText(f"Confidence: {conf}%")
        self.lbl_status.setText(f"Status: {status}")
        self.lbl_mode.setText(f"Mode: {self.engine.mode}")
        self.lbl_event.setText(f"Event: {event}")

        if status == "PEN LOCKED":
            self.lbl_status.setStyleSheet("color: #3fb950; background-color: #0d1117; padding: 6px; border-radius: 4px;")
        else:
            self.lbl_status.setStyleSheet("color: #f85149; background-color: #0d1117; padding: 6px; border-radius: 4px;")

    def closeEvent(self, event):
        self.engine.running = False
        self.engine.wait()
        event.accept()