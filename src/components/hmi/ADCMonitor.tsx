import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { HMIDisplay } from '@/components/ui/hmi-display';
import { Button } from '@/components/ui/button';
import { HMISlider } from '@/components/ui/hmi-slider';
import { HMIApiService, ADCReading } from '@/services/hmi-api';
import { ADCChart } from './ADCChart';
import { BarChart3, Zap, Settings2, TrendingUp } from 'lucide-react';

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

  // Function to read a single sample for averaging
  const readSingleSample = async (): Promise<ADCReading[] | null> => {
    try {
      const response = await apiService.readAllADCChannels();
      if (response.success && response.data) {
        return response.data.channels;
      }
    } catch (error) {
      console.error('Failed to read sample:', error);
    }
    return null;
  };

  // Function to compute averaged readings from samples
  const computeAveragedReadings = (samples: ADCReading[][]): ADCReading[] => {
    if (samples.length === 0) return [];

    const channelCount = 8;
    const averagedChannels: ADCReading[] = [];

    for (let ch = 0; ch < channelCount; ch++) {
      let totalRaw = 0;
      let totalVoltage = 0;
      let validSamples = 0;

      samples.forEach(sample => {
        const channelData = sample.find(c => c.channel === ch);
        if (channelData) {
          totalRaw += channelData.raw_value;
          totalVoltage += channelData.voltage;
          validSamples++;
        }
      });

      if (validSamples > 0) {
        averagedChannels.push({
          channel: ch,
          raw_value: Math.round(totalRaw / validSamples),
          voltage: totalVoltage / validSamples,
          vref: vref
        });
      }
    }

    return averagedChannels;
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
      let sampleInterval: NodeJS.Timeout;
      let updateInterval: NodeJS.Timeout;
      const samples: ADCReading[][] = [];

      // Collect samples every 500ms (6 samples over 3 seconds)
      sampleInterval = setInterval(async () => {
        const sample = await readSingleSample();
        if (sample) {
          samples.push(sample);
          // Keep only the last 6 samples (3 seconds worth)
          if (samples.length > 6) {
            samples.shift();
          }
        }
      }, 500);

      // Update display with averaged values every 3 seconds
      updateInterval = setInterval(() => {
        if (samples.length > 0) {
          const averagedChannels = computeAveragedReadings(samples);
          setChannels(averagedChannels);
        }
      }, 3000);

      return () => {
        clearInterval(sampleInterval);
        clearInterval(updateInterval);
      };
    }
  }, [autoRefresh, vref]);

  const getVoltageStatus = (voltage: number, vref: number): 'normal' | 'warning' | 'error' => {
    const percentage = (voltage / vref) * 100;
    if (percentage > 90) return 'warning';
    if (percentage < 5) return 'error';
    return 'normal';
  };

  return (
    <Tabs defaultValue="monitor" className="w-full">
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="monitor" className="flex items-center gap-2">
          <Zap className="w-4 h-4" />
          Real-time Monitor
        </TabsTrigger>
        <TabsTrigger value="chart" className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          Data Chart
        </TabsTrigger>
      </TabsList>

      <TabsContent value="monitor" className="space-y-4">
        <Card className="hmi-panel">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary" />
              ADC Monitor (ADS7828 - 0x48)
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
      </TabsContent>

      <TabsContent value="chart" className="space-y-4">
        <ADCChart apiService={apiService} />
      </TabsContent>
    </Tabs>
  );
}