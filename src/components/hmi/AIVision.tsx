import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { HMIApiService, AIVisionStatus, CameraInfo, DetectionResult } from '@/services/hmi-api';
import { Camera, Play, Square, Settings, Eye, Activity, Cpu } from 'lucide-react';

interface AIVisionProps {
  apiService: HMIApiService;
}

export function AIVision({ apiService }: AIVisionProps) {
  const [status, setStatus] = useState<AIVisionStatus | null>(null);
  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<number>(0);
  const [selectedModel, setSelectedModel] = useState<string>('yolo11n.pt');
  const [confidence, setConfidence] = useState<number>(0.5);
  const [detections, setDetections] = useState<DetectionResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLImageElement>(null);
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch system status
  const fetchStatus = async () => {
    try {
      const response = await apiService.getAIVisionStatus();
      if (response.success && response.data) {
        setStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch AI-Vision status:', error);
    }
  };

  // Fetch available cameras
  const fetchCameras = async () => {
    try {
      const response = await apiService.listCameras();
      if (response.success && response.data) {
        setCameras(response.data.cameras);
        if (response.data.cameras.length > 0) {
          setSelectedCamera(response.data.cameras[0].camera_id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch cameras:', error);
    }
  };

  // Fetch available models
  const fetchModels = async () => {
    try {
      const response = await apiService.getAvailableModels();
      if (response.success && response.data) {
        setAvailableModels(response.data.available_models);
      }
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };

  // Fetch recent detections
  const fetchDetections = async () => {
    // Only fetch detections if AI-Vision is active
    if (!status?.active) {
      return;
    }

    try {
      const response = await apiService.getDetections(5);
      if (response.success && response.data) {
        setDetections(response.data.detections);
      } else {
        // If API call fails, silently skip this update
        // This prevents 500 errors from filling the console
      }
    } catch (error) {
      // Silently handle errors to prevent console spam
      // The video streaming will continue working regardless
    }
  };

  // Start AI-Vision system
  const handleStart = async () => {
    if (isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiService.startAIVision(selectedCamera, selectedModel);
      if (response.success) {
        await fetchStatus();
        startVideoStream();
      } else {
        setError(response.error || 'Failed to start AI-Vision');
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  // Stop AI-Vision system
  const handleStop = async () => {
    if (isLoading) return;

    setIsLoading(true);
    try {
      await apiService.stopAIVision();
      await fetchStatus();
      stopVideoStream();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to stop AI-Vision');
    } finally {
      setIsLoading(false);
    }
  };

  // Update confidence threshold
  const handleConfidenceChange = async (newConfidence: number[]) => {
    const confidenceValue = newConfidence[0];
    setConfidence(confidenceValue);

    try {
      await apiService.setConfidenceThreshold(confidenceValue);
    } catch (error) {
      console.error('Failed to update confidence threshold:', error);
    }
  };

  // Fetch and display video frame
  const fetchFrame = async () => {
    try {
      const response = await apiService.getAIVisionFrameData();
      if (response.success && response.data && videoRef.current) {
        const frameDataUrl = `data:image/jpeg;base64,${response.data.frame}`;
        videoRef.current.src = frameDataUrl;
      }
    } catch (error) {
      console.error('Failed to fetch frame:', error);
    }
  };

  // Start video streaming
  const startVideoStream = () => {
    // Start fetching frames every 100ms (10 FPS)
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
    }
    frameIntervalRef.current = setInterval(fetchFrame, 100);

    // Start fetching detections every 2 seconds
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
    }
    streamIntervalRef.current = setInterval(fetchDetections, 2000);
  };

  // Stop video streaming
  const stopVideoStream = () => {
    if (videoRef.current) {
      videoRef.current.src = '';
    }

    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }

    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
  };

  // Initialize component
  useEffect(() => {
    fetchStatus();
    fetchCameras();
    fetchModels();

    // Refresh status every 5 seconds
    const statusInterval = setInterval(fetchStatus, 5000);

    return () => {
      clearInterval(statusInterval);
      stopVideoStream();
    };
  }, []);

  // Get status badge variant
  const getStatusVariant = (active: boolean) => {
    return active ? 'default' : 'secondary';
  };

  // Format detection confidence
  const formatConfidence = (conf: number) => {
    return (conf * 100).toFixed(1);
  };

  // Get model display name
  const getModelDisplayName = (modelName: string) => {
    const modelMap: Record<string, string> = {
      'yolo11n.pt': 'YOLOv11 Nano (Fast)',
      'yolo11s.pt': 'YOLOv11 Small',
      'yolo11m.pt': 'YOLOv11 Medium',
      'yolo11l.pt': 'YOLOv11 Large',
      'yolo11x.pt': 'YOLOv11 Extra Large (Accurate)',
    };
    return modelMap[modelName] || modelName;
  };

  return (
    <div className="space-y-6">
      {/* Status and Controls Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            AI-Vision System
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Status Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Badge variant={getStatusVariant(status?.active || false)}>
                  {status?.active ? 'Active' : 'Inactive'}
                </Badge>
                {status?.model_loaded && (
                  <Badge variant="outline">Model Loaded</Badge>
                )}
                {status?.camera_active && (
                  <Badge variant="outline">Camera Ready</Badge>
                )}
              </div>

              {status && (
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Activity className="h-4 w-4" />
                    {status.fps.toFixed(1)} FPS
                  </div>
                  <div className="flex items-center gap-1">
                    <Cpu className="h-4 w-4" />
                    {status.total_detections} detections
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              {status?.active ? (
                <Button
                  onClick={handleStop}
                  disabled={isLoading}
                  variant="outline"
                  size="sm"
                >
                  <Square className="h-4 w-4 mr-2" />
                  Stop
                </Button>
              ) : (
                <Button
                  onClick={handleStart}
                  disabled={isLoading || cameras.length === 0}
                  size="sm"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Start
                </Button>
              )}
            </div>
          </div>

          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md">
              {error}
            </div>
          )}

          {/* Configuration */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Camera Selection */}
            <div className="space-y-2">
              <Label>Camera</Label>
              <Select
                value={selectedCamera.toString()}
                onValueChange={(value) => setSelectedCamera(parseInt(value))}
                disabled={status?.active}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select camera" />
                </SelectTrigger>
                <SelectContent>
                  {cameras.map((camera) => (
                    <SelectItem key={camera.camera_id} value={camera.camera_id.toString()}>
                      <div className="flex items-center gap-2">
                        <Camera className="h-4 w-4" />
                        {camera.name}
                        <Badge variant="outline" className="text-xs">
                          {camera.camera_type}
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Model Selection */}
            <div className="space-y-2">
              <Label>Model</Label>
              <Select
                value={selectedModel}
                onValueChange={setSelectedModel}
                disabled={status?.active}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  {availableModels.map((model) => (
                    <SelectItem key={model} value={model}>
                      {getModelDisplayName(model)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Confidence Threshold */}
            <div className="space-y-2">
              <Label>Confidence: {(confidence * 100).toFixed(0)}%</Label>
              <Slider
                value={[confidence]}
                onValueChange={handleConfidenceChange}
                min={0.1}
                max={1.0}
                step={0.05}
                className="w-full"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video Stream */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Camera className="h-5 w-5" />
              Live Detection Stream
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative aspect-video bg-muted rounded-md overflow-hidden">
              {status?.active ? (
                <img
                  ref={videoRef}
                  className="w-full h-full object-contain"
                  alt="AI-Vision Stream"
                  onError={() => setError('Failed to load video stream')}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  <div className="text-center">
                    <Camera className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>Start AI-Vision to see live detection stream</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Recent Detections */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Recent Detections
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {detections.length > 0 ? (
                detections.map((result, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">
                        {new Date(result.timestamp * 1000).toLocaleTimeString()}
                      </span>
                      <Badge variant="outline">
                        {result.detections.length} objects
                      </Badge>
                    </div>

                    {result.detections.map((detection, detIndex) => (
                      <div
                        key={detIndex}
                        className="flex items-center justify-between p-2 bg-muted rounded-md"
                      >
                        <div>
                          <div className="font-medium text-sm">
                            {detection.class_name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Confidence: {formatConfidence(detection.confidence)}%
                          </div>
                        </div>
                        <Badge variant="secondary">
                          {formatConfidence(detection.confidence)}%
                        </Badge>
                      </div>
                    ))}

                    {index < detections.length - 1 && <Separator />}
                  </div>
                ))
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  <Settings className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No recent detections</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Information */}
      {status && (
        <Card>
          <CardHeader>
            <CardTitle>System Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <Label className="text-muted-foreground">Current Model</Label>
                <div className="font-medium">{getModelDisplayName(status.model_name)}</div>
              </div>

              <div>
                <Label className="text-muted-foreground">Active Camera</Label>
                <div className="font-medium">
                  {status.current_camera?.name || 'None'}
                </div>
              </div>

              <div>
                <Label className="text-muted-foreground">Available Cameras</Label>
                <div className="font-medium">{status.available_cameras.length}</div>
              </div>

              <div>
                <Label className="text-muted-foreground">Last Detection</Label>
                <div className="font-medium">
                  {status.last_detection_time
                    ? new Date(status.last_detection_time * 1000).toLocaleTimeString()
                    : 'None'
                  }
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}