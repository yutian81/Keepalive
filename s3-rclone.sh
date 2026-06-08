#!/bin/bash
# Rclone 通用服务端（带 WebUI + 多S3存储）集成管理脚本

set -e

# ==================== 颜色定义 ====================
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[36m"
PLAIN="\033[0m"

# ==================== 路径定义 ====================
RCLONE_ROOT="/opt/rclone"
RCLONE_CONFIG="${RCLONE_ROOT}/rclone.conf"
RCLONE_CACHE="${RCLONE_ROOT}/cache"
SERVICE_FILE="/etc/systemd/system/rclone-server.service"

# ==================== 权限检查 ====================
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ 错误: 请使用 root 用户或通过 sudo 运行此脚本！${PLAIN}"
    exit 1
fi

# ==================== IP 获取工具函数 ====================
get_public_ip() {
    local ip=$(curl -4 -s --max-time 3 ifconfig.me 2>/dev/null || true)
    if [ -z "$ip" ]; then
        local ipv6=$(curl -6 -s --max-time 3 ifconfig.me 2>/dev/null || true)
        if [ -n "$ipv6" ]; then ip="[$ipv6]"; fi
    fi
    echo "${ip:-公网IP}"
}

# ==================== 环境检查函数 ====================
check_env() {
    # 检查并安装 curl
    if ! command -v curl &> /dev/null; then
        echo -e "${YELLOW}📦 正在安装基础依赖 curl...${PLAIN}"
        if command -v apt &> /dev/null; then 
            apt update && apt install -y curl || true
        elif command -v yum &> /dev/null; then 
            yum install -y curl || true
        fi
    fi

    # 检查系统是否支持 systemctl
    if ! command -v systemctl &> /dev/null; then
        echo -e "${RED}❌ 错误: 当前系统不支持 systemd，无法注册为守护进程服务。${PLAIN}"
        exit 1
    fi
}

# ==================== 安装函数 ====================
do_install() {
    echo -e ""
    echo -e "${BLUE}====================================================${PLAIN}"
    echo -e "${GREEN}      🚀 Rclone 服务端安装（带 Web 管理面板）${PLAIN}"
    echo -e "${BLUE}====================================================${PLAIN}"
    echo -e ""

    # 执行环境依赖检查
    check_env

    # 配置确认
    echo -e "${YELLOW}📝 配置 Web 面板信息（直接回车使用默认值）${PLAIN}"
    echo -e "${BLUE}----------------------------------------------------${PLAIN}"

    read -p "用户名 (默认: admin): " WEB_USER
    WEB_USER=${WEB_USER:-admin}

    read -p "密码   (默认: admin123): " WEB_PASS
    WEB_PASS=${WEB_PASS:-admin123}

    read -p "端口   (默认: 6768): " WEB_PORT
    WEB_PORT=${WEB_PORT:-6768}

    echo -e ""
    echo -e "${GREEN}✅ 配置确认${PLAIN}"
    echo -e "👤 用户名：${BLUE}$WEB_USER${PLAIN}"
    echo -e "🔑 密码：${BLUE}$WEB_PASS${PLAIN}"
    echo -e "🌐 端口：${BLUE}$WEB_PORT${PLAIN}"
    echo -e ""

    # 安装 Rclone
    echo -e "${YELLOW}📦 正在下载并安装 Rclone 官方二进制文件...${PLAIN}"
    if ! curl https://rclone.org/install.sh | bash; then
        echo -e "${RED}❌ Rclone 安装失败，请检查网络连接（如国内环境是否需要代理）。${PLAIN}"
        exit 1
    fi

    # 创建规范目录
    echo -e "${YELLOW}📂 创建配置目录：${RCLONE_ROOT}${PLAIN}"
    mkdir -p ${RCLONE_ROOT}
    mkdir -p ${RCLONE_CACHE}
    touch ${RCLONE_CONFIG}
    chmod 600 ${RCLONE_CONFIG}

    # 自动探测系统里真实的 rclone 绝对路径
    RCLONE_BIN_PATH=$(command -v rclone || echo "/usr/bin/rclone")

    # 注册系统服务
    echo -e "${YELLOW}⚙️  生成系统服务文件...${PLAIN}"
    tee ${SERVICE_FILE} >/dev/null <<EOF
[Unit]
Description=Rclone Server with WebUI
After=network-online.target
Wants=network-online.target

[Service]
User=root
ExecStart=${RCLONE_BIN_PATH} rcd \\
--rc-addr=0.0.0.0:${WEB_PORT} \\
--rc-user=${WEB_USER} \\
--rc-pass=${WEB_PASS} \\
--rc-web-gui \\
--rc-web-gui-no-open-browser \\
--config=${RCLONE_CONFIG}

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # 安全强化：限制普通用户读取服务文件中的明文密码
    chmod 600 ${SERVICE_FILE}

    # 启动服务
    echo -e "${YELLOW}🚀 启动服务并设置开机自启...${PLAIN}"
    systemctl daemon-reload
    systemctl enable rclone-server
    systemctl restart rclone-server

    echo -e "${YELLOW}⏳ 等待服务状态校验...${PLAIN}"
    sleep 3

    # 检查服务实际运行状态
    if ! systemctl is-active rclone-server &> /dev/null; then
        echo -e "${RED}❌ 服务启动失败！可能是端口 ${WEB_PORT} 被占用。${PLAIN}"
        echo -e "${YELLOW}💡 请运行 'journalctl -u rclone-server -n 20' 查看错误日志。${PLAIN}"
        exit 1
    fi

    # 动态探测外网 IP
    PUBLIC_IP=$(get_public_ip)

    # 完成界面
    echo -e ""
    echo -e "${GREEN}====================================================${PLAIN}"
    echo -e "${GREEN}🎉 Rclone 服务端安装成功且运行正常！${PLAIN}"
    echo -e "====================================================${PLAIN}"
    echo -e "🌐 访问地址：${BLUE}http://${PUBLIC_IP}:${WEB_PORT}${PLAIN}"
    echo -e "👤 用户名：${BLUE}${WEB_USER}${PLAIN}"
    echo -e "🔑 密码：${BLUE}${WEB_PASS}${PLAIN}"
    echo -e ""
    echo -e "📂 配置文件路径：${BLUE}${RCLONE_CONFIG}${PLAIN}"
    echo -e "💡 提示：如果无法访问，请确保防火墙已放行 ${WEB_PORT} 端口。"
    echo -e "====================================================${PLAIN}"
    echo -e ""
}

# ==================== 卸载函数 ====================
do_uninstall() {
    echo -e ""
    echo -e "${RED}====================================================${PLAIN}"
    echo -e "${RED}      ⚠️  Rclone 服务端完全卸载程序${PLAIN}"
    echo -e "${RED}====================================================${PLAIN}"
    echo -e ""
    
    read -p "确定要卸载 Rclone 服务端吗？(y/n): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}❌ 卸载已取消。${PLAIN}"
        exit 0
    fi

    # 1. 停止并清理 Systemd 服务
    if [ -f "$SERVICE_FILE" ]; then
        echo -e "${YELLOW}🛑 正在停止并禁用 rclone-server 服务...${PLAIN}"
        systemctl stop rclone-server || true
        systemctl disable rclone-server || true
        echo -e "${YELLOW}🗑️  删除服务文件...${PLAIN}"
        rm -f "$SERVICE_FILE"
        systemctl daemon-reload
    fi

    # 2. 删除 Rclone 二进制文件
    echo -e "${YELLOW}🗑️  移除 Rclone 主程序二进制文件...${PLAIN}"
    rm -f /usr/bin/rclone || true
    rm -f /usr/local/bin/rclone || true
    rm -rf /usr/share/man/man1/rclone.1 || true

    # 3. 询问是否保留数据
    echo -e ""
    read -p "是否删除所有配置文件、S3存储凭证及缓存目录？(y/n, 默认 n): " REMOVE_DATA
    REMOVE_DATA=${REMOVE_DATA:-n}
    
    if [[ "$REMOVE_DATA" =~ ^[Yy]$ ]]; then
        if [ -d "$RCLONE_ROOT" ]; then
            echo -e "${YELLOW}🗑️  正在清除数据目录 ${RCLONE_ROOT} ...${PLAIN}"
            rm -rf "$RCLONE_ROOT"
        fi
        echo -e "${GREEN}✨ 所有相关配置及缓存已全部清除。${PLAIN}"
    else
        echo -e "${BLUE}💾 已保留配置文件路径: ${RCLONE_CONFIG}${PLAIN}"
    fi

    echo -e ""
    echo -e "${GREEN}🏁 Rclone 服务端及组件已成功卸载！${PLAIN}"
    echo -e ""
}

# ==================== 主菜单控制 ====================
clear
echo -e "${BLUE}====================================================${PLAIN}"
echo -e "${GREEN}    🗂️  Rclone 自动化集成管理工具 (S3挂载)${PLAIN}"
echo -e "${BLUE}====================================================${PLAIN}"
echo -e " 1. 安装 Rclone (带 WebUI)"
echo -e " 2. 卸载 Rclone"
echo -e " 0. 退出脚本"
echo -e "${BLUE}====================================================${PLAIN}"
read -p "请选择一个选项 [0-2]: " CHOICE

case "$CHOICE" in
    1)
        do_install
        ;;
    2)
        do_uninstall
        ;;
    0)
        echo -e "${BLUE}👋 已退出脚本。${PLAIN}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ 输入错误，请输入正确的数字 [0-2]${PLAIN}"
        exit 1
        ;;
esac
