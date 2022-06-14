import base64
import random

import jwt
import hashlib
import time

import requests
from django.shortcuts import render
import json
from django.http import JsonResponse

from carts.views import CartsView
from user.models import UserProfile, Address, WeiBoProfile
from django.conf import settings
from django.core.cache import caches
from django.views import View
from django.db import transaction


from .tasks import async_send_active_email, async_send_message
from utils.logging_dec import logging_check
from utils.sms import YunTongXunAPI
from utils.baseview import BaseView
from utils.weiboapi import OauthWeiBoAPI

CODE_CACHE=caches["default"]
SMS_CACHE = caches["sms"]

def users(request):
    data=json.loads(request.body)
    uname=data.get("uname")
    password=data.get("password")
    email=data.get("email")
    phone=data.get("phone")
    # 获取短信验证码
    verify = data.get("verify")

    expire_key = "sms_expire_{}".format(phone)
    redis_code = SMS_CACHE.get(expire_key)

    if not redis_code:
        # 超过10分钟
        return JsonResponse({"code": 10108, "error": {"message": "已过期,请重新获取短信验证码"}})

    if verify != str(redis_code):
        # 10分钟之内,验证码输入错误
        return JsonResponse({"code": 10109, "error": {"message": "验证码有误,请重新输入验证码"}})

    old_users=UserProfile.objects.filter(username=uname)
    if old_users:
        return JsonResponse({"code":10100,"error":"The username is existed"})
    m=hashlib.md5()
    m.update(password.encode())
    pwd_md5=m.hexdigest()
    try:
        user=UserProfile.objects.create(username=uname,
                                    password=pwd_md5,phone=phone,email=email)
    except Exception as e:
        return JsonResponse({"code":10101,
                             "error":"The username is existed"})
    token=make_token(uname)

    try:
        verify_url = get_verify_url(uname)
        #发送激活邮件
        async_send_active_email.delay(email,verify_url)
    except Exception as e:
        print("send email error",e)

        # 购物车数据合并
        offline_data = data.get("carts")
        carts_count = CartsView().merge_carts(offline_data, user.id)
        # 组织数据返回
        result = {
            "code": 200,
            "username": uname,
            "data": {"token": token},
            "carts_count": carts_count
        }

        return JsonResponse(result)

    result={
        "code":200,
        "username":uname,
        "data":{"token":token},
        "carts_count":0
    }

    return JsonResponse(result)


def make_token(uname,expire=3600*24):
    payload={
        "exp":int(time.time())+expire,
        "username":uname
    }
    key=settings.JWT_TOKEN_KEY
    return jwt.encode(payload,key,algorithm="HS256").decode()



def active_view(request):
    code = request.GET.get("code")
    if not code:
        return JsonResponse({"code": 10102, "error": "激活链接异常"})

    code = base64.urlsafe_b64decode(code.encode()).decode()
    code_num,username=code.split("_")
    key = "active_email_%s" % username
    if code_num != CODE_CACHE.get(key):
        return JsonResponse({"code": 10102, "error": "激活验证码不正确"})
    try:
        user = UserProfile.objects.get(username=username)
        user.is_active=True
        user.save()
        CODE_CACHE.delete(key)
        return JsonResponse({"code":200,"data":"激活成功"})
    except Exception as e:
        result = {"code": 10103, "error": e}


class AddressView(BaseView):
    # @logging_check
    def get(self,request,username):
        user=request.myuser
        all_address=\
            Address.objects.filter(user_profile=user,
                                   is_active=True)
        addresslist=[]
        for address in all_address:
            address_dict={
                'id': address.id,  # 地址id
                'address':address.address,  # 地址
                'receiver':address.receiver, # 收货人
                'receiver_mobile':'12345678901', # 联系电话
                'tag':address.tag,  # 地址标签
                'postcode':address.postcode,
                'is_default':address.is_default,
            }
            addresslist.append(address_dict)
        return JsonResponse({"code":200,"addresslist":addresslist})
    # @logging_check
    def post(self,request,username):
        data=request.data
        user = request.myuser
        receiver= data.get("receiver")
        receiver_phone=data.get("receiver_phone")
        address= data.get("address")
        postcode=data.get("postcode")
        tag=data.get("tag")
        old_address=Address.objects.filter(user_profile=user,is_active=True)
        is_default=False
        if not old_address:
            is_default=True
        Address.objects.create(
            user_profile=user,
            receiver=receiver,
            address=address,
            postcode=postcode,
            receiver_mobile=receiver_phone,
            tag=tag,
            is_default=is_default
        )
        return JsonResponse({"code":200,"data":"新增地址成功！"})

    # @logging_check
    def put(self,request,username,id):
        pass

    # @logging_check
    def delete(self,request,username,id):
        data=json.loads(request.body)
        add_id=data.get("id")
        user=request.myuser
        try:
            address=Address.objects.get(user_profile=user,
                                        id=id,is_active=True)
        except Exception as e:
            print("delete address error:",e)
            return JsonResponse({"code":10104,"error":"Get address error"})
        if not address.is_default:
            address.is_active=False
            address.save()
            return JsonResponse({"code":200,"data":"删除成功"})
        return JsonResponse({"code":10105,"error":"默认地址不能删除"})


