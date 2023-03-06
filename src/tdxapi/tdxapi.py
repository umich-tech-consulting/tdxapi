"""Team Dynamix API as a Python Module."""
import asyncio
from datetime import date
from http import HTTPStatus
from typing import Any, Optional

import aiohttp
import requests

import tdxapi.exceptions


class TeamDynamixInstance:
    """TeamDynamix Instance Representation.

    A representation of the remote Team Dynamix (TDx) instance, stores
    information for communicating with the remote instance and wraps the API
    for easier consumption

    Raises:
        tdxapi.exceptions.NotAuthorizedException: _description_
        tdxapi.exceptions.PropertyNotSetException: _description_
        exception: _description_
        tdxapi.exceptions.NoSuchAttributeException: _description_
        tdxapi.exceptions.RequestFailedException: _description_
        tdxapi.exceptions.InvalidHTTPMethodException: _description_

    Returns:
        _type_: _description_
    """

    _no_owner = "00000000-0000-0000-0000-000000000000"
    # These are hardcoded into the API
    _component_ids = {"Ticket": 9, "Asset": 27}
    # This is used to construct a name -> id dictionary so descriptive names
    # can be used instead of vague IDs
    _populating_dict = {
        "AppIDs": {"Name": "Name", "ID": "AppID", "Endpoint": "applications"},
        "LocationIDs": {"Name": "Name", "ID": "ID", "Endpoint": "locations"},
        "AssetStatusIDs": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": "assets/statuses",
        },
        "TicketStatusIDs": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": "tickets/statuses",
        },
        "AssetAttributes": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": f"attributes/custom?componentId=\
                {_component_ids['Asset']}",
        },
        "TicketAttributes": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": f"attributes/custom?componentId=\
                {_component_ids['Ticket']}",
        },
    }

    def __init__(  # pylint: disable=too-many-arguments
        self,
        domain: str = "",
        auth_token: str = "",
        sandbox: bool = True,
        default_ticket_app_name: str = "",
        default_asset_app_name: str = "",
        api_session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        """Create a new TDx object to interact with the remote instance.

        Args:
            domain (str, optional):
            Domain of the remote instance (eg teamdynamix.umich.edu).
            Defaults to None.

            auth_token (str, optional):
            Auth token provided from remote instance.
            Defaults to None.

            sandbox (bool, optional):
            Whether to use the safe sandbox environment or not.
            Set to False to use production environment. Defaults to True.

            default_ticket_app_name (str, optional):
            Ticket app to use when none is defined.
            Defaults to None.

            default_asset_app_name (str, optional):
            Asset app to use when none is defined.
            Default to None.
        """
        self._domain = domain
        self._auth_token = auth_token
        self._sandbox = sandbox
        self._content: dict[str, Any] = {}
        self._default_ticket_app_name = default_ticket_app_name
        self._default_asset_app_name = default_asset_app_name
        self._api_session = api_session

    def set_auth_token(self, token: str) -> None:
        """Set authentication token.

        Sets the authentication token for accessing remote TDx Instance
        Tokens can be retrieved using any method here:
        https://teamdynamix.umich.edu/TDWebApi/Home/section/Auth

        Args:
            token (str): Token in JWT for authenticating to TDx
        """
        self._auth_token = token

    def get_current_user(self) -> dict[str, Any]:
        """Get current TDx user.

        Returns the currently logged in user,
        useful for testing if TDx can be accessed

        Returns:
            dict: The current user
        """
        response = self._make_request("get", "auth/getuser", True)
        if response.ok:
            user = response.json()
            return user
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            raise tdxapi.exceptions.NotAuthorizedException

        print(
            f"Something went wrong \
                checking authentication: {response.text}"
        )
        raise tdxapi.exceptions.NotAuthorizedException

    def get_domain(self) -> str:
        """Get the domain of the TDx as a string.

        Raises:
            PropertyNotSetException: The domain has not been set

        Returns:
            str: The domain of the TDx instance as a string
        """
        if self._domain:
            return self._domain
        raise tdxapi.exceptions.PropertyNotSetException

    def set_domain(self, domain: str) -> None:
        """Set the domain of the remote TDx instance.

        Args:
            domain (str): Domain of remote instance
        """
        self._domain = domain

    def initialize(self) -> None:
        """Initialize the TDx instance from the remote instance."""
        print(f"Logged in as {self.get_current_user()['PrimaryEmail']}")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._populate_all_ids())
        self._populate_group_ids()

    async def _populate_all_ids(self) -> None:
        """Populate the TDx object with useful name to ID conversions."""
        await self._populate_ids("AppIDs")
        await self._populate_ids("LocationIDs")
        await self._populate_ids("AssetAttributes")
        await self._populate_ids("TicketAttributes")
        return

    def populate_ids_for_app(self, app_type: str, app_name: str) -> None:
        """Retrieve IDs for specific app.

        Args:
            app_type (str): The type of the app, eg "AssetStatusIDs"
            app_name (str): The name of the app in TDx to populate,\
                 eg "ITS Tickets"
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._populate_ids(app_type, app_name))

    def load_auth_token(self, filename: str = "tdx.key") -> None:
        """Load an auth token instead of getting it through the web api.

        Args:
            filename (str, optional): Filename to load the key from.\
                 Defaults to tdx.key.
        """
        try:
            with open("tdx.key", encoding="UTF-8") as keyfile:
                self.set_auth_token(keyfile.read())
        except FileNotFoundError as exception:
            print(f"File {filename} not found")
            raise exception

    def save_auth_token(self, filename: str = "tdx.key") -> None:
        """Save the auth token to a file for later use.

        Args:
            filename (str, optional): File to save the auth token to.\
                 Defaults to tdx.key.
        """
        with open(filename, "w+", encoding="UTF-8") as keyfile:
            keyfile.write(str(self._auth_token))

    ##################
    #                #
    #     Assets     #
    #                #
    ##################

    def inventory_asset(  # pylint: disable=too-many-arguments
        self,
        asset: dict[str, Any],
        location_name: str,
        status_name: str,
        owner_uid: str = "",
        notes: str = "",
        app_name: str = "",
    ) -> None:
        """Update asset status.

        Updates the inventory status of an asset by updating location,
        status, owner, and notes

        Args:
            asset (dict):
            Asset to update

            app_name (str):
            Asset app the asset exists in

            location_name (str):
            New location name, must correlate to an ID already in TDx

            status_name (str):
            New status name, must correlate to an ID already in TDx

            owner_uid (str):
            New owner of the asset, removes owner if not given

            notes (str):
            New notes if provided, keeps previous notes if none given
        """
        if app_name == "":
            app_name = self._default_asset_app_name
        asset["LocationID"] = self._content["LocationIDs"][location_name]
        asset["StatusID"] = self._content[app_name]["AssetStatusIDs"][
            status_name
        ]
        if not owner_uid:
            asset["OwningCustomerID"] = self._no_owner
        else:
            asset["OwningCustomerID"] = owner_uid
        existing_attributes: list[str] = []
        for attr in asset["Attributes"]:
            existing_attributes.append(attr["Name"])
            if attr["Name"] == "Notes":
                attr["Value"] = notes
            if attr["Name"] == "Last Inventoried":
                attr["Value"] = date.today().strftime("%m/%d/%Y")
        if "Last Inventoried" not in existing_attributes:
            asset["Attributes"].append(
                {
                    "ID": self._content["AssetAttributes"]["Last Inventoried"],
                    "Value": date.today().strftime("%m/%d/%Y"),
                }
            )
        if "Notes" not in existing_attributes:
            asset["Attributes"].append(
                {
                    "ID": self._content["AssetAttributes"]["Notes"],
                    "Value": notes,
                }
            )
        self.update_asset(asset)

    def get_asset(self, asset_id: str, app_name: str = "") -> dict[str, Any]:
        """Fetch an asset and returns it in dictionary form.

        Args:
            app_name (str): App the asset exists in
            asset_id (str): Internal TDx ID of the asset

        Returns:
            dict: Asset as dictionary, includes custom attributes
        """
        if not app_name:
            app_name = self._default_asset_app_name
        app_id = self._content["AppIDs"][app_name]
        response = self._make_request("get", f"{app_id}/assets/{asset_id}")
        asset = response.json()
        return asset

    def search_assets(
        self, search_string: str, app_name: str = ""
    ) -> list[dict[str, Any]]:
        """Find an asset.

        Searches for assets in the given app using the given search string
        and gives a list of matching assets as dictionaries

        Args:
            app_name (str): App to search in
            search_string (str): Name or Serial of the asset to be searched for

        Returns:
            list: A list of dictionaries representing assets,
            does not include custom attributes
        """
        if not app_name:
            app_name = self._default_asset_app_name
        app_id = self._content["AppIDs"][app_name]
        body = {"SerialLike": search_string}
        response = self._make_request(
            "post", f"{app_id}/assets/search", body=body
        )
        assets = response.json()
        return assets

    def update_asset(
        self, asset: dict[str, Any], app_name: str = ""
    ) -> requests.Response:
        """Update an asset in TDx.

        Args:
            app_name (str): App the asset to be updated exists in
            asset (dict): Asset with updated values to be synced with TDx

        Returns:
            requests.Response:
            The response from the remote TDx instance,
            can be used for error handling but typically unconsumed
        """
        if not app_name:
            app_name = self._default_asset_app_name
        app_id = self._content["AppIDs"][app_name]
        response = self._make_request(
            "post", f"{app_id}/assets/{asset['ID']}", body=asset
        )
        if not response.ok:
            print(f"Unable to update asset: {response.text}")
        return response

    ###################
    #                 #
    #     Tickets     #
    #                 #
    ###################

    def attach_asset_to_ticket(
        self,
        ticket_id: str,
        asset_id: str,
        ticket_app_name: str = "",
    ) -> requests.Response:
        """Attaches an asset to a ticket in a given ticket application.

        Args:
            ticket_app_name (str): App name the ticket exists in
            ticket_id (str): Ticket number of the ticket to attach the asset to
            asset_id (str): Internal TDx ID of the asset to be attached

        Returns:
            requests.Response: Response from TDx,
            can be used for error handling
        """
        if not ticket_app_name:
            ticket_app_name = self._default_ticket_app_name
        app_id = self._content["AppIDs"][ticket_app_name]
        response = self._make_request(
            "post", f"{app_id}/tickets/{ticket_id}/assets/{asset_id}"
        )
        if not response.ok:
            print(
                f"Unable to attach asset {asset_id} to ticket {ticket_id}:\
                    {response.text}"
            )
        return response

    def search_tickets(  # pylint: disable=too-many-arguments
        self,
        requester_uid: str,
        status_names: list[str],
        title: str,
        responsible_group_name: str = "",
        app_name: str = "",
    ) -> list[dict[str, Any]]:
        """Search for ticket.

        Searches a ticket application for a ticket matching the given\
            search criteria

        Args:
            app_name (str): Name of the ticket application
            requester_uid (str): UID of the requester for the ticket
            status_names (list): List of names of statuses that ticket can be
            title (str): Title of the ticket
            responsible_group_name (str, optional):
            Name of the group ticket is assigned to. Defaults to None.

        Returns:
            list: A list of dictionaries representing tickets
        """
        if not app_name:
            app_name = self._default_ticket_app_name
        status_ids: list[int] = []
        for status_name in status_names:
            status_ids.append(
                self._content[app_name]["TicketStatusIDs"][status_name]
            )
        app_id = self._content["AppIDs"][app_name]
        body = {
            "RequestorUids": [requester_uid],
            "StatusIDs": status_ids,
        }
        if not responsible_group_name:
            body["ResponsibilityGroupIDs"] = [
                self._content["GroupIDs"][responsible_group_name]
            ]
        response = self._make_request(
            "post", f"{app_id}/tickets/search", body=body
        )
        tickets = response.json()

        # TDx search doesn't let us search by title,
        # so we filter the list for tickets with matching title
        filtered_tickets: list[dict[str, Any]] = []
        for ticket in tickets:
            if ticket["Title"] == title:
                filtered_tickets.append(ticket)
        return filtered_tickets

    def get_ticket(self, ticket_id: str, app_name: str = "") -> dict[str, Any]:
        """Get full ticket.

        Gets a full ticket based on ID, includes custom attributes

        Args:
            app_name (str): Name of the ticket app the ticket exists in
            ticket_id (str): Ticket number

        Returns:
            dict: Dictionary representing the ticket
        """
        if not app_name:
            app_name = self._default_ticket_app_name
        app_id = self._content["AppIDs"][app_name]
        response = self._make_request("get", f"{app_id}/tickets/{ticket_id}")
        ticket = response.json()
        return ticket

    def get_ticket_attribute(
        self, ticket: dict[str, Any], attr_name: str
    ) -> dict[str, Any]:
        """
        Get a specific attribute from a ticket.

        Args:
            ticket (dict): Ticket to pull attribute from
            attr_name (str): Internal TDx name of the attribute, usually ugly

        Returns:
            dict: Dictionary of the attribute
        """
        for attr in ticket["Attributes"]:
            if attr["Name"] == attr_name:
                return attr
        raise tdxapi.exceptions.NoSuchAttributeException

    def update_ticket_status(
        self,
        ticket_id: str,
        status_name: str,
        comments: str,
        app_name: str = "",
    ) -> requests.Response:
        """Update a ticket status.

        Args:
            ticket_id (str): Ticket number
            status_name (str): Name of the status to set ticket to
            comments (str): Comments to attach to ticket when updating status
            app_name (str): Name of the ticket app the ticket exists in

        Returns:
            requests.Response: Response from the TDx instance
        """
        if not app_name:
            app_name = self._default_ticket_app_name
        app_id = self._content["AppIDs"][app_name]
        status_id = self._content[app_name]["TicketStatusIDs"][status_name]
        body = {
            "NewStatusID": status_id,
            "Comments": comments,
            "IsPrivate": True,
            "IsRichHTML": False,
        }
        response = self._make_request(
            "post", f"{app_id}/tickets/{ticket_id}/feed", body=body
        )
        if not response.ok:
            print(f"Unable to update ticket status: {response.text}")
        return response

    #####################
    #                   #
    #      People       #
    #                   #
    #####################

    def search_people(self, alt_id: str) -> list[dict[str, Any]]:
        """Search for a person with provided alt_id.

        Args:
            alt_id (str): Alternate ID assigned to person (ie uniqname)

        Returns:
            dict: Dictionary representing the person if found
        """
        body = {"AlternateID": alt_id}
        response = self._make_request("post", "people/search", body=body)

        if not response.ok:
            print(f"Unable to search user: {response.text}")
            raise tdxapi.exceptions.RequestFailedException
        people = response.json()
        return people

    #####################
    #                   #
    #      Groups       #
    #                   #
    #####################

    def _populate_group_ids(self) -> None:
        """Populate the group name to ID dictionary for the TDx instance."""
        response = self._make_request("post", "groups/search")
        if not response.ok:
            print("Could not populate groups")
            return
        groups = response.json()
        self._content["GroupIDs"] = {}
        for group in groups:
            self._content["GroupIDs"][group["Name"]] = group["ID"]

    #####################
    #                   #
    #     Utilities     #
    #                   #
    #####################

    async def _populate_ids(self, id_type: str, app_name: str = "") -> None:
        """Populate name to id dictionary for given app.

        Args:
            type (str):
            Type of app to populate, eg "AppIDs"

            app_name (str, optional):
            Name of the application to find IDs for. Defaults to None.
        """
        obj_id = self._populating_dict[id_type]["ID"]
        name = self._populating_dict[id_type]["Name"]
        endpoint = self._populating_dict[id_type]["Endpoint"]
        content = self._content

        if app_name:
            endpoint = str(self._content["AppIDs"][app_name]) + f"/{endpoint}"
        response = await self._make_async_request("get", endpoint)

        # If working with a specific app name,
        # move into that app name's subdictionary
        if app_name and app_name not in self._content:
            content[app_name] = {}
            content = self._content[app_name]

        if id_type not in content:
            content[id_type] = {}
        for obj in response:
            content[id_type][obj[name]] = obj[obj_id]

    def _make_request(
        self,
        request_type: str,
        endpoint: str,
        requires_auth: bool = True,
        body: Optional[dict[str, Any]] = None,
    ) -> requests.Response:
        """Make a request to the remote TDx instance.

        Args:
            type (str):
            The type of request to make, eg "post", "get"

            endpoint (str):
            Api endpoint to send the request to, eg "assets/statuses"

            requires_auth (bool, optional):
            Whether the request requires . Defaults to True.

            body (dict, optional):
            Body of the request to send. Defaults to {}.

        Returns:
            requests.Response: Response from the API endpoint
        """
        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }
        if not body:
            body = {}

        if self._auth_token and requires_auth:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        if self._sandbox:
            api_version = "SBTDWebApi"
        else:
            api_version = "TDWebApi"

        url = f"https://{self._domain}/{api_version}/api/{endpoint}"

        if request_type == "get":
            response = requests.get(url=url, headers=headers, timeout=10)
        elif request_type == "post":
            response = requests.post(
                url=url, headers=headers, json=body, timeout=10
            )
        else:
            print(f"Expected post or get, got {request_type}")
            raise tdxapi.exceptions.InvalidHTTPMethodException

        return response

    async def _make_async_request(
        self,
        id_type: str,
        endpoint: str,
        requires_auth: bool = True,
        body: Optional[dict[str, Any]] = None,
    ) -> dict[Any, Any]:
        if self._sandbox:
            api_version = "SBTDWebApi"
        else:
            api_version = "TDWebApi"

        url = f"https://{self._domain}"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }

        if self._auth_token and requires_auth:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        if self._api_session is None:
            self._api_session = aiohttp.ClientSession(
                f"{url}", headers=headers
            )

        if id_type == "get":
            async with self._api_session.get(
                f"/{api_version}/api/{endpoint}"
            ) as response:
                return await response.json()
        elif id_type == "post":
            async with self._api_session.post(
                f"/{api_version}/api/{endpoint}", data=body
            ) as response:
                return await response.json()
        else:
            print(f"Expected post or get, got {id_type}")
            raise tdxapi.exceptions.InvalidHTTPMethodException
