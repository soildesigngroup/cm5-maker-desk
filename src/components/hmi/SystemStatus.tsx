import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusIndicator } from '@/components/ui/status-indicator';
import { Button } from '@/components/ui/button';
import { HMIApiService, SystemStatus as SystemStatusType } from '@/services/hmi-api';
import { Activity, Wifi, WifiOff, Settings } from 'lucide-react';

interface SystemStatusProps {
  apiService: HMIApiService;
}

export function SystemStatus({ apiService }: SystemStatusProps) {
  const [systemStatus, setSystemStatus] = useState<SystemStatusType | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshStatus = async () => {
    setIsRefreshing(true);
    try {
      const response = await apiService.getSystemStatus();
      if (response.success && response.data) {
        setSystemStatus(response.data);
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('disconnected');
      }
    } catch (error) {
      setConnectionStatus('disconnected');
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const deviceCount = systemStatus ? Object.keys(systemStatus.devices).length : 0;
  const connectedDevices = systemStatus 
    ? Object.values(systemStatus.devices).filter(device => device.connected).length 
    : 0;

  return (
    <Card className="hmi-panel">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          System Status
        </CardTitle>
        <Button
          variant="hmi"
          size="sm"
          onClick={refreshStatus}
          disabled={isRefreshing}
        >
          <Settings className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <StatusIndicator
              status={connectionStatus === 'connected' ? 'connected' : 'disconnected'}
              label="API Connection"
            />
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              {connectionStatus === 'connected' ? (
                <Wifi className="w-4 h-4" />
              ) : (
                <WifiOff className="w-4 h-4" />
              )}
              {connectionStatus === 'connected' ? 'Online' : 'Offline'}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Devices</div>
            <div className="text-2xl font-mono">
              {connectedDevices}/{deviceCount}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Monitoring</div>
            <StatusIndicator
              status={systemStatus?.monitoring_active ? 'connected' : 'disconnected'}
              label={systemStatus?.monitoring_active ? 'Active' : 'Inactive'}
            />
          </div>
        </div>

        {systemStatus && (
          <div className="space-y-3 pt-4 border-t border-border">
            <div className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              Device Status
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
              {Object.entries(systemStatus.devices).map(([deviceId, device]) => (
                <div key={deviceId} className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg">
                  <div>
                    <div className="text-sm font-medium capitalize">{deviceId}</div>
                    <div className="text-xs text-muted-foreground">{device.device_type}</div>
                  </div>
                  <StatusIndicator
                    status={device.connected ? 'connected' : 'disconnected'}
                    showPulse={device.connected}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}