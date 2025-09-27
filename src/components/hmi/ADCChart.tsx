import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Legend } from 'recharts';
import { HMIApiService, ADCDataPoint, LoggingStats } from '@/services/hmi-api';
import { Download, Play, Square, TrendingUp, Settings } from 'lucide-react';

interface ADCChartProps {
  apiService: HMIApiService;
}

interface ChartDataPoint {
  timestamp: number;
  datetime: string;
  [key: string]: number | string; // Dynamic channel keys like 'channel_0', 'channel_1', etc.
}

const CHANNEL_COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#10b981', // green
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#f97316', // orange
  '#84cc16', // lime
];

export function ADCChart({ apiService }: ADCChartProps) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [loggingStats, setLoggingStats] = useState<LoggingStats | null>(null);
  const [selectedChannels, setSelectedChannels] = useState<number[]>([0, 1, 2, 3]);
  const [timeRange, setTimeRange] = useState<number>(300); // 5 minutes in seconds
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [maxDataPoints, setMaxDataPoints] = useState(100);

  // Chart configuration for Recharts
  const chartConfig = {
    timestamp: {
      label: "Time",
    },
    ...Object.fromEntries(
      Array.from({ length: 8 }, (_, i) => [
        `channel_${i}`,
        {
          label: `Channel ${i}`,
          color: CHANNEL_COLORS[i],
        }
      ])
    ),
  };

  const fetchLoggedData = async () => {
    setIsLoading(true);
    try {
      // Get data for all channels or selected channels
      const response = await apiService.getLoggedData(
        undefined, // Get all channels
        maxDataPoints,
        timeRange
      );

      if (response.success && response.data) {
        setLoggingStats(response.data.logging_stats);

        // Transform the data for charting
        const chartPoints: ChartDataPoint[] = [];
        const timestampMap = new Map<number, ChartDataPoint>();

        // Process each channel's data
        Object.entries(response.data.logged_data).forEach(([channelStr, points]) => {
          const channel = parseInt(channelStr);

          points.forEach((point: ADCDataPoint) => {
            const roundedTimestamp = Math.floor(point.timestamp);

            if (!timestampMap.has(roundedTimestamp)) {
              timestampMap.set(roundedTimestamp, {
                timestamp: roundedTimestamp,
                datetime: new Date(point.timestamp * 1000).toLocaleTimeString(),
              });
            }

            const chartPoint = timestampMap.get(roundedTimestamp)!;
            chartPoint[`channel_${channel}`] = point.voltage;
          });
        });

        // Convert to array and sort by timestamp
        const sortedData = Array.from(timestampMap.values()).sort(
          (a, b) => a.timestamp - b.timestamp
        );

        setChartData(sortedData);
      }
    } catch (error) {
      console.error('Failed to fetch logged data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartLogging = async () => {
    try {
      await apiService.startADCLogging();
      await fetchLoggedData(); // Refresh stats
    } catch (error) {
      console.error('Failed to start logging:', error);
    }
  };

  const handleStopLogging = async () => {
    try {
      await apiService.stopADCLogging();
      await fetchLoggedData(); // Refresh stats
    } catch (error) {
      console.error('Failed to stop logging:', error);
    }
  };

  const handleExportCSV = async () => {
    try {
      const filename = `adc_export_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`;
      const response = await apiService.exportADCDataCSV(filename, undefined, timeRange);

      if (response.success) {
        alert(`Data exported to ${response.data?.filename}`);
      } else {
        alert('Export failed');
      }
    } catch (error) {
      console.error('Failed to export data:', error);
      alert('Export failed');
    }
  };

  const toggleChannel = (channel: number) => {
    setSelectedChannels(prev =>
      prev.includes(channel)
        ? prev.filter(c => c !== channel)
        : [...prev, channel].sort()
    );
  };

  useEffect(() => {
    fetchLoggedData();
  }, [timeRange, maxDataPoints]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchLoggedData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [autoRefresh, timeRange, maxDataPoints]);

  const formatTooltipLabel = (value: any) => {
    if (typeof value === 'number') {
      return new Date(value * 1000).toLocaleString();
    }
    return value;
  };

  const formatTooltipValue = (value: any, name: string) => {
    if (typeof value === 'number') {
      return [`${value.toFixed(3)}V`, name.replace('channel_', 'Channel ')];
    }
    return [value, name];
  };

  return (
    <div className="space-y-4">
      {/* Chart Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            ADC Data Chart
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 items-center">
            {/* Time Range Selection */}
            <div className="flex items-center gap-2">
              <Label htmlFor="time-range">Time Range:</Label>
              <Select
                value={timeRange.toString()}
                onValueChange={(value) => setTimeRange(parseInt(value))}
              >
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="60">1 minute</SelectItem>
                  <SelectItem value="300">5 minutes</SelectItem>
                  <SelectItem value="900">15 minutes</SelectItem>
                  <SelectItem value="1800">30 minutes</SelectItem>
                  <SelectItem value="3600">1 hour</SelectItem>
                  <SelectItem value="7200">2 hours</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Max Data Points */}
            <div className="flex items-center gap-2">
              <Label htmlFor="max-points">Max Points:</Label>
              <Select
                value={maxDataPoints.toString()}
                onValueChange={(value) => setMaxDataPoints(parseInt(value))}
              >
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                  <SelectItem value="200">200</SelectItem>
                  <SelectItem value="500">500</SelectItem>
                  <SelectItem value="1000">1000</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Auto Refresh Toggle */}
            <div className="flex items-center gap-2">
              <Switch
                id="auto-refresh"
                checked={autoRefresh}
                onCheckedChange={setAutoRefresh}
              />
              <Label htmlFor="auto-refresh">Auto Refresh</Label>
            </div>

            {/* Logging Controls */}
            {loggingStats && (
              <div className="flex items-center gap-2">
                {loggingStats.active ? (
                  <Button
                    onClick={handleStopLogging}
                    variant="outline"
                    size="sm"
                    className="flex items-center gap-1"
                  >
                    <Square className="h-4 w-4" />
                    Stop Logging
                  </Button>
                ) : (
                  <Button
                    onClick={handleStartLogging}
                    variant="outline"
                    size="sm"
                    className="flex items-center gap-1"
                  >
                    <Play className="h-4 w-4" />
                    Start Logging
                  </Button>
                )}
              </div>
            )}

            {/* Export Button */}
            <Button
              onClick={handleExportCSV}
              variant="outline"
              size="sm"
              className="flex items-center gap-1"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </Button>

            {/* Refresh Button */}
            <Button
              onClick={fetchLoggedData}
              variant="outline"
              size="sm"
              disabled={isLoading}
            >
              {isLoading ? 'Loading...' : 'Refresh'}
            </Button>
          </div>

          {/* Channel Selection */}
          <div className="mt-4">
            <Label className="text-sm font-medium">Visible Channels:</Label>
            <div className="flex flex-wrap gap-2 mt-2">
              {Array.from({ length: 8 }, (_, i) => (
                <div key={i} className="flex items-center gap-1">
                  <input
                    type="checkbox"
                    id={`channel-${i}`}
                    checked={selectedChannels.includes(i)}
                    onChange={() => toggleChannel(i)}
                    className="rounded"
                  />
                  <Label
                    htmlFor={`channel-${i}`}
                    className="text-sm cursor-pointer"
                    style={{ color: CHANNEL_COLORS[i] }}
                  >
                    CH{i}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          {/* Logging Stats */}
          {loggingStats && (
            <div className="mt-4 p-3 bg-muted rounded-md">
              <div className="text-sm space-y-1">
                <div>
                  <span className="font-medium">Logging Status:</span>{' '}
                  <span className={loggingStats.active ? 'text-green-600' : 'text-red-600'}>
                    {loggingStats.active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div>
                  <span className="font-medium">Total Points:</span> {loggingStats.total_memory_points}
                </div>
                <div>
                  <span className="font-medium">Sample Interval:</span> {loggingStats.sample_interval}s
                </div>
                {loggingStats.current_log_file && (
                  <div>
                    <span className="font-medium">Current Log File:</span> {loggingStats.current_log_file}
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Chart */}
      <Card>
        <CardContent className="pt-6">
          <ChartContainer config={chartConfig} className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="datetime"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  domain={[0, 5]}
                  ticks={[0, 1, 2, 3, 4, 5]}
                  label={{ value: 'Voltage (V)', angle: -90, position: 'insideLeft' }}
                />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      labelFormatter={formatTooltipLabel}
                      formatter={formatTooltipValue}
                    />
                  }
                />
                <Legend />
                {selectedChannels.map((channel) => (
                  <Line
                    key={channel}
                    type="monotone"
                    dataKey={`channel_${channel}`}
                    stroke={CHANNEL_COLORS[channel]}
                    strokeWidth={2}
                    dot={false}
                    name={`Channel ${channel}`}
                    connectNulls={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>

          {chartData.length === 0 && (
            <div className="flex items-center justify-center h-[400px] text-muted-foreground">
              <div className="text-center">
                <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No data available</p>
                <p className="text-sm">Start ADC logging to see real-time data</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}