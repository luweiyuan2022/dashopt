import hashlib
import json

from django.shortcuts import render
from django.http import JsonResponse

from carts.views import CartsView
from user.models import UserProfile
# Create your views here.
from user.views import make_token


def tokens(request):
    data=json.loads(request.body)
    username=data.get("username")
    password=data.get("password")
    try:
        user=UserProfile.objects.get(username=username)
    except Exception as e:
        print("Get user error:",e)
        return JsonResponse({"code":10200,
                             "error":"The username is wrong"})
    m=hashlib.md5()
    m.update(password.encode())
    if m.hexdigest()!=user.password:
        return JsonResponse({"code": 10201,
                             "error": "The password is wrong"})
    token=make_token(username)

    # 购物车数据合并[离线购物车和在线购物车]
    offline_data = data.get("carts")
    carts_count = CartsView().merge_carts(offline_data, user.id)
    result={
        'code': 200,
        'username': username,
        'data': { 'token': token },
        'carts_count': carts_count
    }

    return JsonResponse(result)