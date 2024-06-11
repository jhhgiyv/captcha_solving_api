import json

from curl_cffi import requests

from config import settings


def proxy_adapter(proxy: str, proxy_lifetime_sec: int = 120):
    url = f"{settings.proxy_bridge_url}/api/proxy/new"

    payload = json.dumps({
        "proxy": proxy,
        "no_auth": True,
        "proxy_type": "http",
        "proxy_lifetime_sec": proxy_lifetime_sec
    })
    headers = {
        'x-api-key': settings.proxy_bridge_api_key,
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.json().get("status") != 200:
        raise Exception(response.json().get("message"))
    port = response.json().get("data").get("port")
    return f"http://{settings.proxy_bridge_host}:{port}"
