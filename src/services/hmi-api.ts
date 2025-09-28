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

export interface CANMessage {
  arbitration_id: string;
  data: string[];
  timestamp: number;
  is_extended_id: boolean;
  is_remote_frame: boolean;
  dlc: number;
  formatted_time: string;
}

export interface CANBusConfig {
  interface: string;
  channel: string;
  bitrate: number;
  receive_own_messages?: boolean;
}

export interface CANStatus {
  connected: boolean;
  config: CANBusConfig | null;
  message_count: number;
  queue_size: number;
  available_interfaces: string[];
}

export interface AutomationRequest {
  id?: string;
  name: string;
  method: string;
  url: string;
  headers: Record<string, string>;
  body?: string;
  body_type: string;
  auth_type: string;
  auth_config: Record<string, string>;
  timeout: number;
}

export interface AutomationResponse {
  status_code: number;
  headers: Record<string, string>;
  body: string;
  content_type: string;
  size: number;
  elapsed_time: number;
  timestamp: number;
  cookies: Record<string, string>;
  error?: string;
}

export interface Environment {
  id: string;
  name: string;
  variables: Record<string, string>;
  base_url: string;
  active: boolean;
}

export interface Collection {
  id: string;
  name: string;
  description: string;
  requests: AutomationRequest[];
  environment_id?: string;
  created_at: number;
  updated_at: number;
}

export interface TestResult {
  request_id: string;
  collection_id: string;
  success: boolean;
  response?: AutomationResponse;
  error?: string;
  assertions: any[];
  execution_time: number;
  timestamp: number;
}

export interface AutomationStatus {
  environments: number;
  collections: number;
  active_environment?: string;
  total_requests: number;
  test_results: number;
  recent_results: TestResult[];
}

export interface JsonLibrary {
  id: string;
  name: string;
  content: Record<string, any>;
  library_type: 'schema' | 'template' | 'collection' | 'mock_data';
  description?: string;
  created_at: number;
  updated_at: number;
}

// DIAG Agent Interfaces
export interface DiagAgentStatus {
  service_running: boolean;
  overall_health_score: number;
  monitored_files: number;
  total_analyses: number;
  active_alerts: number;
  last_analysis: string | null;
  errors_24h: number;
  avg_response_time: number;
  api_calls_today: number;
  next_scheduled_analysis: string | null;
  ai_online: boolean;
  ai_status_message: string;
}

export interface LogAnalysis {
  id: string;
  timestamp: string;
  log_file: string;
  health_score: number;
  error_count: number;
  warning_count: number;
  avg_response_time: number;
  ai_triggered: boolean;
  summary?: string;
  analysis_data?: {
    critical_issues: string[];
    performance_insights: {
      response_time_analysis: string;
      bottlenecks: string[];
      recommendations: string[];
    };
    error_analysis: {
      patterns: string[];
      root_causes: string[];
      frequency: string;
    };
    recommendations: {
      high_priority: string[];
      medium_priority: string[];
      low_priority: string[];
    };
    trend_analysis: string;
  };
}

export interface AlertRecord {
  id: string;
  timestamp: string;
  alert_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  log_file?: string;
  health_score?: number;
  resolved: boolean;
  resolution_timestamp?: string;
  resolution_notes?: string;
}

export interface DiagConfig {
  claude_api_key: string;
  check_interval: number;
  error_threshold: number;
  response_time_threshold: number;
  high_activity_threshold: number;
  email_enabled: boolean;
  email_smtp_server?: string;
  email_smtp_port?: number;
  email_username?: string;
  email_password?: string;
  email_from?: string;
  email_to?: string;
  log_files: Array<{
    path: string;
    name: string;
    enabled: boolean;
  }>;
  alert_thresholds: {
    health_score: number;
    error_count: number;
    response_time: number;
  };
}

export interface ChatMessage {
  id: string;
  timestamp: string;
  message: string;
  response: string;
  role: 'user' | 'assistant';
  context?: {
    system_status?: any;
    recent_analyses?: LogAnalysis[];
    active_alerts?: AlertRecord[];
  };
}

