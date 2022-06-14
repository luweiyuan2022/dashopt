from django.urls import path
from . import views

urlpatterns=[
    # 用户邮件激活：v1/users/activation
    path("activation", views.active_view),
    # 地址管理[新增和查询]: v1/users/username/address
    path("<str:username>/address", views.AddressView.as_view()),
    # 地址管理[修改和删除]: v1/users/username/address/id
    path("<str:username>/address/<int:id>", views.AddressView.as_view()),
    # 设置默认地址: v1/users/username/address/default
    path("<str:username>/address/default", views.DefaultAddressView.as_view()),
    # 短信验证: v1/users/sms/code
    path("sms/code", views.sms_view),
    # 微博登录[获取授权登录页]: v1/users/weibo/authorization
    path("weibo/authorization", views.OauthWeiBoUrlView.as_view()),
    # 微博登录[获取access_token]: v1/users/weibo/users
    path("weibo/users", views.OauthWeiBoView.as_view()),
]