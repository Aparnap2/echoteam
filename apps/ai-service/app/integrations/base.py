"""Base integration classes for external service connections.

Provides common interface for all integrations:
- OAuth flow handling
- Token refresh
- Sync status tracking
- Episode generation for Graphiti
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class IntegrationStatus(str, Enum):
    """Status of an integration connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"


@dataclass
class IntegrationConfig:
    """Configuration for an integration."""
    user_id: str
    group_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scopes: List[str] = field(default_factory=list)
    last_sync: Optional[datetime] = None
    sync_enabled: bool = True
    sync_interval_hours: int = 24


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    episodes_created: int = 0
    episodes_updated: int = 0
    errors: List[str] = field(default_factory=list)
    synced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseIntegration(ABC):
    """Base class for all integrations.

    Provides common functionality:
    - OAuth token management
    - Sync scheduling
    - Episode generation for Graphiti
    """

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.status = IntegrationStatus.DISCONNECTED
        self._client: Optional[Any] = None

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Name of the service (e.g., 'gmail', 'calendar')."""
        pass

    @property
    @abstractmethod
    def default_scopes(self) -> List[str]:
        """OAuth scopes required for this integration."""
        pass

    async def connect(self, access_token: str, refresh_token: str,
                      expires_at: datetime, scopes: List[str]) -> bool:
        """Establish connection with OAuth tokens."""
        self.config.access_token = access_token
        self.config.refresh_token = refresh_token
        self.config.token_expires_at = expires_at
        self.config.scopes = scopes or self.default_scopes
        self.status = IntegrationStatus.CONNECTED
        logger.info(f"{self.service_name}: Connected for user {self.config.user_id}")
        return True

    async def disconnect(self) -> None:
        """Disconnect and clear tokens."""
        self.config.access_token = None
        self.config.refresh_token = None
        self.config.token_expires_at = None
        self.status = IntegrationStatus.DISCONNECTED
        self._client = None
        logger.info(f"{self.service_name}: Disconnected for user {self.config.user_id}")

    async def is_connected(self) -> bool:
        """Check if integration is connected and tokens are valid."""
        if not self.config.access_token:
            return False
        if self.config.token_expires_at and datetime.now(timezone.utc) > self.config.token_expires_at:
            return False
        return self.status == IntegrationStatus.CONNECTED

    async def refresh_token_if_needed(self) -> bool:
        """Refresh OAuth token if expired or expiring soon."""
        if not self.config.refresh_token:
            return False
        if not self.config.token_expires_at:
            return True
        # Refresh if token expires within 5 minutes
        threshold = datetime.now(timezone.utc) + timedelta(minutes=5)
        if self.config.token_expires_at > threshold:
            return True
        return await self._refresh_oauth_token()

    @abstractmethod
    async def _refresh_oauth_token(self) -> bool:
        """Implement OAuth token refresh. Override in subclass."""
        pass

    async def sync(self, since: Optional[datetime] = None) -> SyncResult:
        """Sync data from the service.

        Args:
            since: Only sync items after this time. If None, sync all.

        Returns:
            SyncResult with episode counts and any errors.
        """
        if not await self.is_connected():
            return SyncResult(
                success=False,
                errors=["Not connected"]
            )

        if not await self.refresh_token_if_needed():
            return SyncResult(
                success=False,
                errors=["Token refresh failed"]
            )

        self.status = IntegrationStatus.SYNCING
        try:
            result = await self._perform_sync(since)
            self.config.last_sync = result.synced_at
            self.status = IntegrationStatus.CONNECTED
            return result
        except Exception as e:
            logger.error(f"{self.service_name}: Sync failed: {e}")
            self.status = IntegrationStatus.ERROR
            return SyncResult(
                success=False,
                errors=[str(e)]
            )

    @abstractmethod
    async def _perform_sync(self, since: Optional[datetime]) -> SyncResult:
        """Implement actual sync logic. Override in subclass.

        Should create episodes for Graphiti via self._create_episode().
        """
        pass

    async def _create_episode(self, name: str, content: str,
                               source_type: str, metadata: Dict[str, Any]) -> bool:
        """Create an episode in memory for ingested data.

        Args:
            name: Episode name/identifier
            content: Episode content
            source_type: Type of source (email, event, task, etc.)
            metadata: Additional metadata (subject, date, etc.)
        """
        # Import here to avoid circular imports
        from app.memory import get_memory, MemorySourceType

        try:
            memory = await get_memory(user_id=self.config.user_id)

            # Map source_type to MemorySourceType enum
            source_map = {
                "email": MemorySourceType.EMAIL,
                "calendar": MemorySourceType.CALENDAR,
                "task": MemorySourceType.TASK,
                "note": MemorySourceType.NOTE,
                "research": MemorySourceType.RESEARCH,
            }
            source = source_map.get(source_type, MemorySourceType.SYSTEM)

            result = await memory.add(
                content=content,
                metadata={"source": source.value, "name": name, **metadata},
            )
            return result.status.value == "success"
        except Exception as e:
            logger.error(f"Failed to create episode: {e}")
            return False

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status for UI."""
        return {
            "service": self.service_name,
            "status": self.status.value,
            "last_sync": self.config.last_sync.isoformat() if self.config.last_sync else None,
            "sync_enabled": self.config.sync_enabled,
        }
