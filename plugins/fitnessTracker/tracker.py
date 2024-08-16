# encoding:utf-8
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
import plugins
from plugins import *
from common.log import logger
import re
import requests
from datetime import datetime

def is_valid_month(month_str):
    """检查字符串是否是有效的月份，格式为1到12的数字或对应的中文月份"""
    valid_months = {'1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12',
                    '一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'}
    return month_str in valid_months

@plugins.register(name="FitnessTracker", desc="A plugin for tracking monthly fitness check-ins", version="0.1", author="liutianpeng")
class FitnessTracker(Plugin):


    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.check_in_success_prompt = "请你随机使用一种风格说一句话来恭喜用户今日运动打卡完成。"
        self.check_in_many_success_prompt = "请你随机使用一种风格说一句话来恭喜用户今日运动打卡完成。并告知用户这是他今日的第{count}次打卡"
        self.check_in_failure_prompt = "打卡失败，努力修复中。。。"
        logger.info("[FitnessTracker] Plugin initialized")

    def on_handle_context(self, e_context: EventContext):
        context = e_context['context']
        if context.type != ContextType.TEXT:
            return

            # 仅在群消息中处理
        if context.get('isgroup'):
            group_name = context['msg'].other_user_nickname
            # 判断 group_name 是否为特定名称
            if group_name == "打卡测试":
                content = context.content.strip()
                # 正则表达式匹配以#滴开头并且包含月卡的消息
                pattern = r"^#滴(.*)月卡.*"
                match = re.match(pattern, content)

                if match:
                    # 提取信息
                    middle_content = match.group(1)

                    current_month = datetime.now().strftime('%m')  # 获取当前月份数字
                    current_month = str(int(current_month))
                    current_month_chinese = datetime.now().strftime('%B')  # 获取当前月份中文
                    current_month_chinese = current_month_chinese.replace('January', '一').replace('February', '二').replace('March', '三').replace('April', '四').replace('May', '五').replace('June', '六').replace('July', '七').replace('August', '八').replace('September', '九').replace('October', '十').replace('November', '十一').replace('December', '十二')

                    # 检查中间的字是否是当前月份
                    if middle_content in {current_month, current_month_chinese}:
                        group_id = context['msg'].other_user_id
                        user_id = context['msg'].actual_user_id
                        user_group_name = context['msg'].actual_user_nickname #如设置昵称则为昵称
                        user_name = context['msg'].actual_user_nick_wx_name #微信名
                        # 调用接口
                        api_url = 'http://47.109.194.91:8080/api/record/punch'
                        payload = {
                            'group_id': group_id,
                            'group_name': group_name,
                            'user_id': user_id,
                            'user_group_name': user_group_name,
                            'user_name': user_name
                        }

                        try:
                            response = requests.post(api_url, json=payload)
                            response.raise_for_status()

                            # 解析接口返回的 JSON 数据
                            response_data = response.json()
                            status = response_data.get('status')
                            record = response_data.get('record', {})

                            if status == 'success':
                                logger.info(f"Punch request successful: {response_data}")
                                # 提取打卡次数
                                punch_count = record.get('PunchCount', 1)

                                e_context["context"].type = ContextType.TEXT
                                if punch_count == 1:
                                    e_context["context"].content = self.check_in_success_prompt
                                elif punch_count > 1:
                                    e_context["context"].content = self.check_in_many_success_prompt.format(count=punch_count)
                                e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
                                return
                            else:
                                logger.warning(f"Punch request failed: {response_data}")
                                reply = Reply()
                                reply.type = ReplyType.TEXT
                                reply.content = self.check_in_failure_prompt
                                e_context["reply"] = reply
                                e_context.action = EventAction.BREAK_PASS
                                return
                        except requests.RequestException as e:
                            logger.error(f"Error sending punch request: {e}")

                        # 准备回复内容
                        reply_content = f"打卡成功！你的打卡信息已记录。"
                        reply = Reply(type=ReplyType.TEXT, content=reply_content)
                        e_context['reply'] = reply
                        e_context.action = EventAction.BREAK_PASS  # 跳过默认处理逻辑
                    else:
                        logger.info("The extracted month is not the current month.")
                        reply = Reply()
                        reply.type = ReplyType.TEXT
                        reply.content = "打卡失败，当前是"+current_month_chinese+"月"
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                        return
                else:
                    logger.info("Message does not match the required pattern.")
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    reply.content = "已关闭AI功能"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
            else:
                logger.info("Message does not belong to a group. Ignoring.")
                e_context.action = EventAction.CONTINUE  # 继续处理
        else:
            logger.info("Message does not belong to a group. Ignoring.")
            e_context.action = EventAction.CONTINUE  # 继续处理