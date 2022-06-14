from django.contrib import admin
from .models import SKU
from django.core.cache import caches

# admin.site.register(SKU)
from django.core.cache import caches

GOODS_INDEX_CACHE=caches["goods_index"]

@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)
        GOODS_INDEX_CACHE.clear()
        GOODS_DETAIL_CACHES = caches["goods_detail"]
        key = "gd%s" % obj.id
        GOODS_DETAIL_CACHES.delete(key)
        print("更新数据时，首页缓存清除～～～")
    def delete_model(self,request,obj):
        super().delete_model(request,obj)
        GOODS_INDEX_CACHE.clear()
        CACHES = caches["goods_detail"]
        key = "gd" + str(obj.sku_id)
        CACHES.delete(key)
        print("删除数据时，首页缓存清除～～～")

