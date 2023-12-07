from aiohttp import web

from . import views
from .urls import routes

app = web.Application()
app.add_routes(routes)
