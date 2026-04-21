import json
import os
import re
import sys
from typing import Any

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    P2ImMessageReceiveV1,
)

PLACEHOLDER_APP_IDS = {"cli_你的AppID", "YOUR_APP_ID", "your_app_id", ""}
PLACEHOLDER_SECRETS = {"你的AppSecret", "YOUR_APP_SECRET", "your_app_secret", ""}


def _read_openclaw_feishu_credentials() -> tuple[str | None, str | None]:
    """Fallback credentials from ~/.openclaw/openclaw.json."""
    cfg_path = os.path.expanduser("~/.openclaw/openclaw.json")
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError):
        return (None, None)

    channels = cfg.get("channels")
    if not isinstance(channels, dict):
        return (None, None)
    feishu = channels.get("feishu")
    if not isinstance(feishu, dict):
        return (None, None)
    app_id = feishu.get("appId")
    app_secret = feishu.get("appSecret")
    return (
        app_id if isinstance(app_id, str) else None,
        app_secret if isinstance(app_secret, str) else None,
    )


def _resolve_credentials() -> tuple[str, str]:
    env_app_id = os.getenv("FEISHU_APP_ID")
    env_app_secret = os.getenv("FEISHU_APP_SECRET")
    cfg_app_id, cfg_app_secret = _read_openclaw_feishu_credentials()
    app_id = (env_app_id or cfg_app_id or "").strip()
    app_secret = (env_app_secret or cfg_app_secret or "").strip()
    return app_id, app_secret


def _is_placeholder_app_id(value: str) -> bool:
    return value in PLACEHOLDER_APP_IDS or value.lower().startswith("cli_你的")


def _is_placeholder_secret(value: str) -> bool:
    return value in PLACEHOLDER_SECRETS or "appsecret" in value.lower()


APP_ID, APP_SECRET = _resolve_credentials()


def _create_lark_client() -> lark.Client:
    return (
        lark.Client.builder()
        .app_id(APP_ID)
        .app_secret(APP_SECRET)
        .log_level(lark.LogLevel.INFO)
        .build()
    )


LARK_CLIENT = _create_lark_client()


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None


def _extract_json_candidate(text: str) -> dict[str, Any] | None:
    candidates: list[str] = []

    fenced_json = re.findall(r"```json\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    candidates.extend(fenced_json)

    fenced_any = re.findall(r"```\s*([\s\S]*?)\s*```", text)
    candidates.extend(fenced_any)

    first_object = _extract_first_json_object(text)
    if first_object:
        candidates.append(first_object)

    candidates.append(text)

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def translate_to_feishu_card(schema: dict[str, Any]) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []
    meta = schema.get("meta", {}) if isinstance(schema.get("meta"), dict) else {}

    description = meta.get("description")
    if isinstance(description, str) and description.strip():
        elements.append({"tag": "markdown", "content": description})
        elements.append({"tag": "hr"})

    for el in schema.get("elements", []):
        if not isinstance(el, dict):
            continue
        el_type = el.get("type")
        el_id = el.get("id")
        if not isinstance(el_type, str) or not isinstance(el_id, str):
            continue
        label = el.get("label", el_id)
        if isinstance(label, str):
            elements.append({"tag": "markdown", "content": f"**{label}**"})

        if el_type == "input":
            elements.append(
                {
                    "tag": "input",
                    "name": el_id,
                    "placeholder": {
                        "tag": "plain_text",
                        "content": el.get("placeholder", "请输入"),
                    },
                }
            )
        elif el_type == "select":
            options: list[dict[str, Any]] = []
            for opt in el.get("options", []):
                if not isinstance(opt, dict):
                    continue
                opt_label = opt.get("label")
                opt_value = opt.get("value")
                if isinstance(opt_label, str) and isinstance(opt_value, str):
                    options.append(
                        {
                            "text": {"tag": "plain_text", "content": opt_label},
                            "value": opt_value,
                        }
                    )
            if options:
                elements.append({"tag": "select_static", "name": el_id, "options": options})

    actions: list[dict[str, Any]] = []
    task_id = meta.get("task_id")
    for action in schema.get("actions", []):
        if not isinstance(action, dict):
            continue
        label = action.get("label")
        action_type = action.get("action_type")
        if not isinstance(label, str) or not isinstance(action_type, str):
            continue
        value: dict[str, Any] = {
            "task_id": task_id,
            "action_type": action_type,
        }
        if isinstance(action.get("action_id"), str):
            value["action_id"] = action["action_id"]
        actions.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": label},
                "type": "primary" if action.get("theme") == "primary" else "default",
                "value": value,
            }
        )

    if actions:
        elements.append({"tag": "hr"})
        elements.append({"tag": "action", "actions": actions})

    title = meta.get("title") if isinstance(meta.get("title"), str) else "Interactive Card"
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue",
        },
        "elements": elements,
    }


def send_message_to_feishu(text_content: str, chat_id: str) -> None:
    parsed = _extract_json_candidate(text_content)
    if parsed and parsed.get("ui_type") == "interactive_card":
        card = translate_to_feishu_card(parsed)
        body = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("interactive")
            .content(json.dumps(card, ensure_ascii=False))
            .build()
        )
    else:
        body = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(json.dumps({"text": text_content}, ensure_ascii=False))
            .build()
        )

    req = CreateMessageRequest.builder().receive_id_type("chat_id").request_body(body).build()
    resp = LARK_CLIENT.im.v1.message.create(req)
    if not resp.success():
        raise RuntimeError(
            f"send failed: code={resp.code}, msg={resp.msg}, log_id={resp.get_log_id()}"
        )


def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
    message_content = data.event.message.content
    user_openid = data.event.sender.sender_id.open_id
    print(f"[收到文字消息] 用户: {user_openid}, 内容: {message_content}")


def do_interactive_card_action(data: lark.CustomizedEvent) -> None:
    payload = data.event if isinstance(data.event, dict) else {}
    action = payload.get("action", {}) if isinstance(payload.get("action"), dict) else {}
    action_value = action.get("value", {}) if isinstance(action.get("value"), dict) else {}
    form_data = action.get("form_value", {}) if isinstance(action.get("form_value"), dict) else {}
    task_id = action_value.get("task_id")
    action_type = action_value.get("action_type")
    if not task_id:
        return
    print(f"[收到卡片交互] 任务ID: {task_id}, 动作: {action_type}, 数据: {form_data}")


def start_feishu_ws_client() -> None:
    if _is_placeholder_app_id(APP_ID) or _is_placeholder_secret(APP_SECRET):
        print(
            "飞书凭证无效：请设置真实 FEISHU_APP_ID / FEISHU_APP_SECRET，"
            "或在 ~/.openclaw/openclaw.json 的 channels.feishu.appId/appSecret 中填写真实值。"
        )
        print(f"当前 APP_ID: {APP_ID!r}")
        sys.exit(2)

    event_handler = (
        lark.EventDispatcherHandler.builder(APP_ID, APP_SECRET)
        .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
        .register_p1_customized_event("card.action.trigger", do_interactive_card_action)
        .build()
    )
    cli = lark.ws.Client(APP_ID, APP_SECRET, event_handler=event_handler, log_level=lark.LogLevel.INFO)
    print("飞书长连接客户端已启动，等待接收事件...")
    try:
        cli.start()
    except Exception as exc:  # noqa: BLE001 - show actionable startup failures
        print(f"飞书长连接启动失败: {exc}")
        sys.exit(3)


if __name__ == "__main__":
    start_feishu_ws_client()
