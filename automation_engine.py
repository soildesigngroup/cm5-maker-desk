#!/usr/bin/env python3
"""
Automation Engine Module
Inspired by Insomnia API client for automated testing and workflow execution
Supports REST, GraphQL, WebSocket, and custom automation workflows
"""

import json
import time
import requests
import threading
import os
import tempfile
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime
import uuid
import re
import logging
from urllib.parse import urljoin, urlparse
import base64
import jsonschema
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AutomationRequest:
    """HTTP request configuration"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    method: str = "GET"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    body_type: str = "json"  # json, form, raw, file
    auth_type: str = "none"  # none, basic, bearer, api_key
    auth_config: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    follow_redirects: bool = True
    verify_ssl: bool = True
    environment_id: Optional[str] = None
    pre_request_script: Optional[str] = None
    post_response_script: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AutomationResponse:
    """HTTP response data"""
    status_code: int
    headers: Dict[str, str]
    body: str
    content_type: str
    size: int
    elapsed_time: float
    timestamp: float
    cookies: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Environment:
    """Environment variables for automation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    variables: Dict[str, str] = field(default_factory=dict)
    base_url: str = ""
    active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Collection:
    """Collection of automation requests"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    requests: List[AutomationRequest] = field(default_factory=list)
    environment_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['requests'] = [req.to_dict() for req in self.requests]
        return data

@dataclass
class JsonLibrary:
    """JSON library/schema definition"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    library_type: str = "schema"  # schema, template, collection, mock_data
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate_json_schema(self, data: Dict[str, Any]) -> bool:
        """Validate data against this JSON schema"""
        if self.library_type != "schema":
            return False
        try:
            jsonschema.validate(data, self.content)
            return True
        except jsonschema.ValidationError:
            return False

@dataclass
class TestResult:
    """Test execution result"""
    request_id: str
    collection_id: str
    success: bool
    response: Optional[AutomationResponse]
    error: Optional[str]
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.response:
            data['response'] = self.response.to_dict()
        return data

class VariableResolver:
    """Resolves environment variables in requests"""

    def __init__(self, environment: Optional[Environment] = None):
        self.environment = environment
        self.global_vars = {}

    def resolve(self, text: str) -> str:
        """Resolve variables in text using {{variable}} syntax"""
        if not text:
            return text

        # Pattern for {{variable}} syntax
        pattern = r'\{\{([^}]+)\}\}'

        def replacer(match):
            var_name = match.group(1).strip()

            # Check environment variables first
            if self.environment and var_name in self.environment.variables:
                return self.environment.variables[var_name]

            # Check global variables
            if var_name in self.global_vars:
                return self.global_vars[var_name]

            # Built-in variables
            if var_name == 'timestamp':
                return str(int(time.time()))
            elif var_name == 'uuid':
                return str(uuid.uuid4())
            elif var_name == 'datetime':
                return datetime.now().isoformat()

            # Return original if not found
            return match.group(0)

        return re.sub(pattern, replacer, text)

    def set_variable(self, name: str, value: str):
        """Set a global variable"""
        self.global_vars[name] = value

class AuthenticationHandler:
    """Handle different authentication methods"""

    @staticmethod
    def apply_auth(request: AutomationRequest, session: requests.Session):
        """Apply authentication to request"""
        if request.auth_type == "basic" and "username" in request.auth_config:
            username = request.auth_config.get("username", "")
            password = request.auth_config.get("password", "")
            session.auth = (username, password)

        elif request.auth_type == "bearer" and "token" in request.auth_config:
            token = request.auth_config["token"]
            session.headers["Authorization"] = f"Bearer {token}"

        elif request.auth_type == "api_key" and "key" in request.auth_config:
            key = request.auth_config["key"]
            value = request.auth_config.get("value", "")
            header_name = request.auth_config.get("header", "X-API-Key")
            session.headers[header_name] = value

