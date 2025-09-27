#!/usr/bin/env python3
"""
AI-Vision System for CM5 Maker Desk
Implements YOLOv11 object detection with USB and Raspberry Pi camera support
"""

import cv2
import time
import threading
import queue
import base64
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    logger.warning("Ultralytics not available. Install with: pip install ultralytics[export]")
    YOLO_AVAILABLE = False

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    logger.info("picamera2 not available. USB camera mode only.")
    PICAMERA_AVAILABLE = False

try:
    import depthai as dai
    DEPTHAI_AVAILABLE = True
    logger.info("DepthAI available")
except ImportError:
    logger.warning("DepthAI not available. Install with: pip install depthai")
    DEPTHAI_AVAILABLE = False

@dataclass
class Detection:
    """Single object detection result"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    timestamp: float

@dataclass
class CameraInfo:
    """Camera information"""
    camera_id: int
    camera_type: str  # 'usb' or 'picamera'
    name: str
    resolution: Tuple[int, int]
    available: bool

@dataclass
class AIVisionStatus:
    """AI-Vision system status"""
    active: bool
    model_loaded: bool
    camera_active: bool
    current_camera: Optional[CameraInfo]
    available_cameras: List[CameraInfo]
    model_name: str
    fps: float
    total_detections: int
    last_detection_time: Optional[float]

class CameraManager:
    """Manages camera detection and access for USB and Pi cameras"""

    def __init__(self):
        self.available_cameras = []
        self.current_camera = None
        self.cap = None

    def detect_cameras(self) -> List[CameraInfo]:
        """Detect all available cameras"""
        cameras = []

        # Check for USB cameras
        for i in range(5):  # Check first 5 camera indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # Get camera resolution
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                cameras.append(CameraInfo(
                    camera_id=i,
                    camera_type='usb',
                    name=f'USB Camera {i}',
                    resolution=(width, height),
                    available=True
                ))
                cap.release()

        # Check for Raspberry Pi camera
        if PICAMERA_AVAILABLE:
            try:
                picam2 = Picamera2()
                camera_config = picam2.create_preview_configuration()
                main_size = camera_config['main']['size']
                cameras.append(CameraInfo(
                    camera_id=-1,  # Special ID for Pi camera
                    camera_type='picamera',
                    name='Raspberry Pi Camera',
                    resolution=main_size,
                    available=True
                ))
                picam2.close()
            except Exception as e:
                logger.info(f"Pi camera not available: {e}")

        # Check for DepthAI cameras
        if DEPTHAI_AVAILABLE:
            try:
                devices = dai.Device.getAllAvailableDevices()
                for i, device in enumerate(devices):
                    cameras.append(CameraInfo(
                        camera_id=-100 - i,  # Special negative IDs for DepthAI cameras
                        camera_type='depthai',
                        name=f'DepthAI Camera {device.name}',
                        resolution=(1920, 1080),  # Default DepthAI resolution
                        available=True
                    ))
                logger.info(f"Found {len(devices)} DepthAI camera(s)")
            except Exception as e:
                logger.warning(f"DepthAI camera detection failed: {e}")

        self.available_cameras = cameras
        logger.info(f"Found {len(cameras)} cameras")
        return cameras

    def start_camera(self, camera_id: int) -> bool:
        """Start specified camera"""
        try:
            self.stop_camera()  # Stop any existing camera

            camera_info = None
            for cam in self.available_cameras:
                if cam.camera_id == camera_id:
                    camera_info = cam
                    break

            if not camera_info:
                logger.error(f"Camera {camera_id} not found")
                return False

            if camera_info.camera_type == 'usb':
                self.cap = cv2.VideoCapture(camera_id)
                if not self.cap.isOpened():
                    logger.error(f"Failed to open USB camera {camera_id}")
                    return False

                # Set camera properties for better performance
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)

            elif camera_info.camera_type == 'picamera':
                if not PICAMERA_AVAILABLE:
                    logger.error("picamera2 not available")
                    return False

                self.cap = Picamera2()
                camera_config = self.cap.create_preview_configuration(
                    main={"size": (640, 480)}
                )
                self.cap.configure(camera_config)
                self.cap.start()

            elif camera_info.camera_type == 'depthai':
                if not DEPTHAI_AVAILABLE:
                    logger.error("DepthAI not available")
                    return False

                # Create DepthAI device using 3.0 API (no pipeline needed)
                device = dai.Device()

                # Get RGB output queue directly from device
                q_rgb = device.getOutputQueue("rgb", maxSize=4, blocking=False)

                self.cap = {'device': device, 'queue': q_rgb}

            self.current_camera = camera_info
            logger.info(f"Started camera: {camera_info.name}")
            return True

        except Exception as e:
            logger.error(f"Error starting camera {camera_id}: {e}")
            return False

    def capture_frame(self) -> Optional[Any]:
        """Capture a frame from the current camera"""
        if not self.cap or not self.current_camera:
            return None

        try:
            if self.current_camera.camera_type == 'usb':
                ret, frame = self.cap.read()
                return frame if ret else None

            elif self.current_camera.camera_type == 'picamera':
                return self.cap.capture_array()

            elif self.current_camera.camera_type == 'depthai':
                # Get frame from DepthAI queue
                in_rgb = self.cap['queue'].tryGet()
                if in_rgb is not None:
                    # Convert to OpenCV format - DepthAI 3.0 API
                    frame = in_rgb.getCvFrame()
                    return frame
                return None

        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None

    def stop_camera(self):
        """Stop the current camera"""
        if self.cap:
            try:
                if self.current_camera and self.current_camera.camera_type == 'usb':
                    self.cap.release()
                elif self.current_camera and self.current_camera.camera_type == 'picamera':
                    self.cap.stop()
                    self.cap.close()
                elif self.current_camera and self.current_camera.camera_type == 'depthai':
                    # Close DepthAI device
                    if isinstance(self.cap, dict) and 'device' in self.cap:
                        self.cap['device'].close()
            except Exception as e:
                logger.error(f"Error stopping camera: {e}")

            self.cap = None
            self.current_camera = None

class YOLOInferenceEngine:
    """YOLO inference engine for object detection"""

    def __init__(self):
        self.model = None
        self.model_name = None
        self.confidence_threshold = 0.5
        self.class_names = []

    def load_model(self, model_name: str = "yolo11n.pt") -> bool:
        """Load YOLO model"""
        if not YOLO_AVAILABLE:
            logger.error("YOLO not available")
            return False

        try:
            self.model = YOLO(model_name)
            self.model_name = model_name
            self.class_names = self.model.names
            logger.info(f"Loaded YOLO model: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Error loading YOLO model {model_name}: {e}")
            return False

    def set_confidence_threshold(self, threshold: float):
        """Set confidence threshold for detections"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))

    def detect(self, frame) -> List[Detection]:
        """Run object detection on frame"""
        if not self.model or frame is None:
            return []

        try:
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            detections = []

            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        # Extract detection data
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        confidence = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = self.class_names.get(class_id, f"Class_{class_id}")

                        detection = Detection(
                            class_id=class_id,
                            class_name=class_name,
                            confidence=confidence,
                            bbox=(x1, y1, x2, y2),
                            timestamp=time.time()
                        )
                        detections.append(detection)

            return detections

        except Exception as e:
            logger.error(f"Error during detection: {e}")
            return []

    def draw_detections(self, frame, detections: List[Detection]):
        """Draw detection boxes and labels on frame"""
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Draw label
            label = f"{detection.class_name}: {detection.confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]

            # Background for label
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10),
                         (x1 + label_size[0], y1), (0, 255, 0), -1)

            # Label text
            cv2.putText(frame, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        return frame

class AIVisionSystem:
    """Main AI-Vision system coordinator"""

    def __init__(self):
        self.camera_manager = CameraManager()
        self.inference_engine = YOLOInferenceEngine()

        # System state
        self.active = False
        self.processing_thread = None
        self.frame_queue = queue.Queue(maxsize=5)
        self.detection_queue = queue.Queue(maxsize=100)

        # Statistics
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        self.total_detections = 0
        self.last_detection_time = None

        # Latest frame for streaming
        self.latest_frame = None
        self.latest_detections = []
        self.frame_lock = threading.Lock()

    def initialize(self, model_name: str = "yolo11n.pt") -> bool:
        """Initialize the AI-Vision system"""
        logger.info("Initializing AI-Vision system...")

        # Load YOLO model
        if not self.inference_engine.load_model(model_name):
            return False

        # Detect cameras
        cameras = self.camera_manager.detect_cameras()
        logger.info(f"Found {len(cameras)} cameras")

        return True

    def start(self, camera_id: int = 0) -> bool:
        """Start AI-Vision processing"""
        if self.active:
            logger.warning("AI-Vision already active")
            return True

        # Start camera
        if not self.camera_manager.start_camera(camera_id):
            logger.error("Failed to start camera")
            return False

        # Start processing thread
        self.active = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()

        logger.info("AI-Vision started")
        return True

    def stop(self):
        """Stop AI-Vision processing"""
        if not self.active:
            return

        self.active = False

        if self.processing_thread:
            self.processing_thread.join(timeout=5)

        self.camera_manager.stop_camera()

        # Clear queues
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        while not self.detection_queue.empty():
            try:
                self.detection_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("AI-Vision stopped")

    def _processing_loop(self):
        """Main processing loop"""
        logger.info("AI-Vision processing loop started")

        while self.active:
            try:
                # Capture frame
                frame = self.camera_manager.capture_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue

                # Run inference
                detections = self.inference_engine.detect(frame)

                # Update statistics
                self.fps_counter += 1
                current_time = time.time()
                if current_time - self.fps_start_time >= 1.0:
                    self.current_fps = self.fps_counter / (current_time - self.fps_start_time)
                    self.fps_counter = 0
                    self.fps_start_time = current_time

                if detections:
                    self.total_detections += len(detections)
                    self.last_detection_time = current_time

                # Draw detections on frame
                annotated_frame = self.inference_engine.draw_detections(frame.copy(), detections)

                # Store latest frame and detections
                with self.frame_lock:
                    self.latest_frame = annotated_frame
                    self.latest_detections = detections

                # Add to detection queue for API access
                try:
                    self.detection_queue.put_nowait({
                        'timestamp': current_time,
                        'detections': [asdict(d) for d in detections],
                        'fps': self.current_fps
                    })
                except queue.Full:
                    # Remove oldest detection if queue is full
                    try:
                        self.detection_queue.get_nowait()
                        self.detection_queue.put_nowait({
                            'timestamp': current_time,
                            'detections': [asdict(d) for d in detections],
                            'fps': self.current_fps
                        })
                    except queue.Empty:
                        pass

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(0.1)

    def get_status(self) -> AIVisionStatus:
        """Get current system status"""
        return AIVisionStatus(
            active=self.active,
            model_loaded=self.inference_engine.model is not None,
            camera_active=self.camera_manager.current_camera is not None,
            current_camera=self.camera_manager.current_camera,
            available_cameras=self.camera_manager.available_cameras,
            model_name=self.inference_engine.model_name or "None",
            fps=self.current_fps,
            total_detections=self.total_detections,
            last_detection_time=self.last_detection_time
        )

    def get_latest_frame(self) -> Optional[bytes]:
        """Get latest annotated frame as JPEG bytes"""
        with self.frame_lock:
            if self.latest_frame is None:
                return None

            try:
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', self.latest_frame)
                if ret:
                    return buffer.tobytes()
            except Exception as e:
                logger.error(f"Error encoding frame: {e}")

        return None

    def get_recent_detections(self, max_count: int = 10) -> List[Dict]:
        """Get recent detections"""
        detections = []
        temp_queue = queue.Queue()

        # Extract detections from queue
        while not self.detection_queue.empty() and len(detections) < max_count:
            try:
                detection = self.detection_queue.get_nowait()
                detections.append(detection)
                temp_queue.put(detection)
            except queue.Empty:
                break

        # Put detections back in queue
        while not temp_queue.empty():
            try:
                self.detection_queue.put_nowait(temp_queue.get_nowait())
            except queue.Full:
                break

        return list(reversed(detections))  # Most recent first

# Global AI-Vision system instance
ai_vision = None

def get_ai_vision_system() -> AIVisionSystem:
    """Get or create global AI-Vision system instance"""
    global ai_vision
    if ai_vision is None:
        ai_vision = AIVisionSystem()
    return ai_vision

if __name__ == "__main__":
    # Test the AI-Vision system
    vision = AIVisionSystem()

    if vision.initialize():
        print("AI-Vision initialized successfully")

        cameras = vision.camera_manager.detect_cameras()
        print(f"Available cameras: {len(cameras)}")
        for cam in cameras:
            print(f"  - {cam.name} ({cam.camera_type}) - {cam.resolution}")

        if cameras:
            print(f"Starting with camera: {cameras[0].name}")
            if vision.start(cameras[0].camera_id):
                try:
                    # Run for 30 seconds
                    for i in range(30):
                        time.sleep(1)
                        status = vision.get_status()
                        detections = vision.get_recent_detections(1)

                        print(f"FPS: {status.fps:.1f}, "
                              f"Total detections: {status.total_detections}, "
                              f"Recent: {len(detections[0]['detections']) if detections else 0}")

                except KeyboardInterrupt:
                    print("Stopping...")

                finally:
                    vision.stop()
        else:
            print("No cameras available")
    else:
        print("Failed to initialize AI-Vision system")