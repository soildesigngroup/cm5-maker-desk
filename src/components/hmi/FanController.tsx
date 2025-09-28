import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { HMISlider } from '@/components/ui/hmi-slider';
import { HMIDisplay } from '@/components/ui/hmi-display';
import { Button } from '@/components/ui/button';
import { StatusIndicator } from '@/components/ui/status-indicator';
import { HMIApiService, FanStatus } from '@/services/hmi-api';
import { Fan, Gauge, Zap, AlertTriangle } from 'lucide-react';

interface FanControllerProps {
  apiService: HMIApiService;
}

type ControlMode = 'pwm' | 'rpm';

export function FanController({ apiService }: FanControllerProps) {
  const [fanStatus, setFanStatus] = useState<FanStatus | null>(null);
  const [controlMode, setControlMode] = useState<ControlMode>('pwm');
  const [pwmValue, setPwmValue] = useState<number>(0);
  const [rpmValue, setRpmValue] = useState<number>(0);
  const [isUpdating, setIsUpdating] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [rpmHistory, setRpmHistory] = useState<number[]>([]);

  const getFanStatus = async () => {
    try {
      const response = await apiService.getFanStatus();
      if (response.success && response.data) {
        setFanStatus(response.data);
        if (!isUpdating) {
          setPwmValue(response.data.duty_cycle);
          setRpmValue(response.data.target_rpm);
        }
      }
    } catch (error) {
      console.error('Failed to get fan status:', error);
    }
  };

  // Function to read a single RPM sample for averaging
  const readRpmSample = async (): Promise<FanStatus | null> => {
    try {
      const response = await apiService.getFanStatus();
      if (response.success && response.data) {
        return response.data;
      }
    } catch (error) {
      console.error('Failed to read fan sample:', error);
    }
    return null;
  };

  // Function to compute averaged fan status
  const computeAveragedStatus = (samples: FanStatus[]): FanStatus => {
    if (samples.length === 0) return { rpm: 0, target_rpm: 0, duty_cycle: 0 };

    const avgRpm = samples.reduce((sum, sample) => sum + sample.rpm, 0) / samples.length;
    const avgDutyCycle = samples.reduce((sum, sample) => sum + sample.duty_cycle, 0) / samples.length;
    const lastTargetRpm = samples[samples.length - 1].target_rpm; // Use latest target
    const hasFailure = samples.some(sample => sample.failure);

    return {
      rpm: Math.round(avgRpm),
      target_rpm: lastTargetRpm,
      duty_cycle: Math.round(avgDutyCycle * 10) / 10, // Round to 1 decimal
      failure: hasFailure
    };
  };

  const updatePWM = async (newPwm: number) => {
    setIsUpdating(true);
    try {
      const response = await apiService.setFanPWM(newPwm);
      if (response.success) {
        setPwmValue(newPwm);
        // Refresh status after a short delay
        setTimeout(getFanStatus, 500);
      }
    } catch (error) {
      console.error('Failed to set PWM:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  const updateRPM = async (newRpm: number) => {
    setIsUpdating(true);
    try {
      const response = await apiService.setFanRPM(newRpm);
      if (response.success) {
        setRpmValue(newRpm);
        // Refresh status after a short delay
        setTimeout(getFanStatus, 500);
      }
    } catch (error) {
      console.error('Failed to set RPM:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  useEffect(() => {
    getFanStatus();

    if (autoRefresh) {
      let sampleInterval: NodeJS.Timeout;
      let updateInterval: NodeJS.Timeout;
      const samples: FanStatus[] = [];

      // Collect samples every 500ms (6 samples over 3 seconds)
      sampleInterval = setInterval(async () => {
        const sample = await readRpmSample();
        if (sample) {
          samples.push(sample);
          // Keep only the last 6 samples (3 seconds worth)
          if (samples.length > 6) {
            samples.shift();
          }
          // Update RPM history for display purposes
          setRpmHistory(samples.map(s => s.rpm));
        }
      }, 500);

      // Update display with averaged values every 3 seconds
      updateInterval = setInterval(() => {
        if (samples.length > 0) {
          const averagedStatus = computeAveragedStatus(samples);
          setFanStatus(averagedStatus);
          if (!isUpdating) {
            setPwmValue(averagedStatus.duty_cycle);
            setRpmValue(averagedStatus.target_rpm);
          }
        }
      }, 3000);

      return () => {
        clearInterval(sampleInterval);
        clearInterval(updateInterval);
      };
    }
  }, [autoRefresh, isUpdating]);

  const getFanStatusColor = (): 'normal' | 'warning' | 'error' => {
    if (!fanStatus) return 'normal';
    if (fanStatus.failure) return 'error';
    if (fanStatus.rpm > 0 && fanStatus.rpm < fanStatus.target_rpm * 0.8) return 'warning';
    return 'normal';
  };

  const getRPMPercentage = (): number => {
    if (!fanStatus || fanStatus.target_rpm === 0) return 0;
    return Math.min((fanStatus.rpm / fanStatus.target_rpm) * 100, 100);
  };

  return (
    <Card className="hmi-panel">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="flex items-center gap-2">
          <Fan className={`w-5 h-5 text-primary ${fanStatus && fanStatus.rpm > 0 ? 'animate-spin' : ''}`} />
          Fan Controller (EMC2301 - 0x2F)
        </CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            Auto Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Fan Status Display */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-secondary/30 rounded-lg">
          <HMIDisplay
            label="Current RPM"
            value={fanStatus?.rpm ?? 0}
            unit="RPM"
            variant="large"
            status={getFanStatusColor()}
          />
          <HMIDisplay
            label="Target RPM"
            value={fanStatus?.target_rpm ?? 0}
            unit="RPM"
            variant="default"
          />
          <HMIDisplay
            label="Duty Cycle"
            value={fanStatus ? fanStatus.duty_cycle.toFixed(1) : '0.0'}
            unit="%"
            variant="default"
          />
        </div>

        {/* Fan Status Indicators */}
        <div className="flex items-center justify-between p-4 bg-card border border-border rounded-lg">
          <div className="flex items-center gap-4">
            <StatusIndicator
              status={fanStatus?.rpm && fanStatus.rpm > 0 ? 'connected' : 'disconnected'}
              label="Fan Running"
              showPulse={true}
            />
            {fanStatus?.failure && (
              <div className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-sm font-medium">Fan Failure Detected</span>
              </div>
            )}
          </div>
          
          {/* RPM Progress Bar */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Performance:</span>
            <div className="w-24 bg-secondary rounded-full h-2">
              <div
                className={`h-full rounded-full hmi-transition ${
                  getFanStatusColor() === 'normal' ? 'bg-primary' :
                  getFanStatusColor() === 'warning' ? 'bg-warning' : 'bg-destructive'
                }`}
                style={{ width: `${getRPMPercentage()}%` }}
              />
            </div>
            <span className="text-xs font-mono">{getRPMPercentage().toFixed(0)}%</span>
          </div>
        </div>

        {/* Control Mode Selection */}
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">Control Mode:</span>
            <div className="flex gap-2">
              <Button
                variant={controlMode === 'pwm' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setControlMode('pwm')}
                className="flex items-center gap-2"
              >
                <Zap className="w-4 h-4" />
                PWM
              </Button>
              <Button
                variant={controlMode === 'rpm' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setControlMode('rpm')}
                className="flex items-center gap-2"
              >
                <Gauge className="w-4 h-4" />
                RPM
              </Button>
            </div>
          </div>

          {/* PWM Control */}
          {controlMode === 'pwm' && (
            <div className="space-y-4 p-4 bg-secondary/30 rounded-lg">
              <HMISlider
                label="PWM Duty Cycle"
                value={pwmValue}
                onChange={(value) => {
                  setPwmValue(value);
                  // Debounced update
                  clearTimeout(window.pwmTimeout);
                  window.pwmTimeout = setTimeout(() => updatePWM(value), 500);
                }}
                min={0}
                max={100}
                step={1}
                unit="%"
                disabled={isUpdating}
              />
              <div className="text-xs text-muted-foreground">
                PWM control directly sets the duty cycle percentage. Fan RPM will vary based on load and fan characteristics.
              </div>
            </div>
          )}

          {/* RPM Control */}
          {controlMode === 'rpm' && (
            <div className="space-y-4 p-4 bg-secondary/30 rounded-lg">
              <HMISlider
                label="Target RPM"
                value={rpmValue}
                onChange={(value) => {
                  setRpmValue(value);
                  // Debounced update
                  clearTimeout(window.rpmTimeout);
                  window.rpmTimeout = setTimeout(() => updateRPM(value), 500);
                }}
                min={0}
                max={5000}
                step={50}
                unit="RPM"
                disabled={isUpdating}
              />
              <div className="text-xs text-muted-foreground">
                RPM control uses closed-loop feedback to maintain the target speed. The controller will automatically adjust PWM.
              </div>
            </div>
          )}
        </div>

        {/* Quick Presets */}
        <div className="space-y-3">
          <div className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            Quick Presets
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={() => controlMode === 'pwm' ? updatePWM(0) : updateRPM(0)}
              disabled={isUpdating}
            >
              Stop
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => controlMode === 'pwm' ? updatePWM(25) : updateRPM(1000)}
              disabled={isUpdating}
            >
              Low
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => controlMode === 'pwm' ? updatePWM(50) : updateRPM(2000)}
              disabled={isUpdating}
            >
              Medium
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => controlMode === 'pwm' ? updatePWM(75) : updateRPM(3000)}
              disabled={isUpdating}
            >
              High
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => controlMode === 'pwm' ? updatePWM(100) : updateRPM(4000)}
              disabled={isUpdating}
            >
              Max
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Extend Window interface for timeout storage
declare global {
  interface Window {
    pwmTimeout: ReturnType<typeof setTimeout>;
    rpmTimeout: ReturnType<typeof setTimeout>;
  }
}