#!/usr/bin/env python3
"""
Pella 自动续期脚本 (增强稳定性 - 使用 JavaScript 强制输入绕过交互问题)
支持单账号和多账号

配置变量说明:
- 单账号变量:
    - PELLA_EMAIL / LEAFLOW_EMAIL=登录邮箱
    - PELLA_PASSWORD / LEAFLOW_PASSWORD=登录密码
- 多账号变量:
    - PELLA_ACCOUNTS / LEAFLOW_ACCOUNTS: 格式：邮箱1:密码1,邮箱2:密码2,邮箱3:密码3
- 通知变量 (可选):
    - TG_BOT_TOKEN=Telegram 机器人 Token
    - TG_CHAT_ID=Telegram 聊天 ID
"""

import os
import time
import logging
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PellaAutoRenew:
    # 配置class类常量
    LOGIN_URL = "https://www.pella.app/login"
    HOME_URL = "https://www.pella.app/home" # 登录后跳转的首页
    RENEW_WAIT_TIME = 8 # 点击续期链接后在新页面等待的秒数 (略微增加等待时间以确保请求完成)
    WAIT_TIME_AFTER_LOGIN = 15 # 登录后等待跳转到HOME页面的秒数

    def __init__(self, email, password):
        self.email = gvbh520@gmail.com
        self.password = zhang668
        self.telegram_bot_token = os.getenv('TG_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TG_CHAT_ID', '')
        
        # 存储初始时间的详细信息 (字符串) 和总天数 (浮点数)
        self.initial_expiry_details = "N/A" 
        self.initial_expiry_value = -1.0 
        self.server_url = None # 用于存储找到的服务器详情页URL
        
        if not self.email or not self.password:
            raise ValueError("邮箱和密码不能为空")
        
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """设置Chrome驱动选项"""
        chrome_options = Options()
        
        # GitHub Actions环境配置
        if os.getenv('GITHUB_ACTIONS'):
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
        
        # 通用配置
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except WebDriverException as e:
            logger.error(f"❌ 驱动初始化失败，请检查 Chrome/WebDriver 版本是否匹配: {e}")
            raise

    def wait_for_element_clickable(self, by, value, timeout=10):
        """等待元素可点击"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    
    def wait_for_element_present(self, by, value, timeout=10):
        """等待元素出现"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def extract_expiry_days(self, page_source):
        """
        从页面源码中提取过期时间，并计算总天数（包含小时和分钟的浮点数）。
        返回: (detailed_time_string, total_days_float)
        """
        # 匹配详细时间格式: X D Y H Z M (例如: 2D 3H 7M)
        match = re.search(r"Your server expires in\s*(\d+)D\s*(\d+)H\s*(\d+)M", page_source)
        if match:
            days_int = int(match.group(1))
            hours_int = int(match.group(2))
            minutes_int = int(match.group(3))
            detailed_string = f"{days_int} 天 {hours_int} 小时 {minutes_int} 分钟"
            total_days_float = days_int + (hours_int / 24) + (minutes_int / (24 * 60))
            return detailed_string, total_days_float
            
        # 兼容简单格式 (例如: 30D)
        match_simple = re.search(r"Your server expires in\s*(\d+)D", page_source)
        if match_simple:
            days_int = int(match_simple.group(1))
            detailed_string = f"{days_int} 天"
            return detailed_string, float(days_int)
            
        logger.warning("⚠️ 页面中未找到有效的服务器过期时间格式。")
        return "无法提取", -1.0

    def login(self):
        """执行登录流程，使用 JS 强制输入绕过 'element not interactable' 错误，并增强最终点击的稳定性"""
        logger.info(f"🔑 开始登录流程")
        self.driver.get(self.LOGIN_URL)
        
        # JS 脚本：设置值并触发输入事件
        def js_set_value_and_trigger(element, value):
            self.driver.execute_script(f"arguments[0].value = '{value}';", element)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", element)
        
        # 1. 输入邮箱
        try:
            logger.info("🔍 查找邮箱输入框...")
            email_input = self.wait_for_element_present(By.CSS_SELECTOR, "input[name='identifier']", 15)
            
            # 使用 JS 强制填充值和触发事件
            js_set_value_and_trigger(email_input, self.email)
            logger.info("✅ 邮箱输入 (JS 强制填充) 完成")
            
        except Exception as e:
            raise Exception(f"❌ 查找或输入邮箱失败: {e}")
            
        # 2. 点击 Continue (Identifier 提交)
        try:
            logger.info("🔍 查找并点击 Continue 按钮 (进入密码输入阶段)...")
            # 第一次点击，使用 clickable 确保页面加载完成
            continue_btn_1 = self.wait_for_element_clickable(By.XPATH, "//button[contains(., 'Continue')]", 10)
            
            initial_url = self.driver.current_url 
            
            self.driver.execute_script("arguments[0].click();", continue_btn_1)
            logger.info("✅ 已点击 Continue 按钮 (进入密码输入)")
            
            # 等待 URL 变化
            logger.info("⏳ 等待页面 URL 变化...")
            WebDriverWait(self.driver, 10).until(EC.url_changes(initial_url))
            logger.info("✅ 页面已切换至密码输入流程")

            # 3. 等待密码输入框出现
            logger.info("⏳ 等待密码输入框出现...")
            password_selector = "input[type='password']" 
            password_input = self.wait_for_element_present(By.CSS_SELECTOR, password_selector, 15)
            logger.info("✅ 密码输入框已出现")

            # 4. 输入密码 (使用 JS 强制填充)
            js_set_value_and_trigger(password_input, self.password)
            logger.info("✅ 密码输入 (JS 强制填充) 完成")
            
        except TimeoutException as te:
            if password_selector in str(te):
                 raise Exception(f"❌ 找不到密码输入框 ({password_selector})。密码框未在预期时间内加载。")
            elif "url_changes" in str(te):
                 raise Exception(f"❌ 登录流程失败 (URL切换超时): URL 在 10 秒内未改变。")
            else:
                 raise Exception(f"❌ 登录流程在等待元素时超时: {te}")
                 
        except Exception as e:
            raise Exception(f"❌ 登录流程失败 (步骤 2/3): {e}")

        # 5. 点击 Continue 按钮提交登录
        try:
            # 确保最终登录按钮加载完成
            logger.info("⏳ 等待 2 秒，确保最终登录按钮被激活...")
            time.sleep(2) 

            logger.info("🔍 查找 Continue 登录按钮...")
            login_btn = self.wait_for_element_present(By.XPATH, "//button[contains(., 'Continue')]", 15)
            
            # 使用 JS 强制点击
            self.driver.execute_script("arguments[0].click();", login_btn)
            logger.info("✅ (JS 强制) 已点击 Continue 按钮")
            
        except TimeoutException as te:
            raise Exception(f"❌ 查找最终 Continue 按钮超时 (15s)。可能按钮加载时间过长。: {te}")
        except Exception as e:
            # 如果强制点击仍然失败，则尝试强制表单提交
            logger.warning(f"⚠️ 强制点击失败，尝试强制提交表单: {e}")
            try:
                # 尝试找到父级表单元素并提交
                self.driver.execute_script("arguments[0].closest('form').submit();", login_btn)
                logger.info("✅ (JS 强制) 表单提交成功")
            except Exception as e_submit:
                 raise Exception(f"❌ 强制表单提交失败: {e_submit}")

        
        # 6. 等待登录完成并跳转到 HOME 页面（增强错误捕获）
        try:
            WebDriverWait(self.driver, self.WAIT_TIME_AFTER_LOGIN).until(
                EC.url_to_be(self.HOME_URL) # 确认跳转到 home 页面
            )
            
            if self.driver.current_url.startswith(self.HOME_URL):
                logger.info(f"✅ 登录成功，当前URL: {self.HOME_URL}")
                return True
            else:
                # 理论上不会执行到这里，因为 EC.url_to_be 失败会抛出 TimeoutException
                raise Exception(f"⚠️ 登录后未跳转到 HOME 页面: 当前 URL 为 {self.driver.current_url}")
                
        except TimeoutException:
            # 【核心修正】检查是否有登录错误信息
            try:
                # 查找 Clerk 常见的错误消息选择器
                error_msg_element = self.driver.find_element(By.CSS_SELECTOR, ".cl-alert-danger, [data-testid*='error-message']")
                if error_msg_element.is_displayed():
                    error_text = error_msg_element.text.strip()
                    # 尝试关闭错误提示（可选，不影响逻辑）
                    try:
                        close_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close']")
                        self.driver.execute_script("arguments[0].click();", close_btn)
                    except:
                        pass
                    # 如果找到了错误信息，则明确抛出登录失败
                    raise Exception(f"❌ 登录失败: 页面显示错误信息: {error_text}")
            except NoSuchElementException:
                pass
            
            # 如果没有找到明确的错误信息，则抛出通用超时错误
            raise Exception("⚠️ 登录超时，无法确认登录状态。可能是网络延迟、重定向失败或登录失败但无明确提示。")

    
    def get_server_url(self):
        """在 HOME 页面查找并点击服务器链接，获取服务器 URL"""
        logger.info("🔍 在 HOME 页面查找服务器链接并跳转...")
        
        # 确保当前在 HOME 页面
        if not self.driver.current_url.startswith(self.HOME_URL):
            self.driver.get(self.HOME_URL)
            time.sleep(3) # 允许页面元素加载
            
        try:
            # 查找服务器链接元素：它是一个包含 href="/server/" 的 <a> 标签
            server_link_selector = "a[href*='/server/']"
            
            # 使用 wait_for_element_clickable 确保元素存在且可交互
            server_link_element = self.wait_for_element_clickable(
                By.CSS_SELECTOR, server_link_selector, 15
            )
            
            # 获取链接并点击
            server_link_element.click()
            
            # 等待页面跳转完成 (URL 包含 /server/ 即可)
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/server/")
            )
            
            self.server_url = self.driver.current_url
            logger.info(f"✅ 成功跳转到服务器页面: {self.server_url}")
            return True
            
        except TimeoutException:
            raise Exception("❌ 在 HOME 页面找不到服务器链接或跳转超时 (15s)")
        except NoSuchElementException:
            raise Exception("❌ 在 HOME 页面找不到服务器链接")
        except Exception as e:
            raise Exception(f"❌ 点击服务器链接时出现意外错误: {e}")
    
    def renew_server(self):
        """执行续期流程 - 仅在 self.server_url 已设置时运行 (已优化为 While 循环)"""
        if not self.server_url:
            raise Exception("❌ 缺少服务器 URL，无法执行续期")
            
        logger.info(f"👉 开始在服务器页面 ({self.server_url}) 执行续期流程")
        self.driver.get(self.server_url) # 确保在正确的页面
        time.sleep(5) # 基础等待页面内容加载

        # 1. 提取初始过期时间
        page_source = self.driver.page_source
        self.initial_expiry_details, self.initial_expiry_value = self.extract_expiry_days(page_source)
        logger.info(f"ℹ️ 初始服务器过期时间: {self.initial_expiry_details} (约 {self.initial_expiry_value:.2f} 天)")

        if self.initial_expiry_value == -1.0:
            raise Exception("❌ 无法提取初始过期时间，可能页面加载失败或元素变化")

        # 2. 查找并点击所有续期按钮 (使用 While 循环确保处理所有可点击链接)
        try:
            # 查找所有带有 href 且没有被禁用的链接
            renew_link_selectors = "a[href*='/renew/']:not(.opacity-50):not(.pointer-events-none)"
            renewed_count = 0
            original_window = self.driver.current_window_handle
            
            while True:
                # 必须在每次循环中重新查找所有元素，以应对页面状态变化
                renew_buttons = self.driver.find_elements(By.CSS_SELECTOR, renew_link_selectors)
                
                if not renew_buttons:
                    break # 跳出循环，没有可点击的按钮了

                # 总是点击找到的第一个可点击按钮 (因为 re-find 确保了它处于最新状态)
                button = renew_buttons[0]
                renew_url = button.get_attribute('href')
                
                logger.info(f"🚀 开始处理第 {renewed_count + 1} 个续期链接: {renew_url}")
                
                # 在新标签页中打开链接，避免主页面状态被破坏
                self.driver.execute_script("window.open(arguments[0]);", renew_url)
                time.sleep(1) # 切换窗口前的缓冲

                # 切换到新的标签页
                self.driver.switch_to.window(self.driver.window_handles[-1])

                # 尝试等待新页面的某个元素或 URL 稳定
                try:
                    # 等待 URL 至少包含 'renew' 字样 (基础稳定性)
                    WebDriverWait(self.driver, 5).until(EC.url_contains("/renew/"))
                except:
                    logger.warning("⚠️ 续期页面 URL 未在预期内加载，继续固定等待。")

                logger.info(f"⏳ 在续期页面等待 {self.RENEW_WAIT_TIME} 秒...")
                time.sleep(self.RENEW_WAIT_TIME)

                # 关闭新标签页并切回主页面
                self.driver.close()
                self.driver.switch_to.window(original_window)
                logger.info(f"✅ 第 {renewed_count + 1} 个续期链接处理完成")
                renewed_count += 1
                
                # 每次点击后，必须刷新主服务器页面，确保下次循环能获取最新的可点击按钮列表
                self.driver.get(self.server_url)
                time.sleep(3) # 允许刷新和元素重新加载

            
            # 检查是否因为未找到按钮而结束
            if renewed_count == 0:
                # 检查是否有禁用的按钮存在，以确认是否真的已续期
                disabled_renew_selectors = "a[href*='/renew/'].opacity-50, a[href*='/renew/'].pointer-events-none"
                disabled_buttons = self.driver.find_elements(By.CSS_SELECTOR, disabled_renew_selectors)
                
                if disabled_buttons:
                    return "⏳ 未找到可点击的续期按钮，但找到了禁用的按钮，可能今日已续期。"
                else:
                    return "⏳ 未找到任何续期按钮 (无论是可点击还是禁用)，脚本无法判断状态。"

            # 3. 重新加载服务器页面并获取新的过期时间
            if renewed_count > 0:
                logger.info("🔄 重新加载服务器页面以检查续期结果...")
                self.driver.get(self.server_url)
                time.sleep(5)
                
                final_expiry_details, final_expiry_value = self.extract_expiry_days(self.driver.page_source)
                logger.info(f"ℹ️ 最终服务器过期时间: {final_expiry_details} (约 {final_expiry_value:.2f} 天)")
                
                # 比较浮点数
                if final_expiry_value > self.initial_expiry_value:
                    days_added = final_expiry_value - self.initial_expiry_value
                    
                    # 将增加的天数浮点值转换为详细的 D/H/M 字符串
                    added_seconds = round(days_added * 24 * 3600)
                    added_days = int(added_seconds // (24 * 3600))
                    added_hours = int((added_seconds % (24 * 3600)) // 3600)
                    added_minutes = int((added_seconds % 3600) // 60)
                    added_string = f"{added_days} 天 {added_hours} 小时 {added_minutes} 分钟"

                    return (f"✅ 续期成功! 初始 {self.initial_expiry_details} -> 最终 {final_expiry_details} "
                            f"(共续期 {added_string})")
                            
                elif final_expiry_value == self.initial_expiry_value:
                    return f"⚠️ 续期操作完成，但天数未增加 ({final_expiry_details})。可能续期未生效或当天无额外时间。"
                else:
                    return f"❌ 续期操作完成，但天数不升反降! 初始 {self.initial_expiry_details} -> 最终 {final_expiry_details}"
            else:
                # 这种情况理论上会被 while 循环前的检查捕获
                return "⏳ 未执行续期操作，因为没有找到可点击的续期链接。"

        except TimeoutException:
            raise Exception("❌ 页面元素加载超时")
        except NoSuchElementException as e:
            raise Exception(f"❌ 续期元素查找失败: {e}")
        except Exception as e:
            raise Exception(f"❌ 续期流程中出现意外错误: {e}")
            
    def run(self):
        """单个账号执行流程"""
        try:
            logger.info(f"⏳ 开始处理账号: {self.email}")
            
            # 1. 登录
            if self.login():
                # 2. 跳转到服务器页面并获取 URL
                if self.get_server_url():
                    # 3. 续期
                    result = self.renew_server()
                    logger.info(f"📋 续期结果: {result}")
                    return True, result
                else:
                    return False, "❌ 无法获取服务器URL"
            else:
                return False, "❌ 登录失败"
                
        except Exception as e:
            error_msg = f"❌ 自动续期失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        
        finally:
            if self.driver:
                self.driver.quit()

class MultiAccountManager:
    """多账号管理器 - 简化配置版本"""
    
    def __init__(self):
        self.telegram_bot_token = os.getenv('TG_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TG_CHAT_ID', '')
        self.accounts = self.load_accounts()
    
    def load_accounts(self):
        accounts = []
        logger.info("⏳ 开始加载账号配置...")
        
        # 方法1: 冒号分隔多账号格式 (兼容 PELLA_ACCOUNTS 和 LEAFLOW_ACCOUNTS 变量)
        accounts_str = os.getenv('PELLA_ACCOUNTS', os.getenv('LEAFLOW_ACCOUNTS', '')).strip()
        if accounts_str:
            try:
                logger.info("⏳ 尝试解析冒号分隔多账号配置")
                # 兼容逗号、分号分隔
                account_pairs = [pair.strip() for pair in re.split(r'[;,]', accounts_str) if pair.strip()] 
                
                logger.info(f"👉 找到 {len(account_pairs)} 个账号对配置字符串")
                
                for i, pair in enumerate(account_pairs):
                    if ':' in pair:
                        email, password = pair.split(':', 1)
                        email = email.strip()
                        password = password.strip()
                        
                        if email and password:
                            accounts.append({
                                'email': email,
                                'password': password
                            })
                            logger.info(f"✅ 成功添加第 {i+1} 个账号")
                        else:
                            logger.warning(f"❌ 第 {i+1} 个账号对格式错误或内容为空")
                    else:
                        logger.warning(f"❌ 第 {i+1} 个账号对缺少分隔符 ':' : {pair}")
                
                if accounts:
                    logger.info(f"👉 从多账号格式成功加载了 {len(accounts)} 个账号")
                    return accounts
                else:
                    logger.warning("⚠️ 多账号配置中没有找到有效的账号信息")
            except Exception as e:
                logger.error(f"❌ 解析多账号配置失败: {e}")
        
        # 方法2: 单账号格式 (兼容 PELLA_EMAIL/PASSWORD 和 LEAFLOW_EMAIL/PASSWORD 变量)
        single_email = os.getenv('PELLA_EMAIL', os.getenv('LEAFLOW_EMAIL', '')).strip()
        single_password = os.getenv('PELLA_PASSWORD', os.getenv('LEAFLOW_PASSWORD', '')).strip()
        
        if single_email and single_password:
            accounts.append({
                'email': single_email,
                'password': single_password
            })
            logger.info("👉 加载了单个账号配置")
            return accounts
        
        # 如果所有方法都失败
        logger.error("⚠️ 未找到有效的账号配置")
        logger.error("⚠️ 请检查以下环境变量设置:")
        logger.error("⚠️ 1. PELLA_ACCOUNTS 或 LEAFLOW_ACCOUNTS: 冒号分隔多账号 (email1:pass1,email2:pass2)")
        logger.error("⚠️ 2. PELLA_EMAIL/PELLA_PASSWORD 或 LEAFLOW_EMAIL/LEAFLOW_PASSWORD: 单账号")
        
        raise ValueError("⚠️ 未找到有效的账号配置")
    
    def send_notification(self, results):
        """发送汇总通知到Telegram"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.info("⚠️ Telegram配置未设置，跳过通知")
            return
        
        try:
            # 统计结果
            success_count = sum(1 for _, success, result in results if success and "续期成功" in result)
            already_done_count = sum(1 for _, success, result in results if success and "未找到可点击" in result)
            failure_count = sum(1 for _, success, _ in results if not success)
            total_count = len(results)

            message = f"🎁 Pella自动续期通知\n\n"
            message += f"📋 共处理账号: {total_count} 个，其中：\n"
            message += f"📊 续期成功: {success_count} 个\n"
            message += f"📊 今日已续期: {already_done_count} 个\n"
            message += f"❌ 续期失败: {failure_count} 个\n\n"
            
            for email, success, result in results:
                if success and "续期成功" in result:
                    status = "✅" # 续期成功
                elif "未找到可点击" in result:
                    status = "⏳" # 已续期
                else:
                    status = "❌" # 失败
                
                # 隐藏邮箱部分字符以保护隐私
                if '@' in email:
                    local_part, domain = email.split('@', 1)
                    masked_local = local_part[:3] + "***"
                    masked_email = masked_local + "@" + domain
                else:
                    masked_email = email[:3] + "***"
                
                # 限制结果长度
                short_result = result.split('\n')[0][:100] + ('...' if len(result.split('\n')[0]) > 100 else '')
                message += f"{status} {masked_email}: {short_result}\n"
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Telegram 通知发送成功")
            else:
                logger.error(f"❌ Telegram 通知发送失败: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Telegram 通知发送出错: {e}")
    
    def run_all(self):
        """运行所有账号的续期流程"""
        logger.info(f"👉 开始执行 {len(self.accounts)} 个账号的续期任务")
        
        results = []
        
        for i, account in enumerate(self.accounts, 1):
            logger.info(f"==================================================")
            logger.info(f"👉 处理第 {i}/{len(self.accounts)} 个账号: {account['email']}")
            
            # 初始化成功/失败标志
            success, result = False, "未运行"

            try:
                auto_renew = PellaAutoRenew(account['email'], account['password'])
                success, result = auto_renew.run()
                
                # 在账号之间添加间隔，避免请求过于频繁
                if i < len(self.accounts):
                    wait_time = 5
                    logger.info(f"⏳ 等待{wait_time}秒后处理下一个账号...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                error_msg = f"❌ 处理账号时发生异常: {str(e)}"
                logger.error(error_msg)
                result = error_msg
            
            results.append((account['email'], success, result))
        
        logger.info(f"==================================================")
        # 发送汇总通知
        self.send_notification(results)
        
        # 返回总体结果
        success_count = sum(1 for _, success, _ in results if success)
        return success_count == len(self.accounts), results

def main():
    """主函数"""
    try:
        manager = MultiAccountManager()
        overall_success, detailed_results = manager.run_all()
        
        if overall_success:
            logger.info("✅ 所有账号续期任务完成")
            exit(0)
        else:
            success_count = sum(1 for _, success, _ in detailed_results if success)
            logger.warning(f"⚠️ 部分账号续期失败: {success_count}/{len(detailed_results)} 成功")
            exit(0)
            
    except ValueError as e:
        logger.error(f"❌ 脚本因配置错误退出: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"❌ 脚本执行出错: {e}")
        exit(1)

if __name__ == "__main__":
    main()
