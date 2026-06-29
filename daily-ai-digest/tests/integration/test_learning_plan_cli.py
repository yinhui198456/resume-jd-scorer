import json

from digest.jobs import learning_plan


class FakeSheets:
    def get_sheets(self, spreadsheet_token):
        return [{"sheet_id": "349176", "title": "主任务"}]

    def read_values(self, spreadsheet_token, sheet_id, range_name):
        return [
            ["任务序号", "方向", "任务项", "输出", "状态", "月份", "优先级", "备注", "链接"],
            ["L35", "大模型", "Existing", "", "待开始", "", "中", "", ""],
        ]

    def append_values(self, spreadsheet_token, sheet_id, range_name, values):
        return {"updatedRange": "349176!A36:I36"}

    def update_values(self, spreadsheet_token, sheet_id, range_name, values):
        return {"updatedRange": range_name}


def test_preview_does_not_write(monkeypatch, capsys):
    monkeypatch.setattr(learning_plan, "build_sheets_client", lambda config: FakeSheets())

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


def test_apply_appends(monkeypatch, capsys):
    monkeypatch.setattr(learning_plan, "build_sheets_client", lambda config: FakeSheets())

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
