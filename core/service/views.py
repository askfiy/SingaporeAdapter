import enum
import typing
import asyncio

from aiohttp import web

from utils import log

from core.adapter import DeviceAdapterManager
from core.device import Device, SubDevice

from .resp import JsonResponse
from .urls import routes


@routes.get("/")
async def index(request: web.Request):
    return "hello world"


@routes.get("/car/{car_number}/")
async def has_car(request: web.Request):
    """
    查询车板身上是否有货
    """
    try:

        car_number = int(request.match_info["car_number"])

        # 获取基础设备
        device = typing.cast(Device, DeviceAdapterManager.get("basic"))

        rr = await device.has_car(car_number)

        return await JsonResponse(
            code=0,
            msg="查询车板号 {} 上是否有车 {}".format(car_number, rr),
            data=rr
        )

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误"
        )


@routes.post("/report_agv_target_car_number/")
async def report_agv_target_car_number(request: web.Request):
    """
    上报 agv 运行状态中身上的车版号
    """
    try:

        req_data = await request.json()

        car_number = req_data["car_number"]
        agv_id = req_data["agv_id"]

        # 获取基础设备
        device = typing.cast(Device, DeviceAdapterManager.get("basic"))

        await device.report_agv_target_car_number(agv_id, car_number)

        if car_number != 0:
            info = "请求成功, agv {} 上报本次任务的目标车板号 {}".format(agv_id, car_number)
        else:
            info = "请求成功, agv {} 清除本次任务的目标的车板号".format(agv_id)

        return await JsonResponse(
            code=0,
            msg=info
        )

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误"
        )


@routes.post("/report_agv_find_car_number/")
async def report_agv_find_car_number(request: web.Request):
    """
    上报 agv 最终卸货到轿厢中的车板号
    """
    try:

        req_data = await request.json()

        device_name = req_data["device_name"]
        car_number = req_data["car_number"]

        device = typing.cast(SubDevice, DeviceAdapterManager.get(device_name))

        await device.report_agv_find_car_number(car_number)

        return await JsonResponse(
            code=0,
            msg="请求成功, agv 找到放入 {} 的取车板号 {}".format(device_name, car_number)
        )

    except KeyError as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求成功, 无效的设备名称 {}，请检查配置是否正确".format(device_name)
        )

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误"
        )


@routes.post("/report_agv_reverse_car_number/")
async def report_agv_reverse_car_number(request: web.Request):
    """
    上报 agv 需要倒板的所有板号
    """
    try:

        req_data = await request.json()

        car_number_list = req_data["car_number_list"]

        # 获取基础设备
        device = typing.cast(Device, DeviceAdapterManager.get("basic"))

        await device.report_agv_reverse_car_number(car_number_list)

        return await JsonResponse(
            code=0,
            msg="上报需要倒库的车板号成功: {}".format(car_number_list),
        )

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误"
        )


@routes.post("/report_agv_unload_finish_car_number/")
async def report_agv_unload_finish_car_number(request: web.Request):
    """
    上报 agv 最终卸货到轿厢中的车板号
    """
    try:

        req_data = await request.json()

        device_name = req_data["device_name"]
        car_number = req_data["car_number"]

        device = typing.cast(SubDevice, DeviceAdapterManager.get(device_name))

        await device.report_agv_unload_finish_car_number(car_number)

        return await JsonResponse(
            code=0,
            msg="请求成功, 上报轿厢 {} 放入的车板号 {}".format(device_name, car_number)
        )

    except KeyError as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求成功, 无效的设备名称 {}，请检查配置是否正确".format(device_name)
        )

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误"
        )


@routes.post("/ssio/heartbeat/")
async def heartbeat(request: web.Request):
    try:

        req_data = await request.json()
        device_name = req_data["device_name"]

        device = typing.cast(SubDevice, DeviceAdapterManager.get(device_name))

        is_stop = device.mode_is_stop()

        if is_stop:
            return await JsonResponse(
                code=0,
                msg="轿厢 {} 已暂停, 心跳区域生效".format(device_name)
            )

        return await JsonResponse(
            code=1,
            msg="轿厢 {} 未暂停, 不触发区域心跳".format(device_name)
        )

    except KeyError as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 无效的设备名称 {}，请检查配置是否正确".format(device_name)
        )
    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误 "
        )


