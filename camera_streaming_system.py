#!/usr/bin/env python3
"""
Camera Streaming System
Provides MJPEG streaming capabilities for connected cameras via Flask
Based on multi-camera streaming architecture with AI-Vision integration
"""

import time
import threading
import cv2
import io
import json
from typing import Dict, List, Optional, Any, Generator
from dataclasses import dataclass, asdict
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import logging

# Import AI-Vision system
try:
    from ai_vision_system import get_ai_vision_system, AIVisionSystem
    AI_VISION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI-Vision system not available: {e}")
    AI_VISION_AVAILABLE = False

@dataclass
class CameraInfo:
    """Camera information structure"""
    name: str
    device_id: int
    resolution: tuple
    fps: float
    status: str
    last_frame_time: float
    ai_enabled: bool = False

class CameraManager:
    """Manages multiple camera streams with optional AI processing"""

    def __init__(self):
        self.cameras: Dict[str, CameraInfo] = {}
        self.streams: Dict[str, cv2.VideoCapture] = {}
        self.frame_locks: Dict[str, threading.Lock] = {}
        self.latest_frames: Dict[str, bytes] = {}
        self.streaming_threads: Dict[str, threading.Thread] = {}
        self.stop_flags: Dict[str, threading.Event] = {}
        self.ai_vision = None

        # Initialize AI-Vision if available
        if AI_VISION_AVAILABLE:
            try:
                self.ai_vision = get_ai_vision_system()
                print("AI-Vision system initialized for camera streaming")
            except Exception as e:
                print(f"Failed to initialize AI-Vision: {e}")

        self._scan_cameras()

    def _scan_cameras(self):
        """Scan for available cameras"""
        print("Scanning for available cameras...")

        # Test common camera indices
        for i in range(4):  # Check first 4 camera indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # Get camera properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)

                camera_name = f"camera_{i}"
                self.cameras[camera_name] = CameraInfo(
                    name=camera_name,
                    device_id=i,
                    resolution=(width, height),
                    fps=fps if fps > 0 else 30.0,  # Default to 30 FPS if not reported
                    status="available",
                    last_frame_time=0.0
                )
                print(f"Found camera: {camera_name} - {width}x{height} @ {fps:.1f}FPS")
                cap.release()
            else:
                cap.release()

        print(f"Found {len(self.cameras)} camera(s)")

    def get_camera_list(self) -> List[Dict[str, Any]]:
        """Get list of available cameras"""
        return [asdict(camera) for camera in self.cameras.values()]

    def start_stream(self, camera_name: str, ai_enabled: bool = False) -> bool:
        """Start streaming from a camera"""
        if camera_name not in self.cameras:
            print(f"Camera not found: {camera_name}")
            return False

        if camera_name in self.streaming_threads and self.streaming_threads[camera_name].is_alive():
            print(f"Stream already running for {camera_name}")
            return True

        camera_info = self.cameras[camera_name]

        # Initialize video capture
        cap = cv2.VideoCapture(camera_info.device_id)
        if not cap.isOpened():
            print(f"Failed to open camera: {camera_name}")
            return False

        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_info.resolution[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_info.resolution[1])
        cap.set(cv2.CAP_PROP_FPS, camera_info.fps)

        # Store stream objects
        self.streams[camera_name] = cap
        self.frame_locks[camera_name] = threading.Lock()
        self.latest_frames[camera_name] = b''
        self.stop_flags[camera_name] = threading.Event()

        # Update camera info
        camera_info.ai_enabled = ai_enabled
        camera_info.status = "streaming"

        # Start streaming thread
        thread = threading.Thread(
            target=self._stream_worker,
            args=(camera_name,),
            daemon=True
        )
        thread.start()
        self.streaming_threads[camera_name] = thread

        print(f"Started streaming: {camera_name} (AI: {'enabled' if ai_enabled else 'disabled'})")
        return True

    def stop_stream(self, camera_name: str) -> bool:
        """Stop streaming from a camera"""
        if camera_name not in self.streaming_threads:
            return False

        # Signal stop
        if camera_name in self.stop_flags:
            self.stop_flags[camera_name].set()

        # Wait for thread to finish
        if self.streaming_threads[camera_name].is_alive():
            self.streaming_threads[camera_name].join(timeout=2.0)

        # Cleanup
        if camera_name in self.streams:
            self.streams[camera_name].release()
            del self.streams[camera_name]

        if camera_name in self.frame_locks:
            del self.frame_locks[camera_name]

        if camera_name in self.latest_frames:
            del self.latest_frames[camera_name]

        if camera_name in self.stop_flags:
            del self.stop_flags[camera_name]

        if camera_name in self.streaming_threads:
            del self.streaming_threads[camera_name]

        # Update status
        if camera_name in self.cameras:
            self.cameras[camera_name].status = "available"
            self.cameras[camera_name].ai_enabled = False

        print(f"Stopped streaming: {camera_name}")
        return True

    def _stream_worker(self, camera_name: str):
        """Worker thread for camera streaming"""
        cap = self.streams[camera_name]
        stop_flag = self.stop_flags[camera_name]
        frame_lock = self.frame_locks[camera_name]
        camera_info = self.cameras[camera_name]

        frame_interval = 1.0 / camera_info.fps

        while not stop_flag.is_set():
            start_time = time.time()

            ret, frame = cap.read()
            if not ret:
                print(f"Failed to read frame from {camera_name}")
                time.sleep(0.1)
                continue

            # Apply AI processing if enabled
            if camera_info.ai_enabled and self.ai_vision:
                try:
                    # Use AI-Vision system to process frame
                    processed_frame = self._apply_ai_processing(frame)
                    if processed_frame is not None:
                        frame = processed_frame
                except Exception as e:
                    print(f"AI processing error for {camera_name}: {e}")

            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                with frame_lock:
                    self.latest_frames[camera_name] = buffer.tobytes()
                    camera_info.last_frame_time = time.time()

            # Frame rate control
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _apply_ai_processing(self, frame) -> Optional[cv2.Mat]:
        """Apply AI processing to frame using AI-Vision system"""
        if not self.ai_vision:
            return frame

        try:
            # Send frame to AI-Vision system for processing
            # This assumes AI-Vision can process external frames
            processed_frame = self.ai_vision.process_frame(frame)
            return processed_frame if processed_frame is not None else frame
        except Exception as e:
            print(f"AI processing failed: {e}")
            return frame

    def get_latest_frame(self, camera_name: str) -> Optional[bytes]:
        """Get latest frame from camera"""
        if camera_name not in self.frame_locks:
            return None

        with self.frame_locks[camera_name]:
            return self.latest_frames.get(camera_name)

    def generate_stream(self, camera_name: str) -> Generator[bytes, None, None]:
        """Generate MJPEG stream for camera"""
        while camera_name in self.streaming_threads and self.streaming_threads[camera_name].is_alive():
            frame_data = self.get_latest_frame(camera_name)
            if frame_data:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
            time.sleep(1.0 / 30.0)  # 30 FPS output

    def stop_all_streams(self):
        """Stop all active streams"""
        camera_names = list(self.streaming_threads.keys())
        for camera_name in camera_names:
            self.stop_stream(camera_name)

