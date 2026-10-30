"""
Dockerfile Generator
Generates customized, production-ready Dockerfiles and .dockerignore files using Jinja2 templates.
Supports FastAPI, Flask, Streamlit, and Python CLI ML projects.
"""

import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from ..config import settings
from ..models.deployment_request import DeploymentRequest
from ..models.deployment_artifact import DeploymentArtifact

logger = logging.getLogger("deployment.dockerfile_generator")

DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class DockerfileGenerator:
    """
    Renders parameterized Dockerfiles and .dockerignore files from templates
    based on framework, python version, entry point, requirements, and project root.
    """

    FRAMEWORK_TEMPLATES = {
        "fastapi": "fastapi.Dockerfile.j2",
        "flask": "flask.Dockerfile.j2",
        "cli": "cli.Dockerfile.j2",
        "python_cli": "cli.Dockerfile.j2",
        "cli_ml": "cli.Dockerfile.j2",
        "streamlit": "streamlit.Dockerfile.j2",
    }

    DEFAULT_PORTS = {
        "fastapi": 8000,
        "flask": 5000,
        "streamlit": 8501,
        "cli": 8000,
    }

    DOCKERIGNORE_CONTENT = """__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
.git
.gitignore
.dockerignore
uploads/
artifacts/
*.log
.pytest_cache/
.coverage
"""

    def __init__(self, templates_dir: Optional[Union[str, Path]] = None):
        """Initialize the generator with a templates directory."""
        self.templates_dir = Path(templates_dir) if templates_dir else DEFAULT_TEMPLATES_DIR
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True, exist_ok=True)

        if Environment and FileSystemLoader:
            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=select_autoescape([]),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self.env = None

    def _format_app_module(self, entry_point: str, default_app_name: str = "app") -> str:
        """
        Convert entry_point script path (e.g. 'main.py' or 'src/server.py')
        into a module:app specification (e.g. 'main:app' or 'src.server:app').
        """
        clean = entry_point.replace("\\", "/").strip()
        if ":" in clean:
            return clean

        if clean.endswith(".py"):
            module_path = clean[:-3].replace("/", ".")
            return f"{module_path}:{default_app_name}"

        return f"{clean}:{default_app_name}"

    def get_template_filename(self, framework: str, entry_point_type: Optional[str] = None) -> str:
        """Resolve framework name and entry_point_type to template file."""
        if entry_point_type in ("cli_script", "cli", "python_cli", "inference_function"):
            return self.FRAMEWORK_TEMPLATES["cli"]

        key = framework.lower().strip()
        if "cli" in key:
            return self.FRAMEWORK_TEMPLATES["cli"]
        if "flask" in key:
            return self.FRAMEWORK_TEMPLATES["flask"]
        if "streamlit" in key:
            return self.FRAMEWORK_TEMPLATES["streamlit"]
        if key in self.FRAMEWORK_TEMPLATES:
            return self.FRAMEWORK_TEMPLATES[key]

        return self.FRAMEWORK_TEMPLATES["fastapi"]

    def ensure_dockerignore(self, directory: Path) -> Path:
        """Create a default .dockerignore file in the target directory if missing."""
        dockerignore_path = directory / ".dockerignore"
        if not dockerignore_path.exists():
            try:
                dockerignore_path.write_text(self.DOCKERIGNORE_CONTENT, encoding="utf-8")
                logger.info("[Dockerfile Generation] Created .dockerignore at %s", dockerignore_path)
            except Exception as e:
                logger.warning("[Dockerfile Generation] Failed to create .dockerignore at %s: %s", dockerignore_path, e)
        return dockerignore_path

    def generate(self,
                 framework: Union[str, Any],
                 python_version: str = "3.11",
                 requirements_file: str = "requirements.txt",
                 entry_point: str = "main.py",
                 port: Optional[int] = None,
                 health_endpoint: str = "/health",
                 entry_point_type: Optional[str] = None,
                 startup_command: Optional[str] = None) -> str:
        """Render Dockerfile string from template."""
        import json, shlex
        if isinstance(framework, DeploymentArtifact) or hasattr(framework, "project_root"):
            artifact = framework
            framework = getattr(artifact, "framework", "cli") or "cli"
            python_version = getattr(artifact, "python_version", python_version) or python_version
            requirements_file = getattr(artifact, "requirements_file", requirements_file) or requirements_file
            entry_point = getattr(artifact, "entry_point", entry_point) or entry_point
            entry_point_type = getattr(artifact, "entry_point_type", entry_point_type) or entry_point_type
            startup_command = getattr(artifact, "startup_command", startup_command) or startup_command
        framework_norm = framework.lower().strip()
        template_file = self.get_template_filename(framework_norm, entry_point_type=entry_point_type)

        assigned_port = port or self.DEFAULT_PORTS.get(framework_norm, 8000)
        app_module = self._format_app_module(entry_point)

        # Determine container startup instruction dynamically
        if startup_command:
            tokens = shlex.split(startup_command)
            cmd = f"CMD {json.dumps(tokens)}"
        elif entry_point_type in ("cli_script", "cli", "python_cli", "inference_function") or "cli" in framework_norm:
            cmd = f'CMD ["python", "{entry_point}"]'
        elif entry_point_type == "flask":
            cmd = f'CMD ["python", "{entry_point}"]'
        elif framework_norm == "flask":
            cmd = f'CMD ["gunicorn", "--bind", "0.0.0.0:{assigned_port}", "{app_module}"]'
        elif framework_norm == "streamlit":
            cmd = f'CMD ["streamlit", "run", "{entry_point}", "--server.port={assigned_port}", "--server.address=0.0.0.0"]'
        else:
            cmd = f'CMD ["uvicorn", "{app_module}", "--host", "0.0.0.0", "--port", "{assigned_port}"]'

        context: Dict[str, Any] = {
            "framework": framework_norm,
            "entry_point_type": entry_point_type,
            "python_version": python_version or "3.11",
            "requirements_file": Path(requirements_file).name if requirements_file else "requirements.txt",
            "entry_point": entry_point or "main.py",
            "app_module": app_module,
            "port": assigned_port,
            "health_endpoint": health_endpoint or "/health",
            "cmd": cmd,
            "startup_command": startup_command,
        }

        # Render using Jinja2 if available
        if self.env:
            try:
                template = self.env.get_template(template_file)
                return template.render(**context)
            except Exception as exc:
                logger.warning("[Dockerfile Generation] Jinja2 template rendering failed: %s; falling back to direct load.", exc)

        # Fallback reading template file directly and doing string replacement
        tmpl_path = self.templates_dir / template_file
        if tmpl_path.exists():
            raw = tmpl_path.read_text(encoding="utf-8")
            for k, v in context.items():
                raw = raw.replace(f"{{{{ {k} }}}}", str(v))
            return raw

        # In-code ultimate fallback
        return self._generate_fallback(context)

    def _generate_fallback(self, ctx: Dict[str, Any]) -> str:
        """Emergency string generator if template files are missing."""
        py_ver = ctx["python_version"]
        req = ctx["requirements_file"]
        port = ctx["port"]
        ep = ctx["entry_point"]
        app_mod = ctx["app_module"]
        fw = ctx["framework"]
        ep_type = ctx.get("entry_point_type")

        if ctx.get("cmd"):
            cmd = ctx["cmd"]
        elif ep_type in ("cli_script", "cli", "python_cli", "inference_function") or fw == "cli":
            cmd = f'CMD ["python", "{ep}"]'
        elif ep_type == "flask":
            cmd = f'CMD ["python", "{ep}"]'
        elif fw == "flask":
            cmd = f'CMD ["gunicorn", "--bind", "0.0.0.0:{port}", "{app_mod}"]'
        elif fw == "streamlit":
            cmd = f'CMD ["streamlit", "run", "{ep}", "--server.port={port}", "--server.address=0.0.0.0"]'
        else:
            cmd = f'CMD ["uvicorn", "{app_mod}", "--host", "0.0.0.0", "--port", "{port}"]'

        is_cli_mode = ep_type in ("cli_script", "cli", "python_cli") or fw == "cli"
        expose = f"EXPOSE {port}\n" if not is_cli_mode else ""

        return f"""# Auto-generated by ModelForge Deployment Backend
FROM python:{py_ver}-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY {req} .
RUN pip install --no-cache-dir -r {req}

COPY . .

{expose}
{cmd}
"""

    def generate_dockerfile(self,
                            framework: str,
                            python_version: str,
                            requirements_file: str,
                            entry_point: str,
                            working_directory: Union[str, Path],
                            port: Optional[int] = None,
                            health_endpoint: str = "/health",
                            overwrite: bool = False,
                            entry_point_type: Optional[str] = None,
                            startup_command: Optional[str] = None) -> Path:
        """Generate and save a Dockerfile directly inside the specified working directory."""
        work_dir = Path(working_directory).resolve()
        target_file = work_dir / "Dockerfile"

        self.ensure_dockerignore(work_dir)

        return self.generate_to_file(
            target_path=target_file,
            framework=framework,
            python_version=python_version,
            requirements_file=requirements_file,
            entry_point=entry_point,
            port=port,
            health_endpoint=health_endpoint,
            overwrite=overwrite,
            entry_point_type=entry_point_type,
            startup_command=startup_command
        )

    def generate_to_file(self,
                         target_path: Union[str, Path],
                         framework: str,
                         python_version: str = "3.11",
                         requirements_file: str = "requirements.txt",
                         entry_point: str = "main.py",
                         port: Optional[int] = None,
                         health_endpoint: str = "/health",
                         overwrite: bool = False,
                         entry_point_type: Optional[str] = None,
                         startup_command: Optional[str] = None) -> Path:
        """Generate and write Dockerfile to destination."""
        p = Path(target_path).resolve()
        if p.is_dir():
            target_file = p / "Dockerfile"
            self.ensure_dockerignore(p)
        else:
            target_file = p
            self.ensure_dockerignore(p.parent)

        if target_file.exists() and not overwrite:
            logger.info("[Dockerfile Generation] Dockerfile already exists at %s; skipping generation.", target_file)
            return target_file

        dockerfile_content = self.generate(
            framework=framework,
            python_version=python_version,
            requirements_file=requirements_file,
            entry_point=entry_point,
            port=port,
            health_endpoint=health_endpoint,
            entry_point_type=entry_point_type,
            startup_command=startup_command
        )

        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(dockerfile_content, encoding="utf-8")
        logger.info("[Dockerfile Generation] Successfully generated Dockerfile at: %s", target_file)
        return target_file

    def generate_for_artifact(self, artifact: DeploymentArtifact, overwrite: bool = False) -> Path:
        """
        Generate Dockerfile and .dockerignore directly for a DeploymentArtifact.
        Updates artifact.has_dockerfile and artifact.dockerfile_path.
        """
        self.ensure_dockerignore(artifact.project_root)
        dockerfile_path = artifact.project_root / "Dockerfile"

        if dockerfile_path.exists() and not overwrite:
            logger.info("[Dockerfile Generation] Existing Dockerfile preserved at %s", dockerfile_path)
            artifact.has_dockerfile = True
            artifact.dockerfile_path = dockerfile_path
            return dockerfile_path

        logger.info(
            "[Dockerfile Generation] Generating Dockerfile for project '%s' (Framework: %s, Python: %s, EntryPoint: %s, EntryPointType: %s, StartupCommand: %s)",
            artifact.project_id, artifact.framework, artifact.python_version, artifact.entry_point, artifact.entry_point_type, artifact.startup_command
        )

        target = self.generate_to_file(
            target_path=dockerfile_path,
            framework=artifact.framework,
            python_version=artifact.python_version,
            requirements_file=artifact.requirements_file,
            entry_point=artifact.entry_point,
            overwrite=overwrite,
            entry_point_type=artifact.entry_point_type,
            startup_command=artifact.startup_command
        )

        artifact.has_dockerfile = True
        artifact.dockerfile_path = target
        return target

    def generate_for_request(self, request: DeploymentRequest, overwrite: bool = False) -> Path:
        """Convenience method to generate Dockerfile directly from a DeploymentRequest."""
        workspace_p = Path(request.working_directory).resolve()
        self.ensure_dockerignore(workspace_p)
        return self.generate_to_file(
            target_path=workspace_p / "Dockerfile",
            framework=request.framework,
            python_version=request.python_version,
            requirements_file=request.requirements_file,
            entry_point=request.entry_point,
            port=request.target_port,
            health_endpoint=request.health_endpoint,
            overwrite=overwrite,
            entry_point_type=request.entry_point_type,
            startup_command=request.startup_command
        )
