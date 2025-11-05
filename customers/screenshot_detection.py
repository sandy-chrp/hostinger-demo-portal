# customers/screenshot_detection.py
"""
Python-based screenshot detection utilities
"""
import cv2
import numpy as np
from PIL import ImageGrab
import threading
import time
from django.conf import settings

class ScreenshotDetector:
    """
    Server-side screenshot detection using OpenCV
    """
    
    def __init__(self):
        self.monitoring = False
        self.last_screenshot = None
        
    def start_monitoring(self):
        """Start monitoring for screenshot changes"""
        if not settings.DEBUG:  # Only in production
            return
            
        self.monitoring = True
        thread = threading.Thread(target=self._monitor_loop)
        thread.daemon = True
        thread.start()
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                # Take screenshot
                screenshot = ImageGrab.grab()
                screenshot_array = np.array(screenshot)
                
                if self.last_screenshot is not None:
                    # Compare with last screenshot
                    diff = cv2.absdiff(screenshot_array, self.last_screenshot)
                    
                    # If significant change detected
                    if np.sum(diff) > 1000000:  # Threshold
                        self._handle_screenshot_detection()
                
                self.last_screenshot = screenshot_array
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                print(f"Screenshot monitoring error: {e}")
                time.sleep(1)
    
    def _handle_screenshot_detection(self):
        """Handle screenshot detection"""
        print("🚨 Screenshot activity detected!")
        # Log to database or take action

# Global detector instance
screenshot_detector = ScreenshotDetector()