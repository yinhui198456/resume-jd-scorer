import json
from dataclasses import dataclass

import requests


@dataclass(slots=True)
class DeliveryResult:
    delivery_key: str
    message_id: str
    status: str


class FeishuDelivery:
    def __init__(self, app_id: str, app_secret: str, chat_id: str, session=requests):
        self.app_id = app_id
        self.app_secret = app_secret
        self.chat_id = chat_id
        self.session = session

    def get_tenant_token(self) -> str:
        response = self.session.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", json={"app_id": self.app_id, "app_secret": self.app_secret}, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"FEISHU_AUTH_{payload.get('code')}")
        return payload["tenant_access_token"]

    def send_text(self, text: str, delivery_key: str) -> DeliveryResult:
        return self._send("text", {"text": text}, delivery_key)

    def send_post(
        self, payload: dict[str, object], delivery_key: str
    ) -> DeliveryResult:
        return self._send("post", payload, delivery_key)

    def _send(
        self, msg_type: str, content: object, delivery_key: str
    ) -> DeliveryResult:
        token = self.get_tenant_token()
        response = self.session.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            params={"receive_id_type": "chat_id"},
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": self.chat_id,
                "msg_type": msg_type,
                "content": json.dumps(content, ensure_ascii=False),
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"FEISHU_SEND_{payload.get('code')}")
        return DeliveryResult(delivery_key, payload["data"]["message_id"], "succeeded")
