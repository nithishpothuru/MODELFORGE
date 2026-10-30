"""
Nginx Manager
Generates and manages Nginx reverse proxy configurations, upstreams, location blocks, and virtual hosts.
Ensures public URLs route through Nginx reverse proxy instead of exposing container ports directly.
Supports localhost and custom domains (future-ready).
Uses Jinja2 templates for maintainable, template-driven configuration generation.
"""

import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound
except ImportError:
    Environment = None
    FileSystemLoader = None
    TemplateNotFound = None

from ..config import settings

logger = logging.getLogger(__name__)

DEFAULT_NGINX_CONF_DIR = settings.nginx_conf_dir
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class NginxManager:
    """
    Manages reverse proxy routing blocks, file persistence, reload signals,
    and public URL generation for deployed services using Jinja2 templates.
    """

    def __init__(self,
                 conf_dir: Optional[Path] = None,
                 templates_dir: Optional[Path] = None,
                 base_domain: Optional[str] = None,
                 public_base_url: Optional[str] = None):
        self.conf_dir = Path(conf_dir) if conf_dir else DEFAULT_NGINX_CONF_DIR
        self.conf_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
        self.base_domain = base_domain or settings.nginx_base_domain or "localhost"
        self.public_base_url = public_base_url or settings.public_base_url

        if Environment and self.templates_dir.exists():
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self._jinja_env = None

    def generate_upstream(self, deployment_id: str, host_port: int) -> str:
        """
        Generate Nginx upstream configuration block.

        Parameters
        ----------
        deployment_id : str
            Unique identifier of deployment.
        host_port : int
            Internal host TCP port container is listening on.

        Returns
        -------
        str
            Nginx upstream block string.
        """
        upstream_name = f"upstream_modelforge_{deployment_id}"
        if self._jinja_env:
            try:
                template = self._jinja_env.get_template("nginx_upstream.conf.j2")
                return template.render(upstream_name=upstream_name, host_port=host_port)
            except Exception as e:
                logger.debug("Falling back to inline upstream template: %s", e)

        return (
            f"upstream {upstream_name} {{\n"
            f"    server 127.0.0.1:{host_port};\n"
            f"    keepalive 32;\n"
            f"}}"
        )

    def generate_location(self,
                          upstream_name: str,
                          path_prefix: Optional[str] = None,
                          enable_websocket: bool = True) -> str:
        """
        Generate Nginx location routing block.

        Parameters
        ----------
        upstream_name : str
            Name of the upstream group to proxy to.
        path_prefix : Optional[str]
            Optional URL path prefix (e.g. 'deployments/{deployment_id}').
        enable_websocket : bool
            Enable WebSocket upgrade headers.

        Returns
        -------
        str
            Nginx location block string.
        """
        location_path = f"/{path_prefix.strip('/')}/" if path_prefix else "/"
        if self._jinja_env:
            try:
                template = self._jinja_env.get_template("nginx_location.conf.j2")
                return template.render(
                    upstream_name=upstream_name,
                    location_path=location_path,
                    enable_websocket=enable_websocket
                )
            except Exception as e:
                logger.debug("Falling back to inline location template: %s", e)

        ws_headers = """
    # WebSocket support
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";""" if enable_websocket else ""

        return (
            f"location {location_path} {{\n"
            f"    proxy_pass http://{upstream_name};\n"
            f"    proxy_set_header Host $host;\n"
            f"    proxy_set_header X-Real-IP $remote_addr;\n"
            f"    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
            f"    proxy_set_header X-Forwarded-Proto $scheme;\n"
            f"    proxy_read_timeout 300;\n"
            f"    proxy_connect_timeout 300;{ws_headers}\n"
            f"}}"
        )

    def generate_config(self,
                        deployment_id: str,
                        host_port: int,
                        domain_name: Optional[str] = None,
                        custom_domain: Optional[str] = None,
                        path_prefix: Optional[str] = None,
                        enable_websocket: bool = True,
                        listen_port: int = 80,
                        client_max_body_size: str = "100M") -> str:
        """
        Generate full Nginx configuration string for a deployed service.
        Supports localhost, base domain subdomains, and future-ready custom domains.

        Parameters
        ----------
        deployment_id : str
            Unique identifier of deployment.
        host_port : int
            Internal host TCP port container is listening on.
        domain_name : Optional[str]
            Optional domain or subdomain name.
        custom_domain : Optional[str]
            Optional custom domain (e.g. 'api.example.com'). Takes precedence over domain_name.
        path_prefix : Optional[str]
            Optional URL path prefix (e.g. 'deployments/{deployment_id}').
        enable_websocket : bool
            Enable WebSocket upgrade headers.
        listen_port : int
            HTTP listen port (defaults to 80).
        client_max_body_size : str
            Max client upload size (defaults to '100M').

        Returns
        -------
        str
            Complete Nginx configuration content.
        """
        upstream_name = f"upstream_modelforge_{deployment_id}"

        # Resolve server_name: custom_domain -> domain_name -> subdomain / localhost
        effective_domain = custom_domain or domain_name
        if effective_domain:
            server_name = effective_domain
        elif self.base_domain == "localhost":
            server_name = f"localhost {deployment_id}.localhost"
        else:
            server_name = f"{deployment_id}.{self.base_domain}"

        location_path = f"/{path_prefix.strip('/')}/" if path_prefix else "/"

        if self._jinja_env:
            try:
                template = self._jinja_env.get_template("nginx_deployment.conf.j2")
                return template.render(
                    deployment_id=deployment_id,
                    upstream_name=upstream_name,
                    host_port=host_port,
                    server_name=server_name,
                    listen_port=listen_port,
                    client_max_body_size=client_max_body_size,
                    location_path=location_path,
                    enable_websocket=enable_websocket
                )
            except Exception as e:
                logger.debug("Falling back to inline full nginx template: %s", e)

        ws_headers = """
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        """ if enable_websocket else ""

        return f"""# Nginx configuration for ModelForge deployment: {deployment_id}
upstream {upstream_name} {{
    server 127.0.0.1:{host_port};
    keepalive 32;
}}

server {{
    listen {listen_port};
    server_name {server_name};

    client_max_body_size {client_max_body_size};

    location {location_path} {{
        proxy_pass http://{upstream_name};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
{ws_headers}
    }}
}}
"""

    def create_routing(self,
                       deployment_id: str,
                       host_port: int,
                       domain_name: Optional[str] = None,
                       custom_domain: Optional[str] = None,
                       path_prefix: Optional[str] = None,
                       enable_websocket: bool = True,
                       trigger_reload: bool = True) -> Path:
        """
        Generate Nginx config, write it to conf.d, and optionally reload Nginx.

        Returns
        -------
        Path
            Path to saved configuration file.
        """
        conf_content = self.generate_config(
            deployment_id=deployment_id,
            host_port=host_port,
            domain_name=domain_name,
            custom_domain=custom_domain,
            path_prefix=path_prefix,
            enable_websocket=enable_websocket
        )

        conf_file = self.conf_dir / f"{deployment_id}.conf"
        conf_file.write_text(conf_content, encoding="utf-8")
        logger.info("Saved Nginx routing config to: %s", conf_file)

        if trigger_reload:
            self.reload_nginx()

        return conf_file

    def apply_config(self, deployment_id: str, host_port: int, domain_name: Optional[str] = None) -> Path:
        """Alias for create_routing."""
        return self.create_routing(deployment_id=deployment_id, host_port=host_port, domain_name=domain_name)

    def delete_routes(self, deployment_id: str, trigger_reload: bool = True) -> bool:
        """
        Delete Nginx routing config for a deployment and reload server.
        """
        conf_file = self.conf_dir / f"{deployment_id}.conf"
        removed = False
        if conf_file.exists():
            try:
                conf_file.unlink()
                logger.info("Deleted Nginx route: %s", conf_file)
                removed = True
            except OSError as exc:
                logger.warning("Failed to delete Nginx config %s: %s", conf_file, exc)
                return False

        if removed and trigger_reload:
            self.reload_nginx()

        return removed

    def remove_config(self, deployment_id: str) -> bool:
        """Alias for delete_routes."""
        return self.delete_routes(deployment_id)

    def reload_nginx(self) -> bool:
        """
        Verify syntax and signal local Nginx process to reload configuration.
        """
        nginx_bin = shutil.which("nginx")
        if not nginx_bin:
            logger.debug("Nginx executable not found in PATH; skipping live reload.")
            return False

        try:
            # Test configuration syntax first
            test_res = subprocess.run([nginx_bin, "-t"], capture_output=True, text=True, timeout=5)
            if test_res.returncode != 0:
                logger.error("Nginx configuration test failed: %s", test_res.stderr)
                return False

            # Reload
            reload_res = subprocess.run([nginx_bin, "-s", "reload"], capture_output=True, text=True, timeout=5)
            if reload_res.returncode == 0:
                logger.info("Successfully reloaded Nginx.")
                return True
            else:
                logger.warning("Nginx reload returned code %d: %s", reload_res.returncode, reload_res.stderr)
                return False
        except Exception as exc:
            logger.warning("Error signaling Nginx reload: %s", exc)
            return False

    def get_public_url(self,
                       deployment_id: str,
                       domain_name: Optional[str] = None,
                       custom_domain: Optional[str] = None,
                       path_prefix: Optional[str] = None) -> str:
        """
        Construct public URL routing through reverse proxy rather than raw host port.
        Supports localhost, base domain subdomains, and future-ready custom domains.
        """
        scheme = settings.public_url_scheme or "http"
        effective_domain = custom_domain or domain_name

        if self.public_base_url and not effective_domain:
            base = self.public_base_url.rstrip("/")
            path = path_prefix.strip("/") if path_prefix else f"deployments/{deployment_id}"
            return f"{base}/{path}"

        if effective_domain:
            path = f"/{path_prefix.strip('/')}" if path_prefix else ""
            return f"{scheme}://{effective_domain}{path}"

        # Standard virtual host subdomain or path routing
        if self.base_domain == "localhost":
            path = f"/{path_prefix.strip('/')}" if path_prefix else f"/deployments/{deployment_id}"
            return f"{scheme}://localhost{path}"

        return f"{scheme}://{deployment_id}.{self.base_domain}"
