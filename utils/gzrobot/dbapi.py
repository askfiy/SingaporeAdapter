from utils import aiopg

async def update_io_state(io_id):
    UPDATE_IO_STATE = """
        UPDATE layer1_agv.io_state
        SET
           last_updated_timestamp = now(),
          io_status_id = 22
        WHERE
          io_id = $1;
    """

    return await aiopg.execute(UPDATE_IO_STATE, io_id)


async def upsert_gp(key, value):
    UPSERT_GLOBAL_PARAMETERS = """
        INSERT INTO
          layer4_1_om.globalparameters(gp_name, gp_value, gp_value_type)
        VALUES
            ($1, $2, 'str') ON CONFLICT (gp_name) DO
        UPDATE
            SET
                gp_value = $2;
    """
    return await aiopg.execute(UPSERT_GLOBAL_PARAMETERS, key, value)


async def gp_is_exists(key):
    SELECT_GLOBAL_PARAMTERS = """
        SELECT
          gp_id
        FROM
          layer4_1_om.globalparameters
        WHERE
          gp_name = $1
        LIMIT
          1;
    """
    return bool(await aiopg.fetch(SELECT_GLOBAL_PARAMTERS, key))


async def delete_gp(key):
    DELETE_GLOBAL_PARAMTERS = """
    DELETE FROM layer4_1_om.globalparameters
    WHERE
      gp_name = $1;
    """

    return await aiopg.execute(DELETE_GLOBAL_PARAMTERS, key)


async def get_gp_value(key):
    SELECT_GLOBAL_PARAMTERS_VALUE = """
        SELECT
          gp_value
        FROM
          layer4_1_om.globalparameters
        WHERE
          gp_name = $1
        LIMIT
          1;
    """
    rr = await aiopg.fetch(SELECT_GLOBAL_PARAMTERS_VALUE, key)
    return rr[0].get("gp_value")


async def agv_has_rest_task(agv_id):
    agv_id = int(agv_id)
    SELECT_AGV_STATE = """
        SELECT
          agv_management_status_id
        FROM
          layer1_agv.agv_state
        WHERE
          agv_id = $1
        LIMIT
      1;
    """
    rr = await aiopg.fetch(SELECT_AGV_STATE, agv_id)
    return rr[0].get("agv_management_status_id") == 7


async def agv_has_charging_task(agv_id):
    agv_id = int(agv_id)
    SELECT_AGV_STATE = """
        SELECT
          is_charging
        FROM
          layer1_agv.agv_state
        WHERE
          agv_id = $1
        LIMIT
      1;
    """
    rr = await aiopg.fetch(SELECT_AGV_STATE, agv_id)
    return rr[0].get("is_charging")


async def get_all_agv_state():
    """
    network_connected: 在线状态
    can_be_connected: 可以连接
    dispatch_task_active: 有调度任务（包含充电任务）
    fault_happened: 有报错
    """
    SELECT_AGV_STATE = """
        SELECT
          layer2_pallet.agv_dispatch_state.agv_id,
          can_be_connected,
          network_connected,
          dispatch_task_active,
          fault_happened
        FROM
          layer1_agv.agv_state
          INNER JOIN layer2_pallet.agv_dispatch_state ON layer1_agv.agv_state.agv_id = layer2_pallet.agv_dispatch_state.agv_id;
    """
    return await aiopg.fetch(SELECT_AGV_STATE)

async def agv_has_active_order(agv_id):
    agv_id = int(agv_id)

    SELECT_AGV_ORDER = """
        SELECT
          order_id
        FROM
          layer4_1_om.order
        WHERE
          $1 = ANY (agv_list)
          AND status NOT IN (
            'finish',
            'error',
            'cancel_finish',
            'waiting_cancel',
            'waiting_manually_finish',
            'manually_finish',
            'error_hidden'
          )
    """

    return await aiopg.fetch(SELECT_AGV_ORDER, agv_id)
