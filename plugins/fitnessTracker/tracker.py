# encoding:utf-8
import json
import os
import langid
from bridge.bridge import Bridge
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from config import conf
import plugins
from plugins import *
from common.log import logger
import replicate
from common.expired_dict import ExpiredDict
import re
import requests


@plugins.register(name="FitnessTracker", desc="A plugin for tracking monthly fitness check-ins", version="0.1", author="liutianpeng")
class FitnessTracker(Plugin):


    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.check_in_success_prompt = "请随机用诙谐或者严肃的方式说这句话：打卡成功🎉 ，这是你今天第{count}次打卡！继续保持."
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
                pattern = r"^#滴.*月卡.*"
                match = re.match(pattern, content)

                if match:
                    # 提取信息
                    group_id = context['msg'].other_user_id

                    user_id = context['msg'].actual_user_id
                    user_name = context['msg'].actual_user_nickname

                    # 调用接口
                    api_url = 'http://47.109.194.91:8080/api/record/punch'
                    payload = {
                        'group_id': group_id,
                        'group_name': group_name,
                        'user_id': user_id,
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
                            e_context["context"].content = self.check_in_success_prompt.format(count=punch_count)
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