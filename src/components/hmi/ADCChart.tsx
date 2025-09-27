import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { HMIApiService, ADCReading } from '@/services/hmi-api';
import { TrendingUp } from 'lucide-react';

interface ADCChartProps {
  apiService: HMIApiService;
}

interface ChartDataPoint {
  time: string;
  [key: string]: number | string;
}

export function ADCChart({ apiService }: ADCChartProps) {
  const [data, setData] = useState<ChartDataPoint[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await apiService.readAllADCChannels();
        if (response.success && response.data?.channels) {
          const now = new Date().toLocaleTimeString();
          const newPoint: ChartDataPoint = {
            time: now,
          };

          response.data.channels.forEach((channel: ADCReading) => {
            newPoint[`ch${channel.channel}`] = channel.voltage;
          });

          setData(prev => [...prev.slice(-49), newPoint]);
        }
      } catch (error) {
        console.error('Failed to fetch ADC data for chart:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 1000);

    return () => clearInterval(interval);
  }, [apiService]);

  return (
    <Card className="hmi-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          ADC Real-time Chart
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="time" 
                className="text-xs text-muted-foreground"
              />
              <YAxis 
                domain={[0, 3.3]}
                className="text-xs text-muted-foreground"
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
              />
              <Line 
                type="monotone" 
                dataKey="ch0" 
                stroke="hsl(var(--primary))" 
                strokeWidth={2}
                dot={false}
                name="Channel 0"
              />
              <Line 
                type="monotone" 
                dataKey="ch1" 
                stroke="hsl(var(--secondary))" 
                strokeWidth={2}
                dot={false}
                name="Channel 1"
              />
              <Line 
                type="monotone" 
                dataKey="ch2" 
                stroke="hsl(var(--accent))" 
                strokeWidth={2}
                dot={false}
                name="Channel 2"
              />
              <Line 
                type="monotone" 
                dataKey="ch3" 
                stroke="hsl(var(--muted-foreground))" 
                strokeWidth={2}
                dot={false}
                name="Channel 3"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}