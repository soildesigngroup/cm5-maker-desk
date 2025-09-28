#!/usr/bin/env python3
"""
AI-Powered Log Monitoring Agent for Raspberry Pi
Monitors web application logs, analyzes them using Claude API, and provides intelligent diagnostics.
Optimized for Raspberry Pi resource constraints with smart local pre-processing.
"""

import sqlite3
import json
import os
import re
import time
import schedule
import smtplib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple
import anthropic

class DatabaseManager:
    """Handles SQLite database operations for log monitoring data."""

    def __init__(self, db_path: str = "log_monitor.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Analyses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    log_file TEXT NOT NULL,
                    health_score INTEGER,
                    error_count INTEGER,
                    warning_count INTEGER,
                    avg_response_time REAL,
                    analysis_text TEXT,
                    local_metrics TEXT,
                    ai_triggered BOOLEAN DEFAULT 0
                )
            """)

            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    log_file TEXT,
                    resolved BOOLEAN DEFAULT 0,
                    health_score INTEGER
                )
            """)

            # File positions table (track where we last read from each log file)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_positions (
                    log_file TEXT PRIMARY KEY,
                    position INTEGER DEFAULT 0,
                    last_modified REAL,
                    last_check DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def store_analysis(self, log_file: str, health_score: Optional[int], error_count: int,
                      warning_count: int, avg_response_time: float, analysis_text: str,
                      local_metrics: Dict, ai_triggered: bool = False) -> int:
        """Store analysis results in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analyses (log_file, health_score, error_count, warning_count,
                                    avg_response_time, analysis_text, local_metrics, ai_triggered)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_file, health_score, error_count, warning_count, avg_response_time,
                  analysis_text, json.dumps(local_metrics), ai_triggered))
            return cursor.lastrowid

    def store_alert(self, alert_type: str, severity: str, message: str,
                   log_file: str = None, health_score: int = None) -> int:
        """Store alert in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts (alert_type, severity, message, log_file, health_score)
                VALUES (?, ?, ?, ?, ?)
            """, (alert_type, severity, message, log_file, health_score))
            return cursor.lastrowid

    def get_file_position(self, log_file: str) -> Tuple[int, float]:
        """Get last read position and modification time for log file."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT position, last_modified FROM file_positions WHERE log_file = ?", (log_file,))
            result = cursor.fetchone()
            return result if result else (0, 0.0)

    def update_file_position(self, log_file: str, position: int, last_modified: float):
        """Update last read position for log file."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO file_positions (log_file, position, last_modified, last_check)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (log_file, position, last_modified))

    def get_recent_analyses(self, log_file: str, hours: int = 24) -> List[Dict]:
        """Get recent analyses for pattern detection."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, health_score, error_count, warning_count, avg_response_time
                FROM analyses
                WHERE log_file = ? AND timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            """.format(hours), (log_file,))

            columns = ['timestamp', 'health_score', 'error_count', 'warning_count', 'avg_response_time']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_unresolved_alerts(self) -> List[Dict]:
        """Get all unresolved alerts."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, alert_type, severity, message, log_file, health_score
                FROM alerts WHERE resolved = 0
                ORDER BY timestamp DESC
            """)

            columns = ['id', 'timestamp', 'alert_type', 'severity', 'message', 'log_file', 'health_score']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

class LogAnalyzer:
    """Performs local log analysis and determines when AI analysis is needed."""

    def __init__(self, config: Dict):
        self.config = config
        self.error_patterns = [
            r'\b(error|ERROR|Error)\b',
            r'\b(exception|EXCEPTION|Exception)\b',
            r'\b(fatal|FATAL|Fatal)\b',
            r'\b(critical|CRITICAL|Critical)\b',
            r'HTTP/\d\.\d" [45]\d\d',  # HTTP 4xx/5xx status codes
            r'\b(failed|FAILED|Failed)\b'
        ]
        self.warning_patterns = [
            r'\b(warning|WARNING|Warning)\b',
            r'\b(warn|WARN|Warn)\b',
            r'HTTP/\d\.\d" 3\d\d',  # HTTP 3xx status codes
            r'\b(timeout|TIMEOUT|Timeout)\b'
        ]
        self.response_time_pattern = r'(\d+(?:\.\d+)?)\s*ms|time=(\d+(?:\.\d+)?)'

    def analyze_log_content(self, content: str, log_file: str) -> Dict:
        """Perform local analysis of log content."""
        lines = content.split('\n')
        total_lines = len(lines)

        error_count = 0
        warning_count = 0
        response_times = []

        # Count errors and warnings
        for line in lines:
            for pattern in self.error_patterns:
                if re.search(pattern, line):
                    error_count += 1
                    break

            for pattern in self.warning_patterns:
                if re.search(pattern, line):
                    warning_count += 1
                    break

            # Extract response times
            time_match = re.search(self.response_time_pattern, line)
            if time_match:
                time_val = float(time_match.group(1) or time_match.group(2))
                response_times.append(time_val)

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        metrics = {
            'total_lines': total_lines,
            'error_count': error_count,
            'warning_count': warning_count,
            'avg_response_time': avg_response_time,
            'max_response_time': max(response_times) if response_times else 0,
            'error_rate': (error_count / total_lines) * 100 if total_lines > 0 else 0,
            'warning_rate': (warning_count / total_lines) * 100 if total_lines > 0 else 0,
            'log_file': log_file,
            'analysis_timestamp': datetime.now().isoformat()
        }

        return metrics

    def should_trigger_ai_analysis(self, metrics: Dict) -> Tuple[bool, str]:
        """Determine if AI analysis should be triggered based on local metrics."""
        thresholds = self.config['analysis_thresholds']
        reasons = []

        if metrics['error_count'] >= thresholds['error_count']:
            reasons.append(f"High error count: {metrics['error_count']}")

        if metrics['avg_response_time'] >= thresholds['avg_response_time']:
            reasons.append(f"High avg response time: {metrics['avg_response_time']:.2f}ms")

        if metrics['total_lines'] >= thresholds['high_activity']:
            reasons.append(f"High activity: {metrics['total_lines']} new log lines")

        if metrics['error_rate'] >= thresholds.get('error_rate', 5.0):
            reasons.append(f"High error rate: {metrics['error_rate']:.1f}%")

        trigger = len(reasons) > 0
        reason = "; ".join(reasons) if reasons else "No significant issues detected"

        return trigger, reason

class ClaudeAnalyzer:
    """Handles Claude API integration for intelligent log analysis."""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 1000

    def create_analysis_prompt(self, log_content: str, local_metrics: Dict,
                             historical_data: List[Dict]) -> str:
        """Create a comprehensive prompt for Claude analysis."""

        # Truncate log content for API efficiency
        truncated_content = self._truncate_log_content(log_content, 6000)

        # Format historical trends
        trend_summary = self._format_historical_trends(historical_data)

        prompt = f"""You are analyzing logs from a Raspberry Pi web application. Please provide a comprehensive analysis in JSON format.

