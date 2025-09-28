import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { HMIToggle } from '@/components/ui/hmi-toggle';
import { Button } from '@/components/ui/button';
import { StatusIndicator } from '@/components/ui/status-indicator';
import { HMIApiService } from '@/services/hmi-api';
import { ToggleLeft, RefreshCw, Settings } from 'lucide-react';

interface IOControlProps {
  apiService: HMIApiService;
}

interface PinState {
  pin: number;
  state: boolean;
  configured: boolean;
  direction: 'input' | 'output';
}

export function IOControl({ apiService }: IOControlProps) {
  const [pinStates, setPinStates] = useState<PinState[]>([]);
  const [isReading, setIsReading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const initializePins = () => {
    // Initialize 16 pins (0-15)
    const initialPins: PinState[] = Array.from({ length: 16 }, (_, i) => ({
      pin: i,
      state: false,
      configured: false,
      direction: 'output',
    }));
    setPinStates(initialPins);
  };

  const readAllPins = async () => {
    setIsReading(true);
    try {
      const response = await apiService.readAllIOPins();
      if (response.success && response.data) {
        setPinStates(prev => 
          prev.map(pin => {
            const readData = response.data.pins.find(p => p.pin === pin.pin);
            return readData ? { ...pin, state: readData.state, configured: true } : pin;
          })
        );
      }
    } catch (error) {
      console.error('Failed to read I/O pins:', error);
    } finally {
      setIsReading(false);
    }
  };

  const togglePin = async (pin: number, newState: boolean) => {
    try {
      const response = await apiService.writeIOPin(pin, newState);
      if (response.success) {
        setPinStates(prev =>
          prev.map(p => p.pin === pin ? { ...p, state: newState } : p)
        );
      }
    } catch (error) {
      console.error(`Failed to toggle pin ${pin}:`, error);
    }
  };

  const configurePin = async (pin: number, direction: 'input' | 'output') => {
    try {
      const response = await apiService.configureIOPin(pin, direction, false);
      if (response.success) {
        setPinStates(prev =>
          prev.map(p => p.pin === pin ? { ...p, direction, configured: true } : p)
        );
      }
    } catch (error) {
      console.error(`Failed to configure pin ${pin}:`, error);
    }
  };

  useEffect(() => {
    initializePins();
  }, []);

  useEffect(() => {
    readAllPins();
    
    if (autoRefresh) {
      const interval = setInterval(readAllPins, 2000); // 2 second refresh
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const outputPins = pinStates.filter(pin => pin.direction === 'output');
  const inputPins = pinStates.filter(pin => pin.direction === 'input');

  return (
    <Card className="hmi-panel">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="flex items-center gap-2">
          <ToggleLeft className="w-5 h-5 text-primary" />
          I/O Control (PCAL9555A - 0x24)
        </CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="hmi"
            size="sm"
            onClick={readAllPins}
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
            <Settings className="w-4 h-4" />
            Auto
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Pin Configuration */}
        <div className="space-y-4">
          <div className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            Pin Configuration
          </div>
          <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
            {Array.from({ length: 16 }, (_, i) => {
              const pin = pinStates.find(p => p.pin === i);
              return (
                <div key={i} className="flex flex-col items-center space-y-1">
                  <div className="text-xs text-muted-foreground">Pin {i}</div>
                  <div className="flex gap-1">
                    <Button
                      variant={pin?.direction === 'input' ? 'default' : 'outline'}
                      size="sm"
                      className="text-xs px-2 py-1 h-6"
                      onClick={() => configurePin(i, 'input')}
                    >
                      IN
                    </Button>
                    <Button
                      variant={pin?.direction === 'output' ? 'default' : 'outline'}
                      size="sm"
                      className="text-xs px-2 py-1 h-6"
                      onClick={() => configurePin(i, 'output')}
                    >
                      OUT
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Output Controls */}
        {outputPins.length > 0 && (
          <div className="space-y-4">
            <div className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              Output Controls
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {outputPins.map((pin) => (
                <div key={pin.pin} className="p-4 bg-secondary/30 rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Pin {pin.pin}</span>
                    <StatusIndicator
                      status={pin.state ? 'connected' : 'disconnected'}
                      showPulse={pin.state}
                    />
                  </div>
                  <HMIToggle
                    checked={pin.state}
                    onChange={(checked) => togglePin(pin.pin, checked)}
                    label={pin.state ? 'HIGH' : 'LOW'}
                    description={pin.configured ? 'Configured' : 'Not configured'}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Input Status */}
        {inputPins.length > 0 && (
          <div className="space-y-4">
            <div className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              Input Status
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
              {inputPins.map((pin) => (
                <div key={pin.pin} className="p-3 bg-card border border-border rounded-lg text-center space-y-2">
                  <div className="text-xs text-muted-foreground">Pin {pin.pin}</div>
                  <StatusIndicator
                    status={pin.state ? 'connected' : 'disconnected'}
                    showPulse={pin.state}
                  />
                  <div className="text-xs font-mono">
                    {pin.state ? 'HIGH' : 'LOW'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border">
          <div className="text-center">
            <div className="text-2xl font-mono text-primary">{outputPins.length}</div>
            <div className="text-xs text-muted-foreground">Outputs</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-mono text-primary">{inputPins.length}</div>
            <div className="text-xs text-muted-foreground">Inputs</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-mono text-primary">
              {pinStates.filter(p => p.state).length}
            </div>
            <div className="text-xs text-muted-foreground">Active</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}