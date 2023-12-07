import json
import aiohttp
from aiohttp.typedefs import StrOrURL
from typing import Optional, Any


class AioHttpClientResponse:
    def __init__(self, ok, url, status, request_info, headers, text):
        self.ok = ok
        self.url = url
        self.status = status
        self.request_info = request_info
        self.headers = headers
        self._text = text

    async def text(self):
        """
        In keeping with the native calling method, you must add await
        """
        return self._text

    async def json(self):
        """
        In keeping with the native calling method, you must add await
        """
        return json.loads(self._text)


class AioHttpClient:
    """
     An aiohttp-based package that provides the same interface call function as the requests package
     Lack of functions such as stream transmission, if necessary, you can package it yourself
    """

    def __init__(self, keep_alive=True, timeout=0, *args, **kwargs, ) -> None:
        self.session: Optional[aiohttp.ClientSession] = None

        self._args = args
        self._kwargs = kwargs

        self._keep_alive = keep_alive
        self._timeout = timeout

    def get_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            connector = None
            if not self._keep_alive:
                # disabled keep-alive
                connector = aiohttp.TCPConnector(force_close=True)
            if self._timeout > 0:
                self._kwargs["timeout"] = aiohttp.ClientTimeout(total=self._timeout)
            self.session = aiohttp.ClientSession(*self._args, **self._kwargs, connector=connector)

        return self.session

    async def request(
        self, method: str, url: StrOrURL, **kwargs: Any
    ):
        """
        Get necessary data before resp closes
        In this way, there is no need to call resp.close() externally
        """
        async with self.get_session().request(method, url, **kwargs) as resp:
            return AioHttpClientResponse(
                ok=resp.ok,
                url=resp.url,
                status=resp.status,
                request_info=resp.request_info,
                headers=resp.headers,
                text=await resp.text(),
            )

    async def options(self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any):
        return await self.request(
            "OPTIONS",
            url,
            allow_redirects=allow_redirects,
            **kwargs
        )

    async def head(
        self, url: StrOrURL, *, allow_redirects: bool = False, **kwargs: Any
    ):
        return await self.request(
            "HEAD",
            url,
            allow_redirects=allow_redirects,
            **kwargs
        )

    async def get(
        self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any
    ):
        return await self.request(
            "GET",
            url,
            allow_redirects=allow_redirects,
            **kwargs
        )

    async def post(
        self, url: StrOrURL, *, data: Any = None, **kwargs: Any
    ):
        return await self.request(
            "POST",
            url,
            data=data,
            **kwargs
        )

    async def put(
        self, url: StrOrURL, *, data: Any = None, **kwargs: Any
    ):
        return await self.request(
            "PUT",
            url,
            data=data,
            **kwargs
        )

    async def patch(
        self, url: StrOrURL, *, data: Any = None, **kwargs: Any
    ):
        return await self.request(
            "PATCH",
            url,
            data=data,
            **kwargs
        )

    async def delete(self, url: StrOrURL, **kwargs: Any):
        return await self.request(
            "DELETE",
            url,
            **kwargs
        )

    async def close(self):
        if not self.get_session().closed:
            await self.get_session().close()
