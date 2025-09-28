# Automation & API Testing

This application now includes a comprehensive Automation feature inspired by the open-source Insomnia API client, providing powerful API testing and workflow automation capabilities.

## Features

### Backend (Python)
- **Automation Engine** (`automation_engine.py`): Core automation and API testing functionality
- **Insomnia-inspired Architecture**: Request/response handling, collections, environments
- **Multi-protocol Support**: REST, GraphQL, WebSocket support foundation
- **Variable Resolution**: Environment variables with `{{variable}}` syntax
- **Authentication Support**: Bearer, Basic Auth, API Key authentication
- **Collection Management**: Organize requests into testable collections
- **Test Execution**: Run individual requests or entire collections
- **Import/Export**: Support for Insomnia-compatible collection formats

### Frontend (React/TypeScript)
- **Automation Tab**: Dedicated interface positioned after AI Vision tab
- **Request Builder**: Multi-tab interface for request configuration
- **Environment Management**: Create and manage API environments
- **Collection Management**: Organize and run test collections
- **Real-time Testing**: Execute requests and view responses instantly
- **Test Results**: Comprehensive test execution reporting
- **Professional UI**: Clean, Insomnia-inspired interface design

## Installation

### Dependencies
The automation feature requires the `requests` library:
```bash
pip install requests
```

All dependencies are included in `requirements.txt`.

## Core Concepts

### Environments
Environments contain variables and base URLs for different testing contexts:
- **Variables**: Key-value pairs accessible via `{{variable}}` syntax
- **Base URL**: Common URL prefix for all requests in the environment
- **Active Environment**: Currently selected environment for variable resolution

### Collections
Collections are groups of related API requests:
- **Organization**: Group related API tests together
- **Batch Execution**: Run all requests in a collection sequentially
- **Test Results**: Track success/failure rates across collections

### Requests
Individual HTTP requests with full configuration:
- **Methods**: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
- **Headers**: Custom HTTP headers with variable support
- **Body**: JSON, form data, raw text, or file uploads
- **Authentication**: Multiple auth types with credential management
- **Variable Resolution**: Dynamic content using environment variables

## Usage

### Starting the Server
The automation engine is automatically available when the HMI server starts:
```bash
python3 hmi_json_api.py server
```

### Web Interface

#### 1. Creating Environments
1. Navigate to the **Automation** tab
2. Click **+ Environment**
3. Configure:
   - **Name**: Environment identifier
   - **Base URL**: Common URL prefix (e.g., `https://api.example.com`)
   - **Variables**: JSON object with key-value pairs

Example environment variables:
```json
{
  "api_key": "your-api-key-here",
  "version": "v1",
  "user_id": "12345"
}
```

#### 2. Creating Collections
1. Click **+ Collection**
2. Provide name and description
3. Add requests to organize your API tests

#### 3. Building Requests
Use the Request Builder tabs:

**Request Tab:**
- Set request name and HTTP method
- Enter URL with variable support: `{{base_url}}/users/{{user_id}}`

**Headers Tab:**
- Add custom headers
- Use variables: `Authorization: Bearer {{api_key}}`

**Body Tab:**
- Choose body type (JSON, Form, Raw, File)
- Add request payload with variable support

**Auth Tab:**
- Configure authentication (Bearer, Basic, API Key)
- Credentials can use environment variables

#### 4. Executing Tests
- **Single Request**: Click the Send button to execute immediately
- **Collection Run**: Select a collection and click "Run Collection"
- **Environment Context**: All requests use the active environment

### API Endpoints

#### Get Automation Status
```http
GET /api/command
Content-Type: application/json

{
  "action": "get_status",
  "device": "automation",
  "request_id": "automation_status_123"
}
```

#### Create Environment
```http
GET /api/command
Content-Type: application/json

{
  "action": "create_environment",
  "device": "automation",
  "params": {
    "name": "Development",
    "base_url": "https://api.dev.example.com",
    "variables": {
      "api_key": "dev-key-123"
    }
  },
  "request_id": "automation_env_123"
}
```

#### Execute Request
```http
GET /api/command
Content-Type: application/json

{
  "action": "execute_request",
  "device": "automation",
  "params": {
    "request": {
      "name": "Get User",
      "method": "GET",
      "url": "/users/123",
      "headers": {
        "Authorization": "Bearer {{api_key}}"
      },
      "auth_type": "bearer",
      "auth_config": {
        "token": "your-token"
      }
    },
    "environment_id": "env-uuid"
  },
  "request_id": "automation_exec_123"
}
```

#### Run Collection
```http
GET /api/command
Content-Type: application/json

{
  "action": "run_collection",
  "device": "automation",
  "params": {
    "collection_id": "collection-uuid",
    "environment_id": "env-uuid"
  },
  "request_id": "automation_run_123"
}
```

