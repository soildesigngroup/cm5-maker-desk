import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { HMIApiService, AIVisionStatus, DetectionResult } from '@/services/hmi-api';
import { Eye, Camera, Play, Square, AlertCircle } from 'lucide-react';

interface AIVisionProps {
  apiService: HMIApiService;
}

export function AIVision({ apiService }: AIVisionProps) {
  const [status, setStatus] = useState<AIVisionStatus | null>(null);
  const [detections, setDetections] = useState<DetectionResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [apiService]);

  const fetchStatus = async () => {
    try {
      const response = await apiService.getAIVisionStatus();
      if (response.success && response.data) {
        setStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch AI Vision status:', error);
    }
  };

  const startVision = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.startAIVision();
      if (response.success) {
        await fetchStatus();
      }
    } catch (error) {
      console.error('Failed to start AI Vision:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const stopVision = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.stopAIVision();
      if (response.success) {
        await fetchStatus();
      }
    } catch (error) {
      console.error('Failed to stop AI Vision:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchDetections = async () => {
    try {
      const response = await apiService.getDetections(5);
      if (response.success && response.data) {
        setDetections(response.data.detections);
      }
    } catch (error) {
      console.error('Failed to fetch detections:', error);
    }
  };

  useEffect(() => {
    if (status?.active) {
      fetchDetections();
      const interval = setInterval(fetchDetections, 1000);
      return () => clearInterval(interval);
    }
  }, [status?.active]);

  return (
    <div className="space-y-6">
      <Card className="hmi-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="w-5 h-5 text-primary" />
            AI Vision System
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Camera className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Status:</span>
              <Badge variant={status?.active ? "default" : "secondary"}>
                {status?.active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={status?.active ? stopVision : startVision}
                disabled={isLoading}
                variant={status?.active ? "destructive" : "default"}
                size="sm"
              >
                {status?.active ? (
                  <>
                    <Square className="w-4 h-4 mr-2" />
                    Stop
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Start
                  </>
                )}
              </Button>
            </div>
          </div>

          {status && (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Model:</span>
                <div className="font-mono">{status.model_name}</div>
              </div>
              <div>
                <span className="text-muted-foreground">FPS:</span>
                <div className="font-mono">{status.fps.toFixed(1)}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Total Detections:</span>
                <div className="font-mono">{status.total_detections}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Cameras:</span>
                <div className="font-mono">{status.available_cameras.length}</div>
              </div>
            </div>
          )}

          {status?.active && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Video Stream</h4>
              <div className="bg-muted rounded-lg aspect-video flex items-center justify-center">
                <img 
                  src={apiService.getVideoStreamUrl()} 
                  alt="AI Vision Stream"
                  className="max-w-full max-h-full rounded-lg"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
                <div className="text-muted-foreground text-sm">
                  Video Stream Unavailable
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {status?.active && (
        <Card className="hmi-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-primary" />
              Recent Detections
            </CardTitle>
          </CardHeader>
          <CardContent>
            {detections.length > 0 ? (
              <div className="space-y-2">
                {detections.map((detection, index) => (
                  <div key={index} className="border border-border rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">
                        {new Date(detection.timestamp * 1000).toLocaleTimeString()}
                      </span>
                      <Badge variant="outline">
                        {detection.detections.length} objects
                      </Badge>
                    </div>
                    <div className="mt-2 space-y-1">
                      {detection.detections.map((obj, objIndex) => (
                        <div key={objIndex} className="flex items-center justify-between text-xs">
                          <span>{obj.class_name}</span>
                          <Badge variant="secondary">
                            {(obj.confidence * 100).toFixed(1)}%
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-8">
                No detections yet
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}