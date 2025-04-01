import json
import os
import sys
from typing import Dict, Union
from urllib.parse import urlparse

from seleniumbase import SB

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import (
    check_date,
    check_for_duplicate_amr_hash,
    create_database_session,
    generate_md5_hash,
    get_env_variables,
    insert_to_amr_database,
    parse_date,
)

script_path: str = os.path.abspath(__file__)
script_directory: str = os.path.dirname(script_path)
env_path: str = os.path.join(script_directory, ".env")
[
    _,
    _,
    _,
    executable_path,
    _,
    _,
    _,
    browser_type,
    smi_data_url,
    _,
    _,
    _,
    _,
    _,
] = get_env_variables(env_path=env_path)

websites_list_file: str = os.path.join(script_directory, "websites.json")
with open(websites_list_file, "r") as f:
    websites_dict: Dict[str, Union[str, int]] = json.load(f)

session = create_database_session(smi_data_url)

with SB(uc=True, headless=True, incognito=True) as sb:
    for website_idx, website in websites_dict.items():
        print("\n[+] Opening website: ", website["ecgain"])

        sb.activate_cdp_mode(website["url"])

        tr_elements = sb.cdp.find_all("table.listtable tbody tr", timeout=30)

        for index, tr in enumerate(tr_elements, start=1):
            title_element = sb.cdp.find_element(
                website["bid_title_xpath"].format(index)
            )

            title: str = sb.cdp.get_text(
                website["bid_title_xpath"].format(index)
            ).strip()

            parsed_url = urlparse(website["url"])
            file_path: str = title_element.get_attribute("href")
            file_url: str = f"{parsed_url.scheme}://{parsed_url.netloc}{file_path}"

            bid_id: str = sb.cdp.get_text(website["bid_no_xpath"].format(index)).strip()
            if website["bid_no_xpath"] == website["bid_title_xpath"]:
                bid_id = bid_id[:15].strip()

            raw_broadcast_date: str = sb.cdp.get_text(
                website["broadcast_date_xpath"].format(index)
            ).strip()
            broadcast_date: str = parse_date(date=raw_broadcast_date)

            raw_due_date: str = sb.cdp.get_text(website["bid_due_date_xpath"].format(index)).strip()
            due_date: str = parse_date(date=raw_due_date)
            if due_date != "Invalid Date":
                if check_date(due_date):
                    continue

            hash = generate_md5_hash(website["ecgain"], bid_id, None)

            if not check_for_duplicate_amr_hash(session, hash):
                insert_to_amr_database(
                    session=session,
                    ecgain=website["ecgain"],
                    number=title if not bid_id else bid_id,
                    title=title,
                    due_date=None if not due_date else due_date,
                    broadcast_date=None if not broadcast_date else broadcast_date,
                    hash=hash,
                    url1=website["url"],
                    url2=file_url,
                    description=title,
                )
print(f"[+] End of script {script_path}!")
