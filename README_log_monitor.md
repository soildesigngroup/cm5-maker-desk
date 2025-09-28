# AI-Powered Log Monitoring Agent for Raspberry Pi

An intelligent log monitoring system that uses Claude AI to analyze web application logs, detect issues, and provide actionable insights. Optimized for Raspberry Pi resource constraints with smart local pre-processing to minimize API costs.

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-red.svg)

## 🌟 Features

### 🤖 Intelligent Analysis
- **Local Pre-processing**: Analyzes logs locally first to determine when AI analysis is needed
- **Claude AI Integration**: Uses Claude API for deep insights when thresholds are exceeded
- **Smart Thresholds**: Configurable triggers based on error counts, response times, and activity levels
- **Pattern Recognition**: Identifies trends and anomalies in log data

### 📊 Comprehensive Monitoring
- **Multi-file Support**: Monitor multiple log files simultaneously
- **Real-time Analysis**: Tracks file positions to read only new content
- **Log Rotation Handling**: Automatically detects and handles log rotation
- **Historical Trends**: Maintains analysis history for pattern detection

### 🚨 Intelligent Alerting
- **Health Scoring**: 1-10 health scores for quick system status assessment
- **Email Alerts**: HTML-formatted alerts with detailed analysis
- **Severity Levels**: Critical, High, Medium, Low alert classifications
- **Alert Deduplication**: Prevents alert spam with smart filtering

### 🏠 Raspberry Pi Optimized
- **Resource Efficient**: Minimal memory footprint and CPU usage
- **Cost Effective**: Smart API usage to minimize Claude API costs
- **Systemd Integration**: Professional service deployment
- **Security Hardened**: Secure service configuration with proper isolation

### 📈 Reporting & Analytics
- **Daily Summaries**: Automated daily health reports
- **Performance Metrics**: Response time analysis and bottleneck detection
- **Error Analysis**: Pattern identification and root cause suggestions
- **Trend Analysis**: Historical comparison and forecasting

## 🚀 Quick Start

### Prerequisites

