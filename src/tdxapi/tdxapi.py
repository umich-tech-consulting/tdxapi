import requests
import json
import os
from datetime import date

class TeamDynamixInstance:
    _no_owner = '00000000-0000-0000-0000-000000000000'
    # These are hardcoded into the API
    _component_ids = {
        "Ticket": 9,
        "Asset": 27
    }
    # This is used to construct a name -> id dictionary so descriptive names can
    # be used instead of vauge IDs
    _populating_dict = {
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
            "Endpoint": "assets/statuses"
        },
        "TicketStatusIDs": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": "tickets/statuses"
        },
        "AssetAttributes": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": f"attributes/custom?componentId={_component_ids['Asset']}"
        },
        "TicketAttributes": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": f"attributes/custom?componentId={_component_ids['Ticket']}"
        }
    }
    
    def __init__(self, domain: str = None, auth_token: str = None, sandbox: bool = True, default_ticket_app_name: str = None, default_asset_app_name: str = None) -> None:
        """Creates a new TDx object to interact with the remote instance

        Args:
            domain (str, optional): Domain of the remote instance (eg teamdynamix.umich.edu). Defaults to None.
            auth_token (str, optional): Auth token provided from remote instance. Defaults to None.
            sandbox (bool, optional): Whether to use the safe sandbox environment or not. Set to False to use production environment. Defaults to True.
        """
        self.domain = domain
        self.auth_token = auth_token
        self.sandbox = sandbox
        self.content = {}
        self.default_ticket_app_name = default_ticket_app_name
        self.default_asset_app_name = default_asset_app_name

    def check_authentication(self) -> bool:
        """Checks if current auth_token is authorized to the TDx instance

        Returns:
            bool: Whether the TDx instance can be reached as an authenticated user
        """
        response = self._make_request("get", "auth/getuser", True)
        if(response.status_code == 200):
            print(f"Logged in as {json.loads(response.text)['FullName']}")
            return True
        elif(response.status_code == 401):
            print("Unable to get current user, please reauthenticate")
            return False
        else:
            print(f"Something went wrong checking authentication: {response.text}")
            return False

    def initialize(self) -> None:
        """Populates the TDx object with useful name to ID conversions
        """
        self._populate_ids("AppIDs")
        self._populate_ids("LocationIDs")
        self._populate_ids("AssetAttributes")
        self._populate_ids("TicketAttributes")
        self._populate_group_ids()
        return

    def populate_ids_for_app(self, app_type: str, app_name: str) -> None:
        """Populates the TDx object with IDs for a specific app, like tickets or people

        Args:
            app_type (str): The type of the app, eg "AssetStatusIDs"
            app_name (str): The name of the app in TDx to populate, eg "ITS Tickets"
        """
        self._populate_ids(app_type, app_name)
        return

    ##################
    #                #
    #     Assets     #
    #                #
    ##################

    def inventory_asset(self, asset: dict,  location_name: str, status_name: str, owner_uid: str = None, notes: str = None, app_name: str = None) -> None:
        """Updates the inventory status of an asset by updating location, status, owner, and notes

        Args:
            asset (dict): Asset to update
            app_name (str): Asset app the asset exists in
            location_name (str): New location name, must correlate to an ID already in TDx
            status_name (str): New status name, must correlate to an ID already in TDx
            owner_uid (str): New owner of the asset, removes owner if not given
            notes (str): New notes if provided, keeps previous notes if none given
        """
        if(app_name == None):
            app_name = self.default_asset_app_name
        asset["LocationID"] = self.content["LocationIDs"][location_name]
        asset["StatusID"] = self.content[app_name]["AssetStatusIDs"][status_name]
        if(owner_uid is not None):
            asset["OwningCustomerID"] = self._no_owner
        else:
            asset["OwningCustomerID"] = owner_uid
        existing_attributes = []
        for attr in asset["Attributes"]:
            existing_attributes.append(attr["Name"])
            if(attr["Name"] == "Notes"):
                attr["Value"] = notes
            if(attr["Name"] == "Last Inventoried"):
                attr["Value"] = date.today().strftime("%m/%d/%Y")
        if("Last Inventoried" not in existing_attributes):
            asset["Attributes"].append({
                "ID": self.content["AssetAttributes"]["Last Inventoried"],
                "Value": date.today().strftime("%m/%d/%Y")
            })
        if("Notes" not in existing_attributes):
            asset["Attributes"].append({
                "ID": self.content["AssetAttributes"]["Notes"],
                "Value": notes
            })
        self.update_asset(app_name, asset)

    def get_asset(self, asset_id: str, app_name: str = None) -> dict:
        """Fetchs an asset and returns it in dictonary form

        Args:
            app_name (str): App the asset exists in
            asset_id (str): Internal TDx ID of the asset

        Returns:
            dict: Asset as dictonary, includes custom attributes
        """
        if(app_name == None):
            app_name = self.default_asset_app_name
        app_id = self.content["AppIDs"][app_name]
        response = self._make_request("get", f"{app_id}/assets/{asset_id}")
        asset = json.loads(response.text)
        return asset

    def search_assets(self, search_string: str, app_name: str = None) -> list:
        """Searches for assets in the given app using the given search string and gives a list of matching assets as dictionaries

        Args:
            app_name (str): App to search in
            search_string (str): Name or Serial of the asset to be searched for

        Returns:
            list: A list of dictionaries representing assets, does not include custom attributes
        """

        if(app_name == None):
            app_name = self.default_asset_app_name
        app_id = self.content["AppIDs"][app_name]
        body = {
            "SerialLike": search_string
        }
        response = self._make_request("post", f"{app_id}/assets/search", body=body)
        assets = json.loads(response.text)
        return assets

    def update_asset(self, asset: dict, app_name: str = None) -> requests.Response:
        """Updates an asset in TDx

        Args:
            app_name (str): App the asset to be updated exists in
            asset (dict): Asset with updated values to be synced with TDx

        Returns:
            requests.Response: The response from the remote TDx instance, can be used for error handling but typically unconsumed
        """
        if(app_name == None):
            app_name = self.default_asset_app_name
        app_id = self.content["AppIDs"][app_name]
        response = self._make_request("post", f"{app_id}/assets/{asset['ID']}", body=asset)
        if(response.status_code != 200):
            print(f"Unable to update asset: {response.text}")
        return response

    ###################
    #                 #
    #     Tickets     #
    #                 #
    ###################

    def attach_asset_to_ticket(self, ticket_id: str, asset_id: str, ticket_app_name: str = None) -> requests.Response:
        """Attaches an asset to a ticket in a given ticket application

        Args:
            ticket_app_name (str): App name the ticket exists in
            ticket_id (str): Ticket number of the ticket to attach the asset to
            asset_id (str): Internal TDx ID of the asset to be attached

        Returns:
            requests.Response: Response from TDx, can be used for error handling
        """
        if(ticket_app_name == None):
            ticket_app_name = self.default_ticket_app_name
        app_id = self.content["AppIDs"][ticket_app_name]
        response = self._make_request("post", f"{app_id}/tickets/{ticket_id}/assets/{asset_id}")
        if(response.status_code != 200):
            print(f"Unable to attach asset {asset_id} to ticket {ticket_id}: {response.text}")
        return response

    def search_tickets(self, requester_uid: str, status_names: list, title: str, responsible_group_name: str = None, app_name: str = None) -> list:
        """Searches a ticket application for a ticket matching the given search criteria

        Args:
            app_name (str): Name of the ticket application
            requester_uid (str): UID of the requester for the ticket
            status_names (list): List of names of statuses that ticket can be
            title (str): Title of the ticket
            responsible_group_name (str, optional): Name of the group ticket is assigned to. Defaults to None.

        Returns:
            list: A list of dictonaries representing tickets
        """

        if(app_name == None):
            app_name = self.default_ticket_app_name
        status_ids = []
        for status_name in status_names:
            status_ids.append(self.content[app_name]["TicketStatusIDs"][status_name])
        app_id = self.content["AppIDs"][app_name]
        body = {
            "RequestorUids": [requester_uid],
            "StatusIDs": status_ids,
        }
        if(responsible_group_name != None):
            body["ResponsiblityGroupIDs"] = [self.content["GroupIDs"][responsible_group_name]]
        response = self._make_request("post", f"{app_id}/tickets/search", body=body)
        tickets = json.loads(response.text)

        # TDx search doesn't let us search by title, so we filter the list for tickets with matching title
        filtered_tickets = []
        for ticket in tickets:
            if(ticket["Title"] == title):
                filtered_tickets.append(ticket)
        return filtered_tickets

    def get_ticket(self, ticket_id: str, app_name: str = None) -> dict:
        """Gets a full ticket based on ID, includes custom attributes

        Args:
            app_name (str): Name of the ticket app the ticket exists in
            ticket_id (str): Ticket number

        Returns:
            dict: Dictonary representing the ticket
        """

        if(app_name == None):
            app_name = self.default_ticket_app_name
        app_id = self.content["AppIDs"][app_name]
        response = self._make_request("get", f"{app_id}/tickets/{ticket_id}")
        ticket = json.loads(response.text)
        return ticket
        
    def get_ticket_attribute(self, ticket: dict, attr_name: str) -> dict:
        """Gets a specific attribute from a ticket, since attributes are returned from the API in an unordered list

        Args:
            ticket (dict): Ticket to pull attribute from
            attr_name (str): Internal TDx name of the attribute, usually ugly

        Returns:
            dict: Dictonary of the attribute
        """
        for attr in ticket["Attributes"]:
            if(attr["Name"] == attr_name):
                return attr

    def update_ticket_status(self, ticket_id: str, status_name: str, comments: str, app_name: str = None) -> requests.Response:
        """Updates a ticket to the given status with given comments

        Args:
            ticket_id (str): Ticket number
            status_name (str): Name of the status to set ticket to
            comments (str): Comments to attach to ticket when updating status
            app_name (str): Name of the ticket app the ticket exists in

        Returns:
            requests.Response: Response from the TDx instance
        """
        if(app_name == None):
            app_name = self.default_ticket_app_name
        app_id = self.content["AppIDs"][app_name]
        status_id = self.content[app_name]["TicketStatusIDs"][status_name]
        body = {
            "NewStatusID": status_id,
            "Comments": comments,
            "IsPrivate": True,
            "IsRichHTML": False
        }
        response = self._make_request("post", f"{app_id}/tickets/{ticket_id}/feed", body=body)
        if(response.status_code != 200):
            print(f"Unable to update ticket status: {response.text}")
        return response

    #####################
    #                   #
    #      People       #
    #                   #
    #####################

    def search_people(self, alt_id: str) -> dict:
        """Searches for a person with provided alt_id

        Args:
            alt_id (str): Alternate ID assigned to person (ie uniqname)

        Returns:
            dict: Dictonary representing the person if found
        """
        body = {
            "AlternateID": alt_id
        }
        response = self._make_request("post", f"people/search", body=body)

        if(response.status_code != 200):
            print(f"Unable to search user: {response.text}")
            return
        people = json.loads(response.text)
        return people
        

    #####################
    #                   #
    #      Groups       #
    #                   #
    #####################

    def _populate_group_ids(self) -> None:
        """Populates the group name to ID dictonary for the TDx instance
        """
        response = self._make_request("post", "groups/search")
        if(response.status_code != 200):
            print("Could not populate groups")
            return
        groups = json.loads(response.text)
        self.content["GroupIDs"] = {}
        for group in groups:
            self.content["GroupIDs"][group["Name"]] = group["ID"]
        pass
    #####################
    #                   #
    #     Utilities     #
    #                   #
    #####################

    def _populate_ids(self, type: str, app_name: str = None) -> None:
        """Populates name to id dictonary for given app

        Args:
            type (str): Type of app to populate, eg "AppIDs"
            app_name (str, optional): Name of the application to find IDs for. Defaults to None.
        """
        id = self._populating_dict[type]["ID"]
        name = self._populating_dict[type]["Name"]
        endpoint = self._populating_dict[type]["Endpoint"]
        content = self.content

        if(app_name):
            endpoint = str(self.content["AppIDs"][app_name]) + f"/{endpoint}"
        response = self._make_request("get", endpoint)
        objs = json.loads(response.text)

        # If working with a specific app name, move into that app name's subdictionary
        if(app_name and app_name not in self.content):
            content[app_name] = {}
            content = self.content[app_name]

        if(type not in content):
            content[type] = {}
        for obj in objs:
            content[type][obj[name]] = obj[id]


    def _make_request(self, type: str, endpoint: str, requires_auth: bool = True, body: dict = {}) -> requests.Response:
        """Makes a request to the remote TDx instance

        Args:
            type (str): The type of request to make, eg "post", "get"
            endpoint (str): Api endpoint to send the request to, eg "assets/statuses"
            requires_auth (bool, optional): Whether the request requires . Defaults to True.
            body (dict, optional): Body of the request to send. Defaults to {}.

        Returns:
            requests.Response: Response from the API endpoint
        """
        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }

        if(self.auth_token and requires_auth):
            headers["Authorization"] = f"Bearer {self.auth_token}"

        if(self.sandbox):
            api_version = "SBTDWebApi"
        else:
            api_version = "TDWebApi"

        url = f"https://{self.domain}/{api_version}/api/{endpoint}"

        if(type == "get"):
            response = requests.get(url=url, headers=headers)
        elif(type == "post"):
            response = requests.post(url=url, headers=headers, json=body)

        return response