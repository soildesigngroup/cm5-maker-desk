import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { HMIApiService, AIVisionStatus, CameraInfo, DetectionResult } from '@/services/hmi-api';
import { Camera, Play, Square, Settings, Eye, Activity, Cpu, AlertTriangle, Shield, Grid3X3 } from 'lucide-react';

interface AIVisionProps {
  apiService: HMIApiService;
}

interface CameraStreamInfo {
  name: string;
  device_id: number;
  resolution: [number, number];
  fps: number;
  status: string;
  last_frame_time: number;
  ai_enabled: boolean;
}

interface DepthAIOption {
  enabled: boolean;
  port: number;
}

const CAMERA_API_BASE = 'http://localhost:8082';
const DEPTHAI_BASE = 'http://localhost:8083';

export function AIVision({ apiService }: AIVisionProps) {
  // AI-Vision state
  const [status, setStatus] = useState<AIVisionStatus | null>(null);
  const [aiCameras, setAiCameras] = useState<CameraInfo[]>([]);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedAiCamera, setSelectedAiCamera] = useState<number>(0);
  const [selectedModel, setSelectedModel] = useState<string>('yolo11n.pt');
  const [confidence, setConfidence] = useState<number>(0.5);
  const [detections, setDetections] = useState<DetectionResult[]>([]);
  const [aiVisionActive, setAiVisionActive] = useState(false);

  // Camera streaming state
  const [streamCameras, setStreamCameras] = useState<CameraStreamInfo[]>([]);
  const [streamingCameras, setStreamingCameras] = useState<Set<string>>(new Set());
  const [selectedStreamCamera, setSelectedStreamCamera] = useState<string>('');
  const [viewMode, setViewMode] = useState<'single' | 'grid'>('single');

  // DepthAI state
  const [depthAI, setDepthAI] = useState<DepthAIOption>({ enabled: false, port: 8083 });

  // General state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [privacyAcknowledged, setPrivacyAcknowledged] = useState(false);

  const videoRefs = useRef<Record<string, HTMLImageElement>>({});
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Security notice for camera access
  const SecurityNotice = () => (
    <Alert className="mb-4 border-orange-200 bg-orange-50">
      <Shield className="h-4 w-4" />
      <AlertDescription>
        <div className="space-y-2">
          <p className="font-medium">Privacy Notice</p>
          <p className="text-sm">
            This interface provides access to camera systems. Cameras will only activate when you explicitly start them.
            Please ensure you have appropriate permissions before accessing camera feeds.
          </p>
          <div className="flex items-center space-x-2 mt-2">
            <Switch
              id="privacy-acknowledgment"
              checked={privacyAcknowledged}
              onCheckedChange={setPrivacyAcknowledged}
            />
            <Label htmlFor="privacy-acknowledgment" className="text-sm">
              I acknowledge this privacy notice and consent to camera access
            </Label>
          </div>
        </div>
      </AlertDescription>
    </Alert>
  );

  // Fetch AI-Vision status
  const fetchAiVisionStatus = async () => {
    try {
      const response = await apiService.getAIVisionStatus();
      if (response.success && response.data) {
        setStatus(response.data);
        setAiVisionActive(response.data.active);
      }
    } catch (error) {
      console.error('Failed to fetch AI-Vision status:', error);
    }
  };

  // Fetch AI-Vision cameras
  const fetchAiCameras = async () => {
    try {
      const response = await apiService.listCameras();
      if (response.success && response.data) {
        setAiCameras(response.data.cameras);
        if (response.data.cameras.length > 0) {
          setSelectedAiCamera(response.data.cameras[0].camera_id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch AI cameras:', error);
    }
  };

  // Fetch camera streaming system cameras
  const fetchStreamCameras = async () => {
    try {
      const response = await fetch(`${CAMERA_API_BASE}/api/cameras`);
      const data = await response.json();

      if (data.success) {
        setStreamCameras(data.cameras);
        if (data.cameras.length > 0 && !selectedStreamCamera) {
          setSelectedStreamCamera(data.cameras[0].name);
        }
      } else {
        setError(data.error || 'Failed to fetch stream cameras');
      }
    } catch (error) {
      console.error('Failed to fetch stream cameras:', error);
      setError('Failed to connect to camera streaming service');
    }
  };

  // Start AI-Vision
  const startAiVision = async () => {
    if (!privacyAcknowledged) {
      setError('Please acknowledge the privacy notice before starting camera systems');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiService.startAIVision(selectedAiCamera);
      if (response.success) {
        setAiVisionActive(true);
        fetchAiVisionStatus();
      } else {
        setError(response.error || 'Failed to start AI-Vision');
      }
    } catch (error) {
      console.error('Failed to start AI-Vision:', error);
      setError('Failed to start AI-Vision system');
    } finally {
      setIsLoading(false);
    }
  };

  // Stop AI-Vision
  const stopAiVision = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.stopAIVision();
      if (response.success) {
        setAiVisionActive(false);
        setDetections([]);
        fetchAiVisionStatus();
      }
    } catch (error) {
      console.error('Failed to stop AI-Vision:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Start camera stream
  const startStream = async (cameraName: string, withAI: boolean = false) => {
    if (!privacyAcknowledged) {
      setError('Please acknowledge the privacy notice before starting camera systems');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${CAMERA_API_BASE}/api/cameras/${cameraName}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ai_enabled: withAI
        }),
      });

      const data = await response.json();

      if (data.success) {
        setStreamingCameras(prev => new Set([...prev, cameraName]));

        // Start the MJPEG stream
        if (videoRefs.current[cameraName]) {
          videoRefs.current[cameraName].src = `${CAMERA_API_BASE}/stream/${cameraName}`;
        }
      } else {
        setError(data.error || 'Failed to start camera stream');
      }
    } catch (error) {
      console.error('Failed to start stream:', error);
      setError('Failed to start camera stream');
    } finally {
      setIsLoading(false);
    }
  };

  // Stop camera stream
  const stopStream = async (cameraName: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${CAMERA_API_BASE}/api/cameras/${cameraName}/stop`, {
        method: 'POST',
      });

      const data = await response.json();

      if (data.success) {
        setStreamingCameras(prev => {
          const newSet = new Set(prev);
          newSet.delete(cameraName);
          return newSet;
        });

        // Stop the MJPEG stream
        if (videoRefs.current[cameraName]) {
          videoRefs.current[cameraName].src = '';
        }
      } else {
        setError(data.error || 'Failed to stop camera stream');
      }
    } catch (error) {
      console.error('Failed to stop stream:', error);
      setError('Failed to stop camera stream');
    } finally {
      setIsLoading(false);
    }
  };

  // Start DepthAI streaming
  const startDepthAI = async () => {
    if (!privacyAcknowledged) {
      setError('Please acknowledge the privacy notice before starting camera systems');
      return;
    }

    // Note: DepthAI requires manual start via depthai_streaming.py
    // This is a placeholder for future implementation
    setError('DepthAI streaming requires manual activation. Please use the provided Python script.');
  };

  // Register video ref for each camera
  const setVideoRef = (cameraName: string) => (ref: HTMLImageElement | null) => {
    if (ref) {
      videoRefs.current[cameraName] = ref;
    } else {
      delete videoRefs.current[cameraName];
    }
  };

  // Initialize component
  useEffect(() => {
    fetchAiVisionStatus();
    fetchAiCameras();
    fetchStreamCameras();

    const interval = setInterval(() => {
      fetchAiVisionStatus();
      fetchStreamCameras();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Get status variant for badges
  const getStatusVariant = (isActive: boolean) => {
    return isActive ? 'default' : 'secondary';
  };

  // Render camera stream view
  const renderCameraView = () => {
    if (viewMode === 'single') {
      const camera = streamCameras.find(c => c.name === selectedStreamCamera);
      const isStreaming = streamingCameras.has(selectedStreamCamera);

      return (
        <div className="space-y-4">
          <div className="relative aspect-video bg-muted rounded-md overflow-hidden">
            {isStreaming ? (
              <img
                ref={setVideoRef(selectedStreamCamera)}
                className="w-full h-full object-contain"
                alt={`${selectedStreamCamera} Stream`}
                onError={() => setError(`Failed to load stream for ${selectedStreamCamera}`)}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <div className="text-center">
                  <Camera className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Click Start to begin camera stream</p>
                  {camera && (
                    <p className="text-sm">
                      {camera.resolution[0]}x{camera.resolution[1]} @ {camera.fps.toFixed(1)} FPS
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {camera && (
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{camera.name}</span>
              <Badge variant={getStatusVariant(isStreaming)}>
                {isStreaming ? 'Streaming' : 'Ready'}
              </Badge>
            </div>
          )}
        </div>
      );
    }

    // Grid view
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {streamCameras.map((camera) => {
          const isStreaming = streamingCameras.has(camera.name);

          return (
            <Card key={camera.name}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center justify-between">
                  <span>{camera.name}</span>
                  <Badge variant={getStatusVariant(isStreaming)}>
                    {isStreaming ? 'Live' : 'Ready'}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative aspect-video bg-muted rounded-md overflow-hidden mb-2">
                  {isStreaming ? (
                    <img
                      ref={setVideoRef(camera.name)}
                      className="w-full h-full object-contain"
                      alt={`${camera.name} Stream`}
                      onError={() => setError(`Failed to load stream for ${camera.name}`)}
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                      <Camera className="h-8 w-8 opacity-50" />
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                  <span>{camera.resolution[0]}x{camera.resolution[1]}</span>
                  <span>{camera.fps.toFixed(1)} FPS</span>
                </div>

                <div className="flex gap-1">
                  {isStreaming ? (
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => stopStream(camera.name)}
                      disabled={isLoading}
                    >
                      <Square className="h-3 w-3 mr-1" />
                      Stop
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      className="flex-1"
                      onClick={() => startStream(camera.name, false)}
                      disabled={isLoading || !privacyAcknowledged}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      Start
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <SecurityNotice />

      {/* AI-Vision System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            AI-Vision System Status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <Badge variant={status?.model_loaded ? 'default' : 'secondary'}>
                {status?.model_loaded ? 'Model Loaded' : 'Model Not Loaded'}
              </Badge>
              <p className="text-sm text-muted-foreground mt-1">
                {status?.model_name || 'No Model'}
              </p>
            </div>
            <div className="text-center">
              <Badge variant={aiVisionActive ? 'default' : 'secondary'}>
                {aiVisionActive ? 'Active' : 'Inactive'}
              </Badge>
              <p className="text-sm text-muted-foreground mt-1">AI Detection</p>
            </div>
            <div className="text-center">
              <Badge variant="outline">
                {status?.fps.toFixed(1) || '0.0'} FPS
              </Badge>
              <p className="text-sm text-muted-foreground mt-1">Performance</p>
            </div>
            <div className="text-center">
              <Badge variant="outline">
                {status?.total_detections || 0}
              </Badge>
              <p className="text-sm text-muted-foreground mt-1">Total Detections</p>
            </div>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex gap-2">
            {aiVisionActive ? (
              <Button
                onClick={stopAiVision}
                disabled={isLoading}
                variant="outline"
              >
                <Square className="h-4 w-4 mr-2" />
                Stop AI-Vision
              </Button>
            ) : (
              <Button
                onClick={startAiVision}
                disabled={isLoading || !privacyAcknowledged}
              >
                <Play className="h-4 w-4 mr-2" />
                Start AI-Vision
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Camera Streaming System */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            Camera Streaming System
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Controls */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Badge variant="outline">
                {streamCameras.length} Camera{streamCameras.length !== 1 ? 's' : ''} Found
              </Badge>
              {streamingCameras.size > 0 && (
                <Badge variant="default">
                  {streamingCameras.size} Streaming
                </Badge>
              )}
            </div>

            <Button
              onClick={() => setViewMode(viewMode === 'single' ? 'grid' : 'single')}
              variant="outline"
              size="sm"
            >
              {viewMode === 'single' ? (
                <>
                  <Grid3X3 className="h-4 w-4 mr-2" />
                  Grid View
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4 mr-2" />
                  Single View
                </>
              )}
            </Button>
          </div>

          {/* Camera Selection for Single View */}
          {viewMode === 'single' && streamCameras.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Camera</Label>
                <Select
                  value={selectedStreamCamera}
                  onValueChange={setSelectedStreamCamera}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select camera" />
                  </SelectTrigger>
                  <SelectContent>
                    {streamCameras.map((camera) => (
                      <SelectItem key={camera.name} value={camera.name}>
                        {camera.name} ({camera.resolution[0]}x{camera.resolution[1]})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Actions</Label>
                <div className="flex gap-2">
                  {streamingCameras.has(selectedStreamCamera) ? (
                    <Button
                      onClick={() => stopStream(selectedStreamCamera)}
                      disabled={isLoading}
                      variant="outline"
                      size="sm"
                    >
                      <Square className="h-4 w-4 mr-2" />
                      Stop
                    </Button>
                  ) : (
                    <Button
                      onClick={() => startStream(selectedStreamCamera, false)}
                      disabled={isLoading || !privacyAcknowledged}
                      size="sm"
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Start
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Video Display */}
          {renderCameraView()}
        </CardContent>
      </Card>

      {/* DepthAI Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            DepthAI System
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              DepthAI/OAK camera streaming is available through the official Luxonis interface.
              To access DepthAI streaming, run the provided Python script manually.
            </p>
            <div className="bg-muted p-3 rounded-md">
              <code className="text-sm">
                python depthai_streaming.py
              </code>
            </div>
            <p className="text-xs text-muted-foreground">
              Once started, DepthAI streaming will be available at: http://localhost:8083
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}