import datetime
import json
import typing

from utils import aio_requests, log


async def _common_get(url):

    resp = await aio_requests.get(url)

    if 200 != resp.status:
        raise Exception("resp status is not 200")

    resj: typing.Dict[str, typing.Any] = await resp.json()
    # LOG.debug("{} response: \n{}".format(url, resj))

    # if 0 != resj["code"]:
    #     raise Exception("code is not 0")

    return resj


async def _common_post(url, body):

    resp = await aio_requests.post(url, json=body)

    if 200 != resp.status:
        raise Exception("resp status is not 200")

    resj = await resp.json()
    if 0 != resj["code"]:
        raise Exception("code is not 0")

    return resj


async def create_order(order_name, ts_name, parameters):
    url = "/api/om/order/"

    msg = "create order <order name: {}, ts name: {}, parameters: {}>".format(order_name, ts_name, parameters)
    log.info(msg)

    req_body = {
        "order_name": order_name,
        "priority": 1,
        "dead_line": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "ts_name": ts_name,
        "parameters": json.dumps(parameters)
    }

    resj = await _common_post(url, req_body)
    order_id = resj["data"][0]["in_order_id"]
    return order_id


async def clear_agv_error(agv_list):
    url = "/api/engine/ctrl-mgr/clear-fault/"

    msg = "clear {} agv error".format(agv_list)
    log.info(msg)

    req_body = {
        "agv_list": agv_list
    }

    resj = await _common_post(url, req_body)
    return resj


async def get_all_agv_info():
    url = "/api/engine/basic-data/agvs/"
    resj = await _common_get(url)
    return resj["data"] or []


async def get_agv_error_info(agv_id):
    url = "/api/engine/errors/agvs/{}/".format(agv_id)
    resj = await _common_get(url)
    return resj["data"] or []


async def query_children_location(location_id):
    # 3315
    url = "/api/dispatch/universal/basic-data/locations/child_location_info/?parent_id={}".format(
        location_id)
    resj = await _common_get(url)
    return resj["data"] or []

# ------- extend -------


async def get_all_agv_id():
    data = await get_all_agv_info()
    return list(map(lambda d: d["agv_id"], data))
