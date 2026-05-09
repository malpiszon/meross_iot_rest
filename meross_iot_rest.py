#!/usr/bin/python3
import asyncio
import json
import logging
import os
import signal
import threading
import urllib.error
import urllib.request
from queue import Queue, Empty
from datetime import datetime, timezone
from typing import Tuple
from get_docker_secret import get_docker_secret

from flask import Flask, jsonify
from meross_iot.controller.device import BaseDevice
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from waitress import serve

EMAIL = get_docker_secret('meross_email')
PASSWORD = get_docker_secret('meross_password')
DISCORD_WEBHOOK_URL = get_docker_secret('discord_webhook_url')
API_BASE_URL = os.environ.get('MEROSS_API_BASE_URL', 'https://iotx-eu.meross.com')  # Default URL
APP_NAME = os.environ.get('APP_NAME', 'MerossIOT REST')
DISCORD_COLOR_SUCCESS = 0x2ECC71
DISCORD_COLOR_ERROR = 0xE74C3C

# --- Logging ---
logging_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
root_logger = logging.getLogger()
for h in root_logger.handlers[:]:
    h.setFormatter(logging_formatter)
root_logger.setLevel(logging.INFO)

# --- Queue for device operations ---
device_operations_queue: Queue = Queue()
# --- App should be stopped by signal ---
signal_queue: Queue = Queue()
# --- Meross initialization flag ---
meross_initialized = False

app = Flask(__name__)


