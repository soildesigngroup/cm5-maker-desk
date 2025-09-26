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

export interface ADCDataPoint {
  timestamp: number;
  channel: number;
  raw_value: number;
  voltage: number;
  vref: number;
}

export interface LoggingStats {
  enabled: boolean;
  active: boolean;
  sample_interval: number;
  memory_points_per_channel: Record<string, number>;
  total_memory_points: number;
  queue_size: number;
  current_log_file?: string;
}

export interface LoggedDataResponse {
  logged_data: Record<string, ADCDataPoint[]>;
  logging_stats: LoggingStats;
}

export interface CameraInfo {
  camera_id: number;
  camera_type: 'usb' | 'picamera';
  name: string;
  resolution: [number, number];
  available: boolean;
}

export interface Detection {
  class_id: number;
  class_name: string;
  confidence: number;
  bbox: [number, number, number, number]; // x1, y1, x2, y2
  timestamp: number;
}

export interface AIVisionStatus {
  active: boolean;
  model_loaded: boolean;
  camera_active: boolean;
  current_camera?: CameraInfo;
  available_cameras: CameraInfo[];
  model_name: string;
  fps: number;
  total_detections: number;
  last_detection_time?: number;
}

export interface DetectionResult {
  timestamp: number;
  detections: Detection[];
  fps: number;
}

export class HMIApiService {
  private baseUrl: string;
  private ws: WebSocket | null = null;
  private eventCallbacks: Map<string, (data: any) => void> = new Map();

  constructor(baseUrl: string = 'http://localhost:8082') {
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

  // ADC Logging Commands
  async getLoggedData(
    channel?: number,
    maxPoints?: number,
    timeRangeSeconds?: number
  ): Promise<APIResponse<LoggedDataResponse>> {
    return this.sendCommand<LoggedDataResponse>({
      action: 'get_logged_data',
      device: 'adc',
      params: {
        channel,
        max_points: maxPoints,
        time_range_seconds: timeRangeSeconds
      },
      request_id: `adc_logged_${Date.now()}`,
    });
  }

  async startADCLogging(): Promise<APIResponse<{ logging_active: boolean }>> {
    return this.sendCommand({
      action: 'start_logging',
      device: 'adc',
      request_id: `adc_start_log_${Date.now()}`,
    });
  }

  async stopADCLogging(): Promise<APIResponse<{ logging_active: boolean }>> {
    return this.sendCommand({
      action: 'stop_logging',
      device: 'adc',
      request_id: `adc_stop_log_${Date.now()}`,
    });
  }

  async getLoggingStats(): Promise<APIResponse<LoggingStats>> {
    return this.sendCommand<LoggingStats>({
      action: 'get_logging_stats',
      device: 'adc',
      request_id: `adc_log_stats_${Date.now()}`,
    });
  }

  async exportADCDataCSV(
    filename?: string,
    channel?: number,
    timeRangeSeconds?: number
  ): Promise<APIResponse<{ filename: string; exported: boolean }>> {
    return this.sendCommand({
      action: 'export_csv',
      device: 'adc',
      params: {
        filename,
        channel,
        time_range_seconds: timeRangeSeconds
      },
      request_id: `adc_export_${Date.now()}`,
    });
  }

  // AI-Vision Commands
  async getAIVisionStatus(): Promise<APIResponse<AIVisionStatus>> {
    return this.sendCommand<AIVisionStatus>({
      action: 'get_status',
      device: 'ai_vision',
      request_id: `ai_vision_status_${Date.now()}`,
    });
  }

  async listCameras(): Promise<APIResponse<{ cameras: CameraInfo[] }>> {
    return this.sendCommand({
      action: 'list_cameras',
      device: 'ai_vision',
      request_id: `ai_vision_cameras_${Date.now()}`,
    });
  }

  async startAIVision(
    cameraId: number = 0,
    modelName: string = 'yolo11n.pt'
  ): Promise<APIResponse<{ active: boolean; camera_id: number; model_name: string }>> {
    return this.sendCommand({
      action: 'start',
      device: 'ai_vision',
      params: { camera_id: cameraId, model_name: modelName },
      request_id: `ai_vision_start_${Date.now()}`,
    });
  }

  async stopAIVision(): Promise<APIResponse<{ active: boolean }>> {
    return this.sendCommand({
      action: 'stop',
      device: 'ai_vision',
      request_id: `ai_vision_stop_${Date.now()}`,
    });
  }

  async setConfidenceThreshold(confidence: number): Promise<APIResponse<{ confidence_threshold: number }>> {
    return this.sendCommand({
      action: 'set_confidence',
      device: 'ai_vision',
      params: { confidence },
      request_id: `ai_vision_confidence_${Date.now()}`,
    });
  }

  async getAIVisionFrame(): Promise<APIResponse<{ frame: string; format: string; active: boolean }>> {
    return this.sendCommand({
      action: 'get_frame',
      device: 'ai_vision',
      request_id: `ai_vision_frame_${Date.now()}`,
    });
  }

  async getDetections(maxCount: number = 10): Promise<APIResponse<{ detections: DetectionResult[]; count: number }>> {
    return this.sendCommand({
      action: 'get_detections',
      device: 'ai_vision',
      params: { max_count: maxCount },
      request_id: `ai_vision_detections_${Date.now()}`,
    });
  }

  async getAvailableModels(): Promise<APIResponse<{ available_models: string[] }>> {
    return this.sendCommand({
      action: 'get_available_models',
      device: 'ai_vision',
      request_id: `ai_vision_models_${Date.now()}`,
    });
  }

  getVideoStreamUrl(): string {
    return `${this.baseUrl}/api/ai_vision/stream`;
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