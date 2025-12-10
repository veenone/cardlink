"""Script Management REST API for Dashboard.

This module provides REST API endpoints for managing APDU scripts and templates
through the dashboard interface.

Endpoints:
    Scripts:
        GET    /api/scripts           - List all scripts
        GET    /api/scripts/{id}      - Get single script
        POST   /api/scripts           - Create script
        PUT    /api/scripts/{id}      - Update script
        DELETE /api/scripts/{id}      - Delete script
        POST   /api/scripts/{id}/execute - Queue script for execution

    Templates:
        GET    /api/templates         - List all templates
        GET    /api/templates/{id}    - Get single template
        POST   /api/templates         - Create template
        PUT    /api/templates/{id}    - Update template
        DELETE /api/templates/{id}    - Delete template
        POST   /api/templates/{id}/render  - Render template with params
        POST   /api/templates/{id}/preview - Preview render without validation
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from cardlink.scripts import (
    APDUCommand,
    LoadError,
    RenderError,
    Script,
    ScriptManager,
    ScriptNotFoundError,
    Template,
    TemplateNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class ScriptsAPI:
    """REST API handler for script management.

    Provides CRUD operations for scripts and templates, plus template
    rendering and script execution capabilities.

    Example:
        >>> api = ScriptsAPI()
        >>> api.load_default_scripts("examples/scripts")
        >>> response, status = api.handle_request("GET", "/api/scripts", {}, None)
    """

    def __init__(
        self,
        scripts_dir: Optional[Path] = None,
        script_manager: Optional[ScriptManager] = None,
    ) -> None:
        """Initialize Scripts API.

        Args:
            scripts_dir: Directory to load scripts from on startup.
            script_manager: Optional pre-configured ScriptManager instance.
        """
        self._manager = script_manager or ScriptManager()
        self._scripts_dir = scripts_dir
        self._execute_callback: Optional[Callable[[str, List[bytes]], None]] = None

        # Load default scripts if directory provided
        if scripts_dir and scripts_dir.exists():
            try:
                self._manager.load_from_directory(scripts_dir)
                logger.info("Loaded scripts from %s", scripts_dir)
            except LoadError as e:
                logger.warning("Failed to load scripts from %s: %s", scripts_dir, e)

    @property
    def manager(self) -> ScriptManager:
        """Get the underlying ScriptManager."""
        return self._manager

    def set_execute_callback(
        self, callback: Callable[[str, List[bytes]], None]
    ) -> None:
        """Set callback for script execution.

        The callback receives (session_id, commands) where commands is a list
        of C-APDU bytes to queue for execution.

        Args:
            callback: Function to call when executing scripts.
        """
        self._execute_callback = callback

    def handle_request(
        self,
        method: str,
        path: str,
        query_params: Dict[str, str],
        body: Optional[str],
    ) -> Tuple[Any, int]:
        """Route and handle API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: Request path (e.g., "/api/scripts/select-isd").
            query_params: Query string parameters.
            body: Request body (JSON string or None).

        Returns:
            Tuple of (response_data, status_code).
        """
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        # Parse path
        parts = path.rstrip("/").split("/")

        # /api/scripts endpoints
        if len(parts) >= 3 and parts[2] == "scripts":
            return self._handle_scripts(method, parts[3:], query_params, data)

        # /api/templates endpoints
        if len(parts) >= 3 and parts[2] == "templates":
            return self._handle_templates(method, parts[3:], query_params, data)

        return {"error": "Not found"}, 404

    def _handle_scripts(
        self,
        method: str,
        path_parts: List[str],
        query_params: Dict[str, str],
        data: Dict[str, Any],
    ) -> Tuple[Any, int]:
        """Handle /api/scripts/* endpoints.

        Args:
            method: HTTP method.
            path_parts: Path parts after /api/scripts/.
            query_params: Query parameters.
            data: Request body data.

        Returns:
            Tuple of (response_data, status_code).
        """
        # GET /api/scripts - List all scripts
        if method == "GET" and len(path_parts) == 0:
            return self._list_scripts(query_params), 200

        # POST /api/scripts - Create script
        if method == "POST" and len(path_parts) == 0:
            return self._create_script(data)

        # GET/PUT/DELETE /api/scripts/{id}
        if len(path_parts) == 1:
            script_id = path_parts[0]

            if method == "GET":
                return self._get_script(script_id)

            if method == "PUT":
                return self._update_script(script_id, data)

            if method == "DELETE":
                return self._delete_script(script_id)

        # POST /api/scripts/{id}/execute
        if len(path_parts) == 2 and path_parts[1] == "execute":
            script_id = path_parts[0]
            return self._execute_script(script_id, data)

        return {"error": "Not found"}, 404

    def _handle_templates(
        self,
        method: str,
        path_parts: List[str],
        query_params: Dict[str, str],
        data: Dict[str, Any],
    ) -> Tuple[Any, int]:
        """Handle /api/templates/* endpoints.

        Args:
            method: HTTP method.
            path_parts: Path parts after /api/templates/.
            query_params: Query parameters.
            data: Request body data.

        Returns:
            Tuple of (response_data, status_code).
        """
        # GET /api/templates - List all templates
        if method == "GET" and len(path_parts) == 0:
            return self._list_templates(query_params), 200

        # POST /api/templates - Create template
        if method == "POST" and len(path_parts) == 0:
            return self._create_template(data)

        # GET/PUT/DELETE /api/templates/{id}
        if len(path_parts) == 1:
            template_id = path_parts[0]

            if method == "GET":
                return self._get_template(template_id)

            if method == "PUT":
                return self._update_template(template_id, data)

            if method == "DELETE":
                return self._delete_template(template_id)

        # POST /api/templates/{id}/render
        if len(path_parts) == 2 and path_parts[1] == "render":
            template_id = path_parts[0]
            return self._render_template(template_id, data)

        # POST /api/templates/{id}/preview
        if len(path_parts) == 2 and path_parts[1] == "preview":
            template_id = path_parts[0]
            return self._preview_template(template_id, data)

        return {"error": "Not found"}, 404

    # =========================================================================
    # Script CRUD Operations
    # =========================================================================

    def _list_scripts(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """List all scripts with optional filtering.

        Args:
            query_params: Filter parameters (tag, search).

        Returns:
            Dictionary with scripts list.
        """
        tag = query_params.get("tag")
        search = query_params.get("search")

        scripts = self._manager.list_scripts(tag=tag, search=search)
        return {"scripts": [s.to_dict() for s in scripts]}

    def _get_script(self, script_id: str) -> Tuple[Dict[str, Any], int]:
        """Get a single script by ID.

        Args:
            script_id: Script identifier.

        Returns:
            Tuple of (script_dict, status_code).
        """
        try:
            script = self._manager.get_script(script_id)
            return script.to_dict(), 200
        except ScriptNotFoundError:
            return {"error": f"Script not found: {script_id}"}, 404

    def _create_script(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Create a new script.

        Args:
            data: Script data from request body.

        Returns:
            Tuple of (created_script_dict, status_code).
        """
        # Validate required fields
        script_id = data.get("id")
        name = data.get("name")
        commands_data = data.get("commands", [])

        if not script_id:
            return {"error": "Script ID is required"}, 400
        if not name:
            return {"error": "Script name is required"}, 400
        if not commands_data:
            return {"error": "At least one command is required"}, 400

        # Parse commands
        try:
            commands = self._parse_commands(commands_data)
        except ValueError as e:
            return {"error": f"Invalid command: {e}"}, 400

        # Create script
        try:
            script = self._manager.create_script(
                script_id=script_id,
                name=name,
                commands=commands,
                description=data.get("description"),
                tags=data.get("tags", []),
            )
            logger.info("Created script: %s", script_id)
            return script.to_dict(), 201
        except ValidationError as e:
            return {"error": str(e)}, 400
        except ValueError as e:
            return {"error": str(e)}, 409  # Conflict - ID already exists

    def _update_script(
        self, script_id: str, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """Update an existing script.

        Args:
            script_id: Script identifier.
            data: Updated script data.

        Returns:
            Tuple of (updated_script_dict, status_code).
        """
        # Parse commands if provided
        commands = None
        if "commands" in data:
            try:
                commands = self._parse_commands(data["commands"])
            except ValueError as e:
                return {"error": f"Invalid command: {e}"}, 400

        try:
            script = self._manager.update_script(
                script_id=script_id,
                name=data.get("name"),
                commands=commands,
                description=data.get("description"),
                tags=data.get("tags"),
            )
            logger.info("Updated script: %s", script_id)
            return script.to_dict(), 200
        except ScriptNotFoundError:
            return {"error": f"Script not found: {script_id}"}, 404
        except ValidationError as e:
            return {"error": str(e)}, 400

    def _delete_script(self, script_id: str) -> Tuple[Dict[str, Any], int]:
        """Delete a script.

        Args:
            script_id: Script identifier.

        Returns:
            Tuple of (success_dict, status_code).
        """
        try:
            self._manager.delete_script(script_id)
            logger.info("Deleted script: %s", script_id)
            return {"success": True, "id": script_id}, 200
        except ScriptNotFoundError:
            return {"error": f"Script not found: {script_id}"}, 404

    def _execute_script(
        self, script_id: str, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """Execute a script by queuing its commands.

        Args:
            script_id: Script identifier.
            data: Execution parameters (session_id).

        Returns:
            Tuple of (result_dict, status_code).
        """
        session_id = data.get("sessionId") or data.get("session_id")
        if not session_id:
            return {"error": "sessionId is required"}, 400

        if not self._execute_callback:
            return {"error": "Script execution not configured"}, 503

        try:
            script = self._manager.get_script(script_id)
            commands = [cmd.to_bytes() for cmd in script.commands]

            # Queue commands via callback
            self._execute_callback(session_id, commands)

            logger.info(
                "Queued %d commands from script %s for session %s",
                len(commands), script_id, session_id
            )
            return {
                "success": True,
                "scriptId": script_id,
                "sessionId": session_id,
                "commandCount": len(commands),
            }, 200
        except ScriptNotFoundError:
            return {"error": f"Script not found: {script_id}"}, 404

    # =========================================================================
    # Template CRUD Operations
    # =========================================================================

    def _list_templates(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """List all templates with optional filtering.

        Args:
            query_params: Filter parameters (tag, search).

        Returns:
            Dictionary with templates list.
        """
        tag = query_params.get("tag")
        search = query_params.get("search")

        templates = self._manager.list_templates(tag=tag, search=search)
        return {"templates": [t.to_dict() for t in templates]}

    def _get_template(self, template_id: str) -> Tuple[Dict[str, Any], int]:
        """Get a single template by ID.

        Args:
            template_id: Template identifier.

        Returns:
            Tuple of (template_dict, status_code).
        """
        try:
            template = self._manager.get_template(template_id)
            return template.to_dict(), 200
        except TemplateNotFoundError:
            return {"error": f"Template not found: {template_id}"}, 404

    def _create_template(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Create a new template.

        Args:
            data: Template data from request body.

        Returns:
            Tuple of (created_template_dict, status_code).
        """
        # Validate required fields
        template_id = data.get("id")
        name = data.get("name")
        commands_data = data.get("commands", [])

        if not template_id:
            return {"error": "Template ID is required"}, 400
        if not name:
            return {"error": "Template name is required"}, 400
        if not commands_data:
            return {"error": "At least one command is required"}, 400

        # Parse commands
        try:
            commands = self._parse_commands(commands_data)
        except ValueError as e:
            return {"error": f"Invalid command: {e}"}, 400

        # Parse parameters
        parameters = self._parse_parameters(data.get("parameters", {}))

        # Create template
        try:
            template = self._manager.create_template(
                template_id=template_id,
                name=name,
                commands=commands,
                parameters=parameters,
                description=data.get("description"),
                tags=data.get("tags", []),
            )
            logger.info("Created template: %s", template_id)
            return template.to_dict(), 201
        except ValidationError as e:
            return {"error": str(e)}, 400
        except ValueError as e:
            return {"error": str(e)}, 409  # Conflict - ID already exists

    def _update_template(
        self, template_id: str, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """Update an existing template.

        Args:
            template_id: Template identifier.
            data: Updated template data.

        Returns:
            Tuple of (updated_template_dict, status_code).
        """
        # Parse commands if provided
        commands = None
        if "commands" in data:
            try:
                commands = self._parse_commands(data["commands"])
            except ValueError as e:
                return {"error": f"Invalid command: {e}"}, 400

        # Parse parameters if provided
        parameters = None
        if "parameters" in data:
            parameters = self._parse_parameters(data["parameters"])

        try:
            template = self._manager.update_template(
                template_id=template_id,
                name=data.get("name"),
                commands=commands,
                parameters=parameters,
                description=data.get("description"),
                tags=data.get("tags"),
            )
            logger.info("Updated template: %s", template_id)
            return template.to_dict(), 200
        except TemplateNotFoundError:
            return {"error": f"Template not found: {template_id}"}, 404
        except ValidationError as e:
            return {"error": str(e)}, 400

    def _delete_template(self, template_id: str) -> Tuple[Dict[str, Any], int]:
        """Delete a template.

        Args:
            template_id: Template identifier.

        Returns:
            Tuple of (success_dict, status_code).
        """
        try:
            self._manager.delete_template(template_id)
            logger.info("Deleted template: %s", template_id)
            return {"success": True, "id": template_id}, 200
        except TemplateNotFoundError:
            return {"error": f"Template not found: {template_id}"}, 404

    def _render_template(
        self, template_id: str, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """Render a template with parameters, optionally executing it.

        Args:
            template_id: Template identifier.
            data: Render parameters including:
                - params/parameters: Template parameter values
                - execute: If True, execute the rendered commands
                - sessionId/session_id: Session to execute commands for

        Returns:
            Tuple of (rendered_commands_dict, status_code).
        """
        params = data.get("params") or data.get("parameters") or {}
        execute = data.get("execute", False)
        session_id = data.get("sessionId") or data.get("session_id")

        try:
            commands = self._manager.render_template(template_id, params)
            command_dicts = [
                {
                    "hex": cmd.hex,
                    "name": cmd.name,
                    "description": cmd.description,
                }
                for cmd in commands
            ]

            # If execute flag is set, queue the commands
            if execute:
                if not session_id:
                    return {"error": "sessionId is required for execution"}, 400

                if not self._execute_callback:
                    return {"error": "Script execution not configured"}, 503

                # Convert rendered commands to bytes for execution
                command_bytes = [cmd.to_bytes() for cmd in commands]
                self._execute_callback(session_id, command_bytes)

                logger.info(
                    "Queued %d commands from template %s for session %s",
                    len(commands), template_id, session_id
                )

                return {
                    "success": True,
                    "templateId": template_id,
                    "sessionId": session_id,
                    "commandCount": len(commands),
                    "commands": command_dicts,
                    "executed": True,
                }, 200

            return {
                "success": True,
                "templateId": template_id,
                "commands": command_dicts,
            }, 200
        except TemplateNotFoundError:
            return {"error": f"Template not found: {template_id}"}, 404
        except RenderError as e:
            return {"error": f"Render failed: {e}"}, 400
        except ValidationError as e:
            return {"error": f"Validation failed: {e}"}, 400

    def _preview_template(
        self, template_id: str, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """Preview template render without strict validation.

        Args:
            template_id: Template identifier.
            data: Preview parameters.

        Returns:
            Tuple of (preview_dict, status_code).
        """
        params = data.get("params") or data.get("parameters") or {}

        try:
            template = self._manager.get_template(template_id)

            # Import preview function
            from cardlink.scripts.renderer import preview_render

            preview = preview_render(template, params)
            # Return as 'commands' for frontend compatibility
            return {
                "templateId": template_id,
                "commands": preview,
            }, 200
        except TemplateNotFoundError:
            return {"error": f"Template not found: {template_id}"}, 404

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_commands(self, commands_data: List[Any]) -> List[APDUCommand]:
        """Parse command list from request data.

        Args:
            commands_data: List of command dicts or hex strings.

        Returns:
            List of APDUCommand objects.

        Raises:
            ValueError: If command format is invalid.
        """
        commands = []
        for cmd in commands_data:
            if isinstance(cmd, str):
                # Simple hex string
                commands.append(APDUCommand(hex=cmd))
            elif isinstance(cmd, dict):
                # Full command object
                hex_value = cmd.get("hex")
                if not hex_value:
                    raise ValueError("Command missing 'hex' field")
                commands.append(APDUCommand(
                    hex=hex_value,
                    name=cmd.get("name"),
                    description=cmd.get("description"),
                ))
            else:
                raise ValueError(f"Invalid command format: {type(cmd)}")
        return commands

    def _parse_parameters(
        self, params_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse parameter definitions from request data.

        Args:
            params_data: Parameter definitions dict.

        Returns:
            Parsed parameter definitions.
        """
        from cardlink.scripts.models import ParameterDef, ParameterType

        parameters = {}
        for name, param_def in params_data.items():
            if isinstance(param_def, dict):
                # Parse type
                type_str = param_def.get("type", "hex").upper()
                try:
                    param_type = ParameterType[type_str]
                except KeyError:
                    param_type = ParameterType.HEX

                parameters[name] = ParameterDef(
                    name=name,
                    type=param_type,
                    description=param_def.get("description"),
                    default=param_def.get("default"),
                    min_length=param_def.get("min_length"),
                    max_length=param_def.get("max_length"),
                    required=param_def.get("required", param_def.get("default") is None),
                )
            else:
                # Simple parameter with just a default value
                parameters[name] = ParameterDef(name=name, default=str(param_def))

        return parameters

    def load_scripts_from_directory(self, directory: Path) -> int:
        """Load scripts from a directory.

        Args:
            directory: Directory path.

        Returns:
            Number of items loaded.
        """
        scripts_before = len(self._manager.list_scripts())
        templates_before = len(self._manager.list_templates())

        self._manager.load_from_directory(directory)

        scripts_after = len(self._manager.list_scripts())
        templates_after = len(self._manager.list_templates())

        return (scripts_after - scripts_before) + (templates_after - templates_before)

    def save_to_file(self, filepath: Path) -> None:
        """Save all scripts and templates to a YAML file.

        Args:
            filepath: Output file path.
        """
        self._manager.save_to_file(filepath)
