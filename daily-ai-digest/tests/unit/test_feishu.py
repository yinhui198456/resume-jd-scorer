import json

from digest.deliver.feishu import FeishuDelivery


class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class FakeSession:
    def __init__(self): self.responses = []; self.requests = []
    def queue(self, payload): self.responses.append(payload)
    def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return FakeResponse(self.responses.pop(0))


def test_send_targets_chat_id():
    session = FakeSession()
    session.queue({"code": 0, "tenant_access_token": "token", "expire": 7200})
    session.queue({"code": 0, "data": {"message_id": "om_1"}})
    delivery = FeishuDelivery("cli_test", "secret", "oc_test", session)
    result = delivery.send_text("digest", "run-1:sha")
    _, request = session.requests[-1]
    assert request["params"] == {"receive_id_type": "chat_id"}
    assert request["json"]["receive_id"] == "oc_test"
    assert result.message_id == "om_1"


def test_send_post_targets_chat_with_post_payload():
    session = FakeSession()
    session.queue({"code": 0, "tenant_access_token": "token", "expire": 7200})
    session.queue({"code": 0, "data": {"message_id": "om_post"}})
    delivery = FeishuDelivery("cli_test", "secret", "oc_test", session)
    payload = {"zh_cn": {"title": "每日 AI 资讯", "content": []}}

    result = delivery.send_post(payload, "run-1:sha")

    _, request = session.requests[-1]
    assert request["json"]["receive_id"] == "oc_test"
    assert request["json"]["msg_type"] == "post"
    assert json.loads(request["json"]["content"]) == payload
    assert result.message_id == "om_post"
