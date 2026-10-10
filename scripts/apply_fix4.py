import pathlib
import sys


def main() -> int:
    path = pathlib.Path("bot/handlers.py")
    src = path.read_text(encoding="utf-8")

    old_test = 'f"{fa.ADMIN_TEST_SENT}\\n\\n{format_test_card(record)}",'
    new_test = 'f"{fa.ADMIN_TEST_SENT}\\n\\n{format_test_card(record)}\\n\\n{fa.config_code(escape_code(str(record[\'uri\'])))}",'
    count_test = src.count(old_test)
    if count_test != 2:
        print(f"unexpected admin test card occurrences: {count_test} (expected 2)")
        return 1
    src = src.replace(old_test, new_test)

    old_send = 'f"{format_test_card(selected)}\\n\\n{fa.ADMIN_CONFIRM_SEND}",'
    new_send = 'f"{format_test_card(selected)}\\n\\n{fa.config_code(escape_code(str(selected[\'uri\'])))}\\n\\n{fa.ADMIN_CONFIRM_SEND}",'
    count_send = src.count(old_send)
    if count_send != 1:
        print(f"unexpected admin confirm occurrences: {count_send} (expected 1)")
        return 1
    src = src.replace(old_send, new_send)

    path.write_text(src, encoding="utf-8")
    print(f"patched test cards x{count_test}, confirm card x{count_send}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
