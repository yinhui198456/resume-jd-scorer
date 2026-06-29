import urllib.parse

import requests


class FeishuSheetsClient:
    def __init__(self, app_id: str, app_secret: str, session=requests):
        self.app_id = app_id
        self.app_secret = app_secret
        self.session = session

    def get_tenant_token(self) -> str:
        response = self.session.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"FEISHU_AUTH_{payload.get('code')}")
        return payload["tenant_access_token"]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_tenant_token()}"}

    @staticmethod
    def _check(payload: dict[str, object], prefix: str) -> dict[str, object]:
        if payload.get("code") != 0:
            raise RuntimeError(f"{prefix}_{payload.get('code')}")
        data = payload.get("data", {})
        if isinstance(data, dict):
            return data
        return {}

    def get_sheets(self, spreadsheet_token: str) -> list[dict[str, object]]:
        response = self.session.get(
            f"https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query",
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = self._check(response.json(), "FEISHU_SHEETS_QUERY")
        return list(data.get("sheets", []))

    def read_values(
        self, spreadsheet_token: str, sheet_id: str, range_name: str
    ) -> list[list[object]]:
        encoded_range = urllib.parse.quote(f"{sheet_id}!{range_name}", safe="")
        response = self.session.get(
            f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{encoded_range}",
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = self._check(response.json(), "FEISHU_SHEETS_READ")
        value_range = data.get("valueRange", {})
        if isinstance(value_range, dict):
            return list(value_range.get("values", []))
        return []

    def append_values(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        range_name: str,
        values: list[list[object]],
    ) -> dict[str, object]:
        response = self.session.post(
            f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_append",
            headers=self._headers(),
            json={"valueRange": {"range": f"{sheet_id}!{range_name}", "values": values}},
            timeout=20,
        )
        response.raise_for_status()
        return self._check(response.json(), "FEISHU_SHEETS_APPEND")

    def update_values(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        range_name: str,
        values: list[list[object]],
    ) -> dict[str, object]:
        response = self.session.put(
            f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values",
            headers=self._headers(),
            json={"valueRange": {"range": f"{sheet_id}!{range_name}", "values": values}},
            timeout=20,
        )
        response.raise_for_status()
        return self._check(response.json(), "FEISHU_SHEETS_UPDATE")
