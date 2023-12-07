import sys
from asyncio import tasks
from asyncio import futures


if sys.platform == 'win32':  # pragma: no cover
    from asyncio.windows_events import _WindowsSelectorEventLoop as BaseSelectorEventLoop  # type: ignore
    from asyncio.windows_events import _UnixSelectorEventLoop as BaseEventLoopPolicy  # type: ignore
else:
    from asyncio.unix_events import _UnixSelectorEventLoop as BaseSelectorEventLoop  # type: ignore
    from asyncio.unix_events import _UnixDefaultEventLoopPolicy as BaseEventLoopPolicy  # type: ignore


def _run_until_complete_cb(fut):

    if not fut.cancelled():
        exc = fut.exception()

        if isinstance(exc, (SystemExit, KeyboardInterrupt)):
            return


def _task_done(fut):
    loop = fut.get_loop()
    loop.wait.done()

    if loop.wait.is_complete():
        loop.stop()


class AioLoopWait:
    def __init__(self):
        self._task_count = 0

    def add(self):
        self._task_count += 1

    def done(self):
        self._task_count -= 1

    def is_complete(self):
        return self._task_count <= 0

    def clear(self):
        self._task_count = 0


class AioSelectorEventLoop(BaseSelectorEventLoop):
    def __init__(self) -> None:
        super().__init__()
        self.wait = AioLoopWait()

    def run_until_complete(self, future):
        self._check_closed()  # type: ignore
        self._check_running()  # type: ignore

        new_task = not futures.isfuture(future)
        future = tasks.ensure_future(future, loop=self)  # type: ignore

        if new_task:
            future._log_destroy_pending = False
        future.add_done_callback(_run_until_complete_cb)

        try:
            self.run_forever()
        except BaseException:
            if new_task and future.done() and not future.cancelled():
                future.exception()
            raise
        finally:
            self.wait.clear()
            future.remove_done_callback(_run_until_complete_cb)

        if not future.done():
            raise RuntimeError('Event loop stopped before Future completed.')

    def create_task(self, coro, *, name=None, context=None):
        """
        _task_done should be executed after all callbacks have been successfully executed, otherwise there are multiple callbacks that are logically imprecise or problematic

        Such as sub task:

            -> automatically add counter callback, callback's list is [_task_done, ]
            -> user manually adds callback, callback list is [_task_done, user_callback]

        When you run a callback function, the _task_done is run first, not the user_callback.
        It is necessary to ensure that _task_done is finally run in the callback to close the loop to this logical problem
        """
        task = super().create_task(coro, name=name, context=context)
        self.wait.add()
        task.add_done_callback(_task_done)
        return task


class AioEventLoopPolicy(BaseEventLoopPolicy):
    _loop_factory = AioSelectorEventLoop

    def __init__(self):
        super(__class__, self).__init__()
