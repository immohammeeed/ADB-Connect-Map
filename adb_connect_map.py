import argparse
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional


def adb_command(command: str) -> Optional[str]:
    """
    Executes an ADB command and returns the output as a string.
    
    Args:
        command (str): The ADB command to execute.
    
    Returns:
        Optional[str]: The output of the command as a string, or None if the command fails.
    """
    if not isinstance(command, str):
        raise ValueError(f"Expected a string for command, got {type(command)}")
    
    try:
        result = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        return result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return None

# Wireless debugging devices show up in `adb devices` as IP:port (e.g. 192.168.1.5:41005).
# The port is chosen by Android and changes, so we must not assume 5555.
WIRELESS_IP_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}:\d+$')
PAIR_ADDRESS_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}:\d{2,5}$')
PAIR_CODE_RE = re.compile(r'^\d{6}$')


def is_wireless(serial: str) -> bool:
    """True if the device is connected over Wi-Fi (IP:port, or an mDNS name from Wireless debugging)."""
    return bool(WIRELESS_IP_RE.match(serial)) or "._adb-tls-connect._tcp" in serial


def get_device_connection_type(serial: str) -> str:
    """
    Returns whether a device is connected via USB or Wi-Fi.

    Args:
        serial (str): The serial number of the device.

    Returns:
        str: "wifi" for wireless devices (any port), "usb" for cable, "offline" if not listed.
    """
    devices_list = adb_command("adb devices -l")

    if devices_list:
        for line in devices_list.splitlines():
            if serial in line:
                return "wifi" if is_wireless(serial) else "usb"
    return "offline"

def get_device_ip(serial: str) -> Optional[str]:
    """
    Retrieves the IP address of the device.
    For IP:port serials the address is already in the serial, so no extra adb call is needed.

    Args:
        serial (str): The serial number of the device.

    Returns:
        Optional[str]: The IP address of the device, or None if it cannot be determined.
    """
    if WIRELESS_IP_RE.match(serial):
        return serial.split(":")[0]
    ip_address = adb_command(f"adb -s {serial} shell ip addr show wlan0 | grep inet")
    if ip_address:
        return ip_address.split()[1].split('/')[0]
    return None

def get_device_info(serial: str) -> Optional[Dict[str, str]]:
    """
    Retrieves information for a given device using its serial number.
    
    Args:
        serial (str): The serial number of the device.
    
    Returns:
        Optional[Dict[str, str]]: A dictionary containing 'model', 'device_type', 
                                  'serial_number', and 'ip_address', or None if any 
                                  information is unavailable.
    """
    model = adb_command(f"adb -s {serial} shell getprop ro.product.model")
    device_type = adb_command(f"adb -s {serial} shell getprop ro.product.device")
    serial_number = adb_command(f"adb -s {serial} shell getprop ro.serialno")
    
    connection_type = get_device_connection_type(serial)
    
    ip_address = None
    if connection_type == "wifi":
        ip_address = get_device_ip(serial)
    
    if connection_type == "usb":
        ip_address = None
    
    if model and device_type and serial_number:
        return {
            "model": model,
            "device_type": device_type,
            "serial_number": serial_number,
            "ip_address": ip_address
        }
    return None
    
def get_device_status(serial: str) -> str:
    """
    Retrieves the connection status of a device.
    
    Args:
        serial (str): The serial number of the device.
    
    Returns:
        str: The status of the device ('device', 'offline', etc.).
    """
    devices_list = adb_command("adb devices")
    if devices_list:
        for line in devices_list.splitlines():
            if serial in line:
                status = line.split('\t')[1]
                return status
    return "offline"

