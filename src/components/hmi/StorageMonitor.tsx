import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { HardDrive, WifiOff, AlertCircle, CheckCircle, Settings, AlertTriangle, Zap } from 'lucide-react';

interface StorageDevice {
  name: string;
  mountpoint: string;
  filesystem: string;
  size: number;
  used: number;
  available: number;
  use_percent: number;
  device_path: string;
  is_nvme: boolean;
  is_external: boolean;
  speed_test?: SpeedTestResult;
}

interface SpeedTestResult {
  device_path: string;
  device_name: string;
  mount_point: string;
  test_size: string;
  write_speed_mbps: number;
  read_speed_mbps: number;
  write_time_seconds: number;
  read_time_seconds: number;
  timestamp?: number;
}

interface UnformattedDevice {
  name: string;
  device_path: string;
  size: number;
  model: string;
  serial: string;
  is_nvme: boolean;
  is_pcie: boolean;
  needs_formatting: boolean;
}

interface StorageData {
  timestamp: number;
  devices: StorageDevice[];
  nvme_devices: StorageDevice[];
  unformatted_devices: UnformattedDevice[];
  external_connected: boolean;
  total_external_capacity: number;
  total_external_used: number;
  total_external_available: number;
}

const StorageMonitor: React.FC = () => {
  const [storageData, setStorageData] = useState<StorageData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isFormatting, setIsFormatting] = useState(false);
  const [formatDialogOpen, setFormatDialogOpen] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<UnformattedDevice | null>(null);
  const [filesystem, setFilesystem] = useState('ext4');
  const [driveLabel, setDriveLabel] = useState('ExternalDrive');
  const [speedTestResults, setSpeedTestResults] = useState<Map<string, SpeedTestResult>>(new Map());
  const [testingDevices, setTestingDevices] = useState<Set<string>>(new Set());

  const fetchStorageData = async () => {
    try {
      const response = await fetch('http://localhost:8081/api/command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'get_storage_info'
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.data) {
          setStorageData(result.data);
          setLastUpdate(new Date());
        }
      }
    } catch (error) {
      console.error('Error fetching storage data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStorageData();
    const interval = setInterval(fetchStorageData, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStorageStatus = (device: StorageDevice) => {
    if (device.use_percent > 90) return { color: 'destructive', icon: AlertCircle };
    if (device.use_percent > 75) return { color: 'warning', icon: AlertCircle };
    return { color: 'success', icon: CheckCircle };
  };

  const handleFormatDrive = async () => {
    if (!selectedDevice) return;

    setIsFormatting(true);
    try {
      const response = await fetch('http://localhost:8081/api/command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'format_drive',
          params: {
            device_path: selectedDevice.device_path,
            filesystem: filesystem,
            label: driveLabel
          }
        }),
      });

      const result = await response.json();
      if (result.success) {
        alert(`Successfully formatted ${selectedDevice.name} with ${filesystem} filesystem`);
        setFormatDialogOpen(false);
        setSelectedDevice(null);
        // Refresh storage data multiple times to ensure the newly formatted drive is detected
        fetchStorageData();
        setTimeout(fetchStorageData, 1000);
        setTimeout(fetchStorageData, 3000);
        setTimeout(fetchStorageData, 5000);
      } else {
        alert(`Format failed: ${result.error || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Format error: ${error}`);
    } finally {
      setIsFormatting(false);
    }
  };

  const openFormatDialog = (device: UnformattedDevice) => {
    setSelectedDevice(device);
    setDriveLabel(device.model.replace(/[^a-zA-Z0-9]/g, '') || 'ExternalDrive');
    setFormatDialogOpen(true);
  };

  const handleSpeedTest = async (device: StorageDevice) => {
    const devicePath = device.device_path;
    setTestingDevices(prev => new Set(prev).add(devicePath));

    try {
      const response = await fetch('http://localhost:8081/api/command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'test_storage_speed',
          params: {
            device_path: devicePath,
            test_size: '100M'
          }
        }),
      });

      const result = await response.json();
      if (result.success && result.data) {
        const speedResult: SpeedTestResult = {
          ...result.data,
          timestamp: Date.now()
        };
        setSpeedTestResults(prev => new Map(prev).set(devicePath, speedResult));
        alert(`Speed test completed for ${device.name}!\nRead: ${speedResult.read_speed_mbps} MB/s\nWrite: ${speedResult.write_speed_mbps} MB/s`);
      } else {
        alert(`Speed test failed: ${result.error || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Speed test error: ${error}`);
    } finally {
      setTestingDevices(prev => {
        const newSet = new Set(prev);
        newSet.delete(devicePath);
        return newSet;
      });
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HardDrive className="h-5 w-5" />
            External Storage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center p-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <HardDrive className="h-5 w-5" />
          External Storage (PCIe NVMe)
          {storageData?.external_connected ? (
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              <CheckCircle className="h-3 w-3 mr-1" />
              Connected
            </Badge>
          ) : (
            <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
              <WifiOff className="h-3 w-3 mr-1" />
              Not Connected
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Show unformatted drives if any exist */}
        {storageData?.unformatted_devices && storageData.unformatted_devices.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <span className="font-medium text-yellow-800">Unformatted Drive Detected</span>
            </div>
            <p className="text-sm text-yellow-700 mb-3">
              The following NVMe drives are connected but need to be formatted before use:
            </p>

            {storageData.unformatted_devices.map((device, index) => (
              <div key={index} className="bg-white border rounded-lg p-3 mb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <HardDrive className="h-4 w-4 text-gray-600" />
                    <div>
                      <span className="font-medium text-sm text-gray-900">{device.name}</span>
                      <div className="text-xs text-gray-700">
                        {device.model} • {formatBytes(device.size)} • {device.device_path}
                      </div>
                    </div>
                    {device.is_pcie && (
                      <Badge variant="outline" className="text-xs text-black">PCIe</Badge>
                    )}
                  </div>
                  <Button
                    size="sm"
                    onClick={() => openFormatDialog(device)}
                    className="flex items-center gap-1"
                  >
                    <Settings className="h-3 w-3" />
                    Format
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Show formatted external storage summary if exists */}
        {storageData?.total_external_capacity > 0 && (
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium text-gray-900">Total External Storage</span>
              <span className="text-sm text-gray-700">
                {formatBytes(storageData.total_external_used)} / {formatBytes(storageData.total_external_capacity)}
              </span>
            </div>
            <Progress
              value={(storageData.total_external_used / storageData.total_external_capacity) * 100}
              className="h-2"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Available: {formatBytes(storageData.total_external_available)}</span>
              <span>{((storageData.total_external_used / storageData.total_external_capacity) * 100).toFixed(1)}% used</span>
            </div>
          </div>
        )}

        {/* Show formatted NVMe devices */}
        {storageData?.nvme_devices && storageData.nvme_devices.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-medium text-sm text-gray-900">NVMe Devices:</h4>
            {storageData.nvme_devices.map((device, index) => {
              const status = getStorageStatus(device);
              const StatusIcon = status.icon;
              const speedTest = speedTestResults.get(device.device_path);
              const isTesting = testingDevices.has(device.device_path);

              return (
                <div key={index} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <StatusIcon className={`h-4 w-4 ${
                        status.color === 'destructive' ? 'text-red-500' :
                        status.color === 'warning' ? 'text-yellow-500' : 'text-green-500'
                      }`} />
                      <span className="font-medium text-sm">{device.name}</span>
                      <Badge variant="outline" className="text-xs">
                        {device.filesystem}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleSpeedTest(device)}
                        disabled={isTesting}
                        className="flex items-center gap-1 text-xs !text-gray-900 !bg-white border-gray-400 hover:!bg-gray-50"
                      >
                        <Zap className="h-3 w-3" />
                        {isTesting ? 'Testing...' : 'Speed Test'}
                      </Button>
                      <span className="text-xs text-gray-500">
                        {device.device_path}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span>Mount: {device.mountpoint}</span>
                      <span>{formatBytes(device.used)} / {formatBytes(device.size)}</span>
                    </div>
                    <Progress value={device.use_percent} className="h-1.5" />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>Free: {formatBytes(device.available)}</span>
                      <span>{device.use_percent.toFixed(1)}% used</span>
                    </div>

                    {/* Speed test results */}
                    {speedTest && (
                      <div className="mt-2 p-2 bg-blue-50 rounded border">
                        <div className="text-xs font-medium text-blue-800 mb-1">Performance Test Results:</div>
                        <div className="grid grid-cols-2 gap-2 text-xs text-blue-700">
                          <div>Read: <span className="font-medium">{speedTest.read_speed_mbps} MB/s</span></div>
                          <div>Write: <span className="font-medium">{speedTest.write_speed_mbps} MB/s</span></div>
                          <div>Read Time: <span className="font-medium">{speedTest.read_time_seconds}s</span></div>
                          <div>Write Time: <span className="font-medium">{speedTest.write_time_seconds}s</span></div>
                        </div>
                        <div className="text-xs text-blue-600 mt-1">
                          Test Size: {speedTest.test_size} • Tested: {speedTest.timestamp ? new Date(speedTest.timestamp).toLocaleTimeString() : 'Unknown'}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Show message when no NVMe drives detected */}
        {(!storageData?.unformatted_devices || storageData.unformatted_devices.length === 0) &&
         (!storageData?.nvme_devices || storageData.nvme_devices.length === 0) && (
          <div className="text-center p-6 text-gray-500">
            <HardDrive className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No external NVMe PCIe storage detected</p>
            <p className="text-sm">Connect an NVMe drive to the PCIe slot</p>
          </div>
        )}

        {/* All Storage Devices */}
        {storageData?.devices && storageData.devices.length > 0 && (
          <div className="space-y-3 pt-4 border-t">
            <h4 className="font-medium text-sm text-white">All Storage Devices:</h4>
            <div className="grid gap-2">
              {storageData.devices.map((device, index) => {
                const speedTest = speedTestResults.get(device.device_path);
                const isTesting = testingDevices.has(device.device_path);

                return (
                  <div key={index} className="bg-gray-50 rounded border p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <HardDrive className="h-4 w-4 text-gray-600" />
                        <span className="font-medium text-sm text-gray-900">{device.name}</span>
                        {device.is_nvme && (
                          <Badge variant="outline" className="text-xs text-black">NVMe</Badge>
                        )}
                        {device.is_external && (
                          <Badge variant="outline" className="text-xs text-black">External</Badge>
                        )}
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleSpeedTest(device)}
                        disabled={isTesting}
                        className="flex items-center gap-1 text-xs !text-gray-900 !bg-white border-gray-400 hover:!bg-gray-50"
                      >
                        <Zap className="h-3 w-3" />
                        {isTesting ? 'Testing...' : 'Test'}
                      </Button>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-700">Mount: {device.mountpoint}</span>
                        <span className="text-gray-700">{formatBytes(device.used)} / {formatBytes(device.size)}</span>
                      </div>
                      <Progress value={device.use_percent} className="h-2" />
                      <div className="flex justify-between text-xs text-gray-600">
                        <span>Free: {formatBytes(device.available)}</span>
                        <span>{device.use_percent.toFixed(1)}% used</span>
                      </div>
                    </div>

                    {speedTest && (
                      <div className="mt-2">
                        <div className="text-xs bg-blue-100 p-2 rounded text-blue-800">
                          <div className="grid grid-cols-2 gap-2">
                            <span>Read: <strong>{speedTest.read_speed_mbps} MB/s</strong></span>
                            <span>Write: <strong>{speedTest.write_speed_mbps} MB/s</strong></span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {lastUpdate && (
          <div className="text-xs text-gray-500 text-center pt-2 border-t">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}
      </CardContent>

      {/* Format Drive Dialog */}
      <Dialog open={formatDialogOpen} onOpenChange={setFormatDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Format Drive</DialogTitle>
            <DialogDescription>
              This will permanently erase all data on the drive and create a new filesystem.
            </DialogDescription>
          </DialogHeader>

          {selectedDevice && (
            <div className="space-y-4">
              <div className="bg-red-50 border border-red-200 p-3 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <span className="font-medium text-red-800 text-sm">Warning</span>
                </div>
                <p className="text-xs text-red-700">
                  This will permanently erase all data on the drive. This action cannot be undone.
                </p>
              </div>

              <div className="space-y-2">
                <div className="text-sm">
                  <strong>Drive:</strong> {selectedDevice.name} ({selectedDevice.model})
                </div>
                <div className="text-sm">
                  <strong>Size:</strong> {formatBytes(selectedDevice.size)}
                </div>
                <div className="text-sm">
                  <strong>Device:</strong> {selectedDevice.device_path}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="filesystem">Filesystem</Label>
                <Select value={filesystem} onValueChange={setFilesystem}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select filesystem" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ext4">ext4 (Linux)</SelectItem>
                    <SelectItem value="fat32">FAT32 (Universal)</SelectItem>
                    <SelectItem value="ntfs">NTFS (Windows)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="driveLabel">Drive Label</Label>
                <Input
                  id="driveLabel"
                  value={driveLabel}
                  onChange={(e) => setDriveLabel(e.target.value)}
                  placeholder="ExternalDrive"
                  maxLength={32}
                />
              </div>

              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setFormatDialogOpen(false)}
                  disabled={isFormatting}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleFormatDrive}
                  disabled={isFormatting}
                >
                  {isFormatting ? 'Formatting...' : 'Format Drive'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default StorageMonitor;