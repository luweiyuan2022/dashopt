from django.urls import path
from django.views.decorators.cache import cache_page

from . import views

urlpatterns=[
    path("index",cache_page(300,cache="goods_index")(views.GoodsIndexView.as_view())),
    path("detail/<int:sku_id>",views.GoodsDetailView.as_view()),
]