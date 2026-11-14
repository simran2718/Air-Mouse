import time
import csv
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from modules.vision_tracker import PenTracker
from modules.action_handler import ActionController


class VisionEngine(QThread):
    """Background worker thread running the real-time Computer Vision & HCI pipeline."""

    frame_ready = Signal(QImage)
    # Emits: FPS, Latency(ms), X, Y, Confidence, Status, Last_Event
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

        # Performance Benchmark Logs (for Section 11 Evaluation)
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
        cap.set(3, self.cam_w)
        cap.set(4, self.cam_h)
        cap.set(cv2.CAP_PROP_FPS, 60)

        prev_time = 0

        while self.running:
            frame_start = time.perf_counter()
            success, frame = cap.read()
            if not success:
                continue

            frame = cv2.flip(frame, 1)
            curr_time = time.time()
            fps = int(1 / (curr_time - prev_time)) if (curr_time - prev_time) > 0 else 0
            prev_time = curr_time

            lower = np.array([self.h_min, self.s_min, self.v_min])
            upper = np.array([self.h_max, self.s_max, self.v_max])

            detected, (raw_x, raw_y), bbox, confidence, mask = self.tracker.detect_pen(frame, lower, upper)

            # Draw UI Overlays on Video Frame
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

            # Calculate End-to-End Processing Latency in Milliseconds
            latency_ms = round((time.perf_counter() - frame_start) * 1000, 1)

            # Store telemetry sample (keep last 2000 frames)
            if len(self.benchmark_logs) < 2000:
                self.benchmark_logs.append([
                    time.strftime("%H:%M:%S"), self.mode, fps, latency_ms, tip_x, tip_y, confidence
                ])

            display_img = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) if self.show_mask else cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = display_img.shape
            qt_img = QImage(display_img.data, w, h, ch * w, QImage.Format_RGB888).copy()

            self.frame_ready.emit(qt_img)
            self.telemetry_ready.emit(fps, latency_ms, tip_x, tip_y, confidence, status_text, self.last_event_text)

        cap.release()