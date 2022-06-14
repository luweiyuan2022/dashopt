from dashopt.celery import app
from django.core.mail import send_mail
from django.conf import settings

from utils.sms import YunTongXunAPI


@app.task
def async_send_active_email(email,verify_url):
    subject="达达商城激活邮件"
    html_message="""尊敬的用户你好，请点击激活链接进行激活~~~ 
    <a href="%s" target="_blank">点击此处</a>"""%verify_url
    send_mail(
        subject,  # 题目
        "",  # 消息内容
        "864029788@qq.com",  # 发送者[当前配置邮箱]
        [email],  # 接收者邮件列表
        html_message=html_message
    )

@app.task
def async_send_message(phone, code):
    """异步发送短信任务"""
    sms_api = YunTongXunAPI(**settings.SMS_CONFIG)
    sms_api.run(phone, code)