SYSTEM CONTEXT:
- Raspberry Pi environment with resource constraints
- Web application monitoring for production system
- Need actionable insights and specific recommendations

LOCAL ANALYSIS RESULTS:
- Total log lines analyzed: {local_metrics['total_lines']}
- Errors detected: {local_metrics['error_count']}
- Warnings detected: {local_metrics['warning_count']}
- Average response time: {local_metrics['avg_response_time']:.2f}ms
- Error rate: {local_metrics['error_rate']:.1f}%
- Log file: {local_metrics['log_file']}

HISTORICAL TRENDS (last 24h):
{trend_summary}

LOG SAMPLE:
{truncated_content}

Please analyze and return a JSON response with exactly this structure:
{{
    "health_score": <integer 1-10, where 10 is perfect health>,
    "critical_issues": [<list of immediate attention items>],
    "performance_insights": {{
        "response_time_analysis": "<analysis of performance>",
        "bottlenecks": [<identified bottlenecks>],
        "recommendations": [<performance recommendations>]
    }},
    "error_analysis": {{
        "patterns": [<error patterns identified>],
        "root_causes": [<likely root causes>],
        "frequency": "<error frequency assessment>"
    }},
    "recommendations": {{
        "high_priority": [<urgent actions needed>],
        "medium_priority": [<important but not urgent>],
        "low_priority": [<nice to have improvements>]
    }},
    "trend_analysis": "<comparison with historical data>",
    "summary": "<brief overall assessment>"
}}