class DefaultAddressView(BaseView):
    # @logging_check
    def post(self,request,username):
        data=request.data
        user=request.myuser
        uid=data.get("id")
        print("--")
        print(uid)
        with transaction.atomic():
            sid=transaction.savepoint()
            try:
                old_default=Address.objects.get(is_default=True,user_profile=user,is_active=True)
                old_default.is_default=False
                old_default.save()
                new_default=Address.objects.get(id=uid,user_profile=user,is_active=True)
                new_default.is_default=True
                new_default.save()
            except Exception as e:
                print("设置默认失败：",e)
                transaction.savepoint_rollback(sid)
                return JsonResponse({"code":10106,"error":"设置默认地址失败"})
            transaction.savepoint_commit(sid)
        return JsonResponse({"code":200,"data":"设置默认地址成功"})

def sms_view(request):
    """
    短信验证视图逻辑
    1.获取请求体的数据[phone]
    2.调用封装的短信发送接口,实现发送短信
    """
    data = json.loads(request.body)
    phone = data.get("phone")
    # 六位随机数
    code = random.randint(100000, 999999)
    # 判断:如果3分钟之内发过了，则直接返回，否则再发短信
    key = "sms_{}".format(phone)
    redis_code = SMS_CACHE.get(key)
    if redis_code:
        # 3分钟之内已经发过,直接给用户返回,不能再发
        # 前端: data.error.message
        return JsonResponse(
            {"code": 10107, "error": {"message": "3分钟之内只能发一次"}}
        )

    # celery异步发送短信[调用短信接口]
    async_send_message.delay(phone, code)

    # 存入Redis控制短信发送频率：有效期3分钟
    SMS_CACHE.set(key, code, 180)

    # 存入Redis控制验证码有效期：有效期10分钟
    expire_key = "sms_expire_{}".format(phone)
    SMS_CACHE.set(expire_key, code, 600)

    return JsonResponse({"code": 200, "data": "发送成功"})

class OauthWeiBoUrlView(View):
    def get(self,request):
        weibo_api=OauthWeiBoAPI(**settings.WEIBO_CONFIG)
        oauth_url=weibo_api.get_grant_url()
        return JsonResponse({"code": 200, "oauth_url": oauth_url})

class OauthWeiBoView(View):
    def get(self,request):

        code=request.GET.get("code")
        if not code:
            return JsonResponse({"code":10110,"error":"Not code"})
        post_url="https://api.weibo.com/oauth2/access_token"
        post_data={
            "client_id":settings.WEIBO_CONFIG.get("app_key"),
            "client_secret":settings.WEIBO_CONFIG.get("app_secret"),
            "grant_type":"authorization_code",
            "code":code,
            "redirect_uri":settings.WEIBO_CONFIG.get("redirect_uri"),
        }

        access_html=requests.post(url=post_url,data=post_data).json()
        print("------")
        print(access_html)
        print("------")

        # 绑定注册流程
        wuid = access_html.get("uid")
        access_token = access_html.get("access_token")
        # 微博表中查询该 wuid 是否存在
        # 情况1: 不存在,用户第一次使用微博扫码[201]
        # 情况2: 存在,用户一定扫过码,但不一定绑定注册过
        #   2.1 已经和正式用户绑定过[200]
        #   2.2 没有和正式用户绑定过[201]

        # 200: {"code":200, "username": "xxx", "token": "xxx"}
        # 201: {"code": 201, "uid": wuid}
        try:
            weibo_user = WeiBoProfile.objects.get(wuid=wuid)
        except Exception as e:
            print("Get weibo user error:", e)
            # 一定是第一次扫码登录
            WeiBoProfile.objects.create(wuid=wuid, access_token=access_token)
            return JsonResponse({"code": 201, "uid": wuid})

        user = weibo_user.user_profile
        if user:
            # 已经和正式用户绑定过[200]
            return JsonResponse({"code": 200, "username": user.username, "token": make_token(user.username)})
        else:
            # 用户扫过码,但是没有和正式用户绑定过
            return JsonResponse({"code": 201, "uid": wuid})

    def post(self, request):
        """
        绑定注册用户视图逻辑
        1.获取请求体数据
        2.用户表插入数据[UserProfile]
        3.微博表更新数据[WeiBoProfile]
        事务
        """
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        email = data.get("email")
        phone = data.get("phone")
        wuid = data.get("uid")

        # 判断用户名是否可用
        try:
            user = UserProfile.objects.get(username=username)
            return JsonResponse({"code": 10111, "error": "用户名已存在"})
        except Exception as e:
            # 密码加密
            m = hashlib.md5()
            m.update(password.encode())
            pwd_md5 = m.hexdigest()
            # 用户名可用,执行插入和更新语句,事务
            with transaction.atomic():
                sid = transaction.savepoint()
                try:
                    user = UserProfile.objects.create(username=username, password=pwd_md5, email=email, phone=phone)
                    # 更新微博表外键
                    weibo_user = WeiBoProfile.objects.get(wuid=wuid)
                    weibo_user.user_profile = user
                    weibo_user.save()
                except Exception as e:
                    print("Database error:", e)
                    # 回滚
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({"code": 10112, "error": "请重新尝试"})

                # 提交事务
                transaction.savepoint_commit(sid)

            # 生成token
            token = make_token(username)
            # 发送激活邮件
            verify_url = get_verify_url(username)
            async_send_active_email.delay(email, verify_url)

            return JsonResponse({"code": 200, "username": username, "token": token})

def get_verify_url(uname):
    """功能函数: 生成邮件激活链接"""
    code_num = "%d" % random.randint(1000, 9999)
    code = "%s_%s" % (code_num, uname)
    code = base64.urlsafe_b64encode(code.encode()).decode()
    # 存储随机数
    key = "active_email_%s" % uname
    CODE_CACHE.set(key, code_num, 86400 * 3)
    # 激活链接
    verify_url = "http://127.0.0.1:7000/dadashop/templates/active.html?code=" + code

    return verify_url