def update_device_map() -> None:
    """
    Updates the device_map.json file by extracting data from all connected devices.
    Wireless devices (IP:port serials) are supported. Devices that adb does not list
    right now are marked "offline", so old entries never show up as connected.
    """
    devices_list = adb_command("adb devices")
    try:
        with open("device_map.json", "r") as json_file:
            device_map = json.load(json_file)
    except FileNotFoundError:
        device_map = {"devices": []}

    device_index = {device["serial"]: idx for idx, device in enumerate(device_map["devices"])}
    seen = set()

    if devices_list:
        for line in devices_list.splitlines():
            if not line.strip() or line.strip() == "List of devices attached" or line.startswith("*"):
                continue
            serial = line.split('\t')[0].strip()
            if not serial:
                continue
            seen.add(serial)

            status = get_device_status(serial)

            if status == "device":
                if serial in device_index:
                    device = device_map["devices"][device_index[serial]]

                    if not device.get("model"):
                        device["model"] = adb_command(f"adb -s {serial} shell getprop ro.product.model") or ""
                    if not device.get("device_type"):
                        device["device_type"] = adb_command(f"adb -s {serial} shell getprop ro.product.device") or ""

                    if get_device_connection_type(serial) == "wifi":
                        device["ip_address"] = get_device_ip(serial) or device.get("ip_address", "")
                    elif not device.get("ip_address"):
                        device["ip_address"] = ""

                    device["status"] = status
                else:
                    device_info = get_device_info(serial)
                    if device_info:
                        new_device = {
                            "name": "",
                            "serial": serial,
                            "model": device_info.get("model", ""),
                            "device_type": device_info.get("device_type", ""),
                            "ip_address": device_info.get("ip_address") or "",
                            "status": status
                        }
                        device_map["devices"].append(new_device)
                        device_index[serial] = len(device_map["devices"]) - 1
            else:
                if serial in device_index:
                    existing_device = device_map["devices"][device_index[serial]]
                    existing_device["status"] = status
                    display_name = existing_device.get("name") or existing_device.get("model") or serial
                else:
                    display_name = serial
                print(f"Device '{display_name}' is {status}. Skipping...")

    # Anything we saw before but adb no longer lists is not connected.
    for device in device_map["devices"]:
        if device["serial"] not in seen:
            device["status"] = "offline"

    with open("device_map.json", "w") as json_file:
        json.dump(device_map, json_file, indent=4)

def is_device_authorized(serial: str) -> bool:
    """
    Checks if the device is authorized for ADB connections.
    
    Args:
        serial (str): The serial number of the device.
    
    Returns:
        bool: True if the device is authorized, False if unauthorized.
    """
    # Check the device status using `adb devices`
    devices_list = adb_command("adb devices")
    
    # Check if the command returned any data
    if devices_list:
        for line in devices_list.splitlines():
            if serial in line:
                status = line.split('\t')[1]
                if status == "device":
                    return True  # Authorized device
                elif status == "unauthorized":
                    return False  # Unauthorized device
    return False  # Device not found or any other status

def display_device_menu(devices: List[Dict[str, str]]) -> int:
    """
    Displays a CLI menu with all connected devices and returns the selected device index.

    Args:
        devices (List[Dict[str, str]]): A list of devices to display in the menu.

    Returns:
        int: The selected device index (1-based), or 0 if the user wants to exit.
    """
    software_name = "ADB Device Manager"
    software_tagline = "Easily manage and connect your Android devices via ADB"

    print("=" * 55)
    print(f"{software_name}".center(50))
    print(f"{software_tagline}".center(50))
    print("=" * 55)

    print("\nSelect a device to connect to (or 0 to exit):\n")
    for index, device in enumerate(devices, start=1):
        device_name = device.get("name") or device.get("model") or device["serial"]
        kind = "Wi-Fi" if is_wireless(device["serial"]) else "USB"
        print(f"{index}. {device_name} ({device['serial']}) [{kind}]")

    try:
        choice = int(input("\nSelect a number: "))
        if choice == 0:
            return 0
        if 1 <= choice <= len(devices):
            selected_device = devices[choice - 1]
            serial = selected_device['serial']
            device_name = selected_device.get("name") or selected_device.get("model") or serial

            if not is_device_authorized(serial):
                print(f"\nDevice {device_name} is unauthorized for ADB connection.")
                print("Please allow USB debugging on the phone and try again.")
                return 0

            return choice

        print("Invalid choice. Please enter a valid number.")
        return display_device_menu(devices)
    except ValueError:
        print("Invalid input. Please enter a number.")
        return display_device_menu(devices)

