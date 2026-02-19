# tools.py — Tool schemas for what-do-i-become (OpenAI Responses API format)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "execute_command",
        "description": (
            "Execute a shell command on the Raspberry Pi with sudo privileges. "
            "Returns stdout, stderr, and exit code. Use this for EVERYTHING: "
            "inspecting hardware (lsusb, i2cdetect, dmesg, lsblk, vcgencmd, cat /proc/cpuinfo), "
            "installing packages (sudo apt-get install -y ...), writing files, "
            "running Python/Bash scripts, testing devices, checking GPIO, etc. "
            "Commands time out after 300 seconds. Output is truncated to 4000 characters."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                }
            },
            "required": ["command"]
        }
    },
    {
        "type": "function",
        "name": "order_part",
        "description": (
            "Request the human to order and install a hardware part onto your "
            "Raspberry Pi. You may only have ONE pending order at a time. "
            "Think carefully before ordering — consider what capabilities you want, "
            "what dependencies exist between parts, and what order makes sense. "
            "Be as specific as possible so the human orders the correct item."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "part_name": {
                    "type": "string",
                    "description": (
                        "Specific product name/model "
                        "(e.g. 'Raspberry Pi Camera Module 3', 'BME280 I2C Sensor Breakout')"
                    )
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Detailed description including specs, model numbers, "
                        "and anything the human needs to order the exact right part"
                    )
                },
                "rationale": {
                    "type": "string",
                    "description": "Why you want this part, what it enables, how it fits your plan"
                },
                "connection_type": {
                    "type": "string",
                    "description": "How the part connects (USB, GPIO, I2C, SPI, CSI, DSI, HAT, etc.)"
                },
                "detection_hint": {
                    "type": "string",
                    "description": (
                        "The exact command(s) you will run to detect the part once installed "
                        "(e.g. 'lsusb should show 0x1234', 'ls /dev/video0', "
                        "'i2cdetect -y 1 should show 0x76')"
                    )
                },
                "estimated_price": {
                    "type": "string",
                    "description": "Rough price estimate to help the human budget (optional)"
                }
            },
            "required": ["part_name", "description", "rationale", "connection_type", "detection_hint"]
        }
    },
    {
        "type": "function",
        "name": "confirm_part_installed",
        "description": (
            "Confirm that the currently pending part has been detected and is working. "
            "Call this ONLY after you have verified the part using execute_command. "
            "This moves the part from 'pending' to 'installed' and returns you to "
            "EXPLORING state so you can order the next part."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "verification_details": {
                    "type": "string",
                    "description": (
                        "What commands you ran and what output confirmed "
                        "the part is present and functional"
                    )
                }
            },
            "required": ["verification_details"]
        }
    },
    {
        "type": "function",
        "name": "save_notes",
        "description": (
            "Save persistent notes available in ALL future sessions. "
            "This OVERWRITES your entire notes file — include everything you want to keep. "
            "Use this for: your master plan, progress tracking, hardware observations, "
            "ideas for future parts, reminders, and anything you want to remember. "
            "Budget: ~3000 characters. Write in markdown. Be organized and concise."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "Complete content for your notes file (markdown). "
                        "Replaces all previous notes."
                    )
                }
            },
            "required": ["content"]
        }
    }
]
