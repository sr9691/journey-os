# =============================================================================
# WordPress REST API Client
# =============================================================================
#
# Provides async methods to interact with the journey-os WordPress plugin.
#
# Two API namespaces exist in the WordPress plugin:
#
#   RTR Reading Room (directreach/v1/reading-room):
#     - GET /prospects          - List prospects (filterable by campaign, room)
#     - GET /prospects/{id}     - Get single prospect
#     - GET /campaigns          - List campaigns
#
#   Campaign Builder (directreach/v2):
#     - GET  /campaigns/{id}                          - Get campaign details
#     - GET  /campaigns/{id}/content-links            - List content links
#     - GET  /campaigns/{id}/templates                - List email templates
#     - POST /emails/generate                         - Generate email
#     - POST /emails/track-copy                       - Track email copy event
#
# Auth:
#   RTR Reading Room: WordPress cookie auth (current_user_can('edit_posts'))
#   Campaign Builder: WordPress cookie auth (current_user_can('manage_options'))
#   Legacy CPD API:   X-API-Key header (get_option('cpd_api_key'))
#
# For external (non-browser) access, use WordPress Application Passwords
# with Basic Auth, which satisfies current_user_can() checks.
# =============================================================================

import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Response Models
# =============================================================================

class Prospect(BaseModel):
    # Prospect data from rtr_prospects table
    # Fields from rtr_prospects joined with cpd_visitors and dr_campaign_settings
    id: int
    campaign_id: int
    visitor_id: int
    current_room: str = ""  # "problem", "solution", "offer"
    company_name: str = ""
    contact_name: str | None = None
    contact_email: str | None = None
    lead_score: int = 0
    days_in_room: int = 0
    email_sequence_position: int = 0
    engagement_data: str | None = None  # JSON string of recent page visits
    # Joined from cpd_visitors
    job_title: str | None = None
    industry: str | None = None
    employee_count: str | None = None
    # Tracking - URLs already sent to this prospect
    urls_sent: list[str] = Field(default_factory=list)
    # Joined from dr_campaign_settings
    campaign_name: str | None = None
    client_id: int | None = None


class ContentLink(BaseModel):
    # Content asset from rtr_room_content_links table
    # Returned by GET /campaigns/{id}/content-links
    id: int
    campaign_id: int
    room_type: str  # "problem", "solution", "offer"
    link_title: str = ""
    link_url: str = ""
    url_summary: str = ""
    link_description: str = ""
    link_order: int = 0
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class Campaign(BaseModel):
    # Campaign from dr_campaign_settings table
    id: int
    client_id: int = 0
    campaign_name: str = ""
    # Additional fields depend on enrich_campaign_data in the controller


class EmailTemplate(BaseModel):
    # Email template from rtr_email_templates table
    # Returned by GET /campaigns/{id}/templates
    id: int
    campaign_id: int = 0
    room_type: str = ""
    subject_prompt: str | None = None
    opener_prompt: str | None = None
    body_prompt: str | None = None
    cta_prompt: str | None = None
    closer_prompt: str | None = None


# =============================================================================
# Exceptions
# =============================================================================

class WordPressAPIError(Exception):
    # Raised when WordPress API request fails

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


# =============================================================================
# Client
# =============================================================================

