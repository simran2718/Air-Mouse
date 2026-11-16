import time
import csv
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from modules.vision_tracker import PenTracker
from modules.action_handler import ActionController


class VisionEngine(QThread):
    """Optimized background worker thread with frame-rate pacing and buffer clearing."""

    frame_ready = Signal(QImage)
    telemetry_ready = Signal(int, float, int, int, int, str, str)

    def __init__(self, config):
        super().__init__()
        self.running = True
        self.cam_w, self.cam_h = 640, 480

        # Load initial settings from config.json
        self.h_min = config.get("h_min", 106)
        self.s_min = config.get("s_min", 100)
        self.v_min = config.get("v_min", 100)
        self.h_max = config.get("h_max", 130)
        self.s_max = config.get("s_max", 255)
        self.v_max = config.get("v_max", 255)
        self.smoothening = config.get("smoothening", 8)
        self.frame_margin = config.get("frame_margin", 100)
        self.dwell_time_req = config.get("dwell_time_req", 2.0)

        self.mode = "MOUSE"
        self.click_type = "LEFT"
        self.show_mask = False
        self.last_event_text = "System Ready"

        # Sub-modules
        self.tracker = PenTracker()
        self.controller = ActionController(self.cam_w, self.cam_h)

        # Performance Benchmark Logs
        self.benchmark_logs = []

    def export_benchmarks(self, filepath):
        with open(filepath, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Mode", "FPS", "Latency_ms", "Pen_X", "Pen_Y", "Confidence_%"])
            writer.writerows(self.benchmark_logs)

    def run(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_h)
        # FIX 1: Camera buffer size 1 rakhna taaki purane frames queue na hon
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        prev_time = time.perf_counter()
        last_ui_update = 0.0
        frame_counter = 0

        while self.running:
            frame_start = time.perf_counter()
            success, frame = cap.read()
            if not success:
                self.msleep(10)
                continue

            frame = cv2.flip(frame, 1)
            curr_time = time.time()

            # Smooth FPS calculation
            dt = frame_start - prev_time
            fps = int(1.0 / dt) if dt > 0 else 0
            prev_time = frame_start

            lower = np.array([self.h_min, self.s_min, self.v_min])
            upper = np.array([self.h_max, self.s_max, self.v_max])

            detected, (raw_x, raw_y), bbox, confidence, mask = self.tracker.detect_pen(frame, lower, upper)

            if self.mode in ["MOUSE", "SCROLL"]:
                cv2.rectangle(frame, (self.frame_margin, self.frame_margin),
                              (self.cam_w - self.frame_margin, self.cam_h - self.frame_margin),
                              (255, 0, 255), 2)

            if self.mode == "SCROLL":
                mid_y = self.cam_h // 2
                cv2.line(frame, (self.frame_margin, mid_y), (self.cam_w - self.frame_margin, mid_y), (0, 255, 255), 2)
                cv2.putText(frame, "SCROLL UP ZONE", (230, mid_y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                cv2.putText(frame, "SCROLL DOWN ZONE", (220, mid_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            tip_x, tip_y = int(raw_x), int(raw_y)
            status_text = "SEARCHING PEN..."

            if detected:
                status_text = "PEN LOCKED"
                x, y, w, h = bbox
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, (tip_x, tip_y), 7, (0, 0, 255), -1)
                cv2.circle(frame, (tip_x, tip_y), 13, (0, 255, 255), 2)

                event = None
                if self.mode == "MOUSE":
                    event = self.controller.handle_mouse(
                        raw_x, raw_y, frame, curr_time,
                        self.frame_margin, self.smoothening, self.dwell_time_req, self.click_type
                    )
                elif self.mode == "SCROLL":
                    event = self.controller.handle_scroll(tip_y)
                elif self.mode == "DRAW":
                    self.controller.handle_draw(raw_x, raw_y, frame, curr_time)
                elif self.mode == "PPT":
                    event = self.controller.handle_ppt(tip_x, curr_time)

                if event:
                    self.last_event_text = event
            else:
                self.controller.reset_tracking()

            if self.mode == "DRAW":
                frame = self.controller.merge_canvas(frame)

            latency_ms = round((time.perf_counter() - frame_start) * 1000, 1)

            # FIX 2: UI ko sirf ~30 FPS par update karna taaki PySide6 signal queue jam na ho
            # (Mouse tracking backend mein full speed par chalti rahegi!)
            if (frame_start - last_ui_update) >= 0.032:
                display_img = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) if self.show_mask else cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = display_img.shape
                qt_img = QImage(display_img.data, w, h, ch * w, QImage.Format_RGB888).copy()

                self.frame_ready.emit(qt_img)
                self.telemetry_ready.emit(fps, latency_ms, tip_x, tip_y, confidence, status_text, self.last_event_text)
                last_ui_update = frame_start

            # Benchmark log har 10th frame par save karna (memory bachane ke liye)
            frame_counter += 1
            if frame_counter % 10 == 0 and len(self.benchmark_logs) < 1000:
                self.benchmark_logs.append([
                    time.strftime("%H:%M:%S"), self.mode, fps, latency_ms, tip_x, tip_y, confidence
                ])

            # FIX 3: CPU ko 5ms saans lene dena taaki OS mouse events aur GUI smooth rahein
            self.msleep(5)

        cap.release()