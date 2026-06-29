import json
from types import SimpleNamespace

from digest.jobs import learning_plan


class FakeSheets:
    def __init__(self):
        self.append_calls = []
        self.update_calls = []

    def get_sheets(self, spreadsheet_token):
        return [{"sheet_id": "349176", "title": "主任务"}]

    def read_values(self, spreadsheet_token, sheet_id, range_name):
        return [
            ["任务序号", "方向", "任务项", "输出", "状态", "月份", "优先级", "备注", "链接"],
            ["L35", "大模型", "Existing", "", "待开始", "", "中", "", ""],
        ]

    def append_values(self, spreadsheet_token, sheet_id, range_name, values):
        self.append_calls.append((spreadsheet_token, sheet_id, range_name, values))
        return {"updatedRange": "349176!A36:I36"}

    def update_values(self, spreadsheet_token, sheet_id, range_name, values):
        self.update_calls.append((spreadsheet_token, sheet_id, range_name, values))
        return {"updatedRange": range_name}


def patch_dependencies(monkeypatch):
    fake_sheets = FakeSheets()
    fake_config = SimpleNamespace(
        schedule={"timezone": "Asia/Shanghai"},
        feishu_app_id="fake-app-id",
        feishu_app_secret="fake-secret",
        learning_plan_spreadsheet_token="fake-spreadsheet-token",
        learning_plan_sheet_title="主任务",
    )
    monkeypatch.setattr(learning_plan, "load_config", lambda root: fake_config)
    monkeypatch.setattr(learning_plan, "build_sheets_client", lambda config: fake_sheets)
    return fake_sheets


def test_preview_does_not_write(monkeypatch, capsys):
    fake_sheets = patch_dependencies(monkeypatch)

    exit_code = learning_plan.main([
        "--title", "Graphify",
        "--summary", "将代码和文档转为知识图谱。",
        "--url", "https://github.com/safishamsi/graphify",
        "--source-date", "2026-06-29",
        "--intent", "感兴趣",
        "--now", "2026-06-29T10:00:00+08:00",
    ])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "preview"
    assert output["plan"]["action"] == "append"
    assert output["plan"]["values"][0][0] == "L36"
    assert fake_sheets.append_calls == []
    assert fake_sheets.update_calls == []


def test_apply_appends(monkeypatch, capsys):
    fake_sheets = patch_dependencies(monkeypatch)

    exit_code = learning_plan.main([
        "--title", "Graphify",
        "--summary", "将代码和文档转为知识图谱。",
        "--url", "https://github.com/safishamsi/graphify",
        "--source-date", "2026-06-29",
        "--intent", "感兴趣",
        "--now", "2026-06-29T10:00:00+08:00",
        "--apply",
    ])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "apply"
    assert output["result"]["updatedRange"] == "349176!A36:I36"
    assert fake_sheets.append_calls == [
        (
            "fake-spreadsheet-token",
            "349176",
            "A:I",
            output["plan"]["values"],
        )
    ]
    assert fake_sheets.update_calls == []