def send_discord_notification(title: str, message: str, color: int) -> None:
    if not DISCORD_WEBHOOK_URL:
        return

    payload = {
        "username": APP_NAME,
        "embeds": [
            {
                "title": title,
                "description": message,
                "color": color,
                "footer": {"text": APP_NAME},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }

    request = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status >= 400:
                logging.warning("Discord notification failed with status %s.", response.status)
    except urllib.error.HTTPError as e:
        logging.warning("Discord notification failed with status %s.", e.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        logging.warning("Discord notification could not be sent.")


def notify_business_event(title: str, message: str) -> None:
    send_discord_notification(title, message, DISCORD_COLOR_SUCCESS)


def notify_error(title: str, message: str = "An error occurred. Check the application logs.") -> None:
    send_discord_notification(title, message, DISCORD_COLOR_ERROR)


def signal_handler(signum, frame):
    logging.info(f"Signal {signum} received. Starting the shut down process.")
    notify_business_event("App shutdown requested", "The MerossIOT REST app received a shutdown signal.")
    signal_queue.put(signum)


def run_asyncio_loop_forever(asyncio_loop):
    asyncio.set_event_loop(asyncio_loop)
    asyncio_loop.run_forever()


def get_device(manager: MerossManager) -> BaseDevice | None:
    # device_type="mss620" - this is a specific model with two outlets.
    devices = manager.find_devices(device_type="mss620", online_status=OnlineStatus.ONLINE)

    if not devices:
        logging.error(f"No Meross devices found.")
        notify_error("Meross device unavailable", "No supported online Meross device was found.")
        return None

    if len(devices) != 1:
        logging.error(f"Found {len(devices)} devices - should be one.")
        notify_error("Meross device configuration issue", "More than one supported online Meross device was found.")
        return None

    return devices[0]


async def devices_operation_async(device, operation, socket_no):
    try:
        await device.async_update()
        if operation == 'on':
            await device.async_turn_on(channel=socket_no)
            logging.info(f"Turned on socket {socket_no}.")
        elif operation == 'off':
            await device.async_turn_off(channel=socket_no)
            logging.info(f"Turned off socket {socket_no}.")
        elif operation == 'toggle':
            await device.async_toggle(channel=socket_no)
            logging.info(f"Toggled socket {socket_no}.")
        else:
            logging.error(f"Invalid operation: {operation}")
            notify_error("Invalid Meross operation requested", "An unsupported device operation was requested.")
    except Exception as e:
        logging.exception(f"Error during devices operation: {e}")
        notify_error("Meross device operation failed")


async def initialise_meross() -> Tuple[MerossManager, MerossHttpClient]:
    global meross_initialized
    logging.info("Starting Meross main loop.")
    try:
        if not EMAIL:
            logging.error("Meross email not set.")
            raise ValueError("Meross email not set.")
        if not PASSWORD:
            logging.error("Meross password not set.")
            raise ValueError("Meross password not set.")
        http_api_client = await MerossHttpClient.async_from_user_password(
            api_base_url=API_BASE_URL,
            email=EMAIL,
            password=PASSWORD
        )
        manager = MerossManager(http_client=http_api_client)

        await manager.async_device_discovery()
        logging.info("Meross connection initialized successfully.")
        meross_initialized = True

        return manager, http_api_client
    except Exception as e:
        logging.error(f"Failed to initialize Meross connection: {e}")
        meross_initialized = False
        notify_error("Meross initialization failed", "The app could not initialize the Meross connection.")
        raise


async def run_main_meross_loop(manager: MerossManager):
    device = get_device(manager)  # for now only 1 device supported: mss620

    logging.info("Starting main Meross operations loop.")
    while device:
        try:
            signal_data = signal_queue.get(block=False)
            if signal_data:
                break
        except Empty:
            pass

        try:
            operation, socket_no = device_operations_queue.get(timeout=1)
            logging.info(f"Handling operation: {operation}, socket: {socket_no}, device: {device.type}")
            await devices_operation_async(device, operation, socket_no)
            device_operations_queue.task_done()
        except Empty:
            pass
        except Exception as e:
            logging.error(f"Error handling device operation: {e}")
            notify_error("Meross operation handling failed")


async def stop_meross(manager: MerossManager, http_api_client: MerossHttpClient):
    global meross_initialized
    logging.info("Stopping Meross main loop.")
    try:
        meross_initialized = False
        if manager:
            manager.close()
        if http_api_client:
            await http_api_client.async_logout()
        logging.info("Meross connection closed.")
    except Exception as e:
        logging.error(f"Error closing manager: {e}")
        notify_error("Meross shutdown failed", "The app could not cleanly close the Meross connection.")


async def run_meross_loop():
    manager, http_api_client = await initialise_meross()
    await run_main_meross_loop(manager)
    await stop_meross(manager, http_api_client)


@app.route('/', methods=['GET'])
def index():
    return 'Hello to MerossIOT REST!', 200


@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    if meross_initialized:
        return jsonify({"status": "OK"}), 200
    else:
        return jsonify({"status": "Meross loop not initialised"}), 500


@app.route('/sockets/<operation>', methods=['GET'])
@app.route('/sockets/<operation>/<socket_no>', methods=['GET'])
def sockets_operation(operation, socket_no=0):
    try:
        socket_no = int(socket_no)
        # For mss620 socket numbers are between 1 and 2; 0 for all sockets
        if socket_no < 0 or socket_no > 2:
            return jsonify({"error": "Socket number out of bounds"}), 400

        allowed_operations = {"on", "off", "toggle"}
        if operation not in allowed_operations:
            return jsonify({"error": "Invalid operation"}), 400

    except ValueError:
        return jsonify({"error": "Invalid socket number"}), 400

    device_operations_queue.put((operation, socket_no))
    return jsonify({"status": "Operation queued"}), 202


if __name__ == '__main__':
    logging.info("Starting Meross initialization.")
    notify_business_event("App started", "The MerossIOT REST app has started.")
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        asyncio_thread = threading.Thread(target=run_asyncio_loop_forever, args=(loop,))
        asyncio_thread.daemon = True
        asyncio_thread.start()
        asyncio.run_coroutine_threadsafe(run_meross_loop(), loop)
        serve(app, host='0.0.0.0', port=8080)
    except Exception as e:
        logging.error(f"Unexpected error {e}")
        notify_error("Unexpected app error")
    finally:
        logging.info("Shutting down app.")
        notify_business_event("App stopped", "The MerossIOT REST app is shutting down.")
        loop.stop()
