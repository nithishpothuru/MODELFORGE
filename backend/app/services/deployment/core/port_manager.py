"""
Port Manager
Thread-safe port allocator and tracker for host container port assignments.
Prevents duplicate allocations, supports concurrent deployments, and persists active port mappings.
"""

import json
import socket
import threading
import logging
from pathlib import Path
from typing import Set, Dict, Optional, Union

from ..config import settings

logger = logging.getLogger(__name__)

DEFAULT_STATE_FILE = Path(__file__).resolve().parent.parent / "port_mappings.json"


class _ClassOrInstanceMethod:
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        target = instance if instance is not None else owner
        def wrapper(*args, **kwargs):
            return self.func(target, *args, **kwargs)
        return wrapper


class PortManager:
    """
    Manages host port allocation, availability checks, and lifecycle tracking.
    Guarantees thread-safe allocation and persists active mappings to disk.
    """

    _lock = threading.Lock()
    _active_mappings: Dict[int, str] = {}  # port -> deployment_id
    _state_file: Path = DEFAULT_STATE_FILE

    DEFAULT_START_PORT = settings.port_range_start
    DEFAULT_END_PORT = settings.port_range_end

    def __init__(self,
                 start_port: Optional[int] = None,
                 end_port: Optional[int] = None,
                 state_file: Optional[Union[str, Path]] = None,
                 min_port: Optional[int] = None,
                 max_port: Optional[int] = None):
        self.start_port = start_port or min_port or self.DEFAULT_START_PORT
        self.end_port = end_port or max_port or self.DEFAULT_END_PORT
        if state_file:
            self._set_state_file(state_file)
        else:
            self._load_state()

    @classmethod
    def _set_state_file(cls, file_path: Union[str, Path]) -> None:
        """Configure the persistence state file location."""
        with cls._lock:
            cls._state_file = Path(file_path).resolve()
            cls._state_file.parent.mkdir(parents=True, exist_ok=True)
            cls._load_state()

    @classmethod
    def _load_state(cls) -> None:
        """Load persisted port mappings from disk."""
        if cls._state_file.exists() and cls._state_file.is_file():
            try:
                content = cls._state_file.read_text(encoding="utf-8")
                raw = json.loads(content)
                cls._active_mappings = {int(k): str(v) for k, v in raw.items()}
                logger.debug("Loaded %d active port mappings from %s", len(cls._active_mappings), cls._state_file)
            except Exception as exc:
                logger.warning("Failed to load port mappings from %s: %s", cls._state_file, exc)
                cls._active_mappings = {}

    @classmethod
    def _save_state(cls) -> None:
        """Persist current active port mappings to disk."""
        try:
            cls._state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {str(k): v for k, v in cls._active_mappings.items()}
            cls._state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to persist port mappings to %s: %s", cls._state_file, exc)

    @classmethod
    def is_port_available(cls, port: int, host: str = "localhost") -> bool:
        """
        Check if a TCP port is currently open and free to bind on the host.

        Parameters
        ----------
        port : int
            TCP port number.
        host : str
            Host interface address.

        Returns
        -------
        bool
            True if the port is free to use, False otherwise.
        """
        # Step 1: Attempt connect_ex - if 0, another service is actively listening
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex((host, port))
            if result == 0:
                return False

        # Step 2: Attempt binding to confirm the OS permits binding
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("", port))
            return True
        except (OSError, socket.error):
            return False

    @classmethod
    def is_port_allocated(cls, port: int) -> bool:
        """Check if port is currently tracked in active allocations."""
        with cls._lock:
            return port in cls._active_mappings

    @_ClassOrInstanceMethod
    def allocate_port(self_or_cls,
                      start_port: Optional[int] = None,
                      end_port: Optional[int] = None,
                      preferred_port: Optional[int] = None,
                      deployment_id: Optional[str] = None) -> int:
        """
        Thread-safe allocation of an available TCP host port.
        Supports concurrent calls, prevents duplicate allocation, and persists active mapping.
        """
        cls = self_or_cls if isinstance(self_or_cls, type) else type(self_or_cls)
        s_port = start_port or getattr(self_or_cls, "start_port", None) or cls.DEFAULT_START_PORT
        e_port = end_port or getattr(self_or_cls, "end_port", None) or cls.DEFAULT_END_PORT
        dep_id = deployment_id or "unassigned"

        with cls._lock:
            # Check preferred port first
            if preferred_port is not None:
                if preferred_port not in cls._active_mappings and cls.is_port_available(preferred_port):
                    cls._active_mappings[preferred_port] = dep_id
                    cls._save_state()
                    logger.info("Allocated preferred port: %d to deployment %s", preferred_port, dep_id)
                    return preferred_port
                else:
                    logger.warning("Preferred port %d is unavailable or already allocated.", preferred_port)

            # Search range sequentially
            for port in range(s_port, e_port + 1):
                if port in cls._active_mappings:
                    continue

                if cls.is_port_available(port):
                    cls._active_mappings[port] = dep_id
                    cls._save_state()
                    logger.info("Allocated port %d to deployment %s", port, dep_id)
                    return port

            raise RuntimeError(f"No available host ports found in range {s_port}-{e_port}.")

    @classmethod
    def release_port(cls, port: int) -> None:
        """
        Release a previously allocated port back to the free pool and update persistence.
        """
        with cls._lock:
            if port in cls._active_mappings:
                owner = cls._active_mappings.pop(port)
                cls._save_state()
                logger.info("Released port: %d (previously owned by %s)", port, owner)

    @classmethod
    def get_allocated_ports(cls) -> Set[int]:
        """Return the current set of actively allocated ports."""
        with cls._lock:
            return set(cls._active_mappings.keys())

    @classmethod
    def get_active_ports(cls) -> Set[int]:
        """Alias for get_allocated_ports."""
        return cls.get_allocated_ports()

    @classmethod
    def get_active_mappings(cls) -> Dict[int, str]:
        """Return a copy of current port to deployment_id mappings."""
        with cls._lock:
            return dict(cls._active_mappings)

    @classmethod
    def get_port_for_deployment(cls, deployment_id: str) -> Optional[int]:
        """Find the port currently allocated to a deployment ID."""
        with cls._lock:
            for port, dep in cls._active_mappings.items():
                if dep == deployment_id:
                    return port
            return None

    @classmethod
    def clear_all(cls) -> None:
        """Clear all in-memory allocations and wipe state file (for testing)."""
        with cls._lock:
            cls._active_mappings.clear()
            if cls._state_file.exists():
                try:
                    cls._state_file.unlink()
                except OSError:
                    pass

    # Instance method delegates for dependency injection
    def allocate(self, preferred_port: Optional[int] = None, deployment_id: Optional[str] = None) -> int:
        return self.allocate_port(self.start_port, self.end_port, preferred_port, deployment_id)

    def release(self, port: int) -> None:
        self.release_port(port)

    def is_allocated(self, port: int) -> bool:
        return self.is_port_allocated(port)

    def get_mappings(self) -> Dict[int, str]:
        return self.get_active_mappings()
