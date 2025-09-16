import React, { useState } from 'react';
import { HMIApiService } from '@/services/hmi-api';
import { SystemStatus } from '@/components/hmi/SystemStatus';
import { ADCMonitor } from '@/components/hmi/ADCMonitor';
import { IOControl } from '@/components/hmi/IOControl';
import { FanController } from '@/components/hmi/FanController';
import { RTCDisplay } from '@/components/hmi/RTCDisplay';
import { ConnectionSettings } from '@/components/hmi/ConnectionSettings';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Cpu, BarChart3, ToggleLeft, Fan, Clock, Settings, Menu } from 'lucide-react';

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
          <TabsList className="grid w-full grid-cols-6 lg:w-auto lg:grid-cols-6">
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
            <TabsTrigger value="settings" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              <span className="hidden sm:inline">Settings</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6 animate-fade-in">
            <div className="grid gap-6">
              <SystemStatus apiService={apiService} />
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <ADCMonitor apiService={apiService} />
                <FanController apiService={apiService} />
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
