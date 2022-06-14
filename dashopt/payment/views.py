import time

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views import View
from django.conf import settings
from alipay import AliPay


app_private_key_string = open(settings.ALIPAY_KEY_DIRS + "app_private_key.pem").read()
alipay_public_key_string = open(settings.ALIPAY_KEY_DIRS + "alipay_public_key.pem").read()


class MyAlipay(View):
    """
    写一个基类,主要用来初始化alipay对象
    其他视图类继承此类后可调用类中任何对象及方法
    """
    def __init__(self, **kwargs):
        # super():不能影响django-View中初始化
        super().__init__(**kwargs)
        # 初始化alipay对象
        self.alipay = AliPay(
            # 应用id,控制台获取
            appid=settings.ALIPAY_APP_ID,
            # 异步通知地址-必须为公网地址[POST请求]
            app_notify_url=None,
            # 应用私钥[用于签名]
            app_private_key_string=app_private_key_string,
            # alipay公钥[验签-验证消息来源]
            alipay_public_key_string=alipay_public_key_string,
            # 签名使用算法
            sign_type="RSA2",
            # 默认False[生产环境], 设置为True[沙箱环境]
            debug=True
        )


class OrderView(MyAlipay):
    def get(self, request):
        """获取页面"""
        return render(request, "alipay.html")

    def get_pay_url(self,order_id,total_amount):
        """
        生成支付地址pay_url,返给前端
        前端:window.location.href=data.pay_url
        """

        # alipay方法:结果为查询字符串
        params = self.alipay.api_alipay_trade_page_pay(
            # 订单标题
            subject=order_id,
            # 订单编号
            out_trade_no=order_id,
            # 总金额
            total_amount=total_amount,
            # 同步通知地址[GET]
            return_url=settings.ALIPAY_RETURN_URL,
            # 异步通知地址-公网IP[POST]
            notify_url=settings.ALIPAY_NOTIFY_URL
        )
        pay_url = "	https://openapi.alipaydev.com/gateway.do?" + params

        return pay_url

class ResultView(MyAlipay):
    def post(self, request):
        """
        notifyUrl视图逻辑[异步通知]
        获取支付结果,修改订单状态
        1.获取请求体数据[接口文档]
        2.验签[使用Alipay公钥验签]
        3.修改订单状态
        """
        # QueryDict ---> Dict
        request_data = {k:request.POST[k] for k in request.POST.keys()}
        # 验签,result为True | False
        sign = request_data.pop("sign")
        result = self.alipay.verify(request_data, sign)
        if result:
            # 验签通过,获取交易结果
            status = request_data.get("trade_status")
            if status == "TRADE_SUCCESS":
                # 修改订单状态
                return HttpResponse("success")
        else:
            return HttpResponse("违法请求")


class OrderInfo(MyAlipay):
    """
        同步通知[GET请求]
        主动查询支付结果
    """
    def get(self, request):
        """
        主动查询视图逻辑
        1.
        调用主动查询接口获取支付结果
        """
        out_trade_no = request.GET.get("out_trade_no")
        trade_no = request.GET.get("trade_no")

        response = self.alipay.api_alipay_trade_query(
            out_trade_no=out_trade_no,
            trade_no=trade_no
        )

        # 获取支付结果

        result = response.get("trade_status")
        if result == "TRADE_SUCCESS":
            # 支付成功,修改数据库订单状态
            return HttpResponse("主动查询,支付成功")
        else:
            return HttpResponse("主动查询,支付失败")















