
from django.core.cache import caches

def cache_check(**cache_kwargs):
    def _cache_check(func):
        def wrapper(self,request,*args,**kwargs):
            CACHES=caches["goods_detail"]
            if "cache" in cache_kwargs:
                CACHES=caches[cache_kwargs["cache"]]
            key=cache_kwargs["key_prefix"]+str(kwargs["sku_id"])
            response=CACHES.get(key)
            if response:
                return response
            value=func(self,request,*args,**kwargs)
            exp=cache_kwargs.get("expire",300)
            CACHES.set(key,value,exp)
            return value
        return wrapper
    return _cache_check