class WordPressClient:
    # Async client for the journey-os WordPress REST API
    #
    # Usage:
    #     async with WordPressClient() as wp:
    #         prospect = await wp.get_prospect(45)
    #         links = await wp.get_content_links(campaign_id=1)
    #
    # Auth priority:
    #   1. WordPress Application Passwords (Basic Auth) - for REST endpoints
    #      using current_user_can() permission checks
    #   2. X-API-Key header - for legacy CPD endpoints

    # API namespace prefixes
    RTR_NS = "/wp-json/directreach/v1/reading-room"
    CB_NS = "/wp-json/directreach/v2"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        app_user: str | None = None,
        app_password: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = (base_url or settings.wordpress_base_url).rstrip("/")
        self.api_key = api_key or settings.wordpress_api_key
        self.app_user = app_user or settings.wordpress_app_user
        self.app_password = app_password or settings.wordpress_app_password
        self.timeout = timeout or settings.api_timeout_seconds
        self._client: httpx.AsyncClient | None = None

    @property
    def has_basic_auth(self) -> bool:
        # Check if Application Password credentials are available
        return bool(self.app_user and self.app_password)

    async def __aenter__(self) -> "WordPressClient":
        # Enter async context manager
        # Uses Basic Auth (Application Passwords) when credentials are set,
        # falls back to X-API-Key header for legacy endpoints

        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }

        # Always include X-API-Key for legacy CPD endpoints
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        # Build auth for Application Passwords (Basic Auth)
        auth = None
        if self.has_basic_auth:
            auth = httpx.BasicAuth(
                username=self.app_user,
                password=self.app_password,
            )
            logger.info("WordPress client using Basic Auth (Application Passwords)")
        else:
            logger.warning(
                "WordPress client has no Application Password credentials. "
                "REST endpoints using current_user_can() will fail. "
                "Set WORDPRESS_APP_USER and WORDPRESS_APP_PASSWORD in .env"
            )

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            auth=auth,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # Exit async context manager
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        # Get the HTTP client, raising if not in context
        if self._client is None:
            raise RuntimeError(
                "WordPressClient must be used as async context manager: "
                "async with WordPressClient() as wp:"
            )
        return self._client

    # -------------------------------------------------------------------------
    # Prospects (RTR Reading Room namespace)
    # -------------------------------------------------------------------------

    async def get_prospect(self, prospect_id: int) -> Prospect:
        # Fetch a single prospect by ID
        # Endpoint: GET /directreach/v1/reading-room/prospects/{id}
        # Response: { success: true, data: { ...prospect fields } }

        endpoint = f"{self.RTR_NS}/prospects/{prospect_id}"

        logger.debug(f"Fetching prospect {prospect_id}")

        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                raise WordPressAPIError(
                    f"Prospect {prospect_id} not found",
                    status_code=404,
                )

            return Prospect.model_validate(data["data"])

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch prospect {prospect_id}: {e}")
            raise WordPressAPIError(
                f"Prospect {prospect_id} not found",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Request failed for prospect {prospect_id}: {e}")
            raise WordPressAPIError(f"Request failed: {e}") from e

    async def list_prospects(
        self,
        campaign_id: int | None = None,
        client_id: int | None = None,
        room: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> list[Prospect]:
        # List prospects, optionally filtered by campaign and room
        # Endpoint: GET /directreach/v1/reading-room/prospects

        endpoint = f"{self.RTR_NS}/prospects"
        params: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
        }
        if campaign_id:
            params["campaign_id"] = campaign_id
        if client_id:
            params["client_id"] = client_id
        if room:
            params["room"] = room

        logger.debug(
            f"Listing prospects",
            extra={"campaign_id": campaign_id, "room": room},
        )

        try:
            response = await self.client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            # RTR controller returns { success, data: [...], meta: {...} }
            items = data.get("data", [])
            if isinstance(items, dict):
                # Shouldn't happen for list, but handle gracefully
                items = [items]

            return [Prospect.model_validate(p) for p in items]

        except httpx.HTTPError as e:
            logger.error(f"Failed to list prospects: {e}")
            raise WordPressAPIError(f"Failed to list prospects: {e}") from e

    # -------------------------------------------------------------------------
    # Content Links (Campaign Builder namespace)
    # -------------------------------------------------------------------------

    async def get_content_links(
        self,
        campaign_id: int,
    ) -> dict[str, list[ContentLink]]:
        # Fetch content links for a campaign, grouped by room
        # Endpoint: GET /directreach/v2/campaigns/{id}/content-links
        # Response: { success, data: { problem: [...], solution: [...], offer: [...] } }

        endpoint = f"{self.CB_NS}/campaigns/{campaign_id}/content-links"

        logger.debug(f"Fetching content links for campaign {campaign_id}")

        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                raise WordPressAPIError(
                    f"Failed to get content links for campaign {campaign_id}",
                )

            grouped = data.get("data", {})
            result: dict[str, list[ContentLink]] = {}

            for room_type in ("problem", "solution", "offer"):
                room_links = grouped.get(room_type, [])
                result[room_type] = [
                    ContentLink.model_validate(link) for link in room_links
                ]

            return result

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch content links: {e}")
            raise WordPressAPIError(f"Failed to fetch content links: {e}") from e

    async def get_content_links_flat(
        self,
        campaign_id: int,
        room: str | None = None,
    ) -> list[ContentLink]:
        # Fetch content links as a flat list, optionally filtered by room
        # Convenience wrapper around get_content_links

        grouped = await self.get_content_links(campaign_id)

        if room:
            return grouped.get(room, [])

        # Flatten all rooms into a single list
        flat: list[ContentLink] = []
        for room_links in grouped.values():
            flat.extend(room_links)
        return flat

    # -------------------------------------------------------------------------
    # Campaigns (Campaign Builder namespace)
    # -------------------------------------------------------------------------

    async def get_campaign(self, campaign_id: int) -> Campaign:
        # Fetch a campaign by ID
        # Endpoint: GET /directreach/v2/campaigns/{id}

        endpoint = f"{self.CB_NS}/campaigns/{campaign_id}"

        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                raise WordPressAPIError(f"Campaign {campaign_id} not found")

            return Campaign.model_validate(data["data"])

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch campaign {campaign_id}: {e}")
            raise WordPressAPIError(f"Campaign {campaign_id} not found") from e

    # -------------------------------------------------------------------------
    # Email Templates (Campaign Builder namespace)
    # -------------------------------------------------------------------------

    async def get_email_templates(
        self,
        campaign_id: int,
    ) -> list[EmailTemplate]:
        # Fetch email templates for a campaign
        # Endpoint: GET /directreach/v2/campaigns/{id}/templates

        endpoint = f"{self.CB_NS}/campaigns/{campaign_id}/templates"

        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()

            items = data.get("data", [])
            if isinstance(items, dict):
                items = [items]

            return [EmailTemplate.model_validate(t) for t in items]

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch email templates: {e}")
            return []

    # -------------------------------------------------------------------------
    # Email Tracking (Campaign Builder namespace)
    # -------------------------------------------------------------------------

    async def generate_email(
        self,
        prospect_id: int,
        room_type: str,
        email_number: int = 1,
        force_regenerate: bool = False,
    ) -> dict[str, Any]:
        # Trigger email generation via the WordPress endpoint
        # Endpoint: POST /directreach/v2/emails/generate
        # This calls the PHP-side AI email generator
        #
        # For CIS-driven generation, use the LangGraph pipeline instead
        # and log results via log_email_generation()

        endpoint = f"{self.CB_NS}/emails/generate"
        payload = {
            "prospect_id": prospect_id,
            "room_type": room_type,
            "email_number": email_number,
            "force_regenerate": force_regenerate,
        }

        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to generate email: {e}")
            raise WordPressAPIError(f"Failed to generate email: {e}") from e

    async def track_email_copy(
        self,
        email_tracking_id: int,
        prospect_id: int,
        url_included: str = "",
    ) -> dict[str, Any]:
        # Track an email copy (mark as sent)
        # Endpoint: POST /directreach/v2/emails/track-copy

        endpoint = f"{self.CB_NS}/emails/track-copy"
        payload = {
            "email_tracking_id": email_tracking_id,
            "prospect_id": prospect_id,
            "url_included": url_included,
        }

        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to track email copy: {e}")
            raise WordPressAPIError(f"Failed to track email: {e}") from e
