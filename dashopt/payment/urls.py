from django.urls import path
from . import views

urlpatterns = [
    path("url", views.OrderView.as_view()),
    # 异步通知路由: payment/payresult
    path("payresult", views.ResultView.as_view()),
    # 同步通知路由: payment/orderinfo
    path("orderinfo", views.OrderInfo.as_view()),
]









