import time
import math
import cv2
import numpy as np
import pyautogui
from pynput.mouse import Controller, Button
from modules.filters import OneEuroFilter

pyautogui.FAILSAFE = False


class ActionController:
    """Translates tracked pen coordinates into OS mouse actions, drawing, and PPT controls."""

    def __init__(self, cam_w=640, cam_h=480):
        self.mouse = Controller()
        self.screen_w, self.screen_h = pyautogui.size()
        self.cam_w = cam_w
        self.cam_h = cam_h

        self.filter_x = OneEuroFilter(min_cutoff=0.8, beta=0.04)
        self.filter_y = OneEuroFilter(min_cutoff=0.8, beta=0.04)

        # Dwell Click & Drag State
        self.dwell_start = None
        self.anchor_x, self.anchor_y = 0.0, 0.0
        self.last_click_time = 0.0
        self.is_dragging = False

        # Air Drawing Canvas
        self.canvas = np.zeros((self.cam_h, self.cam_w, 3), np.uint8)
        self.draw_prev_x, self.draw_prev_y = 0, 0
        self.brush_color = (0, 255, 255)
        self.brush_size = 6
        self.eraser_on = False

        # PPT Swipe State
        self.swipe_start_x = None
        self.swipe_start_time = 0.0
        self.last_slide_time = 0.0

    def reset_tracking(self):
        self.draw_prev_x, self.draw_prev_y = 0, 0
        self.dwell_start = None
        self.filter_x.reset()
        self.filter_y.reset()

    def clear_canvas(self):
        self.canvas = np.zeros((self.cam_h, self.cam_w, 3), np.uint8)

    def handle_mouse(self, raw_x, raw_y, frame, curr_time, margin, smoothening, dwell_req, click_type):
        event_msg = None
        dynamic_cutoff = max(0.15, 2.2 - (smoothening * 0.13))
        self.filter_x.min_cutoff = dynamic_cutoff
        self.filter_y.min_cutoff = dynamic_cutoff

        tx = np.interp(raw_x, (margin, self.cam_w - margin), (0, self.screen_w))
        ty = np.interp(raw_y, (margin, self.cam_h - margin), (0, self.screen_h))

        smooth_x = self.filter_x.filter(tx, curr_time)
        smooth_y = self.filter_y.filter(ty, curr_time)
        self.mouse.position = (int(smooth_x), int(smooth_y))

        # Dwell Click Logic
        tip_x, tip_y = int(raw_x), int(raw_y)
        dist = math.hypot(raw_x - self.anchor_x, raw_y - self.anchor_y)

        if dist < 14:
            if self.dwell_start is None:
                self.dwell_start = curr_time
            else:
                elapsed = curr_time - self.dwell_start
                angle = int((elapsed / dwell_req) * 360)
                cv2.ellipse(frame, (tip_x, tip_y), (22, 22), 0, 0, angle, (0, 255, 0), 3)

                if elapsed >= dwell_req and (curr_time - self.last_click_time) > 1.0:
                    if click_type == "LEFT":
                        self.mouse.click(Button.left, 1)
                        event_msg = "Left Click Executed"
                    elif click_type == "RIGHT":
                        self.mouse.click(Button.right, 1)
                        event_msg = "Right Click Executed"
                    elif click_type == "DOUBLE":
                        self.mouse.click(Button.left, 2)
                        event_msg = "Double Click Executed"
                    elif click_type == "DRAG":
                        if not self.is_dragging:
                            self.mouse.press(Button.left)
                            self.is_dragging = True
                            event_msg = "Drag Started (Hold)"
                        else:
                            self.mouse.release(Button.left)
                            self.is_dragging = False
                            event_msg = "Drag Released (Drop)"

                    cv2.circle(frame, (tip_x, tip_y), 30, (0, 255, 0), -1)
                    self.last_click_time = curr_time
                    self.dwell_start = None
        else:
            self.anchor_x, self.anchor_y = raw_x, raw_y
            self.dwell_start = None

        return event_msg

    def handle_scroll(self, tip_y):
        mid_y = self.cam_h // 2
        if tip_y < mid_y - 35:
            self.mouse.scroll(0, 1)
            return "Scrolling UP"
        elif tip_y > mid_y + 35:
            self.mouse.scroll(0, -1)
            return "Scrolling DOWN"
        return None

    def handle_draw(self, raw_x, raw_y, frame, curr_time):
        color = (0, 0, 0) if self.eraser_on else self.brush_color
        size = 30 if self.eraser_on else self.brush_size

        draw_x = int(self.filter_x.filter(raw_x, curr_time))
        draw_y = int(self.filter_y.filter(raw_y, curr_time))

        cv2.circle(frame, (draw_x, draw_y), size // 2, (255, 255, 255) if self.eraser_on else color, 2)

        if self.draw_prev_x == 0 and self.draw_prev_y == 0:
            self.draw_prev_x, self.draw_prev_y = draw_x, draw_y
        else:
            cv2.line(self.canvas, (self.draw_prev_x, self.draw_prev_y), (draw_x, draw_y), color, size, cv2.LINE_AA)
            self.draw_prev_x, self.draw_prev_y = draw_x, draw_y

    def handle_ppt(self, tip_x, curr_time):
        if self.swipe_start_x is None:
            self.swipe_start_x = tip_x
            self.swipe_start_time = curr_time
            return None

        dx = tip_x - self.swipe_start_x
        dt = curr_time - self.swipe_start_time

        if dt < 0.6 and (curr_time - self.last_slide_time) > 1.2:
            if dx > 130:
                pyautogui.press('right')
                self.last_slide_time = curr_time
                self.swipe_start_x = None
                return "PPT: Next Slide >>"
            elif dx < -130:
                pyautogui.press('left')
                self.last_slide_time = curr_time
                self.swipe_start_x = None
                return "PPT: << Previous Slide"
        elif dt >= 0.6:
            self.swipe_start_x = tip_x
            self.swipe_start_time = curr_time

        return None

    def merge_canvas(self, frame):
        gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
        _, inv = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY_INV)
        inv = cv2.cvtColor(inv, cv2.COLOR_GRAY2BGR)
        frame = cv2.bitwise_and(frame, inv)
        return cv2.bitwise_or(frame, self.canvas)