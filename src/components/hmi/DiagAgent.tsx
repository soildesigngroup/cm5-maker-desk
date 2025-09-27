import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  HMIApiService,
  DiagAgentStatus,
  LogAnalysis,
  AlertRecord,
  DiagConfig,
  ChatMessage
} from '@/services/hmi-api';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Eye,
  FileText,
  Play,
  Settings,
  Shield,
  Stethoscope,
  TrendingUp,
  XCircle,
  RefreshCw,
  Mail,
  Database,
  BarChart3,
  Brain,
  AlertCircle,
  MessageSquare,
  Send,
  User,
  Bot
} from 'lucide-react';

interface DiagAgentProps {
  apiService: HMIApiService;
}

export function DiagAgent({ apiService }: DiagAgentProps) {
  const [status, setStatus] = useState<DiagAgentStatus | null>(null);
  const [analyses, setAnalyses] = useState<LogAnalysis[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [config, setConfig] = useState<DiagConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showConfigDialog, setShowConfigDialog] = useState(false);

  // Configuration state
  const [newConfig, setNewConfig] = useState<Partial<DiagConfig>>({});

  // Chat state
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatMessage, setChatMessage] = useState('');
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  useEffect(() => {
    fetchStatus();
    fetchRecentAnalyses();
    fetchAlerts();
    fetchConfig();
    fetchChatHistory();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchRecentAnalyses();
      fetchAlerts();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await apiService.getDiagAgentStatus();
      if (response.success && response.data) {
        setStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch DIAG Agent status:', error);
    }
  };

  const fetchRecentAnalyses = async () => {
    try {
      const response = await apiService.getDiagAnalyses();
      if (response.success && response.data) {
        setAnalyses(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch analyses:', error);
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await apiService.getDiagAlerts();
      if (response.success && response.data) {
        setAlerts(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  };

  const fetchConfig = async () => {
    try {
      const response = await apiService.getDiagConfig();
      if (response.success && response.data) {
        setConfig(response.data);
        setNewConfig(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch config:', error);
    }
  };

  const handleStartAnalysis = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.startDiagAnalysis();
      if (response.success) {
        // Refresh data after analysis
        setTimeout(() => {
          fetchStatus();
          fetchRecentAnalyses();
          fetchAlerts();
        }, 2000);
      }
    } catch (error) {
      console.error('Failed to start analysis:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendTestAlert = async () => {
    try {
      const response = await apiService.sendDiagTestAlert();
      if (response.success) {
        console.log('Test alert sent successfully');
      }
    } catch (error) {
      console.error('Failed to send test alert:', error);
    }
  };

  const handleSaveConfig = async () => {
    try {
      const response = await apiService.updateDiagConfig(newConfig);
      if (response.success) {
        setConfig({ ...config, ...newConfig } as DiagConfig);
        setShowConfigDialog(false);
        fetchStatus(); // Refresh status with new config
      }
    } catch (error) {
      console.error('Failed to save config:', error);
    }
  };

  const fetchChatHistory = async () => {
    try {
      const response = await apiService.getDiagChatHistory();
      if (response.success && response.data) {
        setChatHistory(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch chat history:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!chatMessage.trim() || isSendingMessage) return;

    setIsSendingMessage(true);
    try {
      const response = await apiService.sendDiagChatMessage(chatMessage.trim());
      if (response.success && response.data) {
        setChatHistory(prev => [...prev, response.data]);
        setChatMessage('');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearChat = async () => {
    try {
      const response = await apiService.clearDiagChatHistory();
      if (response.success) {
        setChatHistory([]);
      }
    } catch (error) {
      console.error('Failed to clear chat history:', error);
    }
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600';
    if (score >= 6) return 'text-yellow-600';
    if (score >= 4) return 'text-orange-600';
    return 'text-red-600';
  };

  const getHealthScoreBadge = (score: number) => {
    if (score >= 8) return 'default';
    if (score >= 6) return 'secondary';
    if (score >= 4) return 'destructive';
    return 'destructive';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return 'text-red-600';
      case 'high': return 'text-orange-600';
      case 'medium': return 'text-yellow-600';
      case 'low': return 'text-blue-600';
      default: return 'text-gray-600';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="hmi-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Stethoscope className="w-5 h-5 text-primary" />
            DIAG Agent - AI-Powered Log Monitoring
          </CardTitle>
          <div className="flex gap-2">
            <Button
              onClick={handleStartAnalysis}
              disabled={isLoading}
              className="flex items-center gap-2"
            >
              {isLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {isLoading ? 'Analyzing...' : 'Run Analysis'}
            </Button>
            <Button
              onClick={handleSendTestAlert}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <Mail className="w-4 h-4" />
              Test Alert
            </Button>
            <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  <Settings className="w-4 h-4 mr-2" />
                  Configure
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>DIAG Agent Configuration</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="claude-api-key">Claude API Key</Label>
                    <Input
                      id="claude-api-key"
                      type="password"
                      value={newConfig.claude_api_key || ''}
                      onChange={(e) => setNewConfig({ ...newConfig, claude_api_key: e.target.value })}
                      placeholder="sk-ant-..."
                    />
                  </div>
                  <div>
                    <Label htmlFor="check-interval">Check Interval (minutes)</Label>
                    <Input
                      id="check-interval"
                      type="number"
                      value={newConfig.check_interval || 15}
                      onChange={(e) => setNewConfig({ ...newConfig, check_interval: parseInt(e.target.value) })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="error-threshold">Error Count Threshold</Label>
                    <Input
                      id="error-threshold"
                      type="number"
                      value={newConfig.error_threshold || 10}
                      onChange={(e) => setNewConfig({ ...newConfig, error_threshold: parseInt(e.target.value) })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="email-enabled">Email Alerts</Label>
                    <Select
                      value={newConfig.email_enabled ? 'true' : 'false'}
                      onValueChange={(value) => setNewConfig({ ...newConfig, email_enabled: value === 'true' })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="true">Enabled</SelectItem>
                        <SelectItem value="false">Disabled</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleSaveConfig} className="w-full">
                    Save Configuration
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {status && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center">
                <div className={`text-2xl font-bold ${getHealthScoreColor(status.overall_health_score)}`}>
                  {status.overall_health_score}/10
                </div>
                <div className="text-xs text-muted-foreground">Health Score</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">{status.monitored_files}</div>
                <div className="text-xs text-muted-foreground">Log Files</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">{status.total_analyses}</div>
                <div className="text-xs text-muted-foreground">Analyses</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">{status.active_alerts}</div>
                <div className="text-xs text-muted-foreground">Active Alerts</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-medium">
                  {status.service_running ? (
                    <Badge variant="default" className="flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      Running
                    </Badge>
                  ) : (
                    <Badge variant="destructive" className="flex items-center gap-1">
                      <XCircle className="w-3 h-3" />
                      Stopped
                    </Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">Service Status</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Interface */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="analyses">Analyses</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="insights">Insights</TabsTrigger>
          <TabsTrigger value="chat">Chat</TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* System Health Overview */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary" />
                  System Health Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                {status ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Overall Health</span>
                      <Badge variant={getHealthScoreBadge(status.overall_health_score)}>
                        {status.overall_health_score}/10
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Last Analysis</span>
                      <span className="text-sm text-muted-foreground">
                        {status.last_analysis ? formatTimestamp(status.last_analysis) : 'Never'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Errors (24h)</span>
                      <span className="text-sm font-medium text-orange-600">
                        {status.errors_24h}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Avg Response Time</span>
                      <span className="text-sm text-muted-foreground">
                        {status.avg_response_time}ms
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Claude API Calls</span>
                      <span className="text-sm text-muted-foreground">
                        {status.api_calls_today}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    <Stethoscope className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Loading system health data...</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Recent Activity */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5 text-primary" />
                  Recent Activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <div className="space-y-3">
                    {analyses.slice(0, 10).map((analysis, index) => (
                      <div key={analysis.id} className="flex items-center justify-between p-2 border rounded">
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${getHealthScoreColor(analysis.health_score).replace('text-', 'bg-')}`} />
                          <div>
                            <div className="text-sm font-medium">{analysis.log_file}</div>
                            <div className="text-xs text-muted-foreground">
                              {formatTimestamp(analysis.timestamp)}
                            </div>
                          </div>
                        </div>
                        <Badge variant={getHealthScoreBadge(analysis.health_score)}>
                          {analysis.health_score}/10
                        </Badge>
                      </div>
                    ))}
                    {analyses.length === 0 && (
                      <div className="text-center text-muted-foreground py-8">
                        <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No recent analyses available</p>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="analyses">
          <Card className="hmi-panel">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-primary" />
                Analysis Results
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96">
                <div className="space-y-4">
                  {analyses.map((analysis) => (
                    <div key={analysis.id} className="border border-border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-4 h-4 rounded-full ${getHealthScoreColor(analysis.health_score).replace('text-', 'bg-')}`} />
                          <span className="font-medium">{analysis.log_file}</span>
                          <Badge variant={getHealthScoreBadge(analysis.health_score)}>
                            Health: {analysis.health_score}/10
                          </Badge>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {formatTimestamp(analysis.timestamp)}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
                        <div>
                          <span className="text-muted-foreground">Errors:</span>
                          <span className="ml-2 font-medium text-red-600">{analysis.error_count}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Warnings:</span>
                          <span className="ml-2 font-medium text-yellow-600">{analysis.warning_count}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Response Time:</span>
                          <span className="ml-2 font-medium">{analysis.avg_response_time}ms</span>
                        </div>
                      </div>

                      {analysis.ai_triggered && (
                        <div className="bg-muted p-3 rounded-md">
                          <div className="flex items-center gap-2 mb-2">
                            <Brain className="w-4 h-4 text-primary" />
                            <span className="text-sm font-medium">AI Analysis Summary</span>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {analysis.summary || 'AI analysis completed - view detailed insights in the Insights tab'}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                  {analyses.length === 0 && (
                    <div className="text-center text-muted-foreground py-12">
                      <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No analyses available yet</p>
                      <p className="text-xs">Run an analysis to see results here</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alerts">
          <Card className="hmi-panel">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-primary" />
                Active Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96">
                <div className="space-y-3">
                  {alerts.filter(alert => !alert.resolved).map((alert) => (
                    <Alert key={alert.id} className="border-l-4 border-l-orange-500">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        <div className="flex items-center justify-between mb-2">
                          <Badge variant="outline" className={getSeverityColor(alert.severity)}>
                            {alert.severity.toUpperCase()}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatTimestamp(alert.timestamp)}
                          </span>
                        </div>
                        <div className="font-medium mb-1">{alert.alert_type}</div>
                        <div className="text-sm">{alert.message}</div>
                        {alert.log_file && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Source: {alert.log_file}
                          </div>
                        )}
                      </AlertDescription>
                    </Alert>
                  ))}
                  {alerts.filter(alert => !alert.resolved).length === 0 && (
                    <div className="text-center text-muted-foreground py-12">
                      <CheckCircle className="w-12 h-12 mx-auto mb-4 opacity-50 text-green-500" />
                      <p>No active alerts</p>
                      <p className="text-xs">All systems running smoothly</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="insights">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Trend Analysis */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-primary" />
                  Trend Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-3 bg-muted rounded-md">
                    <h4 className="text-sm font-medium mb-2">Health Score Trend</h4>
                    <p className="text-sm text-muted-foreground">
                      System health has been stable over the past 24 hours with an average score of{' '}
                      {status?.overall_health_score || 'N/A'}/10.
                    </p>
                  </div>
                  <div className="p-3 bg-muted rounded-md">
                    <h4 className="text-sm font-medium mb-2">Error Patterns</h4>
                    <p className="text-sm text-muted-foreground">
                      Most common errors are related to connection timeouts and authentication failures.
                      Consider reviewing API configurations.
                    </p>
                  </div>
                  <div className="p-3 bg-muted rounded-md">
                    <h4 className="text-sm font-medium mb-2">Performance Insights</h4>
                    <p className="text-sm text-muted-foreground">
                      Average response time: {status?.avg_response_time || 'N/A'}ms.
                      Performance is within acceptable ranges.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recommendations */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-primary" />
                  AI Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-3 border-l-4 border-l-green-500 bg-green-50 dark:bg-green-950">
                    <h4 className="text-sm font-medium text-green-800 dark:text-green-200 mb-1">
                      System Optimization
                    </h4>
                    <p className="text-sm text-green-700 dark:text-green-300">
                      Consider enabling log rotation to manage disk space more efficiently.
                    </p>
                  </div>
                  <div className="p-3 border-l-4 border-l-yellow-500 bg-yellow-50 dark:bg-yellow-950">
                    <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-1">
                      Monitoring Enhancement
                    </h4>
                    <p className="text-sm text-yellow-700 dark:text-yellow-300">
                      Add more granular error tracking for better root cause analysis.
                    </p>
                  </div>
                  <div className="p-3 border-l-4 border-l-blue-500 bg-blue-50 dark:bg-blue-950">
                    <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-1">
                      Performance Tuning
                    </h4>
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                      Current system performance is optimal for the current load.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="chat">
          <Card className="hmi-panel">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-primary" />
                Chat with AI Agent
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleClearChat}>
                  Clear History
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Chat Messages */}
                <ScrollArea className="h-96 border border-border rounded-lg p-4">
                  <div className="space-y-4">
                    {chatHistory.length === 0 ? (
                      <div className="text-center text-muted-foreground py-12">
                        <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No chat history yet</p>
                        <p className="text-xs">Ask the AI agent about system issues, logs, or get recommendations</p>
                      </div>
                    ) : (
                      chatHistory.map((msg) => (
                        <div key={msg.id} className="space-y-3">
                          {/* User Message */}
                          <div className="flex items-start gap-3">
                            <User className="w-6 h-6 text-blue-600 mt-1" />
                            <div className="flex-1 bg-blue-50 dark:bg-blue-950 p-3 rounded-lg">
                              <div className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-1">You</div>
                              <p className="text-sm text-blue-700 dark:text-blue-300">{msg.message}</p>
                              <div className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                                {formatTimestamp(msg.timestamp)}
                              </div>
                            </div>
                          </div>

                          {/* AI Response */}
                          <div className="flex items-start gap-3">
                            <Bot className="w-6 h-6 text-green-600 mt-1" />
                            <div className="flex-1 bg-green-50 dark:bg-green-950 p-3 rounded-lg">
                              <div className="text-sm font-medium text-green-800 dark:text-green-200 mb-1">AI Agent</div>
                              <div className="text-sm text-green-700 dark:text-green-300 whitespace-pre-wrap">
                                {msg.response}
                              </div>
                              <div className="text-xs text-green-600 dark:text-green-400 mt-2">
                                {formatTimestamp(msg.timestamp)}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>

                {/* Message Input */}
                <div className="flex gap-2">
                  <Textarea
                    placeholder="Ask about system issues, log analysis, or request recommendations..."
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="flex-1 min-h-[80px] resize-none"
                    disabled={isSendingMessage}
                  />
                  <Button
                    onClick={handleSendMessage}
                    disabled={!chatMessage.trim() || isSendingMessage}
                    className="self-end"
                  >
                    {isSendingMessage ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </Button>
                </div>

                {/* Help Text */}
                <div className="text-xs text-muted-foreground bg-muted p-3 rounded-lg">
                  <p className="font-medium mb-2">💡 Try asking:</p>
                  <ul className="space-y-1">
                    <li>• "What are the recent critical errors?"</li>
                    <li>• "Analyze the system performance trends"</li>
                    <li>• "What recommendations do you have for optimization?"</li>
                    <li>• "Explain the current health score"</li>
                    <li>• "What alerts need immediate attention?"</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}