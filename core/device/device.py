import typing
import asyncio

from bidict import bidict

from utils import log
from .implement import BaseDevice


class DeviceManager:

    def __init__(self) -> None:
        self._device_list = []

    def add(self, device):
        self._device_list.append(device)

    def get(self, device_name: str):
        for device in self.get_all_device():
            if device.get_name() == device_name:
                return device
        raise ValueError("attempt to get unknown device name: {}".format(device_name))

    def is_empty(self):
        return not bool(self._device_list)

    def delete(self, device_name: str):
        device = self.get(device_name)
        self._device_list.remove(device)

    def get_all_device(self):
        return self._device_list


class Device(BaseDevice):
    def __repr__(self) -> str:
        return "{} {}".format(__class__.__name__, self.get_name())

    async def send_heartbeat(self):
        """
        向 PLC 发送心跳，设定值：1-100
        每间隔 1s 发送一次心跳，用于通信检测
        """
        SEND_CONF = self.get_send_conf()["HEARTBEAT"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_MAX_VAL = SEND_CONF["MAX"]
        SEND_MIN_VAL = SEND_CONF["MIN"]

        cur_val = typing.cast(int, await self.safe_recv(SEND_ADDR))

        while True:
            if cur_val < SEND_MAX_VAL:
                await self.safe_send(SEND_ADDR, cur_val)
                cur_val += 1
            else:
                cur_val = SEND_MIN_VAL
            await asyncio.sleep(1)

    async def recv_heartbeat(self):
        """
        接收来自 PLC 心跳
        每间隔 1s 发送一次心跳，用于通信检测
        若值较上次值无变化、则记录 log
        """
        RECV_CONF = self.get_recv_conf()["HEARTBEAT"]
        RECV_ADDR = RECV_CONF["ADDRESS"]

        pre_updated_data = await self.safe_recv(RECV_ADDR)

        await asyncio.sleep(1)

        while True:
            cur_updated_data = await self.safe_recv(RECV_ADDR)
            if pre_updated_data == cur_updated_data:
                log.warning("check if {} is broken".format(self))

            pre_updated_data = cur_updated_data

            await asyncio.sleep(1)

    async def has_car(self, car_number):
        """
        车板上是否有车
        """
        RECV_CONF = self.get_recv_conf()["STORE_INFO"]
        RECV_ADDR = RECV_CONF["ADDRESS"] + int(car_number)

        return bool(typing.cast(int, await self.safe_recv(RECV_ADDR)))

    async def write_agv_mode(self, agv_id, mode):
        """
        写入 agv 的模式
            1. 自动（代表可执行任务）
            2. 运行中（代表不可执行任务）
        二者互斥

        在线且未执行订单（自动，网络状态是 true、调度状态为 7 或 9）
            - 休息位
            - 充电中
        """

        agv_id = str(agv_id)

        SEND_CONF = self.get_send_conf()["REPORT_AGV_MODE"]
        SEND_ADDR = SEND_CONF["ADDRESS"]

        SEND_BIT = SEND_CONF[agv_id]["BIT"][mode]

        PRE_VAL = await self.safe_recv(SEND_ADDR)
        NEW_VAL = PRE_VAL | (1 << SEND_BIT)
        if PRE_VAL != NEW_VAL:
            await self.safe_send(SEND_ADDR, NEW_VAL)

    async def reset_agv_mode(self, agv_id, mode):
        """
        重置 agv 的模式
        自动模式的位或者运行中模式的位写 0
        """

        agv_id = str(agv_id)

        SEND_CONF = self.get_send_conf()["REPORT_AGV_MODE"]
        SEND_ADDR = SEND_CONF["ADDRESS"]

        SEND_BIT = SEND_CONF[agv_id]["BIT"][mode]

        PRE_VAL = await self.safe_recv(SEND_ADDR)
        NEW_VAL = PRE_VAL & ~(1 << SEND_BIT)

        if PRE_VAL != NEW_VAL:
            await self.safe_send(SEND_ADDR, NEW_VAL)

    async def report_agv_error_code(self, agv_id, error_code):
        """
        上报 agv 的错误代码

        - 需要人工恢复的才报给对面
        """

        agv_id = str(agv_id)

        SEND_ADDR = self.get_send_conf()["REPORT_AGV_ERROR"][agv_id]["ADDRESS"]
        await self.safe_send(SEND_ADDR, error_code)

    async def report_agv_battery_info(self, agv_id, battery_info):
        """
        上报电池电量信息

        """
        agv_id = str(agv_id)

        SEND_ADDR = self.get_send_conf()["REPORT_AGV_BATTERY"][agv_id]["ADDRESS"]
        await self.safe_send(SEND_ADDR, battery_info)

    async def report_agv_target_car_number(self, agv_id, car_number):
        """
        上报当前 order 的 target location 和 agv id
        """
        agv_id = str(agv_id)

        SEND_ADDR = self.get_send_conf()["REPORT_CAR_ACTION"][agv_id]["ADDRESS"]

        log.info(
            "============== {} ============ report_agv_target_car_number =========== {} ===============".format(
                agv_id,
                car_number))

        await self.safe_send(SEND_ADDR, car_number)

    async def report_agv_reverse_car_number(self, car_number_list):
        """
        上报 agv 需要倒板的所有板号
        """

        SEND_CONF = self.get_send_conf()["REPORT_REVERSE_CAR_NUMBER"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_LENGTH = SEND_CONF["LENGTH"]

        car_number_list = [int(i) for i in car_number_list]

        if len(car_number_list) > SEND_LENGTH:
            log.warn("需要倒库的车板号上报的长度超过预留地址数量! 最大长度: {}, 当前上报长度: {}".format(SEND_LENGTH, len(car_number_list)))

        await self.safe_send(SEND_ADDR, car_number_list)

    async def require_reset_agv_reverse_car_number(self):
        """
        是否需要清理倒板任务的信号
        """
        RECV_CONF = self.get_send_conf()["REPORT_REVERSE_CAR_NUMBER"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        RECV_LENGTH = RECV_CONF["LENGTH"]

        rr = typing.cast(tuple, await self.safe_recv(RECV_ADDR, RECV_LENGTH))
        return any(rr)

    async def reset_agv_reverse_car_number(self):
        """
        清空 agv 需要倒板的库位号
        """
        SEND_CONF = self.get_send_conf()["REPORT_REVERSE_CAR_NUMBER"]
        SEND_LENGTH = SEND_CONF["LENGTH"]
        await asyncio.sleep(3)
        await self.report_agv_reverse_car_number(list(0 for i in range(SEND_LENGTH)))


class SubDeviceModeMinxin:
    """
    子设备的模式判断工具类
    """

    MODE_MAPPING = bidict({
        "MANUAL": 0,
        "AUTO": 1,
        "SEMI_AUTOMATIC": 2,
        "STOP": 3,
        "RESET": 4,
        "CONTINUE": 5,
        "CANCEL": 6,
    })

    @property
    def mode_mapping(self):
        return __class__.MODE_MAPPING

    async def mode_is_available(self, status):
        return self.mode_mapping.inverse[self.mode_mapping[status]] in await self.get_mode()

    async def mode_is_manual(self):
        return await self.mode_is_available("MANUAL")

    async def mode_is_auto(self):
        return await self.mode_is_available("AUTO")

    async def mode_is_semi_automatic(self):
        return await self.mode_is_available("SEMI_AUTOMATIC")

    async def mode_is_stop(self):
        return await self.mode_is_available("STOP")

    async def mode_is_reset(self):
        return await self.mode_is_available("RESET")

    async def mode_is_continue(self):
        return await self.mode_is_available("CONTINUE")

    async def mode_is_cancel(self):
        return await self.mode_is_available("CANCEL")

    async def mode_is_normal(self):
        """
        自动模式下未触发急停
        """
        return await self.mode_is_auto() and not await self.mode_is_stop()

    async def mode_is_abnormal(self):
        """
        不正常
        """
        return not await self.mode_is_normal()

    async def get_mode(self):
        """
        获得当前子设备的状态
        状态返回的是一个列表: ["自动", "急停", "继续执行"]
        """
        sub_device = typing.cast(SubDevice, self)

        # pylint: disable=no-member
        RECV_CONF = sub_device.get_recv_conf()["STATUS"]
        RECV_ADDR = RECV_CONF["ADDRESS"]

        rr = typing.cast(int, await sub_device.safe_recv(RECV_ADDR))

        device_status_list = []

        for pos in sorted(sub_device.mode_mapping.values(), reverse=True):
            if rr & (1 << pos) != 0:
                device_status = sub_device.mode_mapping.inverse[pos]
                device_status_list.append(device_status)

        return device_status_list


class SubDevice(BaseDevice, SubDeviceModeMinxin):
    def __repr__(self) -> str:
        return "{} {}".format(__class__.__name__, self.get_name())

    async def ready_docking(self):
        """
        获取当前子设备是否在对接层准备就绪

        - 是否有门？
        """
        # TODO: 待验证  - 2023-07-25 -
        RECV_CONF = self.get_recv_conf()["COMMAND"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        RECV_BIT = RECV_CONF["BIT"]["DOCKED"]

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))
        return bool(rr & (1 << RECV_BIT))

    async def get_the_level(self):
        """
        获取子设备当前所在的层级
        """
        RECV_CONF = self.get_recv_conf()["LEVEL"]
        RECV_ADDR = RECV_CONF["ADDRESS"]

        return typing.cast(int, await self.safe_recv(RECV_ADDR))

    # ---------------
    async def has_save_car_task(self):
        """
        当前子设备是否拥有一个存板任务？（入库）
        """
        RECV_CONF = self.get_recv_conf()["COMMAND"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        RECV_BIT = RECV_CONF["BIT"]["SAVE"]

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))
        return bool(rr & (1 << RECV_BIT))

    async def has_take_car_task(self):
        """
        当前子设备是否拥有一个取板任务？（出库）
        """
        RECV_CONF = self.get_recv_conf()["COMMAND"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        RECV_BIT = RECV_CONF["BIT"]["TAKE"]

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))
        return bool(rr & (1 << RECV_BIT))

    async def is_wait_save_task(self):
        """
        当前子设备是否在等待存板（入库）
        """
        RECV_CONF = self.get_recv_conf()["COMMAND"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        RECV_BIT = RECV_CONF["BIT"]["WAIT_SAVE"]

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))

        return bool(rr & (1 << RECV_BIT))

    async def is_wait_take_task(self):
        """
        当前子设备是否在等待取板（出库）
        """
        RECV_CONF = self.get_recv_conf()["COMMAND"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        RECV_BIT = RECV_CONF["BIT"]["WAIT_TAKE"]

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))

        return bool(rr & (1 << RECV_BIT))

    async def get_save_car_number(self):
        """
        获取存板号（终点库位）
        电梯库位 -> 终点库位
        """
        RECV_CONF = self.get_recv_conf()["SAVE_NUMBER"]
        RECV_ADDR = RECV_CONF["ADDRESS"]

        return typing.cast(int, await self.safe_recv(RECV_ADDR))

    async def get_take_car_number(self):
        """
        获取取板号（起点库位）
        起点库位 -> 电梯库位
        """
        RECV_CONF = self.get_recv_conf()["TAKE_NUMBER"]
        RECV_ADDR = RECV_CONF["ADDRESS"]

        return typing.cast(int, await self.safe_recv(RECV_ADDR))

    # --------------
    async def save_task_is_start_handle(self):
        """
        存板任务是否已经开始处理
        """
        RECV_CONF = self.get_send_conf()["ORDER_HANDLE"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        RECV_BIT = RECV_CONF["BIT"]["SAVE_CAR_HANDLE"]

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))
        return bool(rr & (1 << RECV_BIT) != 0)

    async def take_task_is_start_handle(self):
        """
        取板任务是否已经开始处理
        """
        RECV_CONF = self.get_send_conf()["ORDER_HANDLE"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        RECV_BIT = RECV_CONF["BIT"]["TAKE_CAR_HANDLE"]

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))
        return bool(rr & (1 << RECV_BIT) != 0)

    # --------------

    async def report_save_task_handle_start(self):
        """
        上报存板任务已被处理
        （接收到命令后发送）
        """
        SEND_CONF = self.get_send_conf()["ORDER_HANDLE"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_BIT = SEND_CONF["BIT"]["SAVE_CAR_HANDLE"]

        PRE_VAL = await self.safe_recv(SEND_ADDR)
        NEW_VAL = PRE_VAL | (1 << SEND_BIT)

        if PRE_VAL != NEW_VAL:
            await self.safe_send(SEND_ADDR, NEW_VAL)

    async def report_take_task_handle_start(self):
        """
        上报取板任务已被处理
        （接收到命令后发送）
        """
        SEND_CONF = self.get_send_conf()["ORDER_HANDLE"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_BIT = SEND_CONF["BIT"]["TAKE_CAR_HANDLE"]

        PRE_VAL = await self.safe_recv(SEND_ADDR)
        NEW_VAL = PRE_VAL | (1 << SEND_BIT)

        if PRE_VAL != NEW_VAL:
            await self.safe_send(SEND_ADDR, NEW_VAL)

    async def report_save_task_handle_finish(self):
        """
        上报存板任务已处理完成，置为 0
        （agv 订单处理完成后进行）
        """
        SEND_CONF = self.get_send_conf()["ORDER_HANDLE"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_BIT = SEND_CONF["BIT"]["SAVE_CAR_HANDLE"]

        PRE_VAL = await self.safe_recv(SEND_ADDR)
        NEW_VAL = PRE_VAL & ~(1 << SEND_BIT)

        if PRE_VAL != NEW_VAL:
            await self.safe_send(SEND_ADDR, NEW_VAL)

    async def report_take_task_handle_finish(self):
        """
        上报取板任务已处理完成，置为 0
        （agv 订单处理完成后进行）
        """
        SEND_CONF = self.get_send_conf()["ORDER_HANDLE"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_BIT = SEND_CONF["BIT"]["TAKE_CAR_HANDLE"]

        PRE_VAL = await self.safe_recv(SEND_ADDR)
        NEW_VAL = PRE_VAL & ~(1 << SEND_BIT)

        if PRE_VAL != NEW_VAL:
            await self.safe_send(SEND_ADDR, NEW_VAL)

    # -----------
    async def report_agv_load_action_start(self):
        """
        上报 agv 的取货动作开始（入库、存板任务）
        """
        SEND_CONF = self.get_send_conf()["LOAD_ACTION"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_VALUE = SEND_CONF["VALUES"]["START"]

        await self.safe_send(SEND_ADDR, SEND_VALUE)

    async def report_agv_load_action_finish(self):
        """
        上报 agv 的取货动作完成（入库、存板任务）
        """
        SEND_CONF = self.get_send_conf()["LOAD_ACTION"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_VALUE = SEND_CONF["VALUES"]["FINISH"]

        await self.safe_send(SEND_ADDR, SEND_VALUE)

    async def require_reset_agv_load_action(self):
        """
        是否需要清理 agv 的取货动作信号
        """
        RECV_CONF = self.get_send_conf()["LOAD_ACTION"]
        RECV_ADDR = RECV_CONF["ADDRESS"]

        MATCH_VALUE = RECV_CONF["VALUES"]["FINISH"]

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))

        return bool(rr == MATCH_VALUE)

    async def reset_agv_load_action(self):
        """
        重置 agv 取货动作的信号位（入库、存板任务）
        完成信号当轿厢就绪信号OFF或轿厢到达二层后清除。
        """
        SEND_CONF = self.get_send_conf()["LOAD_ACTION"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_VALUE = SEND_CONF["VALUES"]["CLEAR"]

        await self.safe_send(SEND_ADDR, SEND_VALUE)

    # -------------

    async def report_agv_unload_action_start(self):
        """
        上报 agv 的卸动作开始（出库、取板任务）
        """
        SEND_CONF = self.get_send_conf()["UNLOAD_ACTION"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_VALUE = SEND_CONF["VALUES"]["START"]

        await self.safe_send(SEND_ADDR, SEND_VALUE)

    async def report_agv_unload_action_finish(self):
        """
        上报 agv 的卸动作完成（出库、取板任务）
        """
        SEND_CONF = self.get_send_conf()["UNLOAD_ACTION"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_VALUE = SEND_CONF["VALUES"]["FINISH"]

        await self.safe_send(SEND_ADDR, SEND_VALUE)

    async def require_reset_agv_unload_action(self):
        """
        是否需要清理 agv 的卸货动作信号
        """
        RECV_CONF = self.get_send_conf()["UNLOAD_ACTION"]
        RECV_ADDR = RECV_CONF["ADDRESS"]

        MATCH_VALUE = RECV_CONF["VALUES"]["FINISH"]

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))
        return bool(rr == MATCH_VALUE)

    async def reset_agv_unload_action(self):
        """
        重置 agv 卸货动作的信号位（出库、取板任务）
        完成信号当轿厢就绪信号 OFF 或轿厢到达二层后清除
        """
        SEND_CONF = self.get_send_conf()["UNLOAD_ACTION"]
        SEND_ADDR = SEND_CONF["ADDRESS"]
        SEND_VALUE = SEND_CONF["VALUES"]["CLEAR"]

        await self.safe_send(SEND_ADDR, SEND_VALUE)

    # -------------

    async def report_agv_unload_finish_car_number(self, car_number):
        """
        上报 agv 最终放入轿厢的板号（出库、取板任务）
        agv 放下板至轿厢中时，上报
        """
        SEND_CONF = self.get_send_conf()["CAR_FINISH_NUMBER"]
        SEND_ADDR = SEND_CONF["ADDRESS"]

        await self.safe_send(SEND_ADDR, car_number)

    async def require_reset_agv_unload_finish_car_number(self):
        """
        是否需要清理 agv 卸货后最终放入轿厢的板号
        """
        RECV_CONF = self.get_send_conf()["CAR_FINISH_NUMBER"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        MATCH_VALUE = 0

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))
        return bool(rr != MATCH_VALUE)

    async def reset_agv_unload_finish_car_number(self):
        """
        重置 agv 最终放入轿厢的板号（出库、取板任务）
        当轿厢就绪信号 OFF 或轿厢到达二层后清除
        """
        await self.report_agv_unload_finish_car_number(0)

    async def report_agv_find_car_number(self, car_number):
        """
        取板任务时 agv 找到空车板后进行上报
        """
        SEND_CONF = self.get_send_conf()["REPORT_FIND_CAR_NUMBER"]
        SEND_ADDR = SEND_CONF["ADDRESS"]

        await self.safe_send(SEND_ADDR, car_number)

    async def require_reset_agv_find_car_number(self):
        """
        是否需要清理 agv 找到的车板号
        """
        RECV_CONF = self.get_send_conf()["REPORT_FIND_CAR_NUMBER"]
        RECV_ADDR = RECV_CONF["ADDRESS"]
        MATCH_VALUE = 0

        rr = typing.cast(int, await self.safe_recv(RECV_ADDR))
        return bool(rr != MATCH_VALUE)

    async def reset_agv_find_car_number(self):
        """
        重置 agv 找到的空车板车板号（出库、取板任务）
        当轿厢就绪信号 OFF 或轿厢到达二层后清除
        """
        await self.report_agv_find_car_number(0)
