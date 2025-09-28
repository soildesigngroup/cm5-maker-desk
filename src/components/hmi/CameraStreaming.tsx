import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Camera, Play, Square, Settings, Eye, Activity, Grid3X3, RefreshCw } from 'lucide-react';

interface CameraInfo {
  name: string;
  device_id: number;
  resolution: [number, number];
  fps: number;
  status: string;
  last_frame_time: number;
  ai_enabled: boolean;
}

interface CameraStreamingProps {
  className?: string;
}

const CAMERA_API_BASE = 'http://localhost:8082';

export function CameraStreaming({ className }: CameraStreamingProps) {
  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string>('');
  const [streamingCameras, setStreamingCameras] = useState<Set<string>>(new Set());
  const [aiEnabled, setAiEnabled] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'single' | 'grid'>('single');

  const videoRefs = useRef<Record<string, HTMLImageElement>>({});

  // Fetch available cameras
  const fetchCameras = async () => {
    try {
      const response = await fetch(`${CAMERA_API_BASE}/api/cameras`);
      const data = await response.json();

      if (data.success) {
        setCameras(data.cameras);
        if (data.cameras.length > 0 && !selectedCamera) {
          setSelectedCamera(data.cameras[0].name);
        }
      } else {
        setError(data.error || 'Failed to fetch cameras');
      }
    } catch (error) {
      console.error('Failed to fetch cameras:', error);
      setError('Failed to connect to camera service');
    }
  };

  // Start camera stream
  const startStream = async (cameraName: string, withAI: boolean = false) => {
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

  // Handle start button click
  const handleStart = () => {
    if (selectedCamera) {
      startStream(selectedCamera, aiEnabled);
    }
  };

  // Handle stop button click
  const handleStop = () => {
    if (selectedCamera) {
      stopStream(selectedCamera);
    }
  };

  // Handle start all cameras
  const handleStartAll = () => {
    cameras.forEach(camera => {
      if (!streamingCameras.has(camera.name)) {
        startStream(camera.name, aiEnabled);
      }
    });
  };

  // Handle stop all cameras
  const handleStopAll = () => {
    streamingCameras.forEach(cameraName => {
      stopStream(cameraName);
    });
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
    fetchCameras();
    const interval = setInterval(fetchCameras, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  // Get status variant for badges
  const getStatusVariant = (isStreaming: boolean) => {
    return isStreaming ? 'default' : 'secondary';
  };

  // Render single camera view
  const renderSingleCamera = () => {
    const camera = cameras.find(c => c.name === selectedCamera);
    const isStreaming = streamingCameras.has(selectedCamera);

    return (
      <div className="space-y-4">
        <div className="relative aspect-video bg-muted rounded-md overflow-hidden">
          {isStreaming ? (
            <img
              ref={setVideoRef(selectedCamera)}
              className="w-full h-full object-contain"
              alt={`${selectedCamera} Stream`}
              onError={() => setError(`Failed to load stream for ${selectedCamera}`)}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center">
                <Camera className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>Start camera to see live stream</p>
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
  };

  // Render grid view of all cameras
  const renderGridView = () => {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cameras.map((camera) => {
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
                      onClick={() => startStream(camera.name, aiEnabled)}
                      disabled={isLoading}
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
    <div className={`space-y-6 ${className}`}>
      {/* Controls Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            Camera Streaming System
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Status Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Badge variant="outline">
                  {cameras.length} Camera{cameras.length !== 1 ? 's' : ''} Found
                </Badge>
                {streamingCameras.size > 0 && (
                  <Badge variant="default">
                    {streamingCameras.size} Streaming
                  </Badge>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={fetchCameras}
                variant="outline"
                size="sm"
                disabled={isLoading}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>

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
          </div>

          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md">
              {error}
            </div>
          )}

          {/* Configuration */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Camera Selection (Single View Only) */}
            {viewMode === 'single' && (
              <div className="space-y-2">
                <Label>Camera</Label>
                <Select
                  value={selectedCamera}
                  onValueChange={setSelectedCamera}
                  disabled={cameras.length === 0}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select camera" />
                  </SelectTrigger>
                  <SelectContent>
                    {cameras.map((camera) => (
                      <SelectItem key={camera.name} value={camera.name}>
                        {camera.name} ({camera.resolution[0]}x{camera.resolution[1]})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* AI Processing Toggle */}
            <div className="space-y-2">
              <Label>AI Processing</Label>
              <div className="flex items-center space-x-2">
                <Switch
                  id="ai-processing"
                  checked={aiEnabled}
                  onCheckedChange={setAiEnabled}
                />
                <Label htmlFor="ai-processing" className="text-sm font-normal">
                  Enable AI object detection
                </Label>
              </div>
            </div>

            {/* Controls */}
            <div className="space-y-2">
              <Label>Actions</Label>
              <div className="flex gap-2">
                {viewMode === 'single' ? (
                  <>
                    {streamingCameras.has(selectedCamera) ? (
                      <Button
                        onClick={handleStop}
                        disabled={isLoading || !selectedCamera}
                        variant="outline"
                        size="sm"
                      >
                        <Square className="h-4 w-4 mr-2" />
                        Stop
                      </Button>
                    ) : (
                      <Button
                        onClick={handleStart}
                        disabled={isLoading || !selectedCamera}
                        size="sm"
                      >
                        <Play className="h-4 w-4 mr-2" />
                        Start
                      </Button>
                    )}
                  </>
                ) : (
                  <>
                    <Button
                      onClick={handleStartAll}
                      disabled={isLoading || cameras.length === 0}
                      size="sm"
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Start All
                    </Button>
                    <Button
                      onClick={handleStopAll}
                      disabled={isLoading || streamingCameras.size === 0}
                      variant="outline"
                      size="sm"
                    >
                      <Square className="h-4 w-4 mr-2" />
                      Stop All
                    </Button>
                  </>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Video Display Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Live Camera {viewMode === 'single' ? 'Stream' : 'Streams'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {viewMode === 'single' ? renderSingleCamera() : renderGridView()}
        </CardContent>
      </Card>
    </div>
  );
}