# Global camera manager instance
camera_manager = CameraManager()

# Flask app for streaming
app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://localhost:3000"])

# Configure logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    """Get list of available cameras"""
    try:
        cameras = camera_manager.get_camera_list()
        return jsonify({
            'success': True,
            'cameras': cameras,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/api/cameras/<camera_name>/start', methods=['POST'])
def start_camera_stream(camera_name: str):
    """Start streaming from a camera"""
    try:
        data = request.get_json() or {}
        ai_enabled = data.get('ai_enabled', False)

        success = camera_manager.start_stream(camera_name, ai_enabled)
        return jsonify({
            'success': success,
            'camera_name': camera_name,
            'ai_enabled': ai_enabled,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/api/cameras/<camera_name>/stop', methods=['POST'])
def stop_camera_stream(camera_name: str):
    """Stop streaming from a camera"""
    try:
        success = camera_manager.stop_stream(camera_name)
        return jsonify({
            'success': success,
            'camera_name': camera_name,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/stream/<camera_name>')
def camera_stream(camera_name: str):
    """MJPEG stream endpoint for camera"""
    if camera_name not in camera_manager.cameras:
        return jsonify({'error': 'Camera not found'}), 404

    if camera_name not in camera_manager.streaming_threads:
        return jsonify({'error': 'Camera stream not started'}), 400

    return Response(
        camera_manager.generate_stream(camera_name),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'cameras_found': len(camera_manager.cameras),
        'active_streams': len(camera_manager.streaming_threads),
        'ai_vision_available': AI_VISION_AVAILABLE
    })

def create_camera_streaming_server(host: str = '0.0.0.0', port: int = 8082, debug: bool = False):
    """Create and run camera streaming server"""
    print(f"Starting Camera Streaming Server on http://{host}:{port}")
    print(f"Available endpoints:")
    print(f"  GET  /api/cameras - List cameras")
    print(f"  POST /api/cameras/<name>/start - Start camera stream")
    print(f"  POST /api/cameras/<name>/stop - Stop camera stream")
    print(f"  GET  /stream/<name> - MJPEG stream")
    print(f"  GET  /api/health - Health check")

    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down camera streaming server...")
        camera_manager.stop_all_streams()
    except Exception as e:
        print(f"Server error: {e}")
        camera_manager.stop_all_streams()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'server':
            # Start camera streaming server
            create_camera_streaming_server(debug=True)
        elif sys.argv[1] == 'test':
            # Test mode - scan cameras and show info
            print("Camera Streaming System - Test Mode")
            print("=" * 40)

            cameras = camera_manager.get_camera_list()
            print(f"Found {len(cameras)} camera(s):")
            for camera in cameras:
                print(f"  {camera['name']}: {camera['resolution'][0]}x{camera['resolution'][1]} @ {camera['fps']:.1f}FPS")

            if cameras:
                # Test streaming first camera
                first_camera = cameras[0]['name']
                print(f"\nTesting stream for {first_camera}...")
                if camera_manager.start_stream(first_camera):
                    print("Stream started successfully")
                    time.sleep(5)
                    camera_manager.stop_stream(first_camera)
                    print("Stream stopped")
                else:
                    print("Failed to start stream")
        else:
            print("Usage: python camera_streaming_system.py [server|test]")
    else:
        print("Camera Streaming System")
        print("Usage: python camera_streaming_system.py [server|test]")
        print("\nserver - Start HTTP streaming server")
        print("test   - Test camera detection and streaming")