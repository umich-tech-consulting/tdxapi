"""Team Dynamix API as a Python Module."""
import asyncio
from http import HTTPStatus
from typing import Any, Optional

import aiohttp
import requests
import logging
import logging.config
from tdxapi import exceptions
import json
import yaml
import jwt
import sched
import time
from datetime import datetime
import os
logging.basicConfig(
    level=logging.DEBUG,
    filename='tdxapi.log',
    filemode='a',
    format='%(name)s - %(levelname)s - %(message)s'
)


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

    no_owner_uid: str = "00000000-0000-0000-0000-000000000000"
    # These are hardcoded into the API
    _component_ids: dict[str, int] = {"Ticket": 9, "Asset": 27}
    # This is used to construct a name -> id dictionary so descriptive names
    # can be used instead of vague IDs
    _populating_dict: dict[str, dict[str, str]] = {
        "AppIDs": {
            "Name": "Name",
            "ID": "AppID",
            "Endpoint": "applications"
        },
        "LocationIDs": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": "locations"
        },
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
        "TicketFormIDs": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": "tickets/forms"
        },
        "AssetFormIDs": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": "assets/forms"
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
        logging.debug("Creating TDx instance")
        self._domain: str = domain
        self._auth_token: str = auth_token
        self._sandbox: bool = sandbox
        self._content: dict[str, Any] = {}
        self._default_ticket_app_name: str = default_ticket_app_name
        self._default_asset_app_name: str = default_asset_app_name
        self._api_session: aiohttp.ClientSession | None = api_session

    async def login(self) -> None:
        username = str(os.getenv("TDX_USERNAME"))
        password = str(os.getenv("TDX_PASSWORD"))
        logging.debug(f"Logging in as {username}")
        body: dict[str, str] = {
            "username": username,
            "password": password
        }
        response = await self._make_async_request(
            "post", "auth/login", False, body=body)
        if response.ok:
            auth_key: str = await response.text()
            self.set_auth_token(auth_key)

            decoded_jwt: dict[str, Any] = jwt.decode(
                auth_key,
                option={"verify_signature": False}
            )
            logging.debug("Scheduling renewal for "
                          f"{datetime.fromtimestamp(decoded_jwt['exp']-3600)}")
            jwt_renewer = sched.scheduler(time.time, time.sleep)
            jwt_renewer.enterabs(
                decoded_jwt["exp"] - 3600,
                1,
                self.login
            )
            jwt_renewer.run()
        else:
            logging.debug(f"Unable to login as {username}")
            raise exceptions.NotAuthorizedException

    def get_id(
        self,
        app_name: str,
        name: str,
        id_type: Optional[str] = None
    ) -> str:
        """Convert a name to an ID.

        Args:
            app_name (str): App to search for the ID with given name
            id_type (str): Type of the ID (ie AssetStatusIDs)
            name (str): Name to convert to ID

        Returns:
            str: ID of the object
        """
        logging.debug(f"Getting id for {name} in {app_name}")
        if id_type:
            logging.debug(f"Found id {self._content[app_name][id_type][name]}")
            return self._content[app_name][id_type][name]
        else:
            logging.debug(f"Found id {self._content[app_name][name]}")
            return self._content[app_name][name]

    def get_default_app_name(self, app_type: str) -> str:
        """Get the default name of an app type.

        Args:
            app_type (str): App type to get (ie Asset, Ticket)

        Returns:
            str: Name of the default app
        """
        logging.debug(f"Getting default app for {app_type}")
        if app_type == "Asset":
            return self._default_asset_app_name
        if app_type == "Ticket":
            return self._default_ticket_app_name
        raise exceptions.InvalidParameterException

    async def close_api_session(self) -> None:
        """Close the API session."""
        logging.debug("Closing client session")
        if isinstance(self._api_session, aiohttp.ClientSession):
            await self._api_session.close()

    def set_auth_token(self, token: str) -> None:
        """Set authentication token.

        Sets the authentication token for accessing remote TDx Instance
        Tokens can be retrieved using any method here:
        https://teamdynamix.umich.edu/TDWebApi/Home/section/Auth

        Args:
            token (str): Token in JWT for authenticating to TDx
        """
        logging.debug("Setting new auth_token for TDx access")
        self._auth_token = token

    def get_current_user(self) -> dict[str, Any]:
        """Get current TDx user.

        Returns the currently logged in user,
        useful for testing if TDx can be accessed

        Returns:
            dict: The current user
        """
        logging.debug("Getting current TDx user")
        response: requests.Response = self._make_request(
            "get", "auth/getuser", True)
        if response.ok:
            user = response.json()
            return user
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            logging.error("TDx auth_key is not authorized")
            raise exceptions.NotAuthorizedException

        logging.error(
            f"Something went wrong \
                checking authentication: {response.text}"
        )
        raise exceptions.NotAuthorizedException

    def get_domain(self) -> str:
        """Get the domain of the TDx as a string.

        Raises:
            PropertyNotSetException: The domain has not been set

        Returns:
            str: The domain of the TDx instance as a string
        """
        logging.debug("Getting TDx domain")
        if self._domain:
            return self._domain
        logging.error("Domain is not set!")
        raise exceptions.PropertyNotSetException

    def set_domain(self, domain: str) -> None:
        """Set the domain of the remote TDx instance.

        Args:
            domain (str): Domain of remote instance
        """
        logging.debug(f"Setting TDx domain to {domain}")
        self._domain = domain

    async def initialize(self) -> None:
        """Initialize the TDx instance from the remote instance."""
        logging.debug(f"Initializing TDx instance for {self.get_domain()}")
        tasks: list[Any] = []
        tasks.append(self._populate_ids("AppIDs"))
        tasks.append(self._populate_ids("LocationIDs"))
        tasks.append(self._populate_ids("AssetAttributes"))
        tasks.append(self._populate_ids("TicketAttributes"))

        logging.debug("Running initilization tasks")
        await asyncio.gather(*tasks)
        logging.debug("First init tasks complete")
        tasks = []
        if self._default_asset_app_name:
            tasks.append(self.populate_ids_for_app(
                "AssetStatusIDs",
                self._default_asset_app_name
            ))
            tasks.append(self.populate_ids_for_app(
                "AssetFormIDs",
                self._default_asset_app_name
            ))
        if self._default_ticket_app_name:
            tasks.append(self.populate_ids_for_app(
                "TicketStatusIDs",
                self._default_ticket_app_name
            ))
            tasks.append(self.populate_ids_for_app(
                "TicketFormIDs",
                self._default_ticket_app_name
            ))

        await asyncio.gather(*tasks)
        logging.debug("Second init tasks complete")
        self._populate_group_ids()
        logging.debug("Initialization complete")

    async def _populate_all_ids(self) -> None:
        """Populate the TDx object with useful name to ID conversions."""
        logging.debug("Populating AppIDs")
        await self._populate_ids("AppIDs")
        logging.debug("Populating LocationIDs")
        await self._populate_ids("LocationIDs")
        logging.debug("Populating AssetAttributes")
        await self._populate_ids("AssetAttributes")
        logging.debug("Populating TicketAttributes")
        await self._populate_ids("TicketAttributes")
        return

    async def populate_ids_for_app(self, app_type: str, app_name: str) -> None:
        """Retrieve IDs for specific app.

        Args:
            app_type (str): The type of the app, eg "AssetStatusIDs"
            app_name (str): The name of the app in TDx to populate,\
                 eg "ITS Tickets"
        """
        logging.debug(f"Populating ids for {app_name}")
        await self._populate_ids(app_type, app_name)

    def load_auth_token(self, filename: str = "tdx.key") -> None:
        """Load an auth token instead of getting it through the web api.

        Args:
            filename (str, optional): Filename to load the key from.\
                 Defaults to tdx.key.
        """
        try:
            logging.debug("Attempting to load auth token from tdx.key")
            with open("tdx.key", encoding="UTF-8") as keyfile:
                self.set_auth_token(keyfile.read())
        except FileNotFoundError as exception:
            logging.error(f"Unable to load auth token from file")
            raise exception

    def save_auth_token(self, filename: str = "tdx.key") -> None:
        """Save the auth token to a file for later use.

        Args:
            filename (str, optional): File to save the auth token to.\
                 Defaults to tdx.key.
        """
        logging.debug(f"Saving auth token to {filename}")
        with open(filename, "w+", encoding="UTF-8") as keyfile:
            keyfile.write(str(self._auth_token))

    ##################
    #                #
    #     Assets     #
    #                #
    ##################

    async def get_asset(
            self,
            asset_id: str,
            app_name: str = ""
    ) -> dict[str, Any]:
        """Fetch an asset and returns it in dictionary form.

        Args:
            app_name (str): App the asset exists in
            asset_id (str): Internal TDx ID of the asset

        Returns:
            dict: Asset as dictionary, includes custom attributes
        """
        logging.debug(f"Getting asset with id {asset_id}")
        if not app_name:
            app_name = self._default_asset_app_name
        app_id = self._content["AppIDs"][app_name]
        response = await self._make_async_request(
            "get", f"{app_id}/assets/{asset_id}"
        )
        asset = await response.json()
        return asset

    async def search_assets(
        self, search_string: str, app_name: str = ""
    ) -> list[dict[str, Any]]:
        """Find an asset.

        Searches for assets in the given app using the given search string
        and gives a list of matching assets as dictionaries. Does NOT return
        custom attributes. For custom attributes, use get_asset()

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
        response: aiohttp.ClientResponse = await self._make_async_request(
            "post", f"{app_id}/assets/search", body=body
        )
        assets = await response.json()
        return assets

    async def update_asset(
        self, asset: dict[str, Any], app_name: str = ""
    ) -> aiohttp.ClientResponse:
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
        response = await self._make_async_request(
            "post", f"{app_id}/assets/{asset['ID']}", body=asset
        )
        if not response.ok:
            logging.error(f"Unable to update asset: {response.text()}")
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
            logging.error(
                f"Unable to attach asset {asset_id} to ticket {ticket_id}:\
                    {response.text}"
            )
            raise exceptions.UnableToAttachAssetException(
                ticket_id,
                asset_id
            )
        return response

    async def get_ticket_assets(
            self,
            ticket_id: str,
            app_name: str = ""
    ) -> list[dict[str, Any]]:
        """Get a ticket's attached assets.

        Gets a list of all configuration items for a ticket. This is
        effectively a list of assets that the ticket has attached to it.

        Args:
            ticket_id (str): Ticket number to get assets for
            app_name (str): Name of the ticket app to search for ticket in

        Returns:
            list: List of dictionaries representing configuration items
        """
        if not app_name:
            app_name = self._default_ticket_app_name
        app_id = self._content["AppIDs"][app_name]

        response = await self._make_async_request(
            "get", f"{app_id}/tickets/{ticket_id}/assets"
        )
        conf_items = await response.json()

        return conf_items

    def search_tickets(  # pylint: disable=too-many-arguments
        self,
        title: str,
        criteria: dict[str, Any],
        app_name: str = "",
    ) -> list[dict[str, Any]]:
        """Search for ticket.

        Searches a ticket application for a ticket matching the given\
            search criteria

        Args:
            app_name (str): Name of the ticket application
            title (str): Title of the ticket
            criteria (dict): Dictionary matching search criteria from TDx docs

        Returns:
            list: A list of dictionaries representing tickets
        """
        if not app_name:
            app_name = self._default_ticket_app_name

        app_id = self._content["AppIDs"][app_name]

        response = self._make_request(
            "post", f"{app_id}/tickets/search", body=criteria
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
        raise exceptions.NoSuchAttributeException

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
        body: dict[str, Any | str | bool] = {
            "NewStatusID": status_id,
            "Comments": comments,
            "IsPrivate": True,
            "IsRichHTML": False,
        }
        response = self._make_request(
            "post", f"{app_id}/tickets/{ticket_id}/feed", body=body
        )
        if not response.ok:
            logging.error(f"Unable to update ticket status: {response.text}")
        return response

    #####################
    #                   #
    #      People       #
    #                   #
    #####################

    async def search_person(self, criteria: dict[str, Any]) -> dict[str, Any]:
        """Search for a person with provided alt_id.

        Args:
            criteria (dict[str, Any]): Criteria to match person in TDx

        Returns:
            dict: Dictionary representing the person if found
        """
        logging.info(f"Searching for person with criteria {criteria}")
        response: aiohttp.ClientResponse = \
            await self._make_async_request(
                "post",
                "people/search",
                body=criteria
            )

        if not response.ok:
            logging.error(f"Unable to search user: {response.text}")
            raise exceptions.RequestFailedException
        people: list[dict[str, Any]] = await response.json()
        if (len(people) == 0):
            logging.error(f"No person matches {criteria}")
            raise exceptions.PersonDoesNotExistException(criteria)
        if (len(people) >= 2):
            logging.error(f"Found more than one match for {criteria}")
            raise exceptions.MultipleMatchesException("person")
        logging.info(f"Found person matching {criteria}")
        logging.info(f"{json.dumps(people, indent=4)}")
        return people[0]

    async def get_person(self, uid: str) -> dict[str, Any]:
        """Get a specific person based on UID.

        Args:
            uid (str): Base64 string unique to each person

        Returns:
            dict: Dictionary representing the person
        """
        logging.info(f"Getting person with uid {uid}")
        response: aiohttp.ClientResponse = \
            await self._make_async_request(
                "get",
                f"people/{uid}"
            )

        if not response.ok:
            logging.error(f"Unable to get user: {response.text}")
            raise exceptions.RequestFailedException
        return await response.json()

    #####################
    #                   #
    #      Groups       #
    #                   #
    #####################

    def _populate_group_ids(self) -> None:
        """Populate the group name to ID dictionary for the TDx instance."""
        response = self._make_request("post", "groups/search")
        if not response.ok:
            logging.error("Could not populate groups")
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
        obj_id: str = self._populating_dict[id_type]["ID"]
        name: str = self._populating_dict[id_type]["Name"]
        endpoint: str = self._populating_dict[id_type]["Endpoint"]
        content: dict[str, Any] = self._content

        if app_name:
            endpoint = str(self._content["AppIDs"][app_name]) + f"/{endpoint}"
        response: aiohttp.ClientResponse = await self._make_async_request(
            "get", endpoint)
        response_data = await response.json()

        # If working with a specific app name,
        # move into that app name's subdictionary
        if app_name:
            if app_name not in self._content:
                content[app_name] = {}
            content = self._content[app_name]

        if id_type not in content:
            content[id_type] = {}
        for obj in response_data:
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
        headers: dict[str, str] = {
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

        url: str = f"https://{self._domain}/{api_version}/api/{endpoint}"

        if request_type == "get":
            response = requests.get(url=url, headers=headers, timeout=10)
        elif request_type == "post":
            response = requests.post(
                url=url, headers=headers, json=body, timeout=10
            )
        else:
            logging.error(f"Expected post or get, got {request_type}")
            raise exceptions.InvalidHTTPMethodException

        return response

    async def _make_async_request(
        self,
        id_type: str,
        endpoint: str,
        requires_auth: bool = True,
        body: Optional[dict[str, Any]] = None,
    ) -> aiohttp.ClientResponse:
        if self._sandbox:
            api_version = "SBTDWebApi"
        else:
            api_version = "TDWebApi"

        url: str = f"https://{self._domain}"
        headers: dict[str, str] = {
            "Content-Type": "application/json; charset=utf-8",
        }

        if not body:
            body = {}

        if self._auth_token and requires_auth:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        if self._api_session is None:
            self._api_session = aiohttp.ClientSession(
                f"{url}", headers=headers
            )
        try:
            if id_type == "get":
                return await self._api_session.get(
                    f"/{api_version}/api/{endpoint}"
                )
            elif id_type == "post":
                return await self._api_session.post(
                    f"/{api_version}/api/{endpoint}",
                    json=body
                )
            else:
                logging.error(f"Expected post or get, got {id_type}")
                raise exceptions.InvalidHTTPMethodException
        except aiohttp.ClientError:
            logging.error("Client Communication Error!")
            raise exceptions.TDXCommunicationException
