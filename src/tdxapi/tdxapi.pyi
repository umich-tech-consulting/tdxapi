import aiohttp
import requests
from typing import Any, Optional

class TeamDynamixInstance:
    def __init__(self, domain: str = ..., auth_token: str = ..., sandbox: bool = ..., default_ticket_app_name: str = ..., default_asset_app_name: str = ..., api_session: Optional[aiohttp.ClientSession] = ...) -> None: ...
    def set_auth_token(self, token: str) -> None: ...
    def get_current_user(self) -> dict[str, Any]: ...
    def get_domain(self) -> str: ...
    def set_domain(self, domain: str) -> None: ...
    def initialize(self) -> None: ...
    def populate_ids_for_app(self, app_type: str, app_name: str) -> None: ...
    def load_auth_token(self, filename: str = ...) -> None: ...
    def save_auth_token(self, filename: str = ...) -> None: ...
    def inventory_asset(self, asset: dict[str, Any], location_name: str, status_name: str, owner_uid: str = ..., notes: str = ..., app_name: str = ...) -> None: ...
    def get_asset(self, asset_id: str, app_name: str = ...) -> dict[str, Any]: ...
    def search_assets(self, search_string: str, app_name: str = ...) -> list[dict[str, Any]]: ...
    def update_asset(self, asset: dict[str, Any], app_name: str = ...) -> requests.Response: ...
    def attach_asset_to_ticket(self, ticket_id: str, asset_id: str, ticket_app_name: str = ...) -> requests.Response: ...
    def search_tickets(self, requester_uid: str, status_names: list[str], title: str, responsible_group_name: str = ..., app_name: str = ...) -> list[dict[str, Any]]: ...
    def get_ticket(self, ticket_id: str, app_name: str = ...) -> dict[str, Any]: ...
    def get_ticket_attribute(self, ticket: dict[str, Any], attr_name: str) -> dict[str, Any]: ...
    def update_ticket_status(self, ticket_id: str, status_name: str, comments: str, app_name: str = ...) -> requests.Response: ...
    def search_people(self, alt_id: str) -> list[dict[str, Any]]: ...