import csv
import hashlib
import io
import json
import os
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


ROOT = Path(__file__).resolve().parent
DEFAULT_SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1SyhE9nQf3LV8QEBTCLavgfr8w45y-mI69XPbtuN2hPA/export?format=csv&gid=1597249711"
)
DEFAULT_BASE_URL = "https://billing.cgnet.com.np/h8ssrms"


def get_env_setting(name: str, default: str) -> str:
    value = os.environ.get(name, default)
    if value is None:
        return default
    value = str(value).strip()
    return default if not value else value


SHEET_CSV_URL = get_env_setting("SHEET_CSV_URL", DEFAULT_SHEET_CSV_URL)
STATE_PATH = Path(
    get_env_setting("TICKET_STATE_PATH", str(ROOT / ".ticket-close-state.json"))
)
BASE_URL = get_env_setting("SSRMS_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
CASE_LIST_URL = f"{BASE_URL}/CaseListMin.aspx"
POLL_SECONDS = 15
ASSIGNEE = "Ramjee Katwal"
_storage_state_path = os.environ.get("SSRMS_STORAGE_STATE", "").strip()
STORAGE_STATE_PATH = Path(_storage_state_path) if _storage_state_path else None


def get_poll_seconds() -> int:
    raw_value = get_env_setting("WATCH_INTERVAL_SECONDS", str(POLL_SECONDS))
    try:
        return int(raw_value)
    except ValueError as error:
        raise RuntimeError(
            "WATCH_INTERVAL_SECONDS must be a valid integer number of seconds."
        ) from error


def get_headless() -> bool:
    value = get_env_setting("SSRMS_HEADLESS", "false").lower()
    if value in {"1", "true", "yes"}:
        return True
    if value in {"0", "false", "no"}:
        return False
    raise RuntimeError("SSRMS_HEADLESS must be true or false.")


def fingerprint(ticket: str, remarks: str) -> str:
    value = f"{ticket}\0{remarks}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def read_state() -> dict[str, str]:
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(f"Could not read processing state {STATE_PATH}: {error}") from error
    if not isinstance(state, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in state.items()
    ):
        raise RuntimeError(f"Processing state has an invalid format: {STATE_PATH}")
    return state


def write_state(state: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = STATE_PATH.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(STATE_PATH)


def parse_sheet_rows(csv_content: str) -> list[tuple[str, str]]:
    try:
        rows = list(csv.reader(io.StringIO(csv_content)))
    except csv.Error as error:
        raise RuntimeError(f"Could not parse the Google Sheets CSV export: {error}") from error

    def normalized_header(value: object) -> str:
        return str(value).strip().lower().replace("-", " ").replace("_", " ")

    header_row = None
    ticket_column = None
    remarks_column = None
    for row_number, cells in enumerate(rows[:10], start=1):
        headers = [normalized_header(value) for value in cells]
        ticket_index = next((index for index, header in enumerate(headers) if header in {"ticket", "ticket number"}), None)
        remarks_index = next((index for index, header in enumerate(headers) if header in {"remarks", "remark"}), None)
        if ticket_index is not None and remarks_index is not None:
            header_row = row_number
            ticket_column = ticket_index
            remarks_column = remarks_index
            break
    if header_row is None:
        raise RuntimeError(
            'Could not find "Ticket" and "Remarks" headers in the first 10 rows '
            "of the Google Sheet CSV export. Check that the sheet is shared for "
            "anyone with the link and that SHEET_CSV_URL points to the correct tab."
        )

    ticket_rows: list[tuple[str, str]] = []
    for row_number, cells in enumerate(rows[header_row:], start=header_row + 1):
        ticket = cells[ticket_column].strip() if ticket_column < len(cells) else ""
        remarks = cells[remarks_column].strip() if remarks_column < len(cells) else ""
        if not ticket and not remarks:
            continue
        if not ticket or not remarks:
            print(
                f"Skipping incomplete row {row_number}: both Ticket and Remarks are required.",
                flush=True,
            )
            continue
        ticket_rows.append((ticket, remarks))
    return ticket_rows


def read_sheet_rows() -> list[tuple[str, str]]:
    try:
        with urlopen(SHEET_CSV_URL, timeout=30) as response:
            csv_content = response.read().decode("utf-8-sig")
    except (OSError, URLError, TimeoutError, UnicodeDecodeError) as error:
        raise RuntimeError(
            f"Could not fetch the Google Sheet CSV export from {SHEET_CSV_URL}: {error}"
        ) from error
    return parse_sheet_rows(csv_content)


def is_login_page(page: Page) -> bool:
    return "/login.aspx" in page.url.lower()


def ensure_logged_in(page: Page, allow_interactive_sign_in: bool = True) -> None:
    page.goto(CASE_LIST_URL, wait_until="domcontentloaded")
    if not is_login_page(page):
        return

    if not allow_interactive_sign_in:
        raise RuntimeError(
            "SSRMS requires sign-in. Create a fresh Playwright storage-state file "
            "and mount it at SSRMS_STORAGE_STATE."
        )
    print("Please sign in to SSRMS in the opened browser window.", flush=True)
    input("Press Enter after signing in: ")
    if is_login_page(page):
        raise RuntimeError("SSRMS still shows the login page; sign in before continuing.")
    page.goto(CASE_LIST_URL, wait_until="domcontentloaded")


def find_ticket(page: Page, ticket: str) -> None:
    page.goto(CASE_LIST_URL, wait_until="domcontentloaded")
    if is_login_page(page):
        raise RuntimeError("SSRMS session expired. Sign in again when prompted.")

    page.locator("#ContentPlaceHolder1_ddllist").select_option(label="Ticket Number")
    page.locator("#ContentPlaceHolder1_txtserch").fill(ticket)
    page.locator("#ContentPlaceHolder1_btnserch").click()
    ticket_link = page.get_by_role("link", name=ticket, exact=True)
    ticket_link.wait_for(state="visible", timeout=15_000)
    ticket_link.click()
    page.wait_for_url(lambda url: url.path.lower().endswith("/caseview.aspx"))


def current_ticket_details(page: Page, remarks: str) -> tuple[bool, bool]:
    rows = page.locator("tr").all_inner_texts()
    assignment_row = next((text for text in rows if "Assign User" in text), None)
    if assignment_row is None:
        raise RuntimeError("Could not read the ticket's current assignee.")
    return ASSIGNEE in assignment_row, remarks in page.locator("body").inner_text()


def update_ticket(page: Page, ticket: str, remarks: str) -> None:
    ensure_logged_in(page)
    find_ticket(page, ticket)
    assigned, has_remark = current_ticket_details(page, remarks)
    if assigned and has_remark:
        return

    page.get_by_role("button", name="Edit", exact=True).first.click()
    page.wait_for_url(lambda url: url.path.lower().endswith("/newcase.aspx"))
    page.locator("#ContentPlaceHolder1_combassign").select_option(label=ASSIGNEE)
    if not has_remark:
        page.locator("#ContentPlaceHolder1_txtDesc").fill(remarks)
    page.locator("#ContentPlaceHolder1_btnsave").click()
    page.wait_for_url(
        lambda url: url.path.lower().endswith("/caselistmin.aspx"),
        timeout=20_000,
    )

    confirmation = page.get_by_role("button", name="OK", exact=True)
    if confirmation.count():
        try:
            confirmation.wait_for(state="visible", timeout=2_000)
            confirmation.click()
        except PlaywrightTimeoutError:
            pass

    find_ticket(page, ticket)
    assigned, has_remark = current_ticket_details(page, remarks)
    if not assigned or not has_remark:
        raise RuntimeError(
            f"SSRMS did not confirm the requested assignee and remark for {ticket}."
        )


def main() -> None:
    poll_seconds = get_poll_seconds()
    headless = get_headless()
    if poll_seconds < 1:
        raise RuntimeError("WATCH_INTERVAL_SECONDS must be at least 1.")
    if headless and STORAGE_STATE_PATH is None:
        raise RuntimeError(
            "SSRMS_STORAGE_STATE is required when SSRMS_HEADLESS is enabled."
        )
    if STORAGE_STATE_PATH is not None and not STORAGE_STATE_PATH.is_file():
        raise RuntimeError(f"SSRMS storage-state file not found: {STORAGE_STATE_PATH}")

    state = read_state()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(
            storage_state=str(STORAGE_STATE_PATH) if STORAGE_STATE_PATH else None
        )
        page = context.new_page()
        try:
            ensure_logged_in(page, allow_interactive_sign_in=not headless)
            print(
                f"Watching Google Sheet every {poll_seconds} seconds. "
                f"New or changed rows will be assigned to {ASSIGNEE}. Press Ctrl+C to stop.",
                flush=True,
            )
            while True:
                try:
                    rows = read_sheet_rows()
                except Exception as error:
                    print(f"Could not read Google Sheet; will retry next poll: {error}", flush=True)
                    time.sleep(poll_seconds)
                    continue

                for ticket, remarks in rows:
                    row_fingerprint = fingerprint(ticket, remarks)
                    if state.get(row_fingerprint) == ticket:
                        continue
                    try:
                        update_ticket(page, ticket, remarks)
                        state[row_fingerprint] = ticket
                        write_state(state)
                        print(f"Processed {ticket}.", flush=True)
                    except Exception as error:
                        print(
                            f"Could not process {ticket}; it will be retried: {error}",
                            flush=True,
                        )
                time.sleep(poll_seconds)
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nWatcher stopped.", flush=True)
    except Exception as error:
        raise SystemExit(str(error)) from error