export interface AudioControl {
  name: string;
  type: 'volume' | 'switch' | 'enum' | 'eq';
  value: string | number;
  min?: number;
  max?: number;
  items?: string[];
}

export interface AudioStatus {
  connected: boolean;
  card_id: number;
  card_name: string;
  total_controls: number;
  volume_controls: number;
  switch_controls: number;
  eq_controls: number;
  last_refresh?: number;
}

export class HMIApiService {
  private baseUrl: string;
  private ws: WebSocket | null = null;
  private eventCallbacks: Map<string, (data: any) => void> = new Map();

  constructor(baseUrl: string = 'http://localhost:8081') {
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

  async getAIVisionFrameData(): Promise<APIResponse<{ frame: string; format: string; timestamp: number }>> {
    return this.request(`/api/ai_vision/frame`);
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

  // CAN Commands
  async getCANStatus(): Promise<APIResponse<CANStatus>> {
    return this.sendCommand({
      action: 'get_status',
      device: 'can',
      request_id: `can_status_${Date.now()}`,
    });
  }

  async getCANInterfaces(): Promise<APIResponse<{ interfaces: string[] }>> {
    return this.sendCommand({
      action: 'get_interfaces',
      device: 'can',
      request_id: `can_interfaces_${Date.now()}`,
    });
  }

  async connectCAN(config: CANBusConfig): Promise<APIResponse<{ connected: boolean; config: CANBusConfig }>> {
    return this.sendCommand({
      action: 'connect',
      device: 'can',
      params: config,
      request_id: `can_connect_${Date.now()}`,
    });
  }

  async disconnectCAN(): Promise<APIResponse<{ connected: boolean }>> {
    return this.sendCommand({
      action: 'disconnect',
      device: 'can',
      request_id: `can_disconnect_${Date.now()}`,
    });
  }

  async sendCANMessage(arbitrationId: string, data: string[], isExtendedId: boolean = false): Promise<APIResponse<{ sent: boolean; arbitration_id: string; data: string[] }>> {
    return this.sendCommand({
      action: 'send_message',
      device: 'can',
      params: {
        arbitration_id: arbitrationId,
        data,
        is_extended_id: isExtendedId,
      },
      request_id: `can_send_${Date.now()}`,
    });
  }

  async getCANMessages(count: number = 50): Promise<APIResponse<{ messages: CANMessage[]; count: number }>> {
    return this.sendCommand({
      action: 'get_messages',
      device: 'can',
      params: { count },
      request_id: `can_messages_${Date.now()}`,
    });
  }

  async clearCANMessages(): Promise<APIResponse<{ cleared: boolean }>> {
    return this.sendCommand({
      action: 'clear_messages',
      device: 'can',
      request_id: `can_clear_${Date.now()}`,
    });
  }

  async executeCANCommand(command: string): Promise<APIResponse<any>> {
    return this.sendCommand({
      action: 'cli_command',
      device: 'can',
      params: { command },
      request_id: `can_cli_${Date.now()}`,
    });
  }

  // Automation Commands
  async getAutomationStatus(): Promise<APIResponse<AutomationStatus>> {
    return this.sendCommand({
      action: 'get_status',
      device: 'automation',
      request_id: `automation_status_${Date.now()}`,
    });
  }

  async createEnvironment(name: string, variables: Record<string, string> = {}, baseUrl: string = ''): Promise<APIResponse<Environment>> {
    return this.sendCommand({
      action: 'create_environment',
      device: 'automation',
      params: { name, variables, base_url: baseUrl },
      request_id: `automation_env_create_${Date.now()}`,
    });
  }

  async listEnvironments(): Promise<APIResponse<{ environments: Environment[] }>> {
    return this.sendCommand({
      action: 'list_environments',
      device: 'automation',
      request_id: `automation_env_list_${Date.now()}`,
    });
  }

  async setActiveEnvironment(environmentId: string): Promise<APIResponse<{ active: boolean }>> {
    return this.sendCommand({
      action: 'set_active_environment',
      device: 'automation',
      params: { environment_id: environmentId },
      request_id: `automation_env_active_${Date.now()}`,
    });
  }

  async createCollection(name: string, description: string = ''): Promise<APIResponse<Collection>> {
    return this.sendCommand({
      action: 'create_collection',
      device: 'automation',
      params: { name, description },
      request_id: `automation_collection_create_${Date.now()}`,
    });
  }

  async listCollections(): Promise<APIResponse<{ collections: Collection[] }>> {
    return this.sendCommand({
      action: 'list_collections',
      device: 'automation',
      request_id: `automation_collection_list_${Date.now()}`,
    });
  }

  async getCollection(collectionId: string): Promise<APIResponse<Collection>> {
    return this.sendCommand({
      action: 'get_collection',
      device: 'automation',
      params: { collection_id: collectionId },
      request_id: `automation_collection_get_${Date.now()}`,
    });
  }

  async addRequestToCollection(collectionId: string, request: AutomationRequest): Promise<APIResponse<{ added: boolean; request_id: string }>> {
    return this.sendCommand({
      action: 'add_request',
      device: 'automation',
      params: { collection_id: collectionId, request },
      request_id: `automation_request_add_${Date.now()}`,
    });
  }

  async executeRequest(request: AutomationRequest, environmentId?: string): Promise<APIResponse<AutomationResponse>> {
    return this.sendCommand({
      action: 'execute_request',
      device: 'automation',
      params: { request, environment_id: environmentId },
      request_id: `automation_request_execute_${Date.now()}`,
    });
  }

  async runCollection(collectionId: string, environmentId?: string): Promise<APIResponse<{ results: TestResult[]; total: number; passed: number; failed: number }>> {
    return this.sendCommand({
      action: 'run_collection',
      device: 'automation',
      params: { collection_id: collectionId, environment_id: environmentId },
      request_id: `automation_collection_run_${Date.now()}`,
    });
  }

  async importCollection(collectionData: any): Promise<APIResponse<Collection>> {
    return this.sendCommand({
      action: 'import_collection',
      device: 'automation',
      params: { collection_data: collectionData },
      request_id: `automation_collection_import_${Date.now()}`,
    });
  }

  async clearAutomationResults(): Promise<APIResponse<{ cleared: boolean }>> {
    return this.sendCommand({
      action: 'clear_results',
      device: 'automation',
      request_id: `automation_clear_${Date.now()}`,
    });
  }

  // JSON Library Commands
  async uploadJsonLibrary(name: string, content: Record<string, any>, libraryType: string = 'schema'): Promise<APIResponse<JsonLibrary>> {
    return this.sendCommand({
      action: 'upload_json_library',
      device: 'automation',
      params: { name, content, type: libraryType },
      request_id: `json_library_upload_${Date.now()}`,
    });
  }

  async listJsonLibraries(): Promise<APIResponse<{ libraries: JsonLibrary[] }>> {
    return this.sendCommand({
      action: 'list_json_libraries',
      device: 'automation',
      request_id: `json_library_list_${Date.now()}`,
    });
  }

  async getJsonLibrary(libraryId: string): Promise<APIResponse<JsonLibrary>> {
    return this.sendCommand({
      action: 'get_json_library',
      device: 'automation',
      params: { library_id: libraryId },
      request_id: `json_library_get_${Date.now()}`,
    });
  }

  async deleteJsonLibrary(libraryId: string): Promise<APIResponse<{ deleted: boolean }>> {
    return this.sendCommand({
      action: 'delete_json_library',
      device: 'automation',
      params: { library_id: libraryId },
      request_id: `json_library_delete_${Date.now()}`,
    });
  }

  async validateJson(schemaId: string, data: Record<string, any>): Promise<APIResponse<{ valid: boolean; errors?: string[] }>> {
    return this.sendCommand({
      action: 'validate_json',
      device: 'automation',
      params: { schema_id: schemaId, data },
      request_id: `json_validate_${Date.now()}`,
    });
  }

  async generateMockData(templateId: string, variables: Record<string, any> = {}): Promise<APIResponse<{ mock_data: any }>> {
    return this.sendCommand({
      action: 'generate_mock_data',
      device: 'automation',
      params: { template_id: templateId, variables },
      request_id: `json_mock_${Date.now()}`,
    });
  }

  // DIAG Agent Commands
  async getDiagAgentStatus(): Promise<APIResponse<DiagAgentStatus>> {
    return this.sendCommand<DiagAgentStatus>({
      action: 'get_status',
      device: 'diag_agent',
      request_id: `diag_status_${Date.now()}`,
    });
  }

  async getDiagAnalyses(limit: number = 50): Promise<APIResponse<LogAnalysis[]>> {
    return this.sendCommand<LogAnalysis[]>({
      action: 'get_analyses',
      device: 'diag_agent',
      params: { limit },
      request_id: `diag_analyses_${Date.now()}`,
    });
  }

  async getDiagAlerts(resolved: boolean = false): Promise<APIResponse<AlertRecord[]>> {
    return this.sendCommand<AlertRecord[]>({
      action: 'get_alerts',
      device: 'diag_agent',
      params: { resolved },
      request_id: `diag_alerts_${Date.now()}`,
    });
  }

  async getDiagConfig(): Promise<APIResponse<DiagConfig>> {
    return this.sendCommand<DiagConfig>({
      action: 'get_config',
      device: 'diag_agent',
      request_id: `diag_config_${Date.now()}`,
    });
  }

  async updateDiagConfig(config: Partial<DiagConfig>): Promise<APIResponse<{ success: boolean }>> {
    return this.sendCommand({
      action: 'update_config',
      device: 'diag_agent',
      params: config,
      request_id: `diag_config_update_${Date.now()}`,
    });
  }

  async startDiagAnalysis(): Promise<APIResponse<{ message: string }>> {
    return this.sendCommand({
      action: 'start_analysis',
      device: 'diag_agent',
      request_id: `diag_analysis_${Date.now()}`,
    });
  }

  async sendDiagTestAlert(): Promise<APIResponse<{ message: string }>> {
    return this.sendCommand({
      action: 'send_test_alert',
      device: 'diag_agent',
      request_id: `diag_test_alert_${Date.now()}`,
    });
  }

  async getDiagInsights(hours: number = 24): Promise<APIResponse<{
    health_trend: Array<{ timestamp: string; score: number }>;
    error_patterns: Array<{ pattern: string; count: number }>;
    performance_metrics: {
      avg_response_time: number;
      peak_response_time: number;
      error_rate: number;
    };
    recommendations: string[];
  }>> {
    return this.sendCommand({
      action: 'get_insights',
      device: 'diag_agent',
      params: { hours },
      request_id: `diag_insights_${Date.now()}`,
    });
  }

  async resolveDiagAlert(alertId: string, notes?: string): Promise<APIResponse<{ success: boolean }>> {
    return this.sendCommand({
      action: 'resolve_alert',
      device: 'diag_agent',
      params: { alert_id: alertId, notes },
      request_id: `diag_resolve_${Date.now()}`,
    });
  }

  async sendDiagChatMessage(message: string): Promise<APIResponse<ChatMessage>> {
    return this.sendCommand<ChatMessage>({
      action: 'send_chat_message',
      device: 'diag_agent',
      params: { message },
      request_id: `diag_chat_${Date.now()}`,
    });
  }

  async getDiagChatHistory(limit: number = 50): Promise<APIResponse<ChatMessage[]>> {
    return this.sendCommand<ChatMessage[]>({
      action: 'get_chat_history',
      device: 'diag_agent',
      params: { limit },
      request_id: `diag_chat_history_${Date.now()}`,
    });
  }

  async clearDiagChatHistory(): Promise<APIResponse<{ success: boolean }>> {
    return this.sendCommand({
      action: 'clear_chat_history',
      device: 'diag_agent',
      request_id: `diag_chat_clear_${Date.now()}`,
    });
  }

  async validateDiagApiKey(): Promise<APIResponse<{ ai_online: boolean; api_key_valid: boolean; message: string }>> {
    return this.sendCommand<{ ai_online: boolean; api_key_valid: boolean; message: string }>({
      action: 'validate_api_key',
      device: 'diag_agent',
      request_id: `diag_validate_${Date.now()}`,
    });
  }

  // Audio Interface Methods
  async getAudioStatus(): Promise<APIResponse<AudioStatus>> {
    return this.sendCommand<AudioStatus>({
      action: 'get_status',
      device: 'audio',
      request_id: `audio_status_${Date.now()}`,
    });
  }

  async getAllAudioControls(): Promise<APIResponse<AudioControl[]>> {
    return this.sendCommand<AudioControl[]>({
      action: 'get_all_controls',
      device: 'audio',
      request_id: `audio_all_controls_${Date.now()}`,
    });
  }

  async getVolumeControls(): Promise<APIResponse<AudioControl[]>> {
    return this.sendCommand<AudioControl[]>({
      action: 'get_volume_controls',
      device: 'audio',
      request_id: `audio_volume_controls_${Date.now()}`,
    });
  }

  async getSwitchControls(): Promise<APIResponse<AudioControl[]>> {
    return this.sendCommand<AudioControl[]>({
      action: 'get_switch_controls',
      device: 'audio',
      request_id: `audio_switch_controls_${Date.now()}`,
    });
  }

  async getEQControls(): Promise<APIResponse<AudioControl[]>> {
    return this.sendCommand<AudioControl[]>({
      action: 'get_eq_controls',
      device: 'audio',
      request_id: `audio_eq_controls_${Date.now()}`,
    });
  }

  async setAudioControl(controlName: string, value: string | number): Promise<APIResponse<{ success: boolean; message: string }>> {
    return this.sendCommand<{ success: boolean; message: string }>({
      action: 'set_control',
      device: 'audio',
      params: { control_name: controlName, value },
      request_id: `audio_set_control_${Date.now()}`,
    });
  }

  async getAudioControl(controlName: string): Promise<APIResponse<AudioControl>> {
    return this.sendCommand<AudioControl>({
      action: 'get_control',
      device: 'audio',
      params: { control_name: controlName },
      request_id: `audio_get_control_${Date.now()}`,
    });
  }

  async refreshAudioControls(): Promise<APIResponse<{ success: boolean; message: string }>> {
    return this.sendCommand<{ success: boolean; message: string }>({
      action: 'refresh_controls',
      device: 'audio',
      request_id: `audio_refresh_${Date.now()}`,
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
    return this.sendCommand<{ cameras: CameraInfo[] }>({
      action: 'list_cameras',
      device: 'ai_vision',
      request_id: `ai_vision_cameras_${Date.now()}`,
    });
  }

  async startAIVision(cameraId: number, modelName?: string): Promise<APIResponse<{ success: boolean; message: string }>> {
    return this.sendCommand<{ success: boolean; message: string }>({
      action: 'start',
      device: 'ai_vision',
      params: { camera_id: cameraId, model_name: modelName },
      request_id: `ai_vision_start_${Date.now()}`,
    });
  }

  async stopAIVision(): Promise<APIResponse<{ success: boolean; message: string }>> {
    return this.sendCommand<{ success: boolean; message: string }>({
      action: 'stop',
      device: 'ai_vision',
      request_id: `ai_vision_stop_${Date.now()}`,
    });
  }

  async setAIVisionConfidence(confidence: number): Promise<APIResponse<{ success: boolean; confidence: number }>> {
    return this.sendCommand<{ success: boolean; confidence: number }>({
      action: 'set_confidence',
      device: 'ai_vision',
      params: { confidence },
      request_id: `ai_vision_confidence_${Date.now()}`,
    });
  }

  async getAIVisionFrame(): Promise<APIResponse<{ frame: string; timestamp: number }>> {
    return this.sendCommand<{ frame: string; timestamp: number }>({
      action: 'get_frame',
      device: 'ai_vision',
      request_id: `ai_vision_frame_${Date.now()}`,
    });
  }

  async getAIVisionDetections(): Promise<APIResponse<DetectionResult[]>> {
    return this.sendCommand<DetectionResult[]>({
      action: 'get_detections',
      device: 'ai_vision',
      request_id: `ai_vision_detections_${Date.now()}`,
    });
  }

  async getAvailableModels(): Promise<APIResponse<{ models: string[] }>> {
    return this.sendCommand<{ models: string[] }>({
      action: 'get_available_models',
      device: 'ai_vision',
      request_id: `ai_vision_models_${Date.now()}`,
    });
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