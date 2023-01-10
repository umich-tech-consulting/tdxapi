import requests
import json
import os
from datetime import date

class TeamDynamixInstance:
    no_owner = '00000000-0000-0000-0000-000000000000'
    # These are hardcoded into the API
    component_ids = {
        "Ticket": 9,
        "Asset": 27
    }

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
            "Endpoint": f"attributes/custom?componentId={component_ids['Asset']}"
        },
        "TicketAttributes": {
            "Name": "Name",
            "ID": "ID",
            "Endpoint": f"attributes/custom?componentId={component_ids['Ticket']}"
        }
    }
    
    def __init__(self, domain = None, auth_token = None, sandbox = True):
        """ 
        Creates a new object for interacting with a TeamDynamix instance

        :param domain: Custom domain TDx instance is 
        """
        self.domain = domain
        self.auth_token = auth_token
        self.sandbox = sandbox
        self.content = {}

    def check_authentication(self):
        response = self._make_request("get", "auth/getuser", True)
        if(response.status_code == 200):
            print(f"Logged in as {json.loads(response.text)['FullName']}")
        elif(response.status_code == 401):
            print("Unable to get current user, please reauthenticate")
        else:
            print(f"Something went wrong checking authentication: {response.text}")

    def initialize(self):
        self._populate_ids("AppIDs")
        self._populate_ids("LocationIDs")
        self._populate_ids("AssetAttributes")
        self._populate_ids("TicketAttributes")

    def populate_ids_for_app(self, app_type, app_name):
        self._populate_ids(app_type, app_name)

    ##################
    #                #
    #     Assets     #
    #                #
    ##################

    def check_in_asset(self, asset, app_name, location_name, status_name, owner_uid, notes):
        asset["LocationID"] = self.content["LocationIDs"][location_name]
        asset["StatusID"] = self.content[app_name]["AssetStatusIDs"][status_name]
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

    def get_asset(self, app_name, id):
        app_id = self.content["AppIDs"][app_name]
        response = self._make_request("get", f"{app_id}/assets/{id}")
        asset = json.loads(response.text)
        return asset

    def search_assets(self, app_name, search_string):
        app_id = self.content["AppIDs"][app_name]
        body = {
            "SerialLike": search_string
        }
        response = self._make_request("post", f"{app_id}/assets/search", body=body)
        assets = json.loads(response.text)
        if(len(assets) == 1):
            asset = self.get_asset(app_name, assets[0]["ID"])
            return asset
        return assets

    def update_asset(self, app_name, asset):
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

    def attach_asset_to_ticket(self, ticket_app_name, ticket_id, asset_id):
        app_id = self.content["AppIDs"][ticket_app_name]
        response = self._make_request("post", f"{app_id}/tickets/{ticket_id}/assets/{asset_id}")
        if(response.status_code != 200):
            print(f"Unable to attach asset {asset_id} to ticket {ticket_id}: {response.text}")
        return response

    def search_tickets(self, app_name, requester_uid, status_names: list, title: str):
        status_ids = []
        for status_name in status_names:
            status_ids.append(self.content[app_name]["TicketStatusIDs"][status_name])
        app_id = self.content["AppIDs"][app_name]
        body = {
            "RequestorUids": [requester_uid],
            "StatusIDs": status_ids,
            "Title": title
        }
        response = self._make_request("post", f"{app_id}/tickets/search", body=body)
        tickets = json.loads(response.text)
        return tickets

    def update_ticket_status(self, ticket_id, status_name, comments, app_name):
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
    #     Utilities     #
    #                   #
    #####################

    def _populate_ids(self, type, app_name = None):
        id = self._populating_dict[type]["ID"]
        name = self._populating_dict[type]["Name"]
        endpoint = self._populating_dict[type]["Endpoint"]
        content = self.content

        if(app_name):
            endpoint = str(self.content["AppIDs"][app_name]) + f"/{endpoint}"
        response = self._make_request("get", endpoint)
        objs = json.loads(response.text)

        # If working with a specific app name, move into that content context
        if(app_name and app_name not in self.content):
            content[app_name] = {}
            content = self.content[app_name]

        if(type not in content):
            content[type] = {}
        for obj in objs:
            content[type][obj[name]] = obj[id]


    def _make_request(self, type, endpoint, requires_auth = True, body = {}):
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