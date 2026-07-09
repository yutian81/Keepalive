## 目录结构

```
.github/workflows/checkin.yml
iamhc
├── checkin.py
├── notify.py
├── requirements.txt
└── README.md
```

## 环境变量

### action Variables

| Variable 名称 | 值 | 说明 |
|---------------|-----|------|
| `IAMHC_BASE_URL` | `https://example.com` | 可不填，默认已设 |
| `IAMHC_USER_ID` | `******` | 用户数字 ID |
| `IAMHC_USERNAME` | `*********` | 登录用户名 |
| `IAMHC_PASSWORD` | `************` | 登录密码 |

> `IAMHC_SESSION_COOKIE` 变量由脚本首次运行时通过 `gh variable set` **自动创建**，无需手动添加。

### action Secrets

| Secret 名称 | 值 | 说明 |
|-------------|-----|------|
| `GH_TOKEN` | `ghp_xxxx...` | GitHub PAT，需 `repo` 或 `actions-variables: write` 权限 |
| `TG_BOT_TOKEN` | `123456:ABC-DEF...` | Telegram Bot Token（不配置则跳过通知） |
| `TG_CHAT_ID` | `123456789` | Telegram Chat ID （不配置则跳过通知）|

## TG 通知效果

### 今日已签到
```
**IAMHC AI 签到通知**
----------------
📅 **日期**：2026年07月09日
👤 **用户**：yuti●●●●●
✅ **签到**：今日已签到
💰 **余额**：$5,746.24
```

### 今日新签到
```
**IAMHC AI 签到通知**
----------------
📅 **日期**：2026年07月09日
👤 **用户**：yuti●●●●●
🎉 **签到**：获得奖励 $1,748.25
💰 **余额**：$6,500.00
```
