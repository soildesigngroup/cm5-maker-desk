import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { StatusIndicator } from '@/components/ui/status-indicator';
import { HMIApiService } from '@/services/hmi-api';
import { Settings, Wifi, Server, TestTube2 } from 'lucide-react';

interface ConnectionSettingsProps {
  apiService: HMIApiService;
  onApiServiceChange: (newService: HMIApiService) => void;
}

export function ConnectionSettings({ apiService, onApiServiceChange }: ConnectionSettingsProps) {
  const [httpUrl, setHttpUrl] = useState('http://localhost:8080');
  const [wsUrl, setWsUrl] = useState('ws://localhost:8081');
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'testing'>('disconnected');
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const [isTesting, setIsTesting] = useState(false);

  const testConnection = async () => {
    setIsTesting(true);
    setConnectionStatus('testing');
    
    try {
      const newApiService = new HMIApiService(httpUrl);
      const isConnected = await newApiService.testConnection();
      
      if (isConnected) {
        setConnectionStatus('connected');
        onApiServiceChange(newApiService);
      } else {
        setConnectionStatus('disconnected');
      }
    } catch (error) {
      setConnectionStatus('disconnected');
    } finally {
      setIsTesting(false);
    }
  };

  const connectWebSocket = () => {
    apiService.connectWebSocket(wsUrl);
    
    apiService.on('connected', () => {
      setWsStatus('connected');
    });
    
    apiService.on('disconnected', () => {
      setWsStatus('disconnected');
    });
    
    apiService.on('error', (error) => {
      console.error('WebSocket error:', error);
      setWsStatus('disconnected');
    });
  };

  const disconnectWebSocket = () => {
    apiService.disconnectWebSocket();
    setWsStatus('disconnected');
  };

  return (
    <Card className="hmi-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5 text-primary" />
          Connection Settings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* HTTP API Connection */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">HTTP API Connection</span>
            <StatusIndicator
              status={connectionStatus}
              showPulse={connectionStatus === 'connected'}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="http-url">API Base URL</Label>
            <div className="flex gap-2">
              <Input
                id="http-url"
                value={httpUrl}
                onChange={(e) => setHttpUrl(e.target.value)}
                placeholder="http://localhost:8080"
                className="font-mono"
              />
              <Button
                onClick={testConnection}
                disabled={isTesting}
                variant="outline"
                className="flex items-center gap-2"
              >
                <TestTube2 className={`w-4 h-4 ${isTesting ? 'animate-pulse' : ''}`} />
                {isTesting ? 'Testing...' : 'Test'}
              </Button>
            </div>
          </div>

          <div className="text-xs text-muted-foreground">
            {connectionStatus === 'connected' && '✓ HTTP API connection successful'}
            {connectionStatus === 'disconnected' && '✗ Cannot connect to HTTP API'}
            {connectionStatus === 'testing' && '⏳ Testing connection...'}
          </div>
        </div>

        {/* WebSocket Connection */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Wifi className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">WebSocket Connection</span>
            <StatusIndicator
              status={wsStatus}
              showPulse={wsStatus === 'connected'}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="ws-url">WebSocket URL</Label>
            <div className="flex gap-2">
              <Input
                id="ws-url"
                value={wsUrl}
                onChange={(e) => setWsUrl(e.target.value)}
                placeholder="ws://localhost:8081"
                className="font-mono"
              />
              <Button
                onClick={wsStatus === 'connected' ? disconnectWebSocket : connectWebSocket}
                variant={wsStatus === 'connected' ? 'destructive' : 'default'}
                className="flex items-center gap-2"
              >
                <Wifi className="w-4 h-4" />
                {wsStatus === 'connected' ? 'Disconnect' : 'Connect'}
              </Button>
            </div>
          </div>

          <div className="text-xs text-muted-foreground">
            {wsStatus === 'connected' && '✓ WebSocket connected - Real-time data streaming enabled'}
            {wsStatus === 'disconnected' && '○ WebSocket disconnected - Using HTTP polling only'}
          </div>
        </div>

        {/* Connection Presets */}
        <div className="space-y-3">
          <div className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            Connection Presets
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setHttpUrl('http://localhost:8080');
                setWsUrl('ws://localhost:8081');
              }}
            >
              Local Development
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setHttpUrl('http://192.168.1.100:8080');
                setWsUrl('ws://192.168.1.100:8081');
              }}
            >
              Network Device
            </Button>
          </div>
        </div>

        {/* Connection Status Summary */}
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
          <div className="text-center">
            <div className={`text-2xl font-mono ${
              connectionStatus === 'connected' ? 'text-success' : 'text-muted-foreground'
            }`}>
              {connectionStatus === 'connected' ? '✓' : '✗'}
            </div>
            <div className="text-xs text-muted-foreground">HTTP API</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-mono ${
              wsStatus === 'connected' ? 'text-success' : 'text-muted-foreground'
            }`}>
              {wsStatus === 'connected' ? '✓' : '○'}
            </div>
            <div className="text-xs text-muted-foreground">WebSocket</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}