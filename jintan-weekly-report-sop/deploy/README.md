# 金坛二期周报自动化部署

## 文件说明

- `jintan-weekly-report.service`：systemd oneshot 服务，运行周报 pipeline，并在运行成功后自动提交并推送 git
- `jintan-weekly-report.timer`：每 2 小时触发一次（整点：00:00, 02:00, 04:00...）

## 部署要求

1. 确保 `/opt/personal-agent-workspace/.env` 包含所需环境变量：
   - `MINIMAX_API_KEY`（如需启用 LLM 下周计划）
   - 飞书/邮件相关配置（如启用）
2. 确保日志目录存在：
   ```bash
   sudo mkdir -p /var/log
   sudo chown agent:agent /var/log/jintan-weekly-report.log
   ```
3. 确保 git 凭证已配置（`~/.git-credentials`），以便 `ExecStartPost` 能自动 `git push`

## 安装步骤

```bash
sudo cp deploy/jintan-weekly-report.service /etc/systemd/system/
sudo cp deploy/jintan-weekly-report.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jintan-weekly-report.timer
```

## 查看状态

```bash
sudo systemctl status jintan-weekly-report.timer
sudo systemctl list-timers --all | grep jintan
sudo journalctl -u jintan-weekly-report.service -n 50
```

## 手动触发

```bash
sudo systemctl start jintan-weekly-report.service
```

## 自动 git 提交说明

服务在 pipeline 成功后执行：

```bash
cd /opt/personal-agent-workspace/jintan-weekly-report-sop
git add -A
# 只有存在变更时才提交并推送
git diff --cached --quiet || (git commit -m "auto: weekly report update <timestamp>" && git push origin <current-branch>)
```

## 失败告警（可选）

可在 `ExecStartPost` 中增加简单告警脚本，例如当 exit code 非 0 时发送飞书消息。当前版本先通过日志和 systemd 状态进行监控。
