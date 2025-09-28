import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { HMIDisplay } from '@/components/ui/hmi-display';
import { Button } from '@/components/ui/button';
import { HMIApiService } from '@/services/hmi-api';
import { Clock, Calendar, RefreshCw } from 'lucide-react';

interface RTCDisplayProps {
  apiService: HMIApiService;
}

export function RTCDisplay({ apiService }: RTCDisplayProps) {
  const [rtcDateTime, setRtcDateTime] = useState<string>('');
  const [systemDateTime, setSystemDateTime] = useState<string>('');
  const [timeDrift, setTimeDrift] = useState<number>(0);
  const [isReading, setIsReading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const readRTCTime = async () => {
    setIsReading(true);
    try {
      const response = await apiService.getRTCDateTime();
      if (response.success && response.data) {
        setRtcDateTime(response.data.datetime);
        
        // Calculate time drift
        const rtcTime = new Date(response.data.datetime).getTime();
        const systemTime = Date.now();
        setTimeDrift((systemTime - rtcTime) / 1000); // in seconds
      }
    } catch (error) {
      console.error('Failed to read RTC time:', error);
    } finally {
      setIsReading(false);
    }
  };

  const syncSystemToRTC = async () => {
    try {
      const now = new Date().toISOString();
      const response = await apiService.setRTCDateTime(now);
      if (response.success) {
        readRTCTime();
      }
    } catch (error) {
      console.error('Failed to sync system time to RTC:', error);
    }
  };

  useEffect(() => {
    // Update system time display
    const updateSystemTime = () => {
      setSystemDateTime(new Date().toISOString());
    };
    
    updateSystemTime();
    const systemTimeInterval = setInterval(updateSystemTime, 1000);
    
    return () => clearInterval(systemTimeInterval);
  }, []);

  useEffect(() => {
    readRTCTime();
    
    if (autoRefresh) {
      const interval = setInterval(readRTCTime, 5000); // 5 second refresh
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const formatDateTime = (isoString: string) => {
    if (!isoString) return { date: '--', time: '--' };
    
    const date = new Date(isoString);
    return {
      date: date.toLocaleDateString(),
      time: date.toLocaleTimeString(),
    };
  };

  const rtcFormatted = formatDateTime(rtcDateTime);
  const systemFormatted = formatDateTime(systemDateTime);

  const getDriftStatus = (): 'normal' | 'warning' | 'error' => {
    const absDrift = Math.abs(timeDrift);
    if (absDrift > 60) return 'error';     // More than 1 minute
    if (absDrift > 10) return 'warning';   // More than 10 seconds
    return 'normal';
  };

  return (
    <Card className="hmi-panel">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-primary" />
          Real-Time Clock (PCF85063A - 0x51)
        </CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="hmi"
            size="sm"
            onClick={readRTCTime}
            disabled={isReading}
          >
            <RefreshCw className={`w-4 h-4 ${isReading ? 'animate-spin' : ''}`} />
            {isReading ? 'Reading...' : 'Read'}
          </Button>
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            Auto
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Time Displays */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* RTC Time */}
          <div className="space-y-4 p-4 bg-secondary/30 rounded-lg">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground uppercase tracking-wide">
              <Clock className="w-4 h-4" />
              RTC Time
            </div>
            <div className="space-y-2">
              <HMIDisplay
                value={rtcFormatted.time}
                variant="large"
                className="text-center"
              />
              <HMIDisplay
                value={rtcFormatted.date}
                variant="default"
                className="text-center"
              />
            </div>
          </div>

          {/* System Time */}
          <div className="space-y-4 p-4 bg-secondary/30 rounded-lg">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground uppercase tracking-wide">
              <Calendar className="w-4 h-4" />
              System Time
            </div>
            <div className="space-y-2">
              <HMIDisplay
                value={systemFormatted.time}
                variant="large"
                className="text-center"
              />
              <HMIDisplay
                value={systemFormatted.date}
                variant="default"
                className="text-center"
              />
            </div>
          </div>
        </div>

        {/* Time Drift Analysis */}
        <div className="p-4 bg-card border border-border rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              Time Synchronization
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={syncSystemToRTC}
            >
              Sync System → RTC
            </Button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <HMIDisplay
              label="Time Drift"
              value={timeDrift.toFixed(1)}
              unit="sec"
              variant="default"
              status={getDriftStatus()}
            />
            <HMIDisplay
              label="Drift Status"
              value={
                getDriftStatus() === 'normal' ? 'SYNC' :
                getDriftStatus() === 'warning' ? 'DRIFT' : 'ERROR'
              }
              variant="default"
              status={getDriftStatus()}
            />
            <HMIDisplay
              label="Last Update"
              value={rtcDateTime ? new Date(rtcDateTime).toLocaleTimeString() : '--'}
              variant="default"
            />
          </div>

          {/* Drift explanation */}
          <div className="mt-4 text-xs text-muted-foreground">
            {getDriftStatus() === 'normal' && 'RTC and system time are synchronized (drift < 10 seconds).'}
            {getDriftStatus() === 'warning' && 'Moderate time drift detected (10-60 seconds). Consider synchronization.'}
            {getDriftStatus() === 'error' && 'Significant time drift detected (>60 seconds). Synchronization recommended.'}
          </div>
        </div>

        {/* RTC Health Indicators */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border">
          <div className="text-center">
            <div className={`text-2xl font-mono ${
              rtcDateTime ? 'text-success' : 'text-muted-foreground'
            }`}>
              {rtcDateTime ? '✓' : '✗'}
            </div>
            <div className="text-xs text-muted-foreground">Connected</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-mono ${
              getDriftStatus() === 'normal' ? 'text-success' : 
              getDriftStatus() === 'warning' ? 'text-warning' : 'text-destructive'
            }`}>
              {getDriftStatus() === 'normal' ? '✓' : '⚠'}
            </div>
            <div className="text-xs text-muted-foreground">Accuracy</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-mono ${
              autoRefresh ? 'text-primary' : 'text-muted-foreground'
            }`}>
              {autoRefresh ? '↻' : '○'}
            </div>
            <div className="text-xs text-muted-foreground">Monitoring</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}