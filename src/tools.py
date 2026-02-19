# tools.py - Tool schemas for what-do-i-become (OpenAI Responses API format)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "execute_command",
        "description": (
            "Execute a shell command on the host machine with sudo privileges. "
            "Use this to inspect hardware/software, install packages, write files, "
            "run scripts, and verify capabilities. Commands time out after 300 seconds."
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
            "Request one hardware part from the human. "
            "Only one request can be open at a time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "part_name": {
                    "type": "string",
                    "description": "Specific product/model to buy"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this part is needed right now"
                },
                "details": {
                    "type": "string",
                    "description": "Specs, wiring, model numbers, or buying notes"
                },
                "detection_hint": {
                    "type": "string",
                    "description": "How you will verify the part once installed"
                },
                "estimated_price": {
                    "type": "string",
                    "description": "Approximate budget (optional)"
                }
            },
            "required": ["part_name", "reason"]
        }
    },
    {
        "type": "function",
        "name": "confirm_part_installed",
        "description": (
            "Confirm the currently requested part has been installed and verified. "
            "Call only after checking with execute_command."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "verification_details": {
                    "type": "string",
                    "description": "Commands run and evidence confirming the part works"
                }
            },
            "required": ["verification_details"]
        }
    },
    {
        "type": "function",
        "name": "save_notes",
        "description": (
            "Overwrite persistent notes.md for this device. "
            "Use for plans, reminders, and ongoing context."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Complete markdown content for notes.md"
                }
            },
            "required": ["content"]
        }
    },
    {
        "type": "function",
        "name": "update_becoming",
        "description": "Update the short phrase describing what this device is becoming.",
        "parameters": {
            "type": "object",
            "properties": {
                "becoming": {
                    "type": "string",
                    "description": "Short phrase (ideally under 120 chars)"
                }
            },
            "required": ["becoming"]
        }
    },
    {
        "type": "function",
        "name": "set_status",
        "description": "Set the device status for this session stage.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": [
                        "FIRST_RUN",
                        "EXPLORING",
                        "WRITING_CODE",
                        "VERIFYING_PART",
                        "AWAITING_PART",
                        "ERROR"
                    ],
                    "description": "New status"
                },
                "note": {
                    "type": "string",
                    "description": "Optional reason for the status change"
                }
            },
            "required": ["status"]
        }
    }
]
