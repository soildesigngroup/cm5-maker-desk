import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { HMIApiService, CANStatus, CANMessage, CANBusConfig } from '@/services/hmi-api';
import {
  Radio,
  Wifi,
  WifiOff,
  Send,
  Trash2,
  Terminal,
  Settings,
  Activity,
  MessageSquare,
  Clock
} from 'lucide-react';

interface CANProps {
  apiService: HMIApiService;
}

export function CAN({ apiService }: CANProps) {
  const [status, setStatus] = useState<CANStatus | null>(null);
  const [interfaces, setInterfaces] = useState<string[]>([]);
  const [messages, setMessages] = useState<CANMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showConsole, setShowConsole] = useState(false);

  // Connection form state
  const [selectedInterface, setSelectedInterface] = useState('cantact');
  const [channel, setChannel] = useState('can0');
  const [bitrate, setBitrate] = useState('250000');

  // Message sending state
  const [arbitrationId, setArbitrationId] = useState('0x123');
  const [messageData, setMessageData] = useState('01 02 03 04');
  const [isExtendedId, setIsExtendedId] = useState(false);

  // CLI Console state
  const [consoleOutput, setConsoleOutput] = useState<string[]>([]);
  const [consoleInput, setConsoleInput] = useState('');
  const [consoleHistory, setConsoleHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const consoleRef = useRef<HTMLTextAreaElement>(null);

  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(false);

  useEffect(() => {
    fetchStatus();
    fetchInterfaces();
  }, [apiService]);

  useEffect(() => {
    if (autoRefresh && status?.connected) {
      const interval = setInterval(() => {
        fetchMessages();
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, status?.connected]);

  const fetchStatus = async () => {
    try {
      const response = await apiService.getCANStatus();
      if (response.success && response.data) {
        setStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch CAN status:', error);
    }
  };

  const fetchInterfaces = async () => {
    try {
      const response = await apiService.getCANInterfaces();
      if (response.success && response.data) {
        setInterfaces(response.data.interfaces);
      }
    } catch (error) {
      console.error('Failed to fetch CAN interfaces:', error);
    }
  };

  const fetchMessages = async () => {
    try {
      const response = await apiService.getCANMessages(100);
      if (response.success && response.data) {
        setMessages(response.data.messages);
      }
    } catch (error) {
      console.error('Failed to fetch CAN messages:', error);
    }
  };

  const handleConnect = async () => {
    setIsLoading(true);
    try {
      const config: CANBusConfig = {
        interface: selectedInterface,
        channel,
        bitrate: parseInt(bitrate),
        receive_own_messages: true,
      };

      const response = await apiService.connectCAN(config);
      if (response.success) {
        await fetchStatus();
        addConsoleOutput(`Connected to ${selectedInterface}:${channel} @ ${bitrate} bps`);
      } else {
        addConsoleOutput(`Failed to connect: ${response.error || 'Unknown error'}`);
      }
    } catch (error) {
      addConsoleOutput(`Connection error: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.disconnectCAN();
      if (response.success) {
        await fetchStatus();
        addConsoleOutput('Disconnected from CAN bus');
      }
    } catch (error) {
      addConsoleOutput(`Disconnect error: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!status?.connected) {
      addConsoleOutput('Error: Not connected to CAN bus');
      return;
    }

    try {
      // Parse data bytes from space-separated hex string
      const dataBytes = messageData.split(/\s+/).filter(s => s.length > 0);

      const response = await apiService.sendCANMessage(arbitrationId, dataBytes, isExtendedId);
      if (response.success && response.data) {
        addConsoleOutput(`Sent: ID=${response.data.arbitration_id} Data=[${response.data.data.join(' ')}]`);
        fetchMessages(); // Refresh messages
      } else {
        addConsoleOutput(`Send failed: ${response.error || 'Unknown error'}`);
      }
    } catch (error) {
      addConsoleOutput(`Send error: ${error}`);
    }
  };

  const handleClearMessages = async () => {
    try {
      const response = await apiService.clearCANMessages();
      if (response.success) {
        setMessages([]);
        addConsoleOutput('Message history cleared');
      }
    } catch (error) {
      addConsoleOutput(`Clear error: ${error}`);
    }
  };

  const addConsoleOutput = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    const formattedMessage = `[${timestamp}] ${message}`;
    setConsoleOutput(prev => [...prev, formattedMessage]);

    // Auto-scroll to bottom
    setTimeout(() => {
      if (consoleRef.current) {
        consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
      }
    }, 100);
  };

  const handleConsoleCommand = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && consoleInput.trim()) {
      const command = consoleInput.trim();
      addConsoleOutput(`> ${command}`);

      // Add to history
      setConsoleHistory(prev => [...prev, command]);
      setHistoryIndex(-1);

      try {
        const response = await apiService.executeCANCommand(command);
        if (response.data?.message) {
          addConsoleOutput(response.data.message);
        } else if (response.success) {
          addConsoleOutput('Command executed successfully');
        } else {
          addConsoleOutput(`Error: ${response.error || 'Command failed'}`);
        }

        // Refresh status after command
        await fetchStatus();
        if (status?.connected) {
          await fetchMessages();
        }
      } catch (error) {
        addConsoleOutput(`Command error: ${error}`);
      }

      setConsoleInput('');
    } else if (e.key === 'ArrowUp') {
      // Navigate command history
      if (consoleHistory.length > 0) {
        const newIndex = Math.min(historyIndex + 1, consoleHistory.length - 1);
        setHistoryIndex(newIndex);
        setConsoleInput(consoleHistory[consoleHistory.length - 1 - newIndex]);
      }
    } else if (e.key === 'ArrowDown') {
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setConsoleInput(consoleHistory[consoleHistory.length - 1 - newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setConsoleInput('');
      }
    }
  };

  const clearConsole = () => {
    setConsoleOutput([]);
  };

  return (
    <div className="space-y-6">
      {/* Connection Panel */}
      <Card className="hmi-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Radio className="w-5 h-5 text-primary" />
            CAN Bus Interface
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {status?.connected ? (
                <Wifi className="w-4 h-4 text-green-500" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" />
              )}
              <span className="text-sm font-medium">Status:</span>
              <Badge variant={status?.connected ? "default" : "secondary"}>
                {status?.connected ? "Connected" : "Disconnected"}
              </Badge>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={status?.connected ? handleDisconnect : handleConnect}
                disabled={isLoading}
                variant={status?.connected ? "destructive" : "default"}
                size="sm"
              >
                {status?.connected ? "Disconnect" : "Connect"}
              </Button>
            </div>
          </div>

          {!status?.connected && (
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="interface">Interface</Label>
                <Select value={selectedInterface} onValueChange={setSelectedInterface}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {interfaces.map(iface => (
                      <SelectItem key={iface} value={iface}>
                        {iface}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="channel">Channel</Label>
                <Input
                  id="channel"
                  value={channel}
                  onChange={(e) => setChannel(e.target.value)}
                  placeholder="can0"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bitrate">Bitrate</Label>
                <Select value={bitrate} onValueChange={setBitrate}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="125000">125 kbps</SelectItem>
                    <SelectItem value="250000">250 kbps</SelectItem>
                    <SelectItem value="500000">500 kbps</SelectItem>
                    <SelectItem value="1000000">1 Mbps</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {status?.connected && status.config && (
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Interface:</span>
                <div className="font-mono">{status.config.interface}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Channel:</span>
                <div className="font-mono">{status.config.channel}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Bitrate:</span>
                <div className="font-mono">{status.config.bitrate} bps</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Message Sending Panel */}
      {status?.connected && (
        <Card className="hmi-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Send className="w-5 h-5 text-primary" />
              Send Message
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="arbitration-id">Arbitration ID</Label>
                <Input
                  id="arbitration-id"
                  value={arbitrationId}
                  onChange={(e) => setArbitrationId(e.target.value)}
                  placeholder="0x123"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="message-data">Data (hex bytes)</Label>
                <Input
                  id="message-data"
                  value={messageData}
                  onChange={(e) => setMessageData(e.target.value)}
                  placeholder="01 02 03 04"
                />
              </div>
              <div className="space-y-2">
                <Label>Options</Label>
                <div className="flex items-center gap-4">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="extended-id"
                      checked={isExtendedId}
                      onCheckedChange={setIsExtendedId}
                    />
                    <Label htmlFor="extended-id" className="text-sm">Extended ID</Label>
                  </div>
                  <Button onClick={handleSendMessage} size="sm">
                    <Send className="w-4 h-4 mr-2" />
                    Send
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* CLI Console */}
      <Card className="hmi-panel">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="w-5 h-5 text-primary" />
              CLI Console
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center space-x-2">
                <Switch
                  id="show-console"
                  checked={showConsole}
                  onCheckedChange={setShowConsole}
                />
                <Label htmlFor="show-console" className="text-sm">Enable</Label>
              </div>
              {showConsole && (
                <Button onClick={clearConsole} size="sm" variant="outline">
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          </CardTitle>
        </CardHeader>
        {showConsole && (
          <CardContent className="space-y-4">
            <Textarea
              ref={consoleRef}
              value={consoleOutput.join('\n')}
              readOnly
              className="font-mono text-xs min-h-[200px] bg-black text-green-400"
              placeholder="Console output will appear here..."
            />
            <Input
              value={consoleInput}
              onChange={(e) => setConsoleInput(e.target.value)}
              onKeyDown={handleConsoleCommand}
              placeholder="Enter CAN commands (type 'help' for available commands)"
              className="font-mono"
            />
            <div className="text-xs text-muted-foreground">
              Commands: status, connect &lt;interface&gt; [channel] [bitrate], disconnect, send &lt;id&gt; &lt;data&gt;, clear, help
            </div>
          </CardContent>
        )}
      </Card>

      {/* Message Monitor */}
      {status?.connected && (
        <Card className="hmi-panel">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-primary" />
                Message Monitor
                <Badge variant="outline">{messages.length}</Badge>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="auto-refresh"
                    checked={autoRefresh}
                    onCheckedChange={setAutoRefresh}
                  />
                  <Label htmlFor="auto-refresh" className="text-sm">Auto-refresh</Label>
                </div>
                <Button onClick={fetchMessages} size="sm" variant="outline">
                  <Activity className="w-4 h-4" />
                </Button>
                <Button onClick={handleClearMessages} size="sm" variant="outline">
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-64">
              <div className="space-y-2">
                {messages.length > 0 ? (
                  messages.slice().reverse().map((msg, index) => (
                    <div key={index} className="border border-border rounded-lg p-3 font-mono text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Clock className="w-3 h-3 text-muted-foreground" />
                          <span className="text-muted-foreground">{msg.formatted_time}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            ID: {msg.arbitration_id}
                          </Badge>
                          {msg.is_extended_id && (
                            <Badge variant="secondary" className="text-xs">EXT</Badge>
                          )}
                          {msg.is_remote_frame && (
                            <Badge variant="secondary" className="text-xs">RTR</Badge>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Data:</span>
                        <span className="text-primary font-bold">
                          [{msg.data.join(' ')}]
                        </span>
                        <span className="text-muted-foreground">
                          ({msg.dlc} bytes)
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No CAN messages received yet
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}