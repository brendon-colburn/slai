"""
SLAI Game Client - HTTP client for the SLAI mod's REST API.

Connects to the SLAI mod's HTTP server (default: localhost:15526)
to read game state. This is READ-ONLY — SLAI never controls the game.

The mod is forked from STS2MCP by Yikun Ji (MIT); the API surface here
is the read-only subset we kept after the fork. See ATTRIBUTION.md.
"""

import httpx
import logging
from typing import Any, Optional

logger = logging.getLogger("slai.game_client")

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 15526


class GameClient:
    """HTTP client for the STS2MCP REST API."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.base_url = f"http://{host}:{port}"
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
        self._connected = False

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def check_connection(self) -> dict[str, Any]:
        """Check if STS2MCP is running and responsive."""
        try:
            response = await self._client.get("/")
            response.raise_for_status()
            data = response.json()
            self._connected = data.get("status") == "ok"
            return {
                "connected": self._connected,
                "message": data.get("message", "Unknown"),
                "status": data.get("status", "unknown"),
            }
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            self._connected = False
            return {
                "connected": False,
                "error": f"Cannot connect to the SLAI mod at {self.base_url}: {e}",
                "hint": "Make sure Slay the Spire 2 is running with the SLAI mod enabled (Settings -> Mods).",
            }
        except Exception as e:
            self._connected = False
            return {"connected": False, "error": str(e)}

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def get_game_state(self, format: str = "json") -> dict[str, Any]:
        """
        Get the current game state from STS2MCP.

        STS2MCP v0.4.0+ splits state into /singleplayer and /multiplayer.
        Try singleplayer first; fall back to multiplayer on 404.

        Args:
            format: 'json' for structured data (best for combat),
                    'markdown' for human-readable overview (best for map/events)
        """
        try:
            params = {"format": format}
            response = await self._client.get("/api/v1/singleplayer", params=params)
            if response.status_code == 404:
                response = await self._client.get("/api/v1/multiplayer", params=params)
            response.raise_for_status()
            self._connected = True

            if format == "json":
                return response.json()
            else:
                return {"markdown": response.text, "format": "markdown"}

        except httpx.ConnectError:
            self._connected = False
            return {"error": "Not connected to STS2MCP", "connected": False}
        except Exception as e:
            logger.error(f"Error getting game state: {e}")
            return {"error": str(e)}

    async def get_game_state_markdown(self) -> str:
        """Get game state as markdown (good for map/event overview)."""
        try:
            params = {"format": "markdown"}
            response = await self._client.get("/api/v1/singleplayer", params=params)
            if response.status_code == 404:
                response = await self._client.get("/api/v1/multiplayer", params=params)
            response.raise_for_status()
            self._connected = True
            return response.text
        except Exception as e:
            logger.error(f"Error getting markdown state: {e}")
            return f"Error: {e}"

    async def get_profile(self) -> dict[str, Any]:
        """Get the active player profile data."""
        try:
            response = await self._client.get("/api/v1/profile")
            response.raise_for_status()
            self._connected = True
            return response.json()
        except httpx.ConnectError:
            self._connected = False
            return {"error": "Not connected to STS2MCP"}
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return {"error": str(e)}

    async def get_compendium(self) -> dict[str, Any]:
        """
        Get compendium data: card_library, relic_collection,
        potion_lab, bestiary, run_history.
        """
        try:
            response = await self._client.get("/api/v1/compendium")
            response.raise_for_status()
            self._connected = True
            return response.json()
        except httpx.ConnectError:
            self._connected = False
            return {"error": "Not connected to STS2MCP"}
        except Exception as e:
            logger.error(f"Error getting compendium: {e}")
            return {"error": str(e)}

    async def search_wiki(
        self, query: str, item_type: Optional[str] = None, limit: int = 5
    ) -> dict[str, Any]:
        """
        Search the in-game wiki for cards, relics, etc.

        Args:
            query: Search term (fuzzy matched)
            item_type: Optional filter (e.g., 'card', 'relic')
            limit: Max results to return
        """
        try:
            params: dict[str, Any] = {"query": query, "limit": limit}
            if item_type:
                params["item_type"] = item_type

            response = await self._client.get("/api/v1/wiki", params=params)
            response.raise_for_status()
            self._connected = True
            return response.json()
        except httpx.ConnectError:
            self._connected = False
            return {"error": "Not connected to STS2MCP"}
        except Exception as e:
            logger.error(f"Error searching wiki: {e}")
            return {"error": str(e)}