- Raspberry Pi (any model) with Raspberry Pi OS
- Python 3.7 or higher
- Claude API key ([Get one here](https://console.anthropic.com/))
- Internet connection for API calls

### Installation

1. **Clone or download the files**:
   ```bash
   # Download the main files to your Raspberry Pi
   wget https://raw.githubusercontent.com/your-repo/log-monitor/main/log_monitor.py
   wget https://raw.githubusercontent.com/your-repo/log-monitor/main/install.sh
   wget https://raw.githubusercontent.com/your-repo/log-monitor/main/requirements.txt
   ```

2. **Run the installation script**:
   ```bash
   chmod +x install.sh
   sudo ./install.sh
   ```

3. **Configure the agent**:
   ```bash
   sudo nano /opt/log-monitor/config.json
   ```

   Add your Claude API key and configure log file paths (see [Configuration](#configuration) below).

4. **Start the service**:
   ```bash
   sudo systemctl start log-monitor
   sudo systemctl status log-monitor
   ```

5. **Enable auto-start on boot**:
   ```bash
   sudo systemctl enable log-monitor
   ```

## ⚙️ Configuration

The agent uses a JSON configuration file with extensive options:

### Basic Configuration

```json
{
  "claude": {
    "api_key": "your-claude-api-key-here",
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1000
  },

  "log_files": [
    {
      "path": "/var/log/nginx/access.log",
      "name": "nginx_access",
      "enabled": true
    },
    {
      "path": "/var/log/nginx/error.log",
      "name": "nginx_error",
      "enabled": true
    }
  ],

  "monitoring": {
    "check_interval_minutes": 15,
    "daily_summary_time": "09:00"
  }
}
```

### Advanced Configuration

#### Analysis Thresholds
```json
"analysis_thresholds": {
  "error_count": 10,        // Trigger AI analysis after 10 errors
  "avg_response_time": 2000, // Trigger if avg response > 2000ms
  "high_activity": 1000,     // Trigger if >1000 new log lines
  "error_rate": 5.0          // Trigger if error rate >5%
}
```

#### Email Alerts
```json
"email": {
  "enabled": true,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "use_tls": true,
  "username": "your-email@gmail.com",
  "password": "your-app-password",
  "from_email": "alerts@yourdomain.com",
  "to_email": "admin@yourdomain.com"
}
```

#### Alert Thresholds
```json
"alert_thresholds": {
  "health_score": 3,    // Alert if health score ≤ 3
  "error_count": 20,    // Alert if >20 errors in one check
  "response_time": 5000 // Alert if avg response time >5000ms
}
```

## 📋 Usage

### Service Management

```bash
# Start the service
sudo systemctl start log-monitor

# Stop the service
sudo systemctl stop log-monitor

# Restart the service
sudo systemctl restart log-monitor

# Check service status
sudo systemctl status log-monitor

# View real-time logs
sudo journalctl -u log-monitor -f

# View recent logs
sudo journalctl -u log-monitor --since "1 hour ago"
```

### Manual Operations

```bash
# Run single analysis cycle
python3 log_monitor.py --once

# Generate daily summary
python3 log_monitor.py --summary

# Send test email
python3 log_monitor.py --test-email

# Run with custom config file
python3 log_monitor.py --config /path/to/config.json

# Get help
python3 log_monitor.py --help
```

### Log File Requirements

The agent can monitor various log formats:

#### Nginx Access Logs
```
192.168.1.100 - - [27/Sep/2024:14:30:45 +0000] "GET /api/users HTTP/1.1" 200 1234 "-" "Mozilla/5.0..."
```

#### Application Logs
```
2024-09-27 14:30:45 ERROR [app.py:123] Database connection failed: timeout after 30s
2024-09-27 14:30:46 WARNING [auth.py:45] Failed login attempt for user: admin
```

#### Apache Access Logs
```
192.168.1.100 - - [27/Sep/2024:14:30:45 +0000] "POST /login HTTP/1.1" 401 512
```

## 🧠 How It Works

### 1. Local Analysis Phase

The agent first performs local analysis to determine if AI analysis is warranted:

- **Error Detection**: Counts errors, exceptions, and failures
- **Performance Metrics**: Measures response times and throughput
- **Activity Monitoring**: Tracks log volume and patterns
- **Threshold Evaluation**: Determines if AI analysis is needed

### 2. AI Analysis Phase (When Triggered)

When thresholds are exceeded, Claude AI analyzes the logs:

- **Contextual Prompts**: Includes local metrics and historical data
- **Intelligent Truncation**: Prioritizes error lines and recent entries
- **Structured Output**: Returns JSON with health scores and recommendations
- **Fallback Handling**: Graceful degradation if API fails

### 3. Alerting & Reporting

Based on analysis results:

- **Health Scoring**: Assigns 1-10 health scores
- **Alert Generation**: Triggers alerts based on severity
- **Email Notifications**: Sends detailed HTML reports
- **Database Storage**: Stores all analysis results for trends

## 📊 Analysis Output

### Health Scores
- **10-8**: Excellent health, no issues detected
- **7-5**: Good health, minor issues or warnings
- **4-3**: Fair health, some problems need attention
- **2-1**: Poor health, immediate action required

### Analysis Components

```json
{
  "health_score": 6,
  "critical_issues": [
    "High error rate in authentication module",
    "Database connection timeouts increasing"
  ],
  "performance_insights": {
    "response_time_analysis": "Average response time increased 300% from baseline",
    "bottlenecks": ["Database queries", "Image processing"],
    "recommendations": ["Add connection pooling", "Optimize query performance"]
  },
  "error_analysis": {
    "patterns": ["Connection timeout errors", "401 authentication failures"],
    "root_causes": ["Database overload", "Invalid API keys"],
    "frequency": "Error rate increased 500% in last hour"
  },
  "recommendations": {
    "high_priority": ["Investigate database performance"],
    "medium_priority": ["Review authentication logs"],
    "low_priority": ["Update monitoring thresholds"]
  },
  "trend_analysis": "Significant degradation compared to yesterday",
  "summary": "System experiencing performance issues requiring immediate attention"
}
```

## 📁 File Structure

```
/opt/log-monitor/           # Installation directory
├── log_monitor.py          # Main application
├── config.json            # Configuration file
├── log_monitor.db         # SQLite database
├── data/                  # Data directory
├── logs/                  # Application logs
└── test_installation.sh   # Installation test script

/var/log/log-monitor/      # Service logs
├── log_monitor_agent.log  # Application logs
└── archived/              # Rotated logs
```

## 📊 Database Schema

### Analyses Table
```sql
CREATE TABLE analyses (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    log_file TEXT,
    health_score INTEGER,
    error_count INTEGER,
    warning_count INTEGER,
    avg_response_time REAL,
    analysis_text TEXT,
    local_metrics TEXT,
    ai_triggered BOOLEAN
);
```

### Alerts Table
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    alert_type TEXT,
    severity TEXT,
    message TEXT,
    log_file TEXT,
    resolved BOOLEAN,
    health_score INTEGER
);
```

### File Positions Table
```sql
CREATE TABLE file_positions (
    log_file TEXT PRIMARY KEY,
    position INTEGER,
    last_modified REAL,
    last_check DATETIME
);
```

## 🔒 Security Features

### Service Hardening
- **User Isolation**: Runs as dedicated `log-monitor` user
- **File System Protection**: Read-only access to system directories
- **Resource Limits**: Memory and CPU quotas prevent resource exhaustion
- **Network Restrictions**: Limited network access for API calls only

### Data Protection
- **Log Sanitization**: Sensitive data filtering before API calls
- **Local Storage**: Analysis results stored locally in SQLite
- **Secure Configuration**: API keys protected with proper file permissions

## 🚨 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status
sudo systemctl status log-monitor

# View detailed logs
sudo journalctl -u log-monitor --since "10 minutes ago"

# Check configuration
python3 /opt/log-monitor/log_monitor.py --help
```

#### API Errors
```bash
# Test API connectivity
python3 -c "
import anthropic
client = anthropic.Anthropic(api_key='your-key')
print('API connection successful')
"

# Check API key in config
sudo grep -A5 'claude' /opt/log-monitor/config.json
```

#### Log File Access
```bash
# Check file permissions
ls -la /var/log/nginx/

# Add log-monitor user to appropriate groups
sudo usermod -a -G adm log-monitor

# Test file access
sudo -u log-monitor cat /var/log/nginx/access.log | head -5
```

#### High Memory Usage
```bash
# Check memory usage
sudo systemctl show log-monitor --property=MemoryCurrent

# Adjust memory limits in service file
sudo nano /etc/systemd/system/log-monitor.service

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart log-monitor
```

### Log Analysis

#### Application Logs
```bash
# View application logs
sudo tail -f /var/log/log-monitor/log_monitor_agent.log

# Search for errors
sudo grep -i error /var/log/log-monitor/log_monitor_agent.log

# View systemd logs
sudo journalctl -u log-monitor -f
```

#### Database Inspection
```bash
# Connect to database
sqlite3 /opt/log-monitor/log_monitor.db

# View recent analyses
.mode column
.headers on
SELECT timestamp, log_file, health_score, error_count
FROM analyses
ORDER BY timestamp DESC
LIMIT 10;

# View alerts
SELECT timestamp, severity, message
FROM alerts
WHERE resolved = 0;
```

## 🔧 Customization

### Adding Custom Log Patterns

Edit the `LogAnalyzer` class to add custom error patterns:

```python
self.error_patterns = [
    r'\b(error|ERROR|Error)\b',
    r'\b(exception|EXCEPTION|Exception)\b',
    r'\bCUSTOM_ERROR_PATTERN\b',  # Add your pattern
    # ... more patterns
]
```

### Custom Analysis Prompts

Modify the `create_analysis_prompt` method in `ClaudeAnalyzer`:

```python
def create_analysis_prompt(self, log_content, local_metrics, historical_data):
    # Add application-specific context
    custom_context = """
    CUSTOM APPLICATION CONTEXT:
    - E-commerce platform running on Raspberry Pi
    - Peak traffic hours: 9 AM - 5 PM
    - Critical endpoints: /checkout, /payment, /inventory
    """

    prompt = f"{custom_context}\n\n{existing_prompt}"
    return prompt
```

### Custom Alert Conditions

Add custom alerting logic in `AlertManager`:

```python
def should_alert(self, analysis_result, local_metrics):
    # Existing logic...

    # Custom alert conditions
    if 'payment_failure' in json.dumps(analysis_result).lower():
        return True, "CRITICAL", "Payment system issues detected"

    # Custom business logic alerts
    if local_metrics.get('checkout_errors', 0) > 5:
        return True, "HIGH", "Checkout process experiencing issues"

    return False, "INFO", "No custom alerts triggered"
```

## 📈 Performance Optimization

### Raspberry Pi Specific

1. **Memory Management**:
   ```json
   "raspberry_pi": {
     "memory_limit_mb": 256,
     "max_concurrent_analyses": 1,
     "cpu_throttle_temp": 80
   }
   ```

2. **File Reading Optimization**:
   - Reads only new content since last check
   - Intelligent log truncation for API calls
   - Efficient SQLite storage with indexes

3. **API Cost Minimization**:
   - Local pre-analysis filters unnecessary API calls
   - Smart content truncation prioritizes important logs
   - Configurable thresholds prevent excessive API usage

### Monitoring Resource Usage

```bash
# Check CPU and memory usage
htop

# Monitor disk usage
df -h

# Check temperature (Raspberry Pi)
vcgencmd measure_temp

# Monitor network usage
iftop
```

## 🔄 Backup & Maintenance

### Database Backup

```bash
# Create backup
sqlite3 /opt/log-monitor/log_monitor.db ".backup /path/to/backup.db"

# Restore from backup
sqlite3 /opt/log-monitor/log_monitor.db ".restore /path/to/backup.db"
```

### Log Rotation

The system automatically configures logrotate:

```bash
# Check logrotate configuration
cat /etc/logrotate.d/log-monitor

# Force log rotation (testing)
sudo logrotate -f /etc/logrotate.d/log-monitor
```

### Cleanup Old Data

```bash
# Remove analyses older than 30 days
sqlite3 /opt/log-monitor/log_monitor.db "
DELETE FROM analyses
WHERE timestamp < datetime('now', '-30 days');
"

# Remove resolved alerts older than 7 days
sqlite3 /opt/log-monitor/log_monitor.db "
DELETE FROM alerts
WHERE resolved = 1 AND timestamp < datetime('now', '-7 days');
"
```

## 📊 Monitoring Dashboard (Future Enhancement)

The system is designed to support future dashboard integration:

```python
# API endpoints for dashboard data
@app.route('/api/health')
def get_health_status():
    # Return current system health

@app.route('/api/analyses')
def get_recent_analyses():
    # Return recent analysis results

@app.route('/api/alerts')
def get_active_alerts():
    # Return unresolved alerts
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic](https://anthropic.com) for the Claude AI API
- [Raspberry Pi Foundation](https://raspberrypi.org) for the amazing hardware
- The open-source community for inspiration and tools

## 📞 Support

- 📧 **Email**: support@yourdomain.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-repo/log-monitor/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-repo/log-monitor/discussions)
- 📖 **Wiki**: [Project Wiki](https://github.com/your-repo/log-monitor/wiki)

---

**Made with ❤️ for the Raspberry Pi community**