Focus on actionable insights specific to Raspberry Pi constraints and web application performance."""

        return prompt

    def _truncate_log_content(self, content: str, max_chars: int) -> str:
        """Intelligently truncate log content for API efficiency."""
        if len(content) <= max_chars:
            return content

        lines = content.split('\n')

        # Prioritize error lines and recent lines
        error_lines = []
        recent_lines = []

        for i, line in enumerate(lines):
            if any(pattern in line.lower() for pattern in ['error', 'exception', 'critical', 'fatal']):
                error_lines.append(line)
            if i >= len(lines) - 100:  # Last 100 lines
                recent_lines.append(line)

        # Combine important content
        important_content = '\n'.join(error_lines[-50:]) + '\n--- RECENT LOGS ---\n' + '\n'.join(recent_lines[-50:])

        if len(important_content) <= max_chars:
            return important_content

        return important_content[:max_chars] + "\n... [truncated for API efficiency]"

    def _format_historical_trends(self, historical_data: List[Dict]) -> str:
        """Format historical data for prompt context."""
        if not historical_data:
            return "No historical data available"

        recent = historical_data[:5]  # Last 5 analyses

        trend_lines = []
        for data in recent:
            trend_lines.append(
                f"- {data['timestamp']}: Health={data['health_score']}, "
                f"Errors={data['error_count']}, Response={data['avg_response_time']:.1f}ms"
            )

        return '\n'.join(trend_lines) if trend_lines else "No recent analysis data"

    def analyze_logs(self, log_content: str, local_metrics: Dict,
                    historical_data: List[Dict]) -> Dict:
        """Perform AI analysis using Claude API."""
        try:
            prompt = self.create_analysis_prompt(log_content, local_metrics, historical_data)

            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse JSON response
            response_text = message.content[0].text

            # Extract JSON from response (handle cases where Claude adds extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_content = response_text[json_start:json_end]
                analysis_result = json.loads(json_content)

                # Validate required fields
                required_fields = ['health_score', 'critical_issues', 'summary']
                for field in required_fields:
                    if field not in analysis_result:
                        analysis_result[field] = f"Missing {field} in analysis"

                return analysis_result
            else:
                return self._create_fallback_analysis(local_metrics, "Invalid JSON response from Claude")

        except Exception as e:
            logging.error(f"Claude API analysis failed: {str(e)}")
            return self._create_fallback_analysis(local_metrics, f"API Error: {str(e)}")

    def _create_fallback_analysis(self, local_metrics: Dict, error_msg: str) -> Dict:
        """Create fallback analysis when Claude API fails."""
        health_score = 7  # Neutral score

        if local_metrics['error_count'] > 20:
            health_score = 3
        elif local_metrics['error_count'] > 10:
            health_score = 5
        elif local_metrics['avg_response_time'] > 2000:
            health_score = 4

        return {
            "health_score": health_score,
            "critical_issues": [f"API analysis unavailable: {error_msg}"],
            "performance_insights": {
                "response_time_analysis": f"Average response time: {local_metrics['avg_response_time']:.2f}ms",
                "bottlenecks": [],
                "recommendations": ["Monitor system resources"]
            },
            "error_analysis": {
                "patterns": [f"Local analysis found {local_metrics['error_count']} errors"],
                "root_causes": ["Analysis pending - API unavailable"],
                "frequency": "Unable to determine"
            },
            "recommendations": {
                "high_priority": ["Investigate API connectivity"],
                "medium_priority": ["Review error patterns manually"],
                "low_priority": ["Update monitoring configuration"]
            },
            "trend_analysis": "Historical comparison unavailable",
            "summary": f"Local analysis: {local_metrics['error_count']} errors, {local_metrics['avg_response_time']:.1f}ms avg response time"
        }

class AlertManager:
    """Handles alert generation and email notifications."""

    def __init__(self, config: Dict):
        self.config = config
        self.email_config = config.get('email', {})
        self.alert_thresholds = config.get('alert_thresholds', {})

    def should_alert(self, analysis_result: Dict, local_metrics: Dict) -> Tuple[bool, str, str]:
        """Determine if an alert should be sent."""
        health_score = analysis_result.get('health_score', 10)
        error_count = local_metrics.get('error_count', 0)
        critical_issues = analysis_result.get('critical_issues', [])

        # Check health score threshold
        if health_score <= self.alert_thresholds.get('health_score', 3):
            return True, "CRITICAL", f"Health score critically low: {health_score}/10"

        # Check error count threshold
        if error_count > self.alert_thresholds.get('error_count', 20):
            return True, "HIGH", f"High error count detected: {error_count} errors"

        # Check for critical keywords in analysis
        critical_keywords = ['CRITICAL', 'DOWN', 'FATAL', 'OFFLINE']
        analysis_text = json.dumps(analysis_result).upper()

        for keyword in critical_keywords:
            if keyword in analysis_text:
                return True, "CRITICAL", f"Critical issue detected: {keyword}"

        # Check for multiple critical issues
        if len(critical_issues) >= 3:
            return True, "HIGH", f"Multiple critical issues: {len(critical_issues)} issues found"

        return False, "INFO", "No alerts triggered"

    def send_alert(self, alert_type: str, severity: str, message: str,
                  analysis_result: Dict, local_metrics: Dict, log_file: str):
        """Send email alert with analysis details."""
        if not self.email_config.get('enabled', False):
            logging.info(f"Email alerts disabled. Alert: {severity} - {message}")
            return

        try:
            # Create email content
            subject = f"[{severity}] Log Monitor Alert - {alert_type}"
            body = self._create_email_body(alert_type, severity, message, analysis_result, local_metrics, log_file)

            # Send email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']

            html_part = MIMEText(body, 'html')
            msg.attach(html_part)

            # Connect to SMTP server
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                if self.email_config.get('use_tls', True):
                    server.starttls()

                if self.email_config.get('username'):
                    server.login(self.email_config['username'], self.email_config['password'])

                server.send_message(msg)

            logging.info(f"Alert email sent: {severity} - {message}")

        except Exception as e:
            logging.error(f"Failed to send email alert: {str(e)}")

    def _create_email_body(self, alert_type: str, severity: str, message: str,
                          analysis_result: Dict, local_metrics: Dict, log_file: str) -> str:
        """Create HTML email body with analysis details."""

        severity_colors = {
            'CRITICAL': '#dc3545',
            'HIGH': '#fd7e14',
            'MEDIUM': '#ffc107',
            'LOW': '#28a745',
            'INFO': '#17a2b8'
        }

        color = severity_colors.get(severity, '#6c757d')

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid {color}; background-color: #f8f9fa; }}
                .metric {{ margin: 5px 0; }}
                .critical {{ color: #dc3545; font-weight: bold; }}
                .recommendation {{ margin: 10px 0; padding: 10px; background-color: #e9ecef; border-radius: 3px; }}
                ul {{ margin: 10px 0; }}
                li {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 Log Monitor Alert - {severity}</h2>
                <p><strong>Alert Type:</strong> {alert_type}</p>
                <p><strong>Message:</strong> {message}</p>
                <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div class="section">
                <h3>📊 Analysis Summary</h3>
                <div class="metric"><strong>Health Score:</strong> {analysis_result.get('health_score', 'N/A')}/10</div>
                <div class="metric"><strong>Log File:</strong> {log_file}</div>
                <div class="metric"><strong>Error Count:</strong> {local_metrics.get('error_count', 0)}</div>
                <div class="metric"><strong>Average Response Time:</strong> {local_metrics.get('avg_response_time', 0):.2f}ms</div>
                <div class="metric"><strong>Total Log Lines:</strong> {local_metrics.get('total_lines', 0)}</div>
                <p><strong>Summary:</strong> {analysis_result.get('summary', 'No summary available')}</p>
            </div>
        """

        # Critical Issues
        critical_issues = analysis_result.get('critical_issues', [])
        if critical_issues:
            html += f"""
            <div class="section">
                <h3 class="critical">🔴 Critical Issues</h3>
                <ul>
                    {''.join(f'<li>{issue}</li>' for issue in critical_issues)}
                </ul>
            </div>
            """

        # Recommendations
        recommendations = analysis_result.get('recommendations', {})
        if recommendations:
            html += '<div class="section"><h3>💡 Recommendations</h3>'

            for priority, items in recommendations.items():
                if items:
                    priority_label = priority.replace('_', ' ').title()
                    html += f'<div class="recommendation"><strong>{priority_label}:</strong><ul>'
                    html += ''.join(f'<li>{item}</li>' for item in items)
                    html += '</ul></div>'

            html += '</div>'

        # Performance Insights
        performance = analysis_result.get('performance_insights', {})
        if performance:
            html += f"""
            <div class="section">
                <h3>⚡ Performance Insights</h3>
                <p><strong>Response Time Analysis:</strong> {performance.get('response_time_analysis', 'N/A')}</p>
            """

            bottlenecks = performance.get('bottlenecks', [])
            if bottlenecks:
                html += '<p><strong>Bottlenecks:</strong></p><ul>'
                html += ''.join(f'<li>{bottleneck}</li>' for bottleneck in bottlenecks)
                html += '</ul>'

            html += '</div>'

        html += """
            <div class="section">
                <h3>📈 Trend Analysis</h3>
                <p>{}</p>
            </div>

            <hr>
            <p><small>This alert was generated by the Raspberry Pi Log Monitoring Agent.</small></p>
        </body>
        </html>
        """.format(analysis_result.get('trend_analysis', 'No trend data available'))

        return html

