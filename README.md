# TDxAPI
A Python wrapper for the [TeamDynamix WebAPI](https://solutions.teamdynamix.com/TDWebApi/) with the primary purpose of automating and standardizing tasks for the University of Michigan Tech Consultants. 

## Getting Started
### Installation
The API can be installed simply through `pip` directly from GitHub like so:

```
pip install tdxapi git+https://github.com/owaink/tdxapi.git
```

This will give you the latest and greatest we have to offer in your Python environment!

### Using the API
To start using the project, import the `tdxapi` package and create a `TeamDynamixInstance`:
```
import tdxapi

tdx = tdxapi.TeamDynamixInstance(
        domain="teamdynamix.umich.edu",
        auth_token="",
        sandbox=True,
        default_asset_app_name="ITS EUC Assets/CIs",
        default_ticket_app_name="ITS Tickets",
    )
```
If you don't provide an `auth_token` when the `TeamDynamixInstance` is created, you'll need to set it using `tdx.set_auth_token(token)` before you can use it. There is currently no built in way to retrieve an `auth_token`, but you can use the methods listed [here](https://solutions.teamdynamix.com/TDWebApi/Home/section/Auth). For instances that only support SSO sign in like ours, we recommend using Selenium to authenticate through a browser and lifting the token from there.

### API Functions
For now, refer to the docstrings found in `tdxapi.py` for what functions are available and how they work. We'll have documentation ~~Soon&trade;~~ ~~Eventually&trade;~~ at some point (hopefully).

# This is a heavy work in progress!
Feel free to clone the repo and play around with it, but be aware it is under heavy development and we are not worried about compatibility at the moment. Forks and pull requests are welcome, but our focus is on our personal usage at the moment. 