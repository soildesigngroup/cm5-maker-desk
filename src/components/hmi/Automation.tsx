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
import {
  HMIApiService,
  AutomationStatus,
  AutomationRequest,
  AutomationResponse,
  Environment,
  Collection,
  TestResult,
  JsonLibrary
} from '@/services/hmi-api';
import {
  Zap,
  Play,
  Plus,
  Folder,
  FileText,
  Send,
  Globe,
  Code,
  CheckCircle,
  XCircle,
  Clock,
  Trash2,
  RotateCcw,
  Library,
  FileJson,
  Shield,
  Copy,
  Upload,
  Edit
} from 'lucide-react';

interface AutomationProps {
  apiService: HMIApiService;
}

export function Automation({ apiService }: AutomationProps) {
  const [status, setStatus] = useState<AutomationStatus | null>(null);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [jsonLibraries, setJsonLibraries] = useState<JsonLibrary[]>([]);
  const [activeEnvironment, setActiveEnvironment] = useState<string>('');
  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  // Request builder state
  const [currentRequest, setCurrentRequest] = useState<AutomationRequest>({
    name: 'New Request',
    method: 'GET',
    url: 'https://api.example.com/endpoint',
    headers: {},
    body: '',
    body_type: 'json',
    auth_type: 'none',
    auth_config: {},
    timeout: 30
  });

  // Response state
  const [response, setResponse] = useState<AutomationResponse | null>(null);
  const [testResults, setTestResults] = useState<TestResult[]>([]);

  // UI state
  const [mainTab, setMainTab] = useState('requests');
  const [activeTab, setActiveTab] = useState('request');
  const [showNewEnvironmentDialog, setShowNewEnvironmentDialog] = useState(false);
  const [showNewCollectionDialog, setShowNewCollectionDialog] = useState(false);
  const [showNewLibraryDialog, setShowNewLibraryDialog] = useState(false);

  // New environment form
  const [newEnvName, setNewEnvName] = useState('');
  const [newEnvBaseUrl, setNewEnvBaseUrl] = useState('');
  const [newEnvVariables, setNewEnvVariables] = useState('{}');

  // New collection form
  const [newCollectionName, setNewCollectionName] = useState('');
  const [newCollectionDescription, setNewCollectionDescription] = useState('');

  // New library form
  const [newLibraryName, setNewLibraryName] = useState('');
  const [newLibraryType, setNewLibraryType] = useState<'schema' | 'template' | 'collection' | 'mock_data'>('schema');
  const [newLibraryContent, setNewLibraryContent] = useState('{}');
  const [uploadMethod, setUploadMethod] = useState<'paste' | 'file'>('paste');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    fetchStatus();
    fetchEnvironments();
    fetchCollections();
    fetchJsonLibraries();
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await apiService.getAutomationStatus();
      if (response.success && response.data) {
        setStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch automation status:', error);
    }
  };

  const fetchEnvironments = async () => {
    try {
      const response = await apiService.listEnvironments();
      if (response.success && response.data) {
        setEnvironments(response.data.environments);
      }
    } catch (error) {
      console.error('Failed to fetch environments:', error);
    }
  };

  const fetchCollections = async () => {
    try {
      const response = await apiService.listCollections();
      if (response.success && response.data) {
        setCollections(response.data.collections);
      }
    } catch (error) {
      console.error('Failed to fetch collections:', error);
    }
  };

  const fetchJsonLibraries = async () => {
    try {
      const response = await apiService.listJsonLibraries();
      if (response.success && response.data) {
        setJsonLibraries(response.data.libraries);
      }
    } catch (error) {
      console.error('Failed to fetch JSON libraries:', error);
    }
  };

  const handleCreateEnvironment = async () => {
    if (!newEnvName.trim()) return;

    try {
      let variables = {};
      if (newEnvVariables.trim()) {
        variables = JSON.parse(newEnvVariables);
      }

      const response = await apiService.createEnvironment(newEnvName, variables, newEnvBaseUrl);
      if (response.success) {
        await fetchEnvironments();
        setShowNewEnvironmentDialog(false);
        setNewEnvName('');
        setNewEnvBaseUrl('');
        setNewEnvVariables('{}');
      }
    } catch (error) {
      console.error('Failed to create environment:', error);
    }
  };

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;

    try {
      const response = await apiService.createCollection(newCollectionName, newCollectionDescription);
      if (response.success) {
        await fetchCollections();
        setShowNewCollectionDialog(false);
        setNewCollectionName('');
        setNewCollectionDescription('');
      }
    } catch (error) {
      console.error('Failed to create collection:', error);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'application/json') {
      setSelectedFile(file);
      // Auto-set library name from filename if not already set
      if (!newLibraryName.trim()) {
        const nameWithoutExt = file.name.replace(/\.json$/i, '');
        setNewLibraryName(nameWithoutExt);
      }
      // Read file content
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const content = e.target?.result as string;
          setNewLibraryContent(content);
        } catch (error) {
          console.error('Failed to read file:', error);
        }
      };
      reader.readAsText(file);
    } else {
      alert('Please select a valid JSON file');
    }
  };

  const handleCreateLibrary = async () => {
    if (!newLibraryName.trim()) return;

    try {
      let content = {};
      if (newLibraryContent.trim()) {
        content = JSON.parse(newLibraryContent);
      }

      const response = await apiService.uploadJsonLibrary(newLibraryName, content, newLibraryType);
      if (response.success) {
        await fetchJsonLibraries();
        setShowNewLibraryDialog(false);
        setNewLibraryName('');
        setNewLibraryType('schema');
        setNewLibraryContent('{}');
        setUploadMethod('paste');
        setSelectedFile(null);
      }
    } catch (error) {
      console.error('Failed to create JSON library:', error);
    }
  };

  const handleDeleteLibrary = async (libraryId: string) => {
    try {
      const response = await apiService.deleteJsonLibrary(libraryId);
      if (response.success) {
        await fetchJsonLibraries();
      }
    } catch (error) {
      console.error('Failed to delete JSON library:', error);
    }
  };

  const handleSetActiveEnvironment = async (envId: string) => {
    try {
      const response = await apiService.setActiveEnvironment(envId);
      if (response.success) {
        setActiveEnvironment(envId);
        await fetchEnvironments();
      }
    } catch (error) {
      console.error('Failed to set active environment:', error);
    }
  };

  const handleExecuteRequest = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.executeRequest(currentRequest, activeEnvironment || undefined);
      if (response.success && response.data) {
        setResponse(response.data);
      }
    } catch (error) {
      console.error('Failed to execute request:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddHeader = () => {
    setCurrentRequest(prev => ({
      ...prev,
      headers: { ...prev.headers, '': '' }
    }));
  };

  const handleUpdateHeader = (oldKey: string, newKey: string, value: string) => {
    setCurrentRequest(prev => {
      const newHeaders = { ...prev.headers };
      if (oldKey !== newKey && oldKey in newHeaders) {
        delete newHeaders[oldKey];
      }
      if (newKey) {
        newHeaders[newKey] = value;
      }
      return { ...prev, headers: newHeaders };
    });
  };

  const handleRemoveHeader = (key: string) => {
    setCurrentRequest(prev => {
      const newHeaders = { ...prev.headers };
      delete newHeaders[key];
      return { ...prev, headers: newHeaders };
    });
  };

  const formatResponseTime = (time: number) => {
    return time < 1 ? `${Math.round(time * 1000)}ms` : `${time.toFixed(2)}s`;
  };

  const getStatusColor = (statusCode: number) => {
    if (statusCode >= 200 && statusCode < 300) return 'text-green-600';
    if (statusCode >= 300 && statusCode < 400) return 'text-yellow-600';
    if (statusCode >= 400 && statusCode < 500) return 'text-orange-600';
    if (statusCode >= 500) return 'text-red-600';
    return 'text-gray-600';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="hmi-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary" />
            Automation & API Testing
          </CardTitle>
          <div className="flex gap-2">
            <Dialog open={showNewEnvironmentDialog} onOpenChange={setShowNewEnvironmentDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  <Plus className="w-4 h-4 mr-2" />
                  Environment
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Environment</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="env-name">Name</Label>
                    <Input
                      id="env-name"
                      value={newEnvName}
                      onChange={(e) => setNewEnvName(e.target.value)}
                      placeholder="Development"
                    />
                  </div>
                  <div>
                    <Label htmlFor="env-base-url">Base URL</Label>
                    <Input
                      id="env-base-url"
                      value={newEnvBaseUrl}
                      onChange={(e) => setNewEnvBaseUrl(e.target.value)}
                      placeholder="https://api.example.com"
                    />
                  </div>
                  <div>
                    <Label htmlFor="env-variables">Variables (JSON)</Label>
                    <Textarea
                      id="env-variables"
                      value={newEnvVariables}
                      onChange={(e) => setNewEnvVariables(e.target.value)}
                      placeholder='{"api_key": "your-key"}'
                      className="font-mono"
                    />
                  </div>
                  <Button onClick={handleCreateEnvironment} className="w-full">
                    Create Environment
                  </Button>
                </div>
              </DialogContent>
            </Dialog>

            <Dialog open={showNewCollectionDialog} onOpenChange={setShowNewCollectionDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  <Plus className="w-4 h-4 mr-2" />
                  Collection
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Collection</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="collection-name">Name</Label>
                    <Input
                      id="collection-name"
                      value={newCollectionName}
                      onChange={(e) => setNewCollectionName(e.target.value)}
                      placeholder="API Test Suite"
                    />
                  </div>
                  <div>
                    <Label htmlFor="collection-description">Description</Label>
                    <Textarea
                      id="collection-description"
                      value={newCollectionDescription}
                      onChange={(e) => setNewCollectionDescription(e.target.value)}
                      placeholder="Collection description..."
                    />
                  </div>
                  <Button onClick={handleCreateCollection} className="w-full">
                    Create Collection
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
                <div className="text-2xl font-bold text-primary">{status.environments}</div>
                <div className="text-xs text-muted-foreground">Environments</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">{status.collections}</div>
                <div className="text-xs text-muted-foreground">Collections</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">{status.total_requests}</div>
                <div className="text-xs text-muted-foreground">Requests</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">{status.test_results}</div>
                <div className="text-xs text-muted-foreground">Test Results</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-medium">
                  {status.active_environment ? (
                    <Badge variant="default">Active</Badge>
                  ) : (
                    <Badge variant="outline">No Environment</Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">Environment</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Interface */}
      <Tabs value={mainTab} onValueChange={setMainTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="requests">Request Builder</TabsTrigger>
          <TabsTrigger value="libraries">JSON Libraries</TabsTrigger>
        </TabsList>

        <TabsContent value="requests">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Request Builder */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Send className="w-5 h-5 text-primary" />
                  Request Builder
                </CardTitle>
                <div className="flex gap-2">
                  <Select value={activeEnvironment} onValueChange={handleSetActiveEnvironment}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select environment" />
                    </SelectTrigger>
                    <SelectContent>
                      {environments.map((env) => (
                        <SelectItem key={env.id} value={env.id}>
                          {env.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    onClick={handleExecuteRequest}
                    disabled={isLoading}
                    className="flex items-center gap-2"
                  >
                    {isLoading ? (
                      <RotateCcw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    Send
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="request">Request</TabsTrigger>
                    <TabsTrigger value="headers">Headers</TabsTrigger>
                    <TabsTrigger value="body">Body</TabsTrigger>
                    <TabsTrigger value="auth">Auth</TabsTrigger>
                  </TabsList>

                  <TabsContent value="request" className="space-y-4">
                    <div>
                      <Label htmlFor="request-name">Request Name</Label>
                      <Input
                        id="request-name"
                        value={currentRequest.name}
                        onChange={(e) => setCurrentRequest(prev => ({ ...prev, name: e.target.value }))}
                      />
                    </div>
                    <div className="flex gap-2">
                      <Select
                        value={currentRequest.method}
                        onValueChange={(value: any) => setCurrentRequest(prev => ({ ...prev, method: value }))}
                      >
                        <SelectTrigger className="w-28">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="GET">GET</SelectItem>
                          <SelectItem value="POST">POST</SelectItem>
                          <SelectItem value="PUT">PUT</SelectItem>
                          <SelectItem value="PATCH">PATCH</SelectItem>
                          <SelectItem value="DELETE">DELETE</SelectItem>
                          <SelectItem value="HEAD">HEAD</SelectItem>
                          <SelectItem value="OPTIONS">OPTIONS</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input
                        value={currentRequest.url}
                        onChange={(e) => setCurrentRequest(prev => ({ ...prev, url: e.target.value }))}
                        placeholder="{{base_url}}/api/endpoint"
                        className="flex-1"
                      />
                    </div>
                  </TabsContent>

                  <TabsContent value="headers" className="space-y-4">
                    <div className="space-y-2">
                      {Object.entries(currentRequest.headers).map(([key, value]) => (
                        <div key={key} className="flex gap-2">
                          <Input
                            value={key}
                            onChange={(e) => handleUpdateHeader(key, e.target.value, value)}
                            placeholder="Header name"
                          />
                          <Input
                            value={value}
                            onChange={(e) => handleUpdateHeader(key, key, e.target.value)}
                            placeholder="Header value"
                          />
                          <Button
                            onClick={() => handleRemoveHeader(key)}
                            variant="ghost"
                            size="sm"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                      <Button onClick={handleAddHeader} variant="outline" size="sm">
                        <Plus className="w-4 h-4 mr-2" />
                        Add Header
                      </Button>
                    </div>
                  </TabsContent>

                  <TabsContent value="body" className="space-y-4">
                    <div>
                      <Label htmlFor="body-type">Body Type</Label>
                      <Select
                        value={currentRequest.body_type}
                        onValueChange={(value: any) => setCurrentRequest(prev => ({ ...prev, body_type: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="json">JSON</SelectItem>
                          <SelectItem value="form">Form Data</SelectItem>
                          <SelectItem value="raw">Raw Text</SelectItem>
                          <SelectItem value="file">File</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="request-body">Body Content</Label>
                      <Textarea
                        id="request-body"
                        value={currentRequest.body}
                        onChange={(e) => setCurrentRequest(prev => ({ ...prev, body: e.target.value }))}
                        placeholder='{"key": "{{variable}}"}'
                        className="font-mono min-h-32"
                      />
                    </div>
                  </TabsContent>

                  <TabsContent value="auth" className="space-y-4">
                    <div>
                      <Label htmlFor="auth-type">Authentication Type</Label>
                      <Select
                        value={currentRequest.auth_type}
                        onValueChange={(value: any) => setCurrentRequest(prev => ({ ...prev, auth_type: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">None</SelectItem>
                          <SelectItem value="bearer">Bearer Token</SelectItem>
                          <SelectItem value="basic">Basic Auth</SelectItem>
                          <SelectItem value="api_key">API Key</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {currentRequest.auth_type === 'bearer' && (
                      <div>
                        <Label htmlFor="bearer-token">Bearer Token</Label>
                        <Input
                          id="bearer-token"
                          value={currentRequest.auth_config?.token || ''}
                          onChange={(e) => setCurrentRequest(prev => ({
                            ...prev,
                            auth_config: { ...prev.auth_config, token: e.target.value }
                          }))}
                          placeholder="{{api_token}}"
                        />
                      </div>
                    )}
                    {currentRequest.auth_type === 'basic' && (
                      <>
                        <div>
                          <Label htmlFor="basic-username">Username</Label>
                          <Input
                            id="basic-username"
                            value={currentRequest.auth_config?.username || ''}
                            onChange={(e) => setCurrentRequest(prev => ({
                              ...prev,
                              auth_config: { ...prev.auth_config, username: e.target.value }
                            }))}
                            placeholder="{{username}}"
                          />
                        </div>
                        <div>
                          <Label htmlFor="basic-password">Password</Label>
                          <Input
                            id="basic-password"
                            type="password"
                            value={currentRequest.auth_config?.password || ''}
                            onChange={(e) => setCurrentRequest(prev => ({
                              ...prev,
                              auth_config: { ...prev.auth_config, password: e.target.value }
                            }))}
                            placeholder="{{password}}"
                          />
                        </div>
                      </>
                    )}
                    {currentRequest.auth_type === 'api_key' && (
                      <>
                        <div>
                          <Label htmlFor="api-key-header">Header Name</Label>
                          <Input
                            id="api-key-header"
                            value={currentRequest.auth_config?.header || ''}
                            onChange={(e) => setCurrentRequest(prev => ({
                              ...prev,
                              auth_config: { ...prev.auth_config, header: e.target.value }
                            }))}
                            placeholder="X-API-Key"
                          />
                        </div>
                        <div>
                          <Label htmlFor="api-key-value">API Key</Label>
                          <Input
                            id="api-key-value"
                            value={currentRequest.auth_config?.value || ''}
                            onChange={(e) => setCurrentRequest(prev => ({
                              ...prev,
                              auth_config: { ...prev.auth_config, value: e.target.value }
                            }))}
                            placeholder="{{api_key}}"
                          />
                        </div>
                      </>
                    )}
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            {/* Response Viewer */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="w-5 h-5 text-primary" />
                  Response
                  {response && (
                    <Badge variant="outline" className={getStatusColor(response.status_code)}>
                      {response.status_code}
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {response ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4 text-muted-foreground" />
                          <span>{formatResponseTime(response.elapsed_time)}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-muted-foreground" />
                          <span>{response.size} bytes</span>
                        </div>
                      </div>
                      <Badge variant={response.error ? "destructive" : "default"}>
                        {response.error ? "Error" : "Success"}
                      </Badge>
                    </div>

                    <Separator />

                    <div>
                      <h4 className="text-sm font-medium mb-2">Response Headers</h4>
                      <ScrollArea className="h-32 border rounded-md p-2">
                        <div className="space-y-1 text-xs font-mono">
                          {Object.entries(response.headers).map(([key, value]) => (
                            <div key={key}>
                              <span className="text-muted-foreground">{key}:</span> {value}
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium mb-2">Response Body</h4>
                      <ScrollArea className="h-64 border rounded-md p-2">
                        <pre className="text-xs font-mono whitespace-pre-wrap">
                          {response.body || 'No response body'}
                        </pre>
                      </ScrollArea>
                    </div>

                    {response.error && (
                      <div className="bg-destructive/10 border border-destructive/20 rounded-md p-3">
                        <h4 className="text-sm font-medium text-destructive mb-1">Error</h4>
                        <p className="text-xs text-destructive">{response.error}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-12">
                    <Send className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Send a request to see the response</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="libraries">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* JSON Library Manager */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Library className="w-5 h-5 text-primary" />
                  JSON Libraries
                </CardTitle>
                <div className="flex gap-2">
                  <Dialog open={showNewLibraryDialog} onOpenChange={setShowNewLibraryDialog}>
                    <DialogTrigger asChild>
                      <Button variant="outline" size="sm">
                        <Plus className="w-4 h-4 mr-2" />
                        Add Library
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl">
                      <DialogHeader>
                        <DialogTitle>Upload JSON Library</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="library-name">Name</Label>
                          <Input
                            id="library-name"
                            value={newLibraryName}
                            onChange={(e) => setNewLibraryName(e.target.value)}
                            placeholder="User Schema"
                          />
                        </div>
                        <div>
                          <Label htmlFor="library-type">Type</Label>
                          <Select value={newLibraryType} onValueChange={(value: any) => setNewLibraryType(value)}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="schema">JSON Schema</SelectItem>
                              <SelectItem value="template">Data Template</SelectItem>
                              <SelectItem value="collection">Collection</SelectItem>
                              <SelectItem value="mock_data">Mock Data</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label>Upload Method</Label>
                          <Tabs value={uploadMethod} onValueChange={(value: any) => setUploadMethod(value)} className="w-full">
                            <TabsList className="grid w-full grid-cols-2">
                              <TabsTrigger value="paste" className="flex items-center gap-2">
                                <Edit className="w-4 h-4" />
                                Paste JSON
                              </TabsTrigger>
                              <TabsTrigger value="file" className="flex items-center gap-2">
                                <Upload className="w-4 h-4" />
                                Upload File
                              </TabsTrigger>
                            </TabsList>
                            <TabsContent value="paste" className="space-y-2">
                              <Label htmlFor="library-content">JSON Content</Label>
                              <Textarea
                                id="library-content"
                                value={newLibraryContent}
                                onChange={(e) => setNewLibraryContent(e.target.value)}
                                placeholder='{"type": "object", "properties": {"name": {"type": "string"}}}'
                                className="font-mono min-h-40"
                              />
                            </TabsContent>
                            <TabsContent value="file" className="space-y-2">
                              <Label htmlFor="library-file">Select JSON File</Label>
                              <div className="border-2 border-dashed border-border rounded-lg p-6 text-center">
                                <input
                                  id="library-file"
                                  type="file"
                                  accept=".json,application/json"
                                  onChange={handleFileSelect}
                                  className="hidden"
                                />
                                <label
                                  htmlFor="library-file"
                                  className="cursor-pointer flex flex-col items-center gap-2"
                                >
                                  <Upload className="w-8 h-8 text-muted-foreground" />
                                  <div className="text-sm">
                                    <span className="font-medium text-primary">Click to upload</span>
                                    <span className="text-muted-foreground"> or drag and drop</span>
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    JSON files only
                                  </div>
                                </label>
                                {selectedFile && (
                                  <div className="mt-4 p-2 bg-muted rounded flex items-center gap-2">
                                    <FileJson className="w-4 h-4 text-primary" />
                                    <span className="text-sm">{selectedFile.name}</span>
                                  </div>
                                )}
                              </div>
                              {newLibraryContent && newLibraryContent !== '{}' && (
                                <div>
                                  <Label>Preview</Label>
                                  <ScrollArea className="h-32 border rounded-md p-2">
                                    <pre className="text-xs font-mono whitespace-pre-wrap">
                                      {newLibraryContent}
                                    </pre>
                                  </ScrollArea>
                                </div>
                              )}
                            </TabsContent>
                          </Tabs>
                        </div>
                        <Button onClick={handleCreateLibrary} className="w-full">
                          Upload Library
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-96">
                  <div className="space-y-2">
                    {jsonLibraries.map((library) => (
                      <div key={library.id} className="border border-border rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <FileJson className="w-4 h-4 text-primary" />
                            <span className="font-medium">{library.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{library.library_type}</Badge>
                            <Button
                              onClick={() => handleDeleteLibrary(library.id)}
                              variant="ghost"
                              size="sm"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Created: {new Date(library.created_at * 1000).toLocaleString()}
                        </div>
                      </div>
                    ))}
                    {jsonLibraries.length === 0 && (
                      <div className="text-center text-muted-foreground py-12">
                        <Library className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No JSON libraries uploaded yet</p>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* JSON Tools */}
            <Card className="hmi-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-primary" />
                  JSON Tools
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium mb-2">Schema Validation</h4>
                    <div className="space-y-2">
                      <Select>
                        <SelectTrigger>
                          <SelectValue placeholder="Select schema library" />
                        </SelectTrigger>
                        <SelectContent>
                          {jsonLibraries
                            .filter(lib => lib.library_type === 'schema')
                            .map(lib => (
                              <SelectItem key={lib.id} value={lib.id}>
                                {lib.name}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                      <Button variant="outline" size="sm" className="w-full">
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Validate JSON
                      </Button>
                    </div>
                  </div>

                  <Separator />

                  <div>
                    <h4 className="text-sm font-medium mb-2">Mock Data Generation</h4>
                    <div className="space-y-2">
                      <Select>
                        <SelectTrigger>
                          <SelectValue placeholder="Select template library" />
                        </SelectTrigger>
                        <SelectContent>
                          {jsonLibraries
                            .filter(lib => lib.library_type === 'template')
                            .map(lib => (
                              <SelectItem key={lib.id} value={lib.id}>
                                {lib.name}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                      <Button variant="outline" size="sm" className="w-full">
                        <Copy className="w-4 h-4 mr-2" />
                        Generate Mock Data
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}