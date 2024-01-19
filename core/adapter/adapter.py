import enum
import asyncio

from core.device import Device
from core.device import SubDevice
from core.device import DeviceManager

from utils import log, conf
from utils.gzrobot import restapi, dbapi
from utils.config import Config


def safe_forever_loop(loop_time):
    def inner(coro):
        async def wrapper(*args, **kwargs):
            while True:
                try:
                    await coro(*args, **kwargs)
                except Exception as e:
                    asyncio.get_running_loop().call_exception_handler({"exception": e})
                await asyncio.sleep(loop_time)
        return wrapper
    return inner


class AGV_STATE(enum.Enum):
    AUTO = "AUTO"
    RUNNING = "RUNNING"


class DeviceAdapterManager:
    _mapping = {}

    @classmethod
    def add(cls, device_name, device: Device | SubDevice):
        cls._mapping[device_name] = device

    @classmethod
    def get(cls, device_name) -> Device | SubDevice:
        return cls._mapping[device_name]


class Adapter:

    device_mapping = DeviceAdapterManager

    def __init__(self, cfg: Config, debug=False) -> None:
        self._conf: Config = cfg
        self._base_device = Device(cfg, debug=debug)
        self._sub_device_manager = DeviceManager()

    def get_conf(self) -> Config:
        return self._conf

    def get_base_device(self) -> Device:
        return self._base_device

    def get_sub_device_manager(self) -> DeviceManager:
        return self._sub_device_manager

    def get_all_sub_devices(self) -> list[SubDevice]:
        return self.get_sub_device_manager().get_all_device()

    def load_sub_device(self):

        SUB_DEVICE_CONF = self.get_base_device().get_conf()["SUB_DEVICE"]
        for sub_device_conf in SUB_DEVICE_CONF:
            # sub_device_conf["HOST"] = self.get_base_device().get_host()
            # sub_device_conf["PORT"] = self.get_base_device().get_port()

            sub_device_conf["HOST"] = self.get_base_device().get_host()
            sub_device_conf["PORT"] = self.get_base_device().get_port()

            self.get_sub_device_manager().add(SubDevice(sub_device_conf))

    def add_adapter_device_relation(self):
        self.device_mapping.add(self.get_base_device().get_name(), self.get_base_device())

        for sub_device in self.get_all_sub_devices():
            self.device_mapping.add(sub_device.get_name(), sub_device)

    # ---- 查询 restapi, dbapi 后通过信号、向设备上报某些信息

    @safe_forever_loop(5)
    async def report_agv_battery_info(self):
        """
        上报电池电量状态
        """
        agv_info_list = await restapi.get_all_agv_info()
        for agv_info in agv_info_list:
            agv_id = agv_info["agv_id"]

            # HACK: 这里的实际电量实际上要获取容量、太菜了
            # current_battery = round(agv_info["battery_current"])

            current_battery = round(agv_info["battery_capacity"])
            # current_battery = 80

            await self.get_base_device().report_agv_battery_info(agv_id, current_battery)

    @safe_forever_loop(3)
    async def report_agv_error_info(self):
        # TODO: 需要进行过滤出关键的常见 code - 2023-07-24 -
        # 复位（没有故障就清除）

        all_agv_state = await dbapi.get_all_agv_state()

        for row in all_agv_state:
            agv_id = row["agv_id"]

            has_fault_happened = row["fault_happened"]

            if has_fault_happened:
                rr = await restapi.get_agv_error_info(agv_id)
                if rr:
                    error_code = rr[0]["error_code"]
                    await self.get_base_device().report_agv_error_code(agv_id, error_code)
                else:
                    await self.get_base_device().report_agv_error_code(agv_id, 0)

            else:
                await self.get_base_device().report_agv_error_code(agv_id, 0)

    @safe_forever_loop(3)
    async def report_agv_state(self):

        all_agv_state = await dbapi.get_all_agv_state()

        for row in all_agv_state:
            agv_id = row["agv_id"]
            has_connection_network = row["network_connected"]
            in_dispatch_active = row["dispatch_task_active"]
            has_fault_happened = row["fault_happened"]

            has_active_order = await dbapi.agv_has_active_order(agv_id)

            if not has_connection_network:
                await self.get_base_device().reset_agv_mode(agv_id, AGV_STATE.AUTO.value)
                await self.get_base_device().reset_agv_mode(agv_id, AGV_STATE.RUNNING.value)
                log.info("agv {} 未连接, 取消「自动」 「运行中」模式".format(agv_id))
                continue

            if not in_dispatch_active:
                await self.get_base_device().reset_agv_mode(agv_id, AGV_STATE.AUTO.value)
                await self.get_base_device().reset_agv_mode(agv_id, AGV_STATE.RUNNING.value)
                log.info("agv {} 未加入调度, 取消「自动」「运行中」模式".format(agv_id))
                continue

            if has_fault_happened:
                await self.get_base_device().reset_agv_mode(agv_id, AGV_STATE.AUTO.value)
                log.info("agv {} 有报错, 取消「自动」模式".format(agv_id))
                continue

            if has_active_order:
                await self.get_base_device().write_agv_mode(agv_id, AGV_STATE.RUNNING.value)
                log.info("agv {} 有存活订单, 上报为 「运行中」模式".format(agv_id))
                continue

            await self.get_base_device().write_agv_mode(agv_id, AGV_STATE.AUTO.value)
            await self.get_base_device().reset_agv_mode(agv_id, AGV_STATE.RUNNING.value)
            log.info("agv {} 状态正常, 上报为 「自动」模式".format(agv_id))

    # ---- 捕捉信号、调用 restapi 或 dbapi 执行相关功能
    @safe_forever_loop(3)
    async def monitor_stop_heartbeat(self):
        """
        如果是非急停模式、则刷入心跳
        """
        for sub_device in self.get_all_sub_devices():
            if not await sub_device.mode_is_stop():
                io_id = conf["HEARTBEAT_DI"][sub_device.get_name()]
                await dbapi.update_io_state(io_id)

    @safe_forever_loop(3)
    async def monitor_clear_error(self):
        """
        如果是重置模式，则清错
        """
        for sub_device in self.get_all_sub_devices():
            if await sub_device.mode_is_reset():
                agv_id_list = [
                    agv_info["id"]
                    for agv_info in await restapi.get_all_agv_info()
                    if agv_info.get("fault_happened")
                ]
                await restapi.clear_agv_error(agv_id_list)
                await asyncio.sleep(3)

    @safe_forever_loop(3)
    async def monitor_generate_order(self):
        """
        生成订单，有 3 种任务：
            1. 入库任务（必定指定板号）
            2. 出库任务（不指定板号）
            3. 出库任务（必定指定板号）
        """
        TS_NAME = conf["ORDER_CONF"]["ts_name"]

        for sub_device in self.get_all_sub_devices():

            device_name = sub_device.get_name()

            if await sub_device.mode_is_abnormal():
                log.info("轿厢 {} 模式不正常".format(device_name))
                continue

            # 入库任务
            if await sub_device.has_save_car_task():
                await asyncio.sleep(0.5)
                # 车板号
                car_number = await sub_device.get_save_car_number()
                if not await sub_device.save_task_is_start_handle():
                    # 创建任务
                    await restapi.create_order(
                        ts_name=TS_NAME,
                        order_name=device_name + "_save",
                        parameters={
                            "task_code": "1000",
                            "task_info": {
                                "car_number": str(car_number),
                                "device_name": str(device_name),
                            }
                        }
                    )

                    # 命令接收完成
                    await sub_device.report_save_task_handle_start()

            # 出库任务
            elif await sub_device.has_take_car_task():
                await asyncio.sleep(0.5)
                # 车板号
                car_number = await sub_device.get_take_car_number()
                # 指定车板号的叫料任务
                if not await sub_device.take_task_is_start_handle():
                    # 创建任务，判断 car_number 是否大于 0, 来区分是否是指定板号

                    if car_number > 0:
                        # 指定车号
                        await restapi.create_order(
                            ts_name=TS_NAME,
                            order_name=device_name + "_take",
                            parameters={
                                "task_code": "2000",
                                "task_info": {
                                    "car_number": str(car_number),
                                    "device_name": str(device_name),
                                }
                            }
                        )
                    else:
                        # 不指定车号
                        await restapi.create_order(
                            ts_name=TS_NAME,
                            order_name=device_name + "_take",
                            parameters={
                                "task_code": "3000",
                                "task_info": {
                                    "car_number": str(car_number),
                                    "device_name": str(device_name),
                                }
                            }
                        )

                    # 命令接收完成
                    await sub_device.report_take_task_handle_start()

    # ---- 捕捉信号、满足条件后做一些操作、不依赖 restapi 或者 dbapi 等外部接口
    @safe_forever_loop(3)
    async def monitor_clear_signal(self):
        """
        清理某些信号
        """

        for sub_device in self.get_all_sub_devices():

            # await sub_device.report_agv_load_action_finish()
            # await sub_device.report_agv_unload_action_finish()

            if not await sub_device.is_wait_save_task() and await sub_device.require_reset_agv_load_action():
                await sub_device.reset_agv_load_action()
                log.info("清理轿厢 {} 的卸货完成信号".format(sub_device.get_name()))

            if not await sub_device.is_wait_take_task() and await sub_device.require_reset_agv_unload_action():
                await sub_device.reset_agv_unload_action()
                log.info("清理轿厢 {} 的卸货完成信号".format(sub_device.get_name()))

            # ------------------------------------------------------------------------

            # 存板入库、取板出库
            if await sub_device.save_task_is_start_handle():
                # sub_device.report_save_task_handle_start()
                await sub_device.report_save_task_handle_finish()
                log.info("清理轿厢 {} 的取板任务确认信号".format(sub_device.get_name()))

            if await sub_device.take_task_is_start_handle():
                # sub_device.report_take_task_handle_start()
                await sub_device.report_take_task_handle_finish()
                log.info("清理轿厢 {} 的存板任务确认信号".format(sub_device.get_name()))

            # 如果轿厢不在对接层
            if not await sub_device.ready_docking():

                if await self.get_base_device().require_reset_agv_reverse_car_number():
                    await self.get_base_device().reset_agv_reverse_car_number()
                    log.info("清理轿厢 {} 的倒板任务信号".format(sub_device.get_name()))

                # ---------------------------------------
                if await sub_device.require_reset_agv_find_car_number():
                    await sub_device.reset_agv_find_car_number()
                    log.info("清理轿厢 {} 的自己寻找的上报板号信号".format(sub_device.get_name()))

                if await sub_device.require_reset_agv_unload_finish_car_number():
                    await sub_device.reset_agv_unload_finish_car_number()
                    log.info("清理轿厢 {} 的最终上报板号完成信号".format(sub_device.get_name()))

    async def run(self):

        self.load_sub_device()
        self.add_adapter_device_relation()

        asyncio.gather(
            # 心跳检测
            self.get_base_device().send_heartbeat(),
            self.get_base_device().recv_heartbeat(),
            # -------------------
            # 上报电池信息
            self.report_agv_battery_info(),
            # 上报错误信息
            self.report_agv_error_info(),
            # # 上报 agv 模式
            self.report_agv_state(),
            # # -------------------
            # 监听区域心跳
            # self.monitor_stop_heartbeat(),
            # 监听生成订单
            self.monitor_generate_order(),
            # 监听 agv 清错指令
            self.monitor_clear_error(),
            # 监听信号清理
            self.monitor_clear_signal()
        )
