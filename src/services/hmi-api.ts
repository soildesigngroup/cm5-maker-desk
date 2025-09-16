export interface APIResponse<T = any> {
  success: boolean;
  timestamp: number;
  request_id?: string;
  data?: T;
  error?: string;
  warnings?: string[];
}

export interface DeviceStatus {
  device_type: string;
  device_id: string;
  connected: boolean;
  last_update: number;
  error_message?: string;
  capabilities?: string[];
}

export interface SystemStatus {
  timestamp: number;
  bus_number: number;
  monitoring_active: boolean;
  monitoring_interval: number;
  devices: Record<string, DeviceStatus>;
}

export interface ADCReading {
  channel: number;
  raw_value: number;
  voltage: number;
  vref?: number;
}

export interface FanStatus {
  rpm: number;
  target_rpm: number;
  duty_cycle: number;
  failure?: boolean;
}

export class HMIApiService {
  private baseUrl: string;
  private ws: WebSocket | null = null;
  private eventCallbacks: Map<string, (data: any) => void> = new Map();

  constructor(baseUrl: string = 'http://localhost:8080') {
    this.baseUrl = baseUrl;
  }

  // HTTP API Methods
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<APIResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}/api${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      return {
        success: false,
        timestamp: Date.now() / 1000,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  private async sendCommand<T>(command: any): Promise<APIResponse<T>> {
    return this.request<T>('/command', {
      method: 'POST',
      body: JSON.stringify(command),
    });
  }

  // System Commands
  async getSystemStatus(): Promise<APIResponse<SystemStatus>> {
    return this.sendCommand<SystemStatus>({
      action: 'get_system_status',
      request_id: `status_${Date.now()}`,
    });
  }

  async getDeviceList(): Promise<APIResponse<{ devices: Record<string, DeviceStatus> }>> {
    return this.sendCommand({
      action: 'get_device_list',
      request_id: `devices_${Date.now()}`,
    });
  }

  async startMonitoring(interval: number = 1.0, devices?: string[]): Promise<APIResponse> {
    return this.sendCommand({
      action: 'start_monitoring',
      params: {
        interval,
        ...(devices && { devices }),
      },
      request_id: `monitor_start_${Date.now()}`,
    });
  }

  async stopMonitoring(): Promise<APIResponse> {
    return this.sendCommand({
      action: 'stop_monitoring',
      request_id: `monitor_stop_${Date.now()}`,
    });
  }

  // ADC Commands
  async readADCChannel(channel: number): Promise<APIResponse<ADCReading>> {
    return this.sendCommand<ADCReading>({
      action: 'read_channel',
      device: 'adc',
      params: { channel },
      request_id: `adc_ch${channel}_${Date.now()}`,
    });
  }

  async readAllADCChannels(): Promise<APIResponse<{ channels: ADCReading[]; vref: number }>> {
    return this.sendCommand({
      action: 'read_all_channels',
      device: 'adc',
      request_id: `adc_all_${Date.now()}`,
    });
  }

  async setADCVref(vref: number): Promise<APIResponse<{ vref: number }>> {
    return this.sendCommand({
      action: 'set_vref',
      device: 'adc',
      params: { vref },
      request_id: `adc_vref_${Date.now()}`,
    });
  }

  // I/O Commands
  async readIOPin(pin: number): Promise<APIResponse<{ pin: number; state: boolean }>> {
    return this.sendCommand({
      action: 'read_pin',
      device: 'io',
      params: { pin },
      request_id: `io_read_${pin}_${Date.now()}`,
    });
  }

  async writeIOPin(pin: number, state: boolean): Promise<APIResponse<{ pin: number; state: boolean }>> {
    return this.sendCommand({
      action: 'write_pin',
      device: 'io',
      params: { pin, state },
      request_id: `io_write_${pin}_${Date.now()}`,
    });
  }

  async configureIOPin(pin: number, direction: 'input' | 'output', pullup?: boolean): Promise<APIResponse> {
    return this.sendCommand({
      action: 'configure_pin',
      device: 'io',
      params: { pin, direction, pullup },
      request_id: `io_config_${pin}_${Date.now()}`,
    });
  }

  async readAllIOPins(): Promise<APIResponse<{ pins: Array<{ pin: number; state: boolean }> }>> {
    return this.sendCommand({
      action: 'read_all_pins',
      device: 'io',
      request_id: `io_all_${Date.now()}`,
    });
  }

  // Fan Commands
  async setFanPWM(dutyCycle: number): Promise<APIResponse<{ duty_cycle: number }>> {
    return this.sendCommand({
      action: 'set_pwm',
      device: 'fan',
      params: { duty_cycle: dutyCycle },
      request_id: `fan_pwm_${Date.now()}`,
    });
  }

  async setFanRPM(targetRpm: number): Promise<APIResponse<{ target_rpm: number }>> {
    return this.sendCommand({
      action: 'set_rpm',
      device: 'fan',
      params: { target_rpm: targetRpm },
      request_id: `fan_rpm_${Date.now()}`,
    });
  }

  async getFanStatus(): Promise<APIResponse<FanStatus>> {
    return this.sendCommand<FanStatus>({
      action: 'get_status',
      device: 'fan',
      request_id: `fan_status_${Date.now()}`,
    });
  }

  // RTC Commands
  async getRTCDateTime(): Promise<APIResponse<{ datetime: string; timestamp: number }>> {
    return this.sendCommand({
      action: 'read_datetime',
      device: 'rtc',
      request_id: `rtc_read_${Date.now()}`,
    });
  }

  async setRTCDateTime(datetime: string): Promise<APIResponse<{ datetime: string }>> {
    return this.sendCommand({
      action: 'set_datetime',
      device: 'rtc',
      params: { datetime },
      request_id: `rtc_set_${Date.now()}`,
    });
  }

  // WebSocket Connection
  connectWebSocket(url: string = 'ws://localhost:8081'): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.emit('connected', null);
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit('data', data);
        
        // Emit specific device events
        if (data.device) {
          this.emit(`${data.device}_data`, data);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      this.emit('disconnected', null);
    };

    this.ws.onerror = (error) => {
      this.emit('error', error);
    };
  }

  disconnectWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  // Event System
  on(event: string, callback: (data: any) => void): void {
    this.eventCallbacks.set(event, callback);
  }

  off(event: string): void {
    this.eventCallbacks.delete(event);
  }

  private emit(event: string, data: any): void {
    const callback = this.eventCallbacks.get(event);
    if (callback) {
      callback(data);
    }
  }

  // Connection Test
  async testConnection(): Promise<boolean> {
    try {
      const response = await this.getSystemStatus();
      return response.success;
    } catch {
      return false;
    }
  }
}