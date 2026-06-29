from digest.learn.sheets import FeishuSheetsClient


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP_{self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if url.endswith("/auth/v3/tenant_access_token/internal"):
            return FakeResponse({"code": 0, "tenant_access_token": "tenant-token"})
        return FakeResponse({"code": 0, "data": {"updatedRange": "349176!A36:I36"}})

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if url.endswith("/sheets/query"):
            return FakeResponse({"code": 0, "data": {"sheets": [{"sheet_id": "349176", "title": "主任务"}]}})
        return FakeResponse({"code": 0, "data": {"valueRange": {"values": [["任务序号"]]}}})

    def put(self, url, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        return FakeResponse({"code": 0, "data": {"updatedRange": "349176!H36:I36"}})


def test_get_sheets_uses_v3_query_endpoint():
    session = FakeSession()
    client = FeishuSheetsClient("app", "secret", session=session)

    sheets = client.get_sheets("spreadsheet-token")

    assert sheets == [{"sheet_id": "349176", "title": "主任务"}]
    method, url, kwargs = session.calls[-1]
    assert method == "GET"
    assert "/sheets/v3/spreadsheets/spreadsheet-token/sheets/query" in url
    assert kwargs["headers"]["Authorization"] == "Bearer tenant-token"


def test_read_values_uses_v2_values_endpoint():
    session = FakeSession()
    client = FeishuSheetsClient("app", "secret", session=session)

    values = client.read_values("spreadsheet-token", "349176", "A1:I225")

    assert values == [["任务序号"]]
    assert "/sheets/v2/spreadsheets/spreadsheet-token/values/" in session.calls[-1][1]


def test_append_values_posts_values_payload():
    session = FakeSession()
    client = FeishuSheetsClient("app", "secret", session=session)

    result = client.append_values("spreadsheet-token", "349176", "A:I", [["L36"]])

    assert result["updatedRange"] == "349176!A36:I36"
    method, url, kwargs = session.calls[-1]
    assert method == "POST"
    assert url == "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/spreadsheet-token/values_append"
    assert kwargs["json"]["valueRange"]["range"] == "349176!A:I"
    assert kwargs["json"]["valueRange"]["values"] == [["L36"]]


def test_update_values_puts_values_payload():
    session = FakeSession()
    client = FeishuSheetsClient("app", "secret", session=session)

    result = client.update_values("spreadsheet-token", "349176", "H36:I36", [["note", "link"]])

    assert result["updatedRange"] == "349176!H36:I36"
    method, url, kwargs = session.calls[-1]
    assert method == "PUT"
    assert url == "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/spreadsheet-token/values"
    assert kwargs["json"]["valueRange"]["range"] == "349176!H36:I36"
    assert kwargs["json"]["valueRange"]["values"] == [["note", "link"]]
