import React, { useState } from 'react';
import { HMIApiService } from '@/services/hmi-api';
import { SystemStatus } from '@/components/hmi/SystemStatus';
import { ADCMonitor } from '@/components/hmi/ADCMonitor';
import { IOControl } from '@/components/hmi/IOControl';
import { FanController } from '@/components/hmi/FanController';
import { RTCDisplay } from '@/components/hmi/RTCDisplay';
import { ConnectionSettings } from '@/components/hmi/ConnectionSettings';
import { AIVision } from '@/components/hmi/AIVision';
import { CameraStreaming } from '@/components/hmi/CameraStreaming';
import { CAN } from '@/components/hmi/CAN';
import { AudioOutput } from '@/components/hmi/AudioOutput';
import { Automation } from '@/components/hmi/Automation';
import { DiagAgent } from '@/components/hmi/DiagAgent';
import StorageMonitor from '@/components/hmi/StorageMonitor';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Cpu, BarChart3, ToggleLeft, Fan, Clock, Settings, Menu, Eye, Camera, Radio, Volume2, Zap, Stethoscope, HardDrive } from 'lucide-react';

const Index = () => {
  const [apiService, setApiService] = useState(new HMIApiService());
  const [activeTab, setActiveTab] = useState('overview');

  const handleApiServiceChange = (newService: HMIApiService) => {
    setApiService(newService);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <Cpu className="w-5 h-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">
                  HMI Control Panel
                </h1>
                <p className="text-sm text-muted-foreground">
                  Raspberry Pi CM5 Device Interface
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setActiveTab('settings')}
                className="flex items-center gap-2"
              >
                <Settings className="w-4 h-4" />
                Settings
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-12 lg:w-auto lg:grid-cols-13">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <Menu className="w-4 h-4" />
              <span className="hidden sm:inline">Overview</span>
            </TabsTrigger>
            <TabsTrigger value="adc" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">ADC</span>
            </TabsTrigger>
            <TabsTrigger value="io" className="flex items-center gap-2">
              <ToggleLeft className="w-4 h-4" />
              <span className="hidden sm:inline">I/O</span>
            </TabsTrigger>
            <TabsTrigger value="fan" className="flex items-center gap-2">
              <Fan className="w-4 h-4" />
              <span className="hidden sm:inline">Fan</span>
            </TabsTrigger>
            <TabsTrigger value="rtc" className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              <span className="hidden sm:inline">RTC</span>
            </TabsTrigger>
            <TabsTrigger value="storage" className="flex items-center gap-2">
              <HardDrive className="w-4 h-4" />
              <span className="hidden sm:inline">Storage</span>
            </TabsTrigger>
            <TabsTrigger value="can" className="flex items-center gap-2">
              <Radio className="w-4 h-4" />
              <span className="hidden sm:inline">CAN</span>
            </TabsTrigger>
            <TabsTrigger value="audio" className="flex items-center gap-2">
              <Volume2 className="w-4 h-4" />
              <span className="hidden sm:inline">Audio</span>
            </TabsTrigger>
            <TabsTrigger value="ai_vision" className="flex items-center gap-2">
              <Eye className="w-4 h-4" />
              <span className="hidden sm:inline">AI-Vision</span>
            </TabsTrigger>
            <TabsTrigger value="camera_streaming" className="flex items-center gap-2">
              <Camera className="w-4 h-4" />
              <span className="hidden sm:inline">Cameras</span>
            </TabsTrigger>
            <TabsTrigger value="automation" className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              <span className="hidden sm:inline">Automation</span>
            </TabsTrigger>
            <TabsTrigger value="diag_agent" className="flex items-center gap-2">
              <Stethoscope className="w-4 h-4" />
              <span className="hidden sm:inline">DIAG Agent</span>
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              <span className="hidden sm:inline">Settings</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6 animate-fade-in">
            <div className="grid gap-6">
              <SystemStatus apiService={apiService} />
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <ADCMonitor apiService={apiService} />
                <FanController apiService={apiService} />
                <StorageMonitor />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="adc" className="animate-fade-in">
            <ADCMonitor apiService={apiService} />
          </TabsContent>

          <TabsContent value="io" className="animate-fade-in">
            <IOControl apiService={apiService} />
          </TabsContent>

          <TabsContent value="fan" className="animate-fade-in">
            <FanController apiService={apiService} />
          </TabsContent>

          <TabsContent value="rtc" className="animate-fade-in">
            <RTCDisplay apiService={apiService} />
          </TabsContent>

          <TabsContent value="storage" className="animate-fade-in">
            <StorageMonitor />
          </TabsContent>

          <TabsContent value="can" className="animate-fade-in">
            <CAN apiService={apiService} />
          </TabsContent>

          <TabsContent value="audio" className="animate-fade-in">
            <AudioOutput apiService={apiService} />
          </TabsContent>

          <TabsContent value="ai_vision" className="animate-fade-in">
            <AIVision apiService={apiService} />
          </TabsContent>

          <TabsContent value="camera_streaming" className="animate-fade-in">
            <CameraStreaming />
          </TabsContent>

          <TabsContent value="automation" className="animate-fade-in">
            <Automation apiService={apiService} />
          </TabsContent>

          <TabsContent value="diag_agent" className="animate-fade-in">
            <DiagAgent apiService={apiService} />
          </TabsContent>

          <TabsContent value="settings" className="animate-fade-in">
            <ConnectionSettings 
              apiService={apiService} 
              onApiServiceChange={handleApiServiceChange} 
            />
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card/30 mt-12">
        <div className="container mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-sm text-muted-foreground">
              HMI Control Panel - Industrial IoT Interface for Raspberry Pi CM5
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>Built with React + TypeScript</span>
              <span>•</span>
              <span>JSON API Integration</span>
              <span>•</span>
              <span>Real-time Monitoring</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
