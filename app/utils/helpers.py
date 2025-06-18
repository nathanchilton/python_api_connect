def validate_email(email: str) -> bool:
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def format_response(data: dict, status_code: int = 200) -> dict:
    return {"status": status_code, "data": data}


def handle_exception(exception: Exception) -> dict:
    return {"status": 500, "error": str(exception)}
