import asyncio
import traceback

from utils import log, sig_cfg
from core.adapter import Adapter
from core.service import app, web


def exception_handler(_, context):
    exception = context.get('exception')

    if exception is None:
        return

    if isinstance(exception, asyncio.CancelledError):
        log.error("调度任务被取消, 可能造成的原因是程序已被强制关闭")

    if isinstance(exception, Exception):
        log.error(traceback.format_exc())


async def main(_):

    asyncio.get_running_loop().set_exception_handler(exception_handler)

    for conf in sig_cfg["DEVICE"]:
        await Adapter(conf).run()

        yield

if __name__ == "__main__":
    app.cleanup_ctx.append(main)
    web.run_app(
        app,
        port=5001,
        access_log=log
    )
