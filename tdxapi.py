import requests
import json
import os
from datetime import date

tdx_key = os.getenv("TDX_KEY")

class TeamDynamixInstance:
    no_owner = '00000000-0000-0000-0000-000000000000'
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
        }
    }
    def __init__(self, domain = None, auth_token = None, sandbox = True):
        self.domain = domain
        self.auth_token = auth_token
        self.sandbox = sandbox
        self.content = {}
        pass

    def initialize(self):
        self._populate_ids("AppIDs")
        self._populate_ids("LocationIDs")

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

    def search_tickets(self, app_name, requester_uid, status_names: list):
        status_ids = []
        for status_name in status_names:
            status_ids.append(self.content[app_name]["TicketStatusIDs"][status_name])
        app_id = self.content["AppIDs"][app_name]
        body = {
            "RequestorUids": [requester_uid],
            "StatusIDs": status_ids
        }
        response = self._make_request("post", f"{app_id}/tickets/search", body=body)
        tickets = json.loads(response.text)
        return tickets

    def update_asset(self, app_name, asset):
        app_id = self.content["AppIDs"][app_name]
        response = self._make_request("post", f"{app_id}/assets/{asset['ID']}", body=asset)
        return response

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

tdx = TeamDynamixInstance("teamdynamix.umich.edu", tdx_key)
tdx.initialize()
tdx._populate_ids("AssetStatusIDs", "ITS EUC Assets/CIs")
tdx._populate_ids("TicketStatusIDs", "ITS Tickets")
asset = tdx.search_assets("ITS EUC Assets/CIs", "SAH00002")
owner = asset["OwningCustomerID"]
tickets = tdx.search_tickets("ITS Tickets", owner, ["Closed", "Scheduled"])

asset["ID"] = asset["ID"]
asset["LocationID"] = tdx.content["LocationIDs"]["MICHIGAN UNION"]
asset["StatusID"] = tdx.content["ITS EUC Assets/CIs"]["AssetStatusIDs"]["In Stock - Reserved"]
asset["OwningCustomerID"] = tdx.no_owner
asset["SerialNumber"] = asset["SerialNumber"]
for attr in asset["Attributes"]:
    if(attr["Name"] == "Notes"):
        attr["Value"] = "Scanned and cleared by Tech Consulting"
    if(attr["Name"] == "Last Inventoried"):
        attr["Value"] = date.today().strftime("%m/%d/%Y")
tdx.update_asset("ITS EUC Assets/CIs", asset)
pass