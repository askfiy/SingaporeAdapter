from aiohttp import web

from utils import log


class JsonResponse:
    async def __new__(cls, code=0, data=None, msg="", err="") -> web.Response:

        if msg:
            log.info(msg)

        if err:
            log.error(err)

        resp = {
            "code": code,
            "data": data,
            "msg": msg,
            "err": err
        }

        return web.json_response(resp)
