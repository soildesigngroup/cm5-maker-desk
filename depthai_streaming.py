#!/usr/bin/env python3
"""
Official DepthAI Camera Streaming
Based on Luxonis manufacturer example
"""

import depthai as dai

def main():
    print("Starting DepthAI streaming server...")

    # Use port 8083 to avoid conflict with camera streaming system (8082)
    remoteConnector = dai.RemoteConnection(httpPort=8083)

    try:
        with dai.Pipeline() as pipeline:
            # Define source and output
            cam = pipeline.create(dai.node.Camera).build()

            # Add video topic with 640x400 resolution
            remoteConnector.addTopic("video", cam.requestOutput((640, 400)), "video")

            print("Starting pipeline...")
            pipeline.start()
            remoteConnector.registerPipeline(pipeline)

            print("DepthAI streaming server running on http://localhost:8083")
            print("Press 'q' to quit")

            while pipeline.isRunning():
                key = remoteConnector.waitKey(1)
                if key == ord("q"):
                    print("Got q key from the remote connection!")
                    break

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    print("DepthAI streaming stopped")

if __name__ == "__main__":
    main()