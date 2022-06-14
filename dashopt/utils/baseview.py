import json

import jwt
from django.http import JsonResponse
from django.views import View

from user.models import UserProfile
from django.conf import settings


class BaseView(View):
    def dispatch(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION")
        if not token:
            return JsonResponse({"code": 403, "error": "Please login01"})
        try:
            payload = jwt.decode(token, key=settings.JWT_TOKEN_KEY, algorithms="HS256")
        except Exception as e:
            return JsonResponse({"code": 403, "error": "Please login02"})
        username = payload.get("username")
        try:
            user = UserProfile.objects.get(username=username)
            request.myuser = user
            data_loads = None
            if request.body:
                data_loads = json.loads(request.body)
            request.data = data_loads
        except:
            return JsonResponse({"code": 403, "error": "Please login03"})


        return super().dispatch(request,*args,**kwargs)