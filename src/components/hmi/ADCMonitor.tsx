import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { HMIDisplay } from '@/components/ui/hmi-display';
import { Button } from '@/components/ui/button';
import { HMISlider } from '@/components/ui/hmi-slider';
import { HMIApiService, ADCReading } from '@/services/hmi-api';
import { BarChart3, Zap, Settings2 } from 'lucide-react';

interface ADCMonitorProps {
  apiService: HMIApiService;
}

export function ADCMonitor({ apiService }: ADCMonitorProps) {
  const [channels, setChannels] = useState<ADCReading[]>([]);
  const [vref, setVref] = useState<number>(3.3);
  const [isReading, setIsReading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const readAllChannels = async () => {
    setIsReading(true);
    try {
      const response = await apiService.readAllADCChannels();
      if (response.success && response.data) {
        setChannels(response.data.channels);
        setVref(response.data.vref);
      }
    } catch (error) {
      console.error('Failed to read ADC channels:', error);
    } finally {
      setIsReading(false);
    }
  };

  const updateVref = async (newVref: number) => {
    try {
      const response = await apiService.setADCVref(newVref);
      if (response.success) {
        setVref(newVref);
        // Refresh readings after vref change
        readAllChannels();
      }
    } catch (error) {
      console.error('Failed to set Vref:', error);
    }
  };

  useEffect(() => {
    readAllChannels();
    
    if (autoRefresh) {
      const interval = setInterval(readAllChannels, 1000); // 1 second refresh
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getVoltageStatus = (voltage: number, vref: number): 'normal' | 'warning' | 'error' => {
    const percentage = (voltage / vref) * 100;
    if (percentage > 90) return 'warning';
    if (percentage < 5) return 'error';
    return 'normal';
  };

  return (
    <Card className="hmi-panel">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-primary" />
          ADC Monitor (ADS7828)
        </CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="hmi"
            size="sm"
            onClick={readAllChannels}
            disabled={isReading}
          >
            <Zap className={`w-4 h-4 ${isReading ? 'animate-pulse' : ''}`} />
            {isReading ? 'Reading...' : 'Read'}
          </Button>
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Settings2 className="w-4 h-4" />
            Auto
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Vref Control */}
        <div className="space-y-4 p-4 bg-secondary/30 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Reference Voltage</span>
            <HMIDisplay value={vref.toFixed(2)} unit="V" variant="default" />
          </div>
          <HMISlider
            value={vref}
            onChange={updateVref}
            min={1.0}
            max={5.0}
            step={0.1}
            unit="V"
          />
        </div>

        {/* Channel Readings */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }, (_, i) => {
            const channel = channels.find(ch => ch.channel === i);
            const voltage = channel?.voltage ?? 0;
            const rawValue = channel?.raw_value ?? 0;
            const status = getVoltageStatus(voltage, vref);

            return (
              <div key={i} className="space-y-2 p-4 bg-card border border-border rounded-lg hmi-transition hover:border-primary/30">
                <div className="text-xs text-muted-foreground uppercase tracking-wide text-center">
                  Channel {i}
                </div>
                <HMIDisplay
                  value={voltage.toFixed(3)}
                  unit="V"
                  variant="default"
                  status={status}
                />
                <div className="text-center">
                  <div className="text-xs text-muted-foreground">
                    Raw: {rawValue}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {((voltage / vref) * 100).toFixed(1)}%
                  </div>
                </div>
                
                {/* Visual bar indicator */}
                <div className="w-full bg-secondary rounded-full h-2 overflow-hidden">
                  <div 
                    className={`h-full hmi-transition ${
                      status === 'normal' ? 'bg-primary' :
                      status === 'warning' ? 'bg-warning' : 'bg-destructive'
                    }`}
                    style={{ width: `${Math.min((voltage / vref) * 100, 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Summary Statistics */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border">
          <HMIDisplay
            label="Max Voltage"
            value={channels.length > 0 ? Math.max(...channels.map(ch => ch.voltage)).toFixed(3) : '0.000'}
            unit="V"
          />
          <HMIDisplay
            label="Min Voltage"
            value={channels.length > 0 ? Math.min(...channels.map(ch => ch.voltage)).toFixed(3) : '0.000'}
            unit="V"
          />
          <HMIDisplay
            label="Avg Voltage"
            value={channels.length > 0 ? (channels.reduce((sum, ch) => sum + ch.voltage, 0) / channels.length).toFixed(3) : '0.000'}
            unit="V"
          />
        </div>
      </CardContent>
    </Card>
  );
}