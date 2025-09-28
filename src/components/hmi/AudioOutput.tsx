import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { HMIApiService, AudioStatus, AudioControl } from '@/services/hmi-api';
import {
  Volume2,
  VolumeX,
  Sliders,
  ToggleLeft,
  Settings,
  RefreshCw,
  Speaker,
  CheckCircle,
  XCircle,
  Headphones,
  Mic,
  Music,
  Zap,
  Route,
  Activity
} from 'lucide-react';

interface AudioOutputProps {
  apiService: HMIApiService;
}

export function AudioOutput({ apiService }: AudioOutputProps) {
  const [status, setStatus] = useState<AudioStatus | null>(null);
  const [volumeControls, setVolumeControls] = useState<AudioControl[]>([]);
  const [switchControls, setSwitchControls] = useState<AudioControl[]>([]);
  const [eqControls, setEqControls] = useState<AudioControl[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Advanced volume controls
  const [headphoneVolume, setHeadphoneVolume] = useState(0);
  const [speakerVolume, setSpeakerVolume] = useState(0);
  const [masterDACVolume, setMasterDACVolume] = useState(0);
  const [adcVolume, setADCVolume] = useState(0);
  const [inputVolume, setInputVolume] = useState(0);
  const [micBoostVolume, setMicBoostVolume] = useState(0);

  // Audio processing controls
  const [eqBand1Enabled, setEQBand1Enabled] = useState(false);
  const [eqBand2Enabled, setEQBand2Enabled] = useState(false);
  const [compressorLevel, setCompressorLevel] = useState(0);
  const [compressionRatio, setCompressionRatio] = useState(1);
  const [sound3DEnabled, setSound3DEnabled] = useState(false);
  const [bassLevel, setBassLevel] = useState(0);
  const [trebleLevel, setTrebleLevel] = useState(0);

  // Routing controls
  const [inputChannelMap, setInputChannelMap] = useState('normal');
  const [leftInputRoute, setLeftInputRoute] = useState('line1');
  const [rightInputRoute, setRightInputRoute] = useState('line1');
  const [headphoneAutoSwitch, setHeadphoneAutoSwitch] = useState(false);
  const [micBiasBoost, setMicBiasBoost] = useState(false);

  // Configuration
  const [sampleRate, setSampleRate] = useState('44100');
  const [audioFormat, setAudioFormat] = useState('16bit');

  useEffect(() => {
    fetchAudioStatus();
    fetchAudioControls();
  }, [apiService]);

  const fetchAudioStatus = async () => {
    try {
      const response = await apiService.getAudioStatus();
      if (response.success && response.data) {
        setStatus(response.data);
      } else {
        console.warn('Audio status request failed:', response.error);
      }
    } catch (error) {
      console.error('Failed to fetch audio status:', error);
      // Set a default status to prevent crashes
      setStatus({
        connected: false,
        card_id: 0,
        card_name: 'hw:0',
        total_controls: 0,
        volume_controls: 0,
        switch_controls: 0,
        eq_controls: 0,
        last_refresh: Date.now() / 1000
      });
    }
  };

  const fetchAudioControls = async () => {
    setIsLoading(true);
    try {
      const [volumeResponse, switchResponse, eqResponse] = await Promise.all([
        apiService.getVolumeControls(),
        apiService.getSwitchControls(),
        apiService.getEQControls()
      ]);

      if (volumeResponse.success && volumeResponse.data) {
        setVolumeControls(Array.isArray(volumeResponse.data) ? volumeResponse.data : []);
      } else {
        setVolumeControls([]);
      }

      if (switchResponse.success && switchResponse.data) {
        setSwitchControls(Array.isArray(switchResponse.data) ? switchResponse.data : []);
      } else {
        setSwitchControls([]);
      }

      if (eqResponse.success && eqResponse.data) {
        setEqControls(Array.isArray(eqResponse.data) ? eqResponse.data : []);
      } else {
        setEqControls([]);
      }
    } catch (error) {
      console.error('Failed to fetch audio controls:', error);
      // Set empty arrays to prevent crashes
      setVolumeControls([]);
      setSwitchControls([]);
      setEqControls([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefreshControls = async () => {
    setIsRefreshing(true);
    try {
      const response = await apiService.refreshAudioControls();
      if (response.success) {
        await fetchAudioStatus();
        await fetchAudioControls();
      }
    } catch (error) {
      console.error('Failed to refresh audio controls:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleVolumeChange = async (controlName: string, value: number[]) => {
    try {
      const response = await apiService.setAudioControl(controlName, value[0]);
      if (response.success) {
        // Update local state
        setVolumeControls(prev =>
          Array.isArray(prev) ? prev.map(ctrl =>
            ctrl.name === controlName ? { ...ctrl, value: value[0] } : ctrl
          ) : []
        );
      } else {
        console.warn('Failed to set volume control:', response.error);
      }
    } catch (error) {
      console.error('Failed to set volume control:', error);
    }
  };

  const handleSwitchChange = async (controlName: string, checked: boolean) => {
    try {
      const response = await apiService.setAudioControl(controlName, checked ? 1 : 0);
      if (response.success) {
        // Update local state
        setSwitchControls(prev =>
          Array.isArray(prev) ? prev.map(ctrl =>
            ctrl.name === controlName ? { ...ctrl, value: checked ? 1 : 0 } : ctrl
          ) : []
        );
      } else {
        console.warn('Failed to set switch control:', response.error);
      }
    } catch (error) {
      console.error('Failed to set switch control:', error);
    }
  };

  const handleEQChange = async (controlName: string, value: number[]) => {
    try {
      const response = await apiService.setAudioControl(controlName, value[0]);
      if (response.success) {
        // Update local state
        setEqControls(prev =>
          Array.isArray(prev) ? prev.map(ctrl =>
            ctrl.name === controlName ? { ...ctrl, value: value[0] } : ctrl
          ) : []
        );
      } else {
        console.warn('Failed to set EQ control:', response.error);
      }
    } catch (error) {
      console.error('Failed to set EQ control:', error);
    }
  };

  const formatControlName = (name: string) => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="space-y-6">
      {/* Status Panel */}
      <Card className="hmi-panel">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Speaker className="w-5 h-5 text-primary" />
              TSCS42xx Audio Interface (I2C - 0x69)
            </div>
            <div className="flex items-center gap-2">
              {status?.connected ? (
                <CheckCircle className="w-4 h-4 text-green-500" />
              ) : (
                <XCircle className="w-4 h-4 text-red-500" />
              )}
              <Badge variant={status?.connected ? "default" : "secondary"}>
                {status?.connected ? "Connected" : "Disconnected"}
              </Badge>
              <Button
                onClick={handleRefreshControls}
                disabled={isRefreshing}
                variant="outline"
                size="sm"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {status && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Card ID:</span>
                <div className="font-mono">{status.card_id}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Card Name:</span>
                <div className="font-mono">{status.card_name}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Total Controls:</span>
                <div className="font-mono">{status.total_controls}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Last Refresh:</span>
                <div className="font-mono">
                  {status.last_refresh ? new Date(status.last_refresh * 1000).toLocaleTimeString() : 'Never'}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Advanced Audio Controls */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            <span className="hidden sm:inline">Overview</span>
          </TabsTrigger>
          <TabsTrigger value="volume" className="flex items-center gap-2">
            <Volume2 className="w-4 h-4" />
            <span className="hidden sm:inline">Volume</span>
          </TabsTrigger>
          <TabsTrigger value="processing" className="flex items-center gap-2">
            <Zap className="w-4 h-4" />
            <span className="hidden sm:inline">Processing</span>
          </TabsTrigger>
          <TabsTrigger value="routing" className="flex items-center gap-2">
            <Route className="w-4 h-4" />
            <span className="hidden sm:inline">Routing</span>
          </TabsTrigger>
          <TabsTrigger value="equalizer" className="flex items-center gap-2">
            <Sliders className="w-4 h-4" />
            <span className="hidden sm:inline">EQ</span>
          </TabsTrigger>
          <TabsTrigger value="config" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            <span className="hidden sm:inline">Config</span>
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Quick Volume Controls */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Volume2 className="w-5 h-5 text-primary" />
                  Quick Volume
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Headphone Volume</Label>
                  <Slider
                    value={[headphoneVolume]}
                    onValueChange={(value) => setHeadphoneVolume(value[0])}
                    min={-88}
                    max={6}
                    step={1}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{headphoneVolume} dB</span>
                </div>
                <div className="space-y-2">
                  <Label>Speaker Volume</Label>
                  <Slider
                    value={[speakerVolume]}
                    onValueChange={(value) => setSpeakerVolume(value[0])}
                    min={-77}
                    max={6}
                    step={1}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{speakerVolume} dB</span>
                </div>
              </CardContent>
            </Card>

            {/* Basic Controls */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ToggleLeft className="w-5 h-5 text-primary" />
                  Quick Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>3D Sound Effect</Label>
                  <Switch checked={sound3DEnabled} onCheckedChange={setSound3DEnabled} />
                </div>
                <div className="flex items-center justify-between">
                  <Label>Headphone Auto Switch</Label>
                  <Switch checked={headphoneAutoSwitch} onCheckedChange={setHeadphoneAutoSwitch} />
                </div>
                <div className="flex items-center justify-between">
                  <Label>Mic Bias Boost</Label>
                  <Switch checked={micBiasBoost} onCheckedChange={setMicBiasBoost} />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Volume Tab */}
        <TabsContent value="volume" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Output Volume Controls */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Headphones className="w-5 h-5 text-primary" />
                  Output Volume
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Headphone Volume (-88.5 to +6.75 dB)</Label>
                  <Slider
                    value={[headphoneVolume]}
                    onValueChange={(value) => setHeadphoneVolume(value[0])}
                    min={-88}
                    max={6}
                    step={0.25}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{headphoneVolume} dB</span>
                </div>
                <div className="space-y-2">
                  <Label>Speaker Volume (-77.25 to +6.75 dB)</Label>
                  <Slider
                    value={[speakerVolume]}
                    onValueChange={(value) => setSpeakerVolume(value[0])}
                    min={-77}
                    max={6}
                    step={0.25}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{speakerVolume} dB</span>
                </div>
                <div className="space-y-2">
                  <Label>Master DAC Volume (-95.63 to +1.5 dB)</Label>
                  <Slider
                    value={[masterDACVolume]}
                    onValueChange={(value) => setMasterDACVolume(value[0])}
                    min={-95}
                    max={1}
                    step={0.25}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{masterDACVolume} dB</span>
                </div>
              </CardContent>
            </Card>

            {/* Input Volume Controls */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Mic className="w-5 h-5 text-primary" />
                  Input Volume
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>ADC/PCM Volume (-71.25 to +1.5 dB)</Label>
                  <Slider
                    value={[adcVolume]}
                    onValueChange={(value) => setADCVolume(value[0])}
                    min={-71}
                    max={1}
                    step={0.25}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{adcVolume} dB</span>
                </div>
                <div className="space-y-2">
                  <Label>Input Volume (-17.25 to +4.5 dB)</Label>
                  <Slider
                    value={[inputVolume]}
                    onValueChange={(value) => setInputVolume(value[0])}
                    min={-17}
                    max={4}
                    step={0.25}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{inputVolume} dB</span>
                </div>
                <div className="space-y-2">
                  <Label>Mic Boost Volume</Label>
                  <Slider
                    value={[micBoostVolume]}
                    onValueChange={(value) => setMicBoostVolume(value[0])}
                    min={0}
                    max={40}
                    step={1}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">+{micBoostVolume} dB</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Audio Processing Tab */}
        <TabsContent value="processing" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Equalizer Controls */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sliders className="w-5 h-5 text-primary" />
                  Equalizer
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>EQ Band 1 Enable</Label>
                  <Switch checked={eqBand1Enabled} onCheckedChange={setEQBand1Enabled} />
                </div>
                <div className="flex items-center justify-between">
                  <Label>EQ Band 2 Enable</Label>
                  <Switch checked={eqBand2Enabled} onCheckedChange={setEQBand2Enabled} />
                </div>
                <div className="space-y-2">
                  <Label>Bass Level</Label>
                  <Slider
                    value={[bassLevel]}
                    onValueChange={(value) => setBassLevel(value[0])}
                    min={-12}
                    max={12}
                    step={1}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{bassLevel > 0 ? '+' : ''}{bassLevel} dB</span>
                </div>
                <div className="space-y-2">
                  <Label>Treble Level</Label>
                  <Slider
                    value={[trebleLevel]}
                    onValueChange={(value) => setTrebleLevel(value[0])}
                    min={-12}
                    max={12}
                    step={1}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{trebleLevel > 0 ? '+' : ''}{trebleLevel} dB</span>
                </div>
              </CardContent>
            </Card>

            {/* Dynamic Processing */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Music className="w-5 h-5 text-primary" />
                  Dynamic Processing
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Compressor Level</Label>
                  <Slider
                    value={[compressorLevel]}
                    onValueChange={(value) => setCompressorLevel(value[0])}
                    min={0}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                  <span className="text-xs text-muted-foreground">{compressorLevel}%</span>
                </div>
                <div className="space-y-2">
                  <Label>Compression Ratio</Label>
                  <Select value={compressionRatio.toString()} onValueChange={(value) => setCompressionRatio(parseFloat(value))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1:1 (No Compression)</SelectItem>
                      <SelectItem value="1.5">1.5:1 (Light)</SelectItem>
                      <SelectItem value="2">2:1 (Mild)</SelectItem>
                      <SelectItem value="4">4:1 (Medium)</SelectItem>
                      <SelectItem value="8">8:1 (Heavy)</SelectItem>
                      <SelectItem value="20">20:1 (Limiting)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center justify-between">
                  <Label>3D Sound Effect</Label>
                  <Switch checked={sound3DEnabled} onCheckedChange={setSound3DEnabled} />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Routing Tab */}
        <TabsContent value="routing" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Input Routing */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Route className="w-5 h-5 text-primary" />
                  Input Routing
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Input Channel Map</Label>
                  <Select value={inputChannelMap} onValueChange={setInputChannelMap}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="normal">Normal</SelectItem>
                      <SelectItem value="left_to_right">Left to Right</SelectItem>
                      <SelectItem value="right_to_left">Right to Left</SelectItem>
                      <SelectItem value="swap">Swap Channels</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Left Input Route</Label>
                  <Select value={leftInputRoute} onValueChange={setLeftInputRoute}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="line1">Line 1</SelectItem>
                      <SelectItem value="line2">Line 2</SelectItem>
                      <SelectItem value="line3">Line 3</SelectItem>
                      <SelectItem value="d2s">D2S</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Right Input Route</Label>
                  <Select value={rightInputRoute} onValueChange={setRightInputRoute}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="line1">Line 1</SelectItem>
                      <SelectItem value="line2">Line 2</SelectItem>
                      <SelectItem value="line3">Line 3</SelectItem>
                      <SelectItem value="d2s">D2S</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Output Routing */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Speaker className="w-5 h-5 text-primary" />
                  Output Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Headphone Auto Switch</Label>
                  <Switch checked={headphoneAutoSwitch} onCheckedChange={setHeadphoneAutoSwitch} />
                </div>
                <div className="flex items-center justify-between">
                  <Label>Mic Bias Boost</Label>
                  <Switch checked={micBiasBoost} onCheckedChange={setMicBiasBoost} />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Equalizer Tab */}
        <TabsContent value="equalizer" className="space-y-6">
          <Card className="hmi-panel">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-primary" />
                Advanced Equalizer
                <Badge variant="outline">{Array.isArray(eqControls) ? eqControls.length : 0}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ScrollArea className="h-96">
                <div className="space-y-4 pr-4">
                  {Array.isArray(eqControls) ? eqControls.map((control, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm font-medium">
                          {formatControlName(control.name)}
                        </Label>
                        <span className="text-xs text-muted-foreground font-mono">
                          {typeof control.value === 'number' ? control.value : control.value}
                          {control.min !== undefined && control.max !== undefined &&
                            ` (${control.min}-${control.max})`
                          }
                        </span>
                      </div>
                      <Slider
                        value={[typeof control.value === 'number' ? control.value : 0]}
                        onValueChange={(value) => handleEQChange(control.name, value)}
                        min={control.min || -50}
                        max={control.max || 50}
                        step={1}
                        className="w-full"
                      />
                    </div>
                  )) : null}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Configuration Tab */}
        <TabsContent value="config" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Sample Rate & Format */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5 text-primary" />
                  Audio Format
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Sample Rate</Label>
                  <Select value={sampleRate} onValueChange={setSampleRate}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="8000">8 kHz</SelectItem>
                      <SelectItem value="11025">11.025 kHz</SelectItem>
                      <SelectItem value="16000">16 kHz</SelectItem>
                      <SelectItem value="22050">22.05 kHz</SelectItem>
                      <SelectItem value="24000">24 kHz</SelectItem>
                      <SelectItem value="32000">32 kHz</SelectItem>
                      <SelectItem value="44100">44.1 kHz</SelectItem>
                      <SelectItem value="48000">48 kHz</SelectItem>
                      <SelectItem value="88200">88.2 kHz</SelectItem>
                      <SelectItem value="96000">96 kHz</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Audio Format</Label>
                  <Select value={audioFormat} onValueChange={setAudioFormat}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="16bit">16-bit PCM</SelectItem>
                      <SelectItem value="20bit">20-bit PCM</SelectItem>
                      <SelectItem value="24bit">24-bit PCM</SelectItem>
                      <SelectItem value="32bit">32-bit PCM</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Legacy Controls */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ToggleLeft className="w-5 h-5 text-primary" />
                  Legacy Controls
                  <Badge variant="outline">{(Array.isArray(volumeControls) ? volumeControls.length : 0) + (Array.isArray(switchControls) ? switchControls.length : 0)}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <div className="space-y-4 pr-4">
                    {/* Volume Controls */}
                    {Array.isArray(volumeControls) ? volumeControls.map((control, index) => (
                      <div key={`vol-${index}`} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label className="text-sm font-medium">
                            {formatControlName(control.name)}
                          </Label>
                          <span className="text-xs text-muted-foreground font-mono">
                            {typeof control.value === 'number' ? control.value : control.value}
                          </span>
                        </div>
                        <Slider
                          value={[typeof control.value === 'number' ? control.value : 0]}
                          onValueChange={(value) => handleVolumeChange(control.name, value)}
                          min={control.min || 0}
                          max={control.max || 100}
                          step={1}
                          className="w-full"
                        />
                      </div>
                    )) : null}

                    {/* Switch Controls */}
                    {Array.isArray(switchControls) ? switchControls.map((control, index) => (
                      <div key={`switch-${index}`} className="flex items-center justify-between">
                        <Label className="text-sm font-medium">
                          {formatControlName(control.name)}
                        </Label>
                        <Switch
                          checked={control.value === 1 || control.value === '1'}
                          onCheckedChange={(checked) => handleSwitchChange(control.name, checked)}
                        />
                      </div>
                    )) : null}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* No Controls Message */}
      {!isLoading &&
        (Array.isArray(volumeControls) ? volumeControls.length : 0) === 0 &&
        (Array.isArray(switchControls) ? switchControls.length : 0) === 0 &&
        (Array.isArray(eqControls) ? eqControls.length : 0) === 0 && (
        <Card className="hmi-panel">
          <CardContent className="py-8">
            <div className="text-center text-muted-foreground">
              <VolumeX className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">No Audio Controls Available</p>
              <p className="text-sm">
                {status?.connected
                  ? "No ALSA controls found for this audio device."
                  : "Audio device is not connected."
                }
              </p>
              {status?.connected && (
                <Button
                  onClick={handleRefreshControls}
                  variant="outline"
                  className="mt-4"
                  disabled={isRefreshing}
                >
                  <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                  Refresh Controls
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}