def get_connected_devices() -> List[Dict[str, str]]:
    """Refreshes device_map.json and returns only the devices that are connected right now."""
    update_device_map()
    try:
        with open("device_map.json", "r") as json_file:
            device_map = json.load(json_file)
    except FileNotFoundError:
        return []
    return [device for device in device_map["devices"] if device.get("status") == "device"]


def wireless_setup() -> None:
    """
    Guides the user through connecting a phone over Wi-Fi (Android 11+ Wireless debugging).
    Everything typed here is checked before it is used, so it cannot inject shell commands.
    """
    print("\nOn the phone: Settings > Developer options > Wireless debugging (turn it on).")
    print("Phone and computer must be on the same Wi-Fi network.\n")

    print("Step 1 (first time only): tap 'Pair device with pairing code' on the phone.")
    pair_address = input("Pairing address IP:PORT (press Enter to skip if already paired): ").strip()
    if pair_address:
        code = input("6-digit pairing code: ").strip()
        if PAIR_ADDRESS_RE.match(pair_address) and PAIR_CODE_RE.match(code):
            print(adb_command(f"adb pair {pair_address} {code}") or "Pairing failed. Check the address and code.")
        else:
            print("That address or code does not look right. Skipping pairing.")

    print("\nStep 2: use the IP address and port shown on the main Wireless debugging screen.")
    address = input("Connect address IP:PORT (press Enter to cancel): ").strip()
    if address:
        if PAIR_ADDRESS_RE.match(address):
            print(adb_command(f"adb connect {address}") or "Connection failed. Check the address.")
        else:
            print("That address does not look right.")


def choose_action() -> str:
    """Asks what to open for the selected device."""
    print("\nWhat do you want to open?\n")
    print("1. Live dashboard (opens in your browser)")
    print("2. Screen mirror (scrcpy)")
    print("0. Exit")
    choice = input("\nSelect a number: ").strip()
    return {"1": "dashboard", "2": "scrcpy"}.get(choice, "exit")


def launch_dashboard(serial: str, port: int = 8000) -> None:
    """Starts the live phone dashboard (server.py, in the same folder) for one device."""
    try:
        import server
    except ImportError:
        print("server.py was not found next to adb_connect_map.py.")
        return
    server.run(serial=serial, port=port, open_browser=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ADB Device Manager")
    parser.add_argument("--action", choices=["dashboard", "scrcpy"], help="skip the 'what to open' question")
    parser.add_argument("--port", type=int, default=8000, help="port for the live dashboard (default 8000)")
    return parser.parse_args()


def main() -> None:
    """
    Main function: find connected devices (USB or Wi-Fi), let the user pick one,
    then open the live dashboard or a scrcpy screen mirror.
    """
    args = parse_args()
    devices = get_connected_devices()

    if not devices:
        print("No devices are currently connected.")
        if input("Set up a wireless connection now? [y/N] ").strip().lower().startswith("y"):
            wireless_setup()
            devices = get_connected_devices()
        if not devices:
            print("No devices connected. Exiting.")
            return

    choice = display_device_menu(devices)
    if choice == 0:
        print("Exiting...")
        return

    selected_device = devices[choice - 1]
    serial = selected_device["serial"]

    action = args.action or choose_action()

    if action == "dashboard":
        launch_dashboard(serial, args.port)
        return
    if action != "scrcpy":
        print("Exiting...")
        return

    # Disconnect all devices except the selected one (original behavior of the scrcpy path)
    for device in devices:
        if device != selected_device:
            other = device["serial"]
            print(f"Disconnecting {device.get('name') or device.get('model') or other} ({other})...")
            adb_command(f"adb -s {other} disconnect")

    # A wireless device is already connected (its serial is its IP:port). Only USB needs this.
    if get_device_connection_type(serial) == "usb":
        adb_command(f"adb -s {serial} usb")

    # Launch scrcpy to allow remote access to the device (output hidden)
    subprocess.run(["scrcpy", "-s", serial], stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
    print("\nDisconnected.")
    sys.exit()

if __name__ == "__main__":
    main()