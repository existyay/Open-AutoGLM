"""Input utilities for Android device text input."""

import base64
from typing import Optional

from phone_agent.adb.utils import run_adb_command, get_adb_prefix


def type_text(text: str, device_id: str | None = None) -> None:
    """
    Type text into the currently focused input field using ADB Keyboard.

    Args:
        text: The text to type.
        device_id: Optional ADB device ID for multi-device setups.

    Note:
        Requires ADB Keyboard to be installed on the device.
        See: https://github.com/nicnocquee/AdbKeyboard
    """
    adb_prefix = get_adb_prefix(device_id)
    encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    run_adb_command(
        adb_prefix + [
            "shell",
            "am",
            "broadcast",
            "-a",
            "ADB_INPUT_B64",
            "--es",
            "msg",
            encoded_text,
        ]
    )


def clear_text(device_id: str | None = None) -> None:
    """
    Clear text in the currently focused input field.

    Args:
        device_id: Optional ADB device ID for multi-device setups.
    """
    adb_prefix = get_adb_prefix(device_id)

    run_adb_command(
        adb_prefix + ["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"]
    )


def detect_and_set_adb_keyboard(device_id: str | None = None) -> str:
    """
    Detect current keyboard and switch to ADB Keyboard if needed.

    Args:
        device_id: Optional ADB device ID for multi-device setups.

    Returns:
        The original keyboard IME identifier for later restoration.
    """
    adb_prefix = get_adb_prefix(device_id)

    # Get current IME
    result = run_adb_command(
        adb_prefix + ["shell", "settings", "get", "secure", "default_input_method"]
    )
    current_ime = ((result.stdout or "") + (result.stderr or "")).strip()

    # Switch to ADB Keyboard if not already set
    if "com.android.adbkeyboard/.AdbIME" not in current_ime:
        run_adb_command(
            adb_prefix + ["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"]
        )

    # Warm up the keyboard
    type_text("", device_id)

    return current_ime


def restore_keyboard(ime: str, device_id: str | None = None) -> None:
    """
    Restore the original keyboard IME.

    Args:
        ime: The IME identifier to restore.
        device_id: Optional ADB device ID for multi-device setups.
    """
    adb_prefix = get_adb_prefix(device_id)

    run_adb_command(
        adb_prefix + ["shell", "ime", "set", ime]
    )