class AutomationEngine:
    """Main automation engine inspired by Insomnia"""

    def __init__(self):
        self.environments: Dict[str, Environment] = {}
        self.collections: Dict[str, Collection] = {}
        self.json_libraries: Dict[str, JsonLibrary] = {}
        self.active_environment: Optional[Environment] = None
        self.test_results: List[TestResult] = []
        self.variable_resolver = VariableResolver()
        self.library_storage_path = os.path.join(tempfile.gettempdir(), "automation_libraries")

    def create_environment(self, name: str, variables: Dict[str, str] = None, base_url: str = "") -> Environment:
        """Create a new environment"""
        env = Environment(
            name=name,
            variables=variables or {},
            base_url=base_url
        )
        self.environments[env.id] = env
        return env

    def set_active_environment(self, env_id: str) -> bool:
        """Set the active environment"""
        if env_id in self.environments:
            # Deactivate current environment
            if self.active_environment:
                self.active_environment.active = False

            # Activate new environment
            self.active_environment = self.environments[env_id]
            self.active_environment.active = True
            self.variable_resolver.environment = self.active_environment
            return True
        return False

    def create_collection(self, name: str, description: str = "") -> Collection:
        """Create a new collection"""
        collection = Collection(
            name=name,
            description=description
        )
        self.collections[collection.id] = collection
        return collection

    def add_request_to_collection(self, collection_id: str, request: AutomationRequest) -> bool:
        """Add a request to a collection"""
        if collection_id in self.collections:
            self.collections[collection_id].requests.append(request)
            self.collections[collection_id].updated_at = time.time()
            return True
        return False

    def execute_request(self, request: AutomationRequest, environment: Optional[Environment] = None) -> AutomationResponse:
        """Execute a single HTTP request"""
        start_time = time.time()

        try:
            # Use provided environment or active environment
            env = environment or self.active_environment
            resolver = VariableResolver(env)

            # Resolve variables in request
            url = resolver.resolve(request.url)
            if env and env.base_url:
                url = urljoin(env.base_url, url)

            # Prepare headers
            headers = {}
            for key, value in request.headers.items():
                headers[resolver.resolve(key)] = resolver.resolve(value)

            # Prepare body
            body = None
            if request.body:
                body = resolver.resolve(request.body)
                if request.body_type == "json":
                    try:
                        body = json.loads(body)
                    except json.JSONDecodeError:
                        pass

            # Create session and apply authentication
            session = requests.Session()
            session.headers.update(headers)
            AuthenticationHandler.apply_auth(request, session)

            # Execute request
            response = session.request(
                method=request.method,
                url=url,
                json=body if request.body_type == "json" and isinstance(body, dict) else None,
                data=body if request.body_type != "json" or not isinstance(body, dict) else None,
                timeout=request.timeout,
                allow_redirects=request.follow_redirects,
                verify=request.verify_ssl
            )

            elapsed_time = time.time() - start_time

            # Extract cookies
            cookies = {}
            for cookie in response.cookies:
                cookies[cookie.name] = cookie.value

            return AutomationResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.text,
                content_type=response.headers.get('content-type', ''),
                size=len(response.content),
                elapsed_time=elapsed_time,
                timestamp=time.time(),
                cookies=cookies
            )

        except Exception as e:
            elapsed_time = time.time() - start_time
            return AutomationResponse(
                status_code=0,
                headers={},
                body="",
                content_type="",
                size=0,
                elapsed_time=elapsed_time,
                timestamp=time.time(),
                error=str(e)
            )

    def run_collection(self, collection_id: str, environment_id: Optional[str] = None) -> List[TestResult]:
        """Run all requests in a collection"""
        if collection_id not in self.collections:
            return []

        collection = self.collections[collection_id]
        environment = None

        if environment_id and environment_id in self.environments:
            environment = self.environments[environment_id]

        results = []

        for request in collection.requests:
            start_time = time.time()

            try:
                response = self.execute_request(request, environment)
                execution_time = time.time() - start_time

                # Simple success check (can be extended with assertions)
                success = response.error is None and 200 <= response.status_code < 400

                result = TestResult(
                    request_id=request.id,
                    collection_id=collection_id,
                    success=success,
                    response=response,
                    error=response.error,
                    execution_time=execution_time
                )

                results.append(result)
                self.test_results.append(result)

            except Exception as e:
                execution_time = time.time() - start_time
                result = TestResult(
                    request_id=request.id,
                    collection_id=collection_id,
                    success=False,
                    response=None,
                    error=str(e),
                    execution_time=execution_time
                )
                results.append(result)
                self.test_results.append(result)

        return results

    def create_automation_workflow(self, name: str, requests: List[AutomationRequest],
                                 environment_id: Optional[str] = None) -> Collection:
        """Create an automation workflow (collection) with multiple requests"""
        collection = self.create_collection(name, f"Automation workflow: {name}")

        if environment_id:
            collection.environment_id = environment_id

        for request in requests:
            self.add_request_to_collection(collection.id, request)

        return collection

    def import_insomnia_collection(self, insomnia_data: Dict[str, Any]) -> Collection:
        """Import an Insomnia-format collection"""
        # This would parse Insomnia's export format
        # For now, create a basic collection structure
        collection = self.create_collection(
            insomnia_data.get("name", "Imported Collection"),
            insomnia_data.get("description", "")
        )

        # Parse requests from Insomnia format
        if "requests" in insomnia_data:
            for req_data in insomnia_data["requests"]:
                request = AutomationRequest(
                    name=req_data.get("name", ""),
                    method=req_data.get("method", "GET"),
                    url=req_data.get("url", ""),
                    headers=req_data.get("headers", {}),
                    body=req_data.get("body", None)
                )
                self.add_request_to_collection(collection.id, request)

        return collection

    def get_status(self) -> Dict[str, Any]:
        """Get automation engine status"""
        return {
            "environments": len(self.environments),
            "collections": len(self.collections),
            "json_libraries": len(self.json_libraries),
            "active_environment": self.active_environment.name if self.active_environment else None,
            "total_requests": sum(len(col.requests) for col in self.collections.values()),
            "test_results": len(self.test_results),
            "recent_results": [result.to_dict() for result in self.test_results[-10:]],
            "library_types": {
                "schema": len([lib for lib in self.json_libraries.values() if lib.library_type == "schema"]),
                "template": len([lib for lib in self.json_libraries.values() if lib.library_type == "template"]),
                "mock_data": len([lib for lib in self.json_libraries.values() if lib.library_type == "mock_data"]),
                "collection": len([lib for lib in self.json_libraries.values() if lib.library_type == "collection"])
            }
        }

    def clear_results(self):
        """Clear test results"""
        self.test_results.clear()

    # JSON Library Management Methods

    def upload_json_library(self, name: str, content: Dict[str, Any],
                           library_type: str = "schema", description: str = "",
                           version: str = "1.0.0", tags: List[str] = None) -> JsonLibrary:
        """Upload a JSON library (schema, template, etc.)"""
        # Ensure storage directory exists
        os.makedirs(self.library_storage_path, exist_ok=True)

        library = JsonLibrary(
            name=name,
            description=description,
            content=content,
            library_type=library_type,
            version=version,
            tags=tags or []
        )

        # Save to file system
        file_path = os.path.join(self.library_storage_path, f"{library.id}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump({
                    'metadata': {
                        'id': library.id,
                        'name': library.name,
                        'description': library.description,
                        'library_type': library.library_type,
                        'version': library.version,
                        'tags': library.tags,
                        'created_at': library.created_at,
                        'updated_at': library.updated_at
                    },
                    'content': library.content
                }, f, indent=2)

            library.file_path = file_path
            self.json_libraries[library.id] = library

            logger.info(f"JSON library uploaded: {library.name} ({library.library_type})")
            return library

        except Exception as e:
            logger.error(f"Failed to save JSON library: {e}")
            raise

    def upload_json_file(self, file_content: str, name: str,
                        library_type: str = "schema", description: str = "",
                        version: str = "1.0.0", tags: List[str] = None) -> JsonLibrary:
        """Upload JSON content from file"""
        try:
            content = json.loads(file_content)
            return self.upload_json_library(name, content, library_type, description, version, tags)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON content: {e}")

    def get_json_library(self, library_id: str) -> Optional[JsonLibrary]:
        """Get a JSON library by ID"""
        return self.json_libraries.get(library_id)

    def list_json_libraries(self, library_type: Optional[str] = None) -> List[JsonLibrary]:
        """List all JSON libraries, optionally filtered by type"""
        libraries = list(self.json_libraries.values())
        if library_type:
            libraries = [lib for lib in libraries if lib.library_type == library_type]
        return sorted(libraries, key=lambda x: x.created_at, reverse=True)

    def delete_json_library(self, library_id: str) -> bool:
        """Delete a JSON library"""
        if library_id not in self.json_libraries:
            return False

        library = self.json_libraries[library_id]

        # Remove file if it exists
        if library.file_path and os.path.exists(library.file_path):
            try:
                os.remove(library.file_path)
            except Exception as e:
                logger.warning(f"Failed to remove library file: {e}")

        # Remove from memory
        del self.json_libraries[library_id]
        logger.info(f"JSON library deleted: {library.name}")
        return True

    def validate_json_against_schema(self, data: Dict[str, Any], schema_id: str) -> Dict[str, Any]:
        """Validate JSON data against a schema library"""
        schema_library = self.get_json_library(schema_id)
        if not schema_library:
            return {"valid": False, "error": "Schema not found"}

        if schema_library.library_type != "schema":
            return {"valid": False, "error": "Library is not a JSON schema"}

        try:
            jsonschema.validate(data, schema_library.content)
            return {"valid": True, "error": None}
        except jsonschema.ValidationError as e:
            return {"valid": False, "error": str(e)}
        except jsonschema.SchemaError as e:
            return {"valid": False, "error": f"Invalid schema: {str(e)}"}

    def generate_mock_data(self, schema_id: str) -> Dict[str, Any]:
        """Generate mock data from a JSON schema"""
        schema_library = self.get_json_library(schema_id)
        if not schema_library or schema_library.library_type != "schema":
            return {}

        return self._generate_from_schema(schema_library.content)

    def _generate_from_schema(self, schema: Dict[str, Any]) -> Any:
        """Generate mock data from JSON schema definition"""
        schema_type = schema.get("type", "object")

        if schema_type == "object":
            result = {}
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                result[prop_name] = self._generate_from_schema(prop_schema)
            return result

        elif schema_type == "array":
            items_schema = schema.get("items", {"type": "string"})
            return [self._generate_from_schema(items_schema)]

        elif schema_type == "string":
            enum_values = schema.get("enum")
            if enum_values:
                return enum_values[0]
            return schema.get("default", "example_string")

        elif schema_type == "number":
            return schema.get("default", 42.0)

        elif schema_type == "integer":
            return schema.get("default", 42)

        elif schema_type == "boolean":
            return schema.get("default", True)

        else:
            return None

    def apply_json_template(self, template_id: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply variables to a JSON template"""
        template_library = self.get_json_library(template_id)
        if not template_library or template_library.library_type != "template":
            return {}

        variables = variables or {}
        template_str = json.dumps(template_library.content)

        # Replace template variables
        for var_name, var_value in variables.items():
            template_str = template_str.replace(f"{{{{ {var_name} }}}}", str(var_value))

        try:
            return json.loads(template_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse template after variable substitution")
            return template_library.content

    def load_libraries_from_storage(self):
        """Load JSON libraries from file system storage"""
        if not os.path.exists(self.library_storage_path):
            return

        for filename in os.listdir(self.library_storage_path):
            if filename.endswith('.json'):
                file_path = os.path.join(self.library_storage_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)

                    metadata = data.get('metadata', {})
                    content = data.get('content', {})

                    library = JsonLibrary(
                        id=metadata.get('id', str(uuid.uuid4())),
                        name=metadata.get('name', ''),
                        description=metadata.get('description', ''),
                        content=content,
                        library_type=metadata.get('library_type', 'schema'),
                        version=metadata.get('version', '1.0.0'),
                        tags=metadata.get('tags', []),
                        created_at=metadata.get('created_at', time.time()),
                        updated_at=metadata.get('updated_at', time.time()),
                        file_path=file_path
                    )

                    self.json_libraries[library.id] = library

                except Exception as e:
                    logger.warning(f"Failed to load library from {filename}: {e}")

    def export_json_library(self, library_id: str) -> Optional[str]:
        """Export a JSON library as JSON string"""
        library = self.get_json_library(library_id)
        if not library:
            return None

        export_data = {
            'metadata': {
                'name': library.name,
                'description': library.description,
                'library_type': library.library_type,
                'version': library.version,
                'tags': library.tags,
                'exported_at': time.time()
            },
            'content': library.content
        }

        return json.dumps(export_data, indent=2)

    def import_json_library(self, json_data: str, name: Optional[str] = None) -> JsonLibrary:
        """Import a JSON library from JSON string"""
        try:
            data = json.loads(json_data)

            # Handle different import formats
            if 'metadata' in data and 'content' in data:
                # Our export format
                metadata = data['metadata']
                content = data['content']

                return self.upload_json_library(
                    name=name or metadata.get('name', 'Imported Library'),
                    content=content,
                    library_type=metadata.get('library_type', 'schema'),
                    description=metadata.get('description', ''),
                    version=metadata.get('version', '1.0.0'),
                    tags=metadata.get('tags', [])
                )
            else:
                # Raw JSON content
                return self.upload_json_library(
                    name=name or 'Imported JSON',
                    content=data,
                    library_type='schema',
                    description='Imported JSON content'
                )

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")

# Global automation engine instance
_automation_engine = None

def get_automation_engine() -> AutomationEngine:
    """Get global automation engine instance"""
    global _automation_engine
    if _automation_engine is None:
        _automation_engine = AutomationEngine()
    return _automation_engine