## Variable System

### Syntax
Use double curly braces: `{{variable_name}}`

### Built-in Variables
- `{{timestamp}}`: Current Unix timestamp
- `{{uuid}}`: Generated UUID4
- `{{datetime}}`: Current ISO datetime

### Environment Variables
Variables defined in environments are automatically resolved:
```json
{
  "base_url": "https://api.example.com",
  "api_key": "secret-key",
  "version": "v2"
}
```

Usage examples:
- URL: `{{base_url}}/{{version}}/users`
- Header: `Authorization: Bearer {{api_key}}`
- Body: `{"timestamp": "{{timestamp}}", "version": "{{version}}"}`

## Authentication

### Bearer Token
```json
{
  "auth_type": "bearer",
  "auth_config": {
    "token": "{{api_token}}"
  }
}
```

### Basic Authentication
```json
{
  "auth_type": "basic",
  "auth_config": {
    "username": "{{username}}",
    "password": "{{password}}"
  }
}
```

### API Key
```json
{
  "auth_type": "api_key",
  "auth_config": {
    "header": "X-API-Key",
    "value": "{{api_key}}"
  }
}
```

## Testing

### Automated Testing
```bash
python3 test_automation_engine.py
```

This test demonstrates:
- Environment creation and management
- Collection and request creation
- Variable resolution
- Request execution
- Collection batch testing
- Insomnia import simulation

### Response Analysis
Test results include:
- **Status Code**: HTTP response status
- **Response Time**: Request execution time
- **Response Size**: Payload size in bytes
- **Headers**: Complete response headers
- **Body**: Response content
- **Cookies**: Set cookies from response
- **Errors**: Detailed error information

## Integration with Insomnia

### Compatibility
- **Collection Format**: Compatible with Insomnia export format
- **Variable Syntax**: Uses same `{{variable}}` syntax
- **Request Structure**: Similar request/response model
- **Authentication**: Supports common auth methods
- **Environments**: Equivalent environment concept

### Import/Export
```python
# Import Insomnia collection
insomnia_data = {
    "name": "My API Collection",
    "requests": [
        {
            "name": "Get Users",
            "method": "GET",
            "url": "/users",
            "headers": {"Accept": "application/json"}
        }
    ]
}

collection = automation_engine.import_insomnia_collection(insomnia_data)
```

## Architecture

### Backend Components
- `automation_engine.py`: Core automation functionality
- `AutomationEngine` class: Main engine management
- `AutomationRequest`: Request configuration
- `AutomationResponse`: Response data structure
- `Environment`: Environment management
- `Collection`: Request organization
- `VariableResolver`: Variable resolution system
- `AuthenticationHandler`: Authentication processing

### Frontend Components
- `src/components/hmi/Automation.tsx`: React component
- `src/services/hmi-api.ts`: TypeScript API client
- Multi-tab interface for request building
- Real-time response viewing
- Environment and collection management

## Advanced Features

### Request Chaining
Responses can be used to set variables for subsequent requests:
```python
# Extract data from response and set as variable
response = engine.execute_request(login_request)
if response.status_code == 200:
    data = json.loads(response.body)
    engine.variable_resolver.set_variable("auth_token", data["token"])
```

### Custom Assertions
Extend test results with custom validation:
```python
def validate_response(response):
    assertions = []

    # Status code assertion
    assertions.append({
        "name": "Status is 200",
        "passed": response.status_code == 200
    })

    # Response time assertion
    assertions.append({
        "name": "Response time < 1s",
        "passed": response.elapsed_time < 1.0
    })

    return assertions
```

### Workflow Automation
Create complex testing workflows:
```python
# Multi-step API workflow
workflow = [
    ("Login", login_request),
    ("Get Profile", profile_request),
    ("Update Data", update_request),
    ("Verify Changes", verify_request)
]

for step_name, request in workflow:
    result = engine.execute_request(request)
    print(f"{step_name}: {'✓' if result.status_code < 400 else '✗'}")
```

## Security Considerations
- Sensitive data in environment variables is handled securely
- Authentication credentials are not logged
- Request/response data can contain sensitive information
- Environment variables support secure credential storage

## Troubleshooting

### Common Issues
1. **Connection Errors**: Verify target API is accessible
2. **Authentication Failures**: Check credentials and auth type
3. **Variable Resolution**: Ensure variables are defined in active environment
4. **Timeout Issues**: Adjust request timeout settings

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Insomnia Project

This implementation is inspired by and compatible with the Kong Insomnia project:
- **Repository**: https://github.com/Kong/insomnia
- **License**: Apache-2.0 (same as Insomnia)
- **Philosophy**: Developer-friendly API testing
- **Features**: Maintains core Insomnia concepts and workflows

The automation engine provides a web-based alternative to Insomnia while maintaining compatibility with its core concepts and export formats.