@routes.post("/ssio/request/in/")
async def ssio_request_in(request: web.Request):
    """
    这里请求进入需要和轿厢做真正意义上的交互、因为我们要确保轿厢真正的停靠在了对接层
    {
        "device_name": "lift-a",
        "action": "load"
    }
    """
    try:

        req_data = await request.json()

        device_name = req_data["device_name"]

        # 动作（load、unload）
        request_action = req_data["action"]

        device = typing.cast(SubDevice, DeviceAdapterManager.get(device_name))

        is_ready = int(await device.ready_docking())

        if is_ready:

            # --------------------

            # 给出进入轿厢的信号

            if request_action == "load":
                log.info("轿厢 {} 已给出进入取货动作".format(device_name))
                await device.report_agv_load_action_start()

            if request_action == "unload":
                log.info("轿厢 {} 已给出进入卸货动作".format(device_name))
                await device.report_agv_unload_action_start()

            # --------------------

            return await JsonResponse(
                code=0,
                msg="请求成功, 轿厢 {} 已就绪、允许进入".format(device_name)
            )

        return await JsonResponse(
            code=1,
            msg="请求成功, 轿厢 {} 未就绪、不允许进入".format(device_name)
        )

    except KeyError as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 无效的设备名称 {}，请检查配置是否正确".format(device_name)
        )

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误"
        )


@routes.post("/deprecate/ssio/request/action/")
async def dep_ssio_request_action(request: web.Request):
    """
    这里其实并不需要轿厢进行实际的允许、我们只需要将数据写入即可
    {
        "device_name": "lift-a",
        "action": "load"
    }

    已弃用（合并在请求进入接口中）
    """
    try:
        req_data = await request.json()

        # 轿厢
        device_name = req_data["device_name"]

        # 动作（load、unload）
        request_action = req_data["action"]

        device = typing.cast(SubDevice, DeviceAdapterManager.get(device_name))

        if request_action == "load":
            await device.report_agv_load_action_start()
            return await JsonResponse(
                code=0,
                err="请求成功, 轿厢 {} 允许请求取货动作".format(device_name)
            )
        if request_action == "unload":
            await device.report_agv_unload_action_start()
            return await JsonResponse(
                code=0,
                err="请求成功, 轿厢 {} 允许请求卸货动作".format(device_name)
            )

        return await JsonResponse(
            code=1,
            err="请求失败, 无效的请求动作 {}, 期望得到 load 或者 unload".format(request_action)
        )

    except KeyError as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 无效的设备名称 {}，请检查配置是否正确".format(device_name)
        )

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误 "
        )


@routes.post("/ssio/request/level/")
async def ssio_request_level(request: web.Request):
    """
    同上，不需要轿厢实际的允许
    {
        "device_name": "lift-a",
        "action": "load"
    }
    """
    try:
        req_data = await request.json()

        # 轿厢
        device_name = req_data["device_name"]
        # 动作（load、unload）
        request_action = req_data["action"]

        device = typing.cast(SubDevice, DeviceAdapterManager.get(device_name))

        if request_action == "load":
            await device.report_agv_load_action_finish()
            return await JsonResponse(
                code=0,
                err="请求成功, 轿厢 {} 允许请求取货离开".format(device_name)
            )

        if request_action == "unload":
            await device.report_agv_unload_action_finish()
            return await JsonResponse(
                code=0,
                err="请求成功, 轿厢 {} 允许请求卸货离开".format(device_name)
            )

        return await JsonResponse(
            code=1,
            err="请求失败, 无效的请求动作 {}, 期望得到 load 或者 unload".format(request_action)
        )

    except KeyError as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 无效的设备名称 {}，请检查配置是否正确".format(device_name)
        )

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误, 可能的原因"
        )


# --------------------------------------------------------------------


@routes.post("/deprecate/report_task_finish/")
async def dep_report_task_finish(request: web.Request):
    # DEP: 弃用接口（现改为对面任务信号清除后由 adapter 中进行清除）
    """
    上报任务结束, 用于清理 task 的订单:
        {
            "device_name": "lift-a",
            "task_code": 1000
        }
    """
    try:
        req_data = await request.json()

        device_name = req_data["device_name"]
        task_code = req_data["task_code"]

        device = typing.cast(SubDevice, DeviceAdapterManager.get(device_name))

        if 1000 == task_code:
            await device.report_take_task_handle_finish()
            return await JsonResponse(
                code=0,
                msg="请求成功, 指定取板任务已完成"
            )

        if 2000 == task_code:
            await device.report_take_task_handle_finish()
            return await JsonResponse(
                code=0,
                msg="请求成功, 非指定取板任务已完成"
            )

        if 3000 == task_code:
            await device.report_save_task_handle_finish()
            return await JsonResponse(
                code=0,
                msg="请求成功, 存板任务已完成"
            )

        return await JsonResponse(
            code=1,
            err="请求失败, 未知的任务编号: {}".format(task_code)
        )

    except KeyError as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 无效的设备名称 {}，请检查配置是否正确".format(device_name)
        )

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return await JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误"
        )