class LogMonitoringAgent:
    """Main class that coordinates all log monitoring operations."""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_or_create_config()

        # Initialize components
        self.db_manager = DatabaseManager(self.config['database']['path'])
        self.log_analyzer = LogAnalyzer(self.config)
        self.claude_analyzer = ClaudeAnalyzer(self.config['claude']['api_key'])
        self.alert_manager = AlertManager(self.config)

        # Setup logging
        self._setup_logging()

        logging.info("Log Monitoring Agent initialized")

    def _load_or_create_config(self) -> Dict:
        """Load configuration or create default config file."""
        if not os.path.exists(self.config_path):
            self._create_default_config()

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Validate required sections
            self._validate_config(config)
            return config

        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Invalid configuration file: {e}")
            raise

    def _create_default_config(self):
        """Create default configuration file with comments."""
        default_config = {
            "_comment": "AI-Powered Log Monitoring Agent Configuration",
            "_description": "Configure settings for Raspberry Pi log monitoring with Claude AI analysis",

            "claude": {
                "_comment": "Claude AI API configuration",
                "api_key": "your-claude-api-key-here",
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000
            },

            "log_files": [
                {
                    "_comment": "Add your log files here",
                    "path": "/var/log/nginx/access.log",
                    "name": "nginx_access",
                    "enabled": True
                },
                {
                    "path": "/var/log/nginx/error.log",
                    "name": "nginx_error",
                    "enabled": True
                },
                {
                    "path": "/var/log/myapp/app.log",
                    "name": "application",
                    "enabled": False
                }
            ],

            "monitoring": {
                "_comment": "Monitoring schedule and intervals",
                "check_interval_minutes": 15,
                "daily_summary_time": "09:00",
                "max_file_size_mb": 100,
                "retain_analyses_days": 30
            },

            "analysis_thresholds": {
                "_comment": "Thresholds for triggering AI analysis",
                "error_count": 10,
                "avg_response_time": 2000,
                "high_activity": 1000,
                "error_rate": 5.0
            },

            "alert_thresholds": {
                "_comment": "Thresholds for sending alerts",
                "health_score": 3,
                "error_count": 20,
                "response_time": 5000
            },

            "email": {
                "_comment": "Email alert configuration",
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True,
                "username": "your-email@gmail.com",
                "password": "your-app-password",
                "from_email": "your-email@gmail.com",
                "to_email": "admin@yourdomain.com"
            },

            "database": {
                "_comment": "Database configuration",
                "path": "log_monitor.db",
                "backup_enabled": True,
                "backup_interval_hours": 24
            },

            "logging": {
                "_comment": "Agent logging configuration",
                "level": "INFO",
                "file": "log_monitor_agent.log",
                "max_size_mb": 10,
                "backup_count": 5
            },

            "raspberry_pi": {
                "_comment": "Raspberry Pi specific optimizations",
                "memory_limit_mb": 256,
                "max_concurrent_analyses": 1,
                "cpu_throttle_temp": 80,
                "disk_space_threshold_gb": 1
            }
        }

        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

        print(f"Default configuration created at {self.config_path}")
        print("Please edit the configuration file and add your Claude API key before running.")
        print("At minimum, update: claude.api_key and log_files paths")

    def _validate_config(self, config: Dict):
        """Validate configuration has required fields."""
        required_sections = ['claude', 'log_files', 'monitoring', 'analysis_thresholds']

        for section in required_sections:
            if section not in config:
                raise KeyError(f"Missing required configuration section: {section}")

        if not config['claude']['api_key'] or config['claude']['api_key'] == "your-claude-api-key-here":
            raise ValueError("Claude API key not configured. Please update config.json")

        if not config['log_files']:
            raise ValueError("No log files configured for monitoring")

    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config.get('logging', {})

        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_config.get('file', 'log_monitor_agent.log')),
                logging.StreamHandler()
            ]
        )

    def read_new_log_content(self, log_file_config: Dict) -> Tuple[str, Dict]:
        """Read new content from log file since last check."""
        log_path = log_file_config['path']

        if not os.path.exists(log_path):
            logging.warning(f"Log file not found: {log_path}")
            return "", {}

        try:
            # Get file stats
            stat = os.stat(log_path)
            current_size = stat.st_size
            current_mtime = stat.st_mtime

            # Get last read position
            last_position, last_mtime = self.db_manager.get_file_position(log_path)

            # Check if file was rotated (size decreased or mtime changed significantly)
            if current_size < last_position or abs(current_mtime - last_mtime) > 60:
                logging.info(f"Log rotation detected for {log_path}, reading from beginning")
                last_position = 0

            # Read new content
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_content = f.read()
                new_position = f.tell()

            # Update position in database
            self.db_manager.update_file_position(log_path, new_position, current_mtime)

            # Return content and metadata
            metadata = {
                'file_size': current_size,
                'bytes_read': len(new_content.encode('utf-8')),
                'lines_read': len(new_content.split('\n')) if new_content else 0,
                'last_position': last_position,
                'new_position': new_position
            }

            return new_content, metadata

        except Exception as e:
            logging.error(f"Error reading log file {log_path}: {str(e)}")
            return "", {}

    def analyze_single_log(self, log_file_config: Dict) -> Dict:
        """Analyze a single log file and return results."""
        log_path = log_file_config['path']
        log_name = log_file_config['name']

        logging.info(f"Analyzing log file: {log_name} ({log_path})")

        # Read new log content
        log_content, read_metadata = self.read_new_log_content(log_file_config)

        if not log_content.strip():
            logging.info(f"No new content in {log_name}")
            return {
                'log_file': log_name,
                'status': 'no_new_content',
                'message': 'No new log content to analyze'
            }

        # Perform local analysis
        local_metrics = self.log_analyzer.analyze_log_content(log_content, log_name)
        local_metrics.update(read_metadata)

        # Determine if AI analysis is needed
        should_analyze, reason = self.log_analyzer.should_trigger_ai_analysis(local_metrics)

        analysis_result = None
        ai_triggered = False

        if should_analyze:
            logging.info(f"Triggering AI analysis for {log_name}: {reason}")

            # Get historical data for context
            historical_data = self.db_manager.get_recent_analyses(log_name, 24)

            # Perform AI analysis
            analysis_result = self.claude_analyzer.analyze_logs(log_content, local_metrics, historical_data)
            ai_triggered = True
        else:
            logging.info(f"Skipping AI analysis for {log_name}: {reason}")
            analysis_result = {
                'health_score': 8,  # Default good health score
                'summary': f"Local analysis only: {reason}",
                'critical_issues': [],
                'recommendations': {'low_priority': ['Continue monitoring']},
                'trend_analysis': 'Stable - no significant issues detected'
            }

        # Store analysis in database
        analysis_id = self.db_manager.store_analysis(
            log_name,
            analysis_result.get('health_score'),
            local_metrics['error_count'],
            local_metrics['warning_count'],
            local_metrics['avg_response_time'],
            json.dumps(analysis_result),
            local_metrics,
            ai_triggered
        )

        # Check if alerts should be sent
        should_alert, severity, alert_message = self.alert_manager.should_alert(analysis_result, local_metrics)

        if should_alert:
            logging.warning(f"Alert triggered for {log_name}: {severity} - {alert_message}")

            # Store alert
            alert_id = self.db_manager.store_alert(
                "log_analysis",
                severity,
                alert_message,
                log_name,
                analysis_result.get('health_score')
            )

            # Send email alert
            self.alert_manager.send_alert(
                "log_analysis",
                severity,
                alert_message,
                analysis_result,
                local_metrics,
                log_name
            )

        return {
            'log_file': log_name,
            'status': 'analyzed',
            'analysis_id': analysis_id,
            'ai_triggered': ai_triggered,
            'local_metrics': local_metrics,
            'analysis_result': analysis_result,
            'alert_triggered': should_alert,
            'alert_severity': severity if should_alert else None
        }

    def run_analysis_cycle(self):
        """Run a complete analysis cycle for all enabled log files."""
        logging.info("Starting analysis cycle")

        enabled_logs = [log for log in self.config['log_files'] if log.get('enabled', True)]

        if not enabled_logs:
            logging.warning("No enabled log files configured")
            return

        results = []

        for log_config in enabled_logs:
            try:
                result = self.analyze_single_log(log_config)
                results.append(result)

                # Brief pause between analyses to prevent resource overload
                time.sleep(1)

            except Exception as e:
                logging.error(f"Error analyzing {log_config.get('name', 'unknown')}: {str(e)}")
                results.append({
                    'log_file': log_config.get('name', 'unknown'),
                    'status': 'error',
                    'error': str(e)
                })

        # Log cycle summary
        successful = len([r for r in results if r['status'] == 'analyzed'])
        errors = len([r for r in results if r['status'] == 'error'])
        ai_analyses = len([r for r in results if r.get('ai_triggered', False)])
        alerts = len([r for r in results if r.get('alert_triggered', False)])

        logging.info(f"Analysis cycle complete: {successful} successful, {errors} errors, "
                    f"{ai_analyses} AI analyses, {alerts} alerts")

        return results

    def generate_daily_summary(self):
        """Generate and send daily summary report."""
        logging.info("Generating daily summary report")

        # Get analyses from last 24 hours
        yesterday = datetime.now() - timedelta(days=1)

        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()

            # Get analysis summary
            cursor.execute("""
                SELECT log_file, COUNT(*) as analysis_count, AVG(health_score) as avg_health,
                       SUM(error_count) as total_errors, AVG(avg_response_time) as avg_response
                FROM analyses
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY log_file
            """)

            analysis_summary = cursor.fetchall()

            # Get alert summary
            cursor.execute("""
                SELECT severity, COUNT(*) as alert_count
                FROM alerts
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY severity
            """)

            alert_summary = cursor.fetchall()

        # Create summary content
        summary = {
            'timestamp': datetime.now().isoformat(),
            'period': '24 hours',
            'analysis_summary': [
                {
                    'log_file': row[0],
                    'analysis_count': row[1],
                    'avg_health_score': round(row[2], 1) if row[2] else None,
                    'total_errors': row[3],
                    'avg_response_time': round(row[4], 2) if row[4] else None
                }
                for row in analysis_summary
            ],
            'alert_summary': [
                {'severity': row[0], 'count': row[1]}
                for row in alert_summary
            ]
        }

        # Send summary email if configured
        if self.config['email'].get('enabled', False):
            try:
                self._send_daily_summary_email(summary)
            except Exception as e:
                logging.error(f"Failed to send daily summary email: {str(e)}")

        logging.info("Daily summary generated")
        return summary

    def _send_daily_summary_email(self, summary: Dict):
        """Send daily summary email."""
        email_config = self.config['email']

        subject = f"Daily Log Monitor Summary - {datetime.now().strftime('%Y-%m-%d')}"

        # Create HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #007bff; color: white; padding: 15px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; background-color: #f8f9fa; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .good {{ color: #28a745; }}
                .warning {{ color: #ffc107; }}
                .danger {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 Daily Log Monitor Summary</h2>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
                <p><strong>Period:</strong> Last 24 hours</p>
            </div>

            <div class="section">
                <h3>📈 Analysis Summary</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Log File</th>
                            <th>Analyses</th>
                            <th>Avg Health Score</th>
                            <th>Total Errors</th>
                            <th>Avg Response Time</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for item in summary['analysis_summary']:
            health_class = 'good' if (item['avg_health_score'] or 0) >= 7 else 'warning' if (item['avg_health_score'] or 0) >= 4 else 'danger'
            html_body += f"""
                        <tr>
                            <td>{item['log_file']}</td>
                            <td>{item['analysis_count']}</td>
                            <td class="{health_class}">{item['avg_health_score'] or 'N/A'}</td>
                            <td>{item['total_errors']}</td>
                            <td>{item['avg_response_time'] or 'N/A'}ms</td>
                        </tr>
            """

        html_body += """
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h3>🚨 Alert Summary</h3>
        """

        if summary['alert_summary']:
            html_body += """
                <table>
                    <thead>
                        <tr><th>Severity</th><th>Count</th></tr>
                    </thead>
                    <tbody>
            """
            for alert in summary['alert_summary']:
                html_body += f"<tr><td>{alert['severity']}</td><td>{alert['count']}</td></tr>"
            html_body += "</tbody></table>"
        else:
            html_body += "<p>✅ No alerts in the last 24 hours</p>"

        html_body += """
            </div>

            <hr>
            <p><small>This summary was generated by the Raspberry Pi Log Monitoring Agent.</small></p>
        </body>
        </html>
        """

        # Send email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = email_config['from_email']
        msg['To'] = email_config['to_email']

        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            if email_config.get('use_tls', True):
                server.starttls()

            if email_config.get('username'):
                server.login(email_config['username'], email_config['password'])

            server.send_message(msg)

        logging.info("Daily summary email sent")

    def start_monitoring(self):
        """Start the monitoring service with scheduled analysis cycles."""
        logging.info("Starting log monitoring service")

        # Schedule regular analysis cycles
        interval = self.config['monitoring']['check_interval_minutes']
        schedule.every(interval).minutes.do(self.run_analysis_cycle)

        # Schedule daily summary
        daily_time = self.config['monitoring']['daily_summary_time']
        schedule.every().day.at(daily_time).do(self.generate_daily_summary)

        logging.info(f"Monitoring scheduled: analysis every {interval} minutes, daily summary at {daily_time}")

        # Run initial analysis
        self.run_analysis_cycle()

        # Main monitoring loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")
        except Exception as e:
            logging.error(f"Monitoring loop error: {str(e)}")
            raise

def main():
    """Main entry point for the log monitoring agent."""
    import argparse

    parser = argparse.ArgumentParser(description="AI-Powered Log Monitoring Agent for Raspberry Pi")
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--once', action='store_true', help='Run analysis once and exit')
    parser.add_argument('--summary', action='store_true', help='Generate daily summary and exit')
    parser.add_argument('--test-email', action='store_true', help='Send test email and exit')

    args = parser.parse_args()

    try:
        agent = LogMonitoringAgent(args.config)

        if args.once:
            logging.info("Running single analysis cycle")
            results = agent.run_analysis_cycle()
            print(f"Analysis complete: {len(results)} files processed")

        elif args.summary:
            logging.info("Generating daily summary")
            summary = agent.generate_daily_summary()
            print("Daily summary generated")

        elif args.test_email:
            logging.info("Sending test email")
            test_analysis = {
                'health_score': 8,
                'summary': 'Test email from Log Monitoring Agent',
                'critical_issues': [],
                'recommendations': {'info': ['This is a test email']},
                'trend_analysis': 'Test email - all systems normal'
            }
            test_metrics = {'error_count': 0, 'avg_response_time': 150.0, 'total_lines': 100}

            agent.alert_manager.send_alert(
                'test', 'INFO', 'Test email from Log Monitoring Agent',
                test_analysis, test_metrics, 'test.log'
            )
            print("Test email sent")

        else:
            # Start continuous monitoring
            agent.start_monitoring()

    except Exception as e:
        print(f"Error: {str(e)}")
        logging.error(f"Application error: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())