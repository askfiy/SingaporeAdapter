from logging import Logger
from .config import Config
from .logrus import Logrus
from .aio_postgresql import AioPostgresql
from .protocol.http.aio_http_client import AioHttpClient

conf: Config = Config("./conf/config.json")
sig_cfg: Config = Config("./conf/private/signal.json")
log: Logger = Logrus("./conf/private/log.json").get_logger()
aiopg: AioPostgresql = AioPostgresql(conf_dict=conf["DATABASE"])
aio_requests: AioHttpClient = AioHttpClient(base_url=conf["RESTAPI"], keep_alive=False, timeout=60)
