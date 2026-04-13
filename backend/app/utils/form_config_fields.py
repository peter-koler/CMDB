import json
from typing import Any


CONTROL_TYPE_TO_FIELD_TYPE = {
    "text": "text",
    "textarea": "text",
    "number": "number",
    "numberRange": "numberRange",
    "date": "date",
    "datetime": "datetime",
    "select": "select",
    "dropdown": "dropdown",
    "radio": "select",
    "checkbox": "multiselect",
    "cascade": "cascade",
    "switch": "boolean",
    "user": "user",
    "reference": "reference",
    "image": "image",
    "file": "file",
    "richtext": "richtext",
}


def parse_form_config(value: Any) -> list[dict]:
    if not value:
        return []

    parsed = value
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except Exception:
            return []
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except Exception:
            return []

    return parsed if isinstance(parsed, list) else []


def map_control_type_to_field_type(control_type: str | None) -> str:
    return CONTROL_TYPE_TO_FIELD_TYPE.get(control_type or "", "text")


def _normalize_options(raw_options: Any) -> list[dict]:
    if not isinstance(raw_options, list):
        return []

    options = []
    for item in raw_options:
        if isinstance(item, dict):
            label = item.get("label", item.get("value", ""))
            value = item.get("value", label)
            options.append({"label": label, "value": value})
    return options


def extract_form_fields(form_config: Any) -> list[dict]:
    config_data = parse_form_config(form_config)
    if not config_data:
        return []

    result: list[dict] = []
    seen: set[str] = set()

    def push_field(item: dict, index_key: str, group_label: str, group_order: int):
        props = item.get("props") if isinstance(item.get("props"), dict) else {}
        code = props.get("code")
        if not code or code in seen:
            return

        field = {
            "id": item.get("id") or f"field_{index_key}",
            "code": code,
            "name": props.get("label") or code,
            "field_type": map_control_type_to_field_type(item.get("controlType")),
            "control_type": item.get("controlType") or "text",
            "required": bool(props.get("required")),
            "is_required": bool(props.get("required")),
            "default_value": props.get("defaultValue"),
            "placeholder": props.get("placeholder") or "",
            "options": _normalize_options(props.get("options")),
            "option_type": props.get("optionType") or "custom",
            "dictionary_code": props.get("dictionaryCode") or "",
            "reference_model_id": props.get("refModelId"),
            "date_format": props.get("format"),
            "span": int(props.get("span") or 24),
            "help_text": props.get("helpText") or "",
            "description": props.get("description") or "",
            "group_label": group_label,
            "group_order": group_order,
            "field_order": int(props.get("sortOrder") or 0),
        }
        result.append(field)
        seen.add(code)

    def walk(items: list[dict], group_label: str = "基础属性", group_order: int = -1):
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            control_type = item.get("controlType")
            props = item.get("props") if isinstance(item.get("props"), dict) else {}
            if control_type == "group":
                child_group_label = props.get("label") or "属性分组"
                child_group_order = int(props.get("sortOrder") or group_order or 0)
                children = item.get("children")
                if isinstance(children, list):
                    walk(children, child_group_label, child_group_order)
                continue

            push_field(item, str(index), group_label, group_order)

            children = item.get("children")
            if isinstance(children, list):
                walk(children, group_label, group_order)

    walk(config_data)
    result.sort(key=lambda item: (item.get("group_order", -1), item.get("field_order", 0)))
    return result


def extract_form_field_map(form_config: Any) -> dict[str, dict]:
    return {field["code"]: field for field in extract_form_fields(form_config)}
