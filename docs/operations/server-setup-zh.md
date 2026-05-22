# 服务器设置

目标：服务器只做 Feishu 桥接和任务队列，不保存 Binance 交易密钥。

## 1. 服务位置

项目路径：

```bash
/home/ubuntu/Bian
```

systemd 服务：

```bash
bian-brain.service
```

常用命令：

```bash
sudo systemctl status bian-brain
sudo systemctl restart bian-brain
```

## 2. Feishu 回调

Nginx 将公网地址转发到本地 Brain：

```text
https://dl.zeroxcore.tech/feishu/events -> http://127.0.0.1:8765/feishu/events
```

Feishu 事件订阅 Request URL 使用：

```text
https://dl.zeroxcore.tech/feishu/events
```

## 3. Runner Token

服务器和本地电脑必须使用同一个 `TRADING_LEARNING_RUNNER_TOKEN`。

服务器环境文件示例：

```bash
export TRADING_LEARNING_RUNNER_TOKEN='use-a-random-local-secret'
```

不要把 token 写入 Git。

## 4. 更新部署

```bash
cd /home/ubuntu/Bian
git pull
/home/ubuntu/.local/bin/uv pip install -e . --python /home/ubuntu/Bian/.venv/bin/python --index-url http://mirrors.tencentyun.com/pypi/simple --allow-insecure-host mirrors.tencentyun.com
sudo systemctl restart bian-brain
```

## 5. 安全边界

- 服务器不保存 Binance API key。
- 服务器不直接下实盘订单。
- 本地电脑通过 `/runner/claim` 主动拉任务。
- Feishu 只能入队或查询状态，不能绕过本地确认。
