from django.http import JsonResponse
from goods.models import SKU
from django.core.cache import caches
from django.conf import settings
from utils.baseview import BaseView

CARTS_CACHE = caches["carts"]


class CartsView(BaseView):
    def post(self, request, username):
        """
        添加购物车视图逻辑
        1.获取请求体数据[sku_id | count]
        2.检查上下架状态[sku模型类]
        3.校验库存
        4.存入redis数据库
        5.组织数据返回
        user_id: {
            "sku_id1": [5,1],
            "sku_id2": [8,1],
            "sku_id3": [2,1]
        }
        """
        data = request.data
        sku_id = data.get("sku_id")
        count = int(data.get("count"))
        # 1.上下架状态[sku-is_launched]
        try:
            sku = SKU.objects.get(id=sku_id, is_launched=True)
        except Exception as e:
            return JsonResponse({"code": 10400, "error": "该商品已下架"})
        # 2.库存[sku-stock]
        if count > sku.stock:
            return JsonResponse({"code": 10401, "error": "库存量不足"})
        # 3.存入redis数据库
        # 3.1 获取该用户现在购物车所有数据
        user = request.myuser
        cache_key = self.get_cache_key(user.id)
        carts_data = self.get_carts_all_data(cache_key)
        # 3.2 数据合并
        # {}  ---> {1:[5,1]}
        # {2:[1,1]} ---> {2:[1,1], 1:[5,1]}
        # {1:[1,1]} ---> {1:[6,1]}
        if not carts_data:
            # 用户第一次添加购物车
            li = [count, 1]
        else:
            li = carts_data.get(sku_id)
            if not li:
                # 无需合并
                li = [count, 1]
            else:
                # 需要合并
                old_count = li[0]
                new_count = count + old_count
                if new_count > sku.stock:
                    return JsonResponse({"code": 10402, "error": "库存量不足"})

                li = [new_count, 1]

        # 存入redis数据库
        carts_data[sku_id] = li
        CARTS_CACHE.set(cache_key, carts_data)

        result = {
            "code": 200,
            "data": {"carts_count": len(carts_data)},
            "base_url": settings.PIC_URL
        }

        return JsonResponse(result)

    def get(self, request, username):
        """
        查询购物车视图逻辑
        {"code":200,"skus_list":[{},{}],"base_url":xx}
        1.先从redis中获取数据
        2.根据sku_id获取mysql中数据
        3.组织数据返回
        """
        user = request.myuser
        skus_list = self.get_carts_list(user.id)

        result = {
            "code": 200,
            "data": skus_list,
            "base_url": settings.PIC_URL
        }

        return JsonResponse(result)

    def get_cache_key(self, user_id):
        """
        功能函数: 生成key
        :param user_id: 用户id
        """
        return "carts_%s" % user_id

    def get_carts_all_data(self, cache_key):
        """
        功能函数:获取该用户所有购物车数据
        :param cache_key: redis中的key
        :return: {}
        """
        data = CARTS_CACHE.get(cache_key)
        if not data:
            return {}

        return data

    def merge_carts(self, offline_data, user_id):
        """
        合并购物车
        :param offline_data: 离线购物车数据[{},{}]
        :return: 合并后购物车商品种类的数量
        """
        cache_key = self.get_cache_key(user_id)
        carts_data = self.get_carts_all_data(cache_key)
        # carts_data:{"1":[5,1],"2":[8,1]}
        # offline_data: [{"id":1, "count":5},{"id":3, "count": 6}]
        if not offline_data:
            return len(carts_data)

        for sku_dict in offline_data:
            sku_id = sku_dict.get("id")
            count = int(sku_dict.get("count"))
            if sku_id in carts_data:
                last_count = carts_data[sku_id][0] + count
                carts_data[sku_id][0] = last_count
            else:
                carts_data[sku_id] = [count, 1]

        # 合并完成后更新到redis
        CARTS_CACHE.set(cache_key, carts_data)

        # 并返回合并后的商品总数量
        return len(carts_data)

    def get_carts_list(self, id):
        """
        确认订单页商品列表
        :param id: 用户id
        :return: [{8个键值对},{},...]
        """
        cache_key = self.get_cache_key(id)
        # {"1":[5,1], "2":[3,1]}
        carts_data = self.get_carts_all_data(cache_key)
        skus_query = SKU.objects.filter(id__in=carts_data.keys())

        skus_list = []
        # {"1":[5,1], "2":[8,1]}
        for sku in skus_query:
            value_query = sku.sale_attr_value.all()
            sku_dict = {
                "id": sku.id,
                "name": sku.name,
                "count": carts_data[str(sku.id)][0],
                "selected": carts_data[str(sku.id)][1],
                "default_image_url": str(sku.default_image_url),
                "price": sku.price,
                "sku_sale_attr_name": [i.spu_sale_attr.name for i in value_query],
                "sku_sale_attr_val": [i.name for i in value_query]
            }

            skus_list.append(sku_dict)

        return skus_list

    def get_carts_dict(self, id):
        """
        功能函数:筛选购物车中选中的商品的字典
        :param id: 用户id
        :return: carts_dict
        """
        cache_key = self.get_cache_key(id)
        print("---cache_key---")
        print(cache_key)
        # {"1":[5,1], "2":[3,1],"3":[8,0]}
        carts_data = self.get_carts_all_data(cache_key)
        print("---carts_data---")
        print(carts_data)

        return {k: v for k, v in carts_data.items() if v[1] == 1}

    def del_carts_dict(self, id):
        """
        清除购物车数据[选中状态]
        :param id: 用户id
        :return:
        """
        cache_key = self.get_cache_key(id)
        carts_data = self.get_carts_all_data(cache_key)
        carts_dict = {}
        for k, v in carts_data.items():
            if v[1] == 0:
                carts_dict[k] = v

        # 更新到redis
        CARTS_CACHE.set(cache_key, carts_dict)

        return len(carts_dict)