@routes.post("/deprecate/agvStateReport/")
async def dep_report_agv_status(request: web.Request):
    # DEP: 弃用接口（现改为从数据库中获取 agv 的状态信息并通过 adapter 进行上报）
    """
    {
        "agvID": 2,
        "agvStatusID": 3,
        "lastAgvStatusID": 1,
        "canBeConnected": 1,
        "netConnected": 1,
        "dispatchTaskActive": 0,
        "faultHappened": 0,
        "safetyInformation": "bank_id:0 enable:0 status:normal",
        "isBlocked": 0,
        "blockedByAgvId": 2,
        "blockInformation": "null",
        "networkStatus": 0,
        "isCharging": 0,
        "safetyTriggered": 0,
        "trafficStatus": 0,
        "safetyEnabled": false,
        "bankId": "{\"cur_bank_id\":0,\"cur_bank_level\":0,\"enable\":1,\"enabled\":0,\"manual_bank_id\":0,\"manual_bank_level\":0,\"safety_result\":0,\"sensor_trrigered\":{\"data_src_channel\":true,\"dev_data_type\":0,\"result\":0,\"sensor\":\"\",\"src_dev_id\":0,\"src_dev_type\":0}}\n",
        "startSoc": 0,
        "endSoc": 0,
        "lastUpdatedTS": "2023-07-25 17:11:27.586923+08",
        "extraInfo1": "",
        "extraInfo2": ""
    }


    根据 netConnected 判断 agv 是否联网
        1 是联网

    根据 faultHappened 判断 agv 是否有报错
        1 是有报错

    上面 2 个条件都满足，则判断 dispatchTaskActive 字段判断是否有任务
        1 代表有任务，不可指派任nvim务

    上面 2 个条件都满足，则判断 isCharging 字段判断是否在充电
        1 代表在充电
    """

    class AGV_STATE(enum.StrEnum):
        AUTO = "AUTO"
        RUNNING = "RUNNING"

    from utils.gzrobot import dbapi

    try:
        req_data = await request.json()

        agv_id = req_data["agvID"]
        is_connected = 1 == req_data["netConnected"]
        has_error = 1 == req_data["faultHappened"]
        has_dispatch_task = 1 == req_data["dispatchTaskActive"]
        has_charging_task = 1 == req_data["isCharging"]
        has_rest_task = await dbapi.agv_has_charging_task(agv_id)

        # 获取设备
        device = typing.cast(Device, DeviceAdapterManager.get("basic"))

        if not is_connected:

            await device.reset_agv_mode(agv_id, AGV_STATE.AUTO)
            return await JsonResponse(code=0, msg="请求成功, agv {} 未连接, 取消「自动」模式".format(agv_id))

        if has_error:
            await device.reset_agv_mode(agv_id, AGV_STATE.AUTO)
            return await JsonResponse(code=0, msg="请求成功, agv {} 有报错, 取消「自动」模式".format(agv_id))

        if has_dispatch_task:

            # 充电任务是可以被打断的
            if has_charging_task:
                await device.write_agv_mode(agv_id, AGV_STATE.AUTO)
                return await JsonResponse(code=0, msg="请求成功, agv {} 有充电任务, 上报为「自动」模式".format(agv_id))

            if has_rest_task:
                await device.write_agv_mode(agv_id, AGV_STATE.AUTO)
                return await JsonResponse(code=0, msg="请求成功, agv {} 有休息任务, 上报为「自动」模式".format(agv_id))

            await device.write_agv_mode(agv_id, AGV_STATE.RUNNING)
            return await JsonResponse(code=0, msg="请求成功, agv {} 有非充电任务, 上报为「运行」中模式".format(agv_id))

        await device.write_agv_mode(agv_id, AGV_STATE.AUTO)
        return await JsonResponse(code=0, msg="请求成功, agv {} 无任务、上报为「自动」模式".format(agv_id))

    except Exception as e:
        asyncio.get_running_loop().call_exception_handler({"exception": e})
        return JsonResponse(
            code=1,
            err="请求失败, 在请求过程中发生了一些错误请求失败"
        )
