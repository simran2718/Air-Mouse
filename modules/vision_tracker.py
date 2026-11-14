import math
import cv2
import numpy as np


class PenTracker:
    """Handles HSV color masking, noise reduction, and sub-pixel pen tip detection."""

    def __init__(self):
        self.raw_prev_x = 0.0
        self.raw_prev_y = 0.0

    def detect_pen(self, frame, lower_hsv, upper_hsv):
        blurred = cv2.GaussianBlur(frame, (9, 9), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # HSV Thresholding & Morphological Filtering
        mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)

            if area > 250:
                confidence = min(100, int((area / 2500) * 100) + 40)
                bbox = cv2.boundingRect(largest)

                # Sub-pixel top-contour tip calculation (accurate even when pen tilts)
                pts = largest.reshape(-1, 2)
                min_y = np.min(pts[:, 1])
                top_pts = pts[pts[:, 1] <= min_y + 8]
                raw_tip_x = float(np.mean(top_pts[:, 0]))
                raw_tip_y = float(min_y)

                # Micro-jitter deadzone lock (1.8px threshold)
                if math.hypot(raw_tip_x - self.raw_prev_x, raw_tip_y - self.raw_prev_y) < 1.8:
                    raw_tip_x, raw_tip_y = self.raw_prev_x, self.raw_prev_y
                else:
                    self.raw_prev_x, self.raw_prev_y = raw_tip_x, raw_tip_y

                return True, (raw_tip_x, raw_tip_y), bbox, confidence, mask

        return False, (0.0, 0.0), None, 0, mask