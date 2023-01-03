import requests
import json

tdx_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1bmlxdWVfbmFtZSI6Im93YWlua0B1bWljaC5lZHUiLCJ0ZHhfZW50aXR5IjoiMiIsInRkeF9wYXJ0aXRpb24iOiI1NSIsIm5iZiI6MTY3Mjc1NTEzMiwiZXhwIjoxNjcyODQxNTMyLCJpYXQiOjE2NzI3NTUxMzIsImlzcyI6IlREIiwiYXVkIjoiaHR0cHM6Ly93d3cudGVhbWR5bmFtaXguY29tLyJ9.jqV8GqJ6H2KG5jhMzQ3jFl5SlXLYg1CWUw697Ds6j6I"
class TeamDynamixInstance:
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
    }
    def __init__(self, domain = None, auth_token = None, sandbox = True):
        self.domain = domain
        self.auth_token = auth_token
        self.sandbox = sandbox
        self.content = {}
        pass

    def initialize(self):
        for ids in self._populating_dict.keys():
            self._populate_ids(ids)

    def authenticate(self):
        response = self._make_request("get", "auth/getuser", True)
        if(response.status_code == 200):
            return
        elif(response.status_code == 401):
            print("Unable to get current user, please reauthenticate")

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

    def get_asset(self, app_name, id):
        app_id = self.content["AppIDs"][app_name]
        response = self._make_request("get", f"{app_id}/assets/{id}")
        asset = json.loads(response.text)
        return asset

    def search_tickets(self, app_name, requester_uid, status_name):
        app_id = self.content["AppIDs"][app_name]
        body = {
            "RequestorUids": [requester_uid],
            "StatusIDs": self.content["TicketStatusIDs"][status_name]
        }
        response = self._make_request("post", f"{app_id}/tickets/search", body=body)
        tickets = json.loads(response.text)
        return tickets

    def _populate_ids(self, type, app_name = None):
        id = self._populating_dict[type]["ID"]
        name = self._populating_dict[type]["Name"]
        endpoint = self._populating_dict[type]["Endpoint"]
        content = self.content

        if(app_name):
            endpoint = self.content["AppIDs"][app_name] + f"/{endpoint}"
        response = self._make_request("get", endpoint)
        objs = json.loads(response.text)

        # If working with a specific app name, move into that content context
        if(app_name not in self.content):
            self.content[app_name] = {}
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

tdx = TeamDynamixInstance("teamdynamix.umich.edu", tdx_key)
tdx.initialize()
asset = tdx.search_assets("ITS EUC Assets/CIs", "SAH00001")
owner = asset["OwningCustomerID"]
tickets = tdx.search_tickets("ITS Tickets", owner, "Closed")
pass