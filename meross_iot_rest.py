#!/usr/bin/python3
import asyncio
import logging
from get_docker_secret import get_docker_secret

from flask import Flask
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus

EMAIL = get_docker_secret('meross_email')
PASSWORD = get_docker_secret('meross_password')

app = Flask(__name__)


async def sockets_operation_async(operation, socket_no):
    meross_root_logger = logging.getLogger("meross_iot")
    meross_root_logger.setLevel(logging.WARNING)
    http_api_client = await MerossHttpClient.async_from_user_password(api_base_url='https://iotx-eu.meross.com',
                                                                      email=EMAIL,
                                                                      password=PASSWORD)
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    await manager.async_device_discovery()

    sockets = manager.find_devices(device_type="mss620", online_status=OnlineStatus.ONLINE)
    if len(sockets) == 1:
        socket = sockets[0]
        await socket.async_update()

        if operation == 'on':
            await socket.async_turn_on(channel=socket_no)
        elif operation == 'off':
            await socket.async_turn_off(channel=socket_no)
        else:
            status = socket.is_on()
            if status:
                await socket.async_turn_off(channel=socket_no)
            else:
                await socket.async_turn_on(channel=socket_no)

    manager.close()
    await http_api_client.async_logout()


@app.route('/', methods=['GET'])
def index():
    return 'Hello to MerossIOT REST!'


@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    return 'OK', 200


@app.route('/sockets/<operation>', methods=['GET'])
@app.route('/sockets/<operation>/<socket>', methods=['GET'])
def sockets_operation(operation, socket=0):
    if EMAIL is None or PASSWORD is None:
        return 'nOK', 500
    if operation in ('on', 'off', 'toggle'):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(sockets_operation_async(operation, socket))
        loop.stop()
        return 'ok', 202
    else:
        return 'nOK', 400
