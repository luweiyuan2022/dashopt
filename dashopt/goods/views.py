from django.conf import settings
from django.http import JsonResponse
from django.views import View

from goods.models import Catalog,SKU,SPU,SKUImage,SPUSaleAttr,SaleAttrValue,SKUSpecValue
from utils.cache_dec import cache_check


class GoodsIndexView(View):
    def get(self,request):
        print("------")
        data=[]
        all_catalog=Catalog.objects.all()
        for cata in all_catalog:
            cata_dict={}
            cata_dict["catalog_id"]=cata.id
            cata_dict["catalog_name"]=cata.name
            spu_ids=SPU.objects.filter(catalog=cata).values("id")
            sku_list=SKU.objects.filter(spu__in=spu_ids)[:3]
            sku=[]
            for one_sku in sku_list:
                d={
                    "skuid": one_sku.id,
                    "caption": one_sku.caption,
                    "name": one_sku.name,
                    "price": one_sku.price,
                    "image": str(one_sku.default_image_url)
                }
                sku.append(d)
            cata_dict["sku"] = sku
            data.append(cata_dict)
        result={
            "code":200,
            "data":data,
            "base_url":settings.PIC_URL
        }
        return JsonResponse(result)


class GoodsDetailView(View):
    @cache_check(key_prefix="gd",key_param="sku_id",cache="goods_detail",expire=60)
    def get(self,request,sku_id):
        try:
            sku_item=SKU.objects.get(id=sku_id)


        except Exception as e:
            return JsonResponse({"code":10300,"error":"没有此商品"})

        data = {}
        sku_catalog=sku_item.spu.catalog
        data["catalog_id"]=sku_catalog.id
        data["catalog_name"]=sku_catalog.name
        data["name"]= sku_item.name,
        data["caption"]=sku_item.caption,
        data["price"]= sku_item.price,
        data["image"]= str(sku_item.default_image_url),
        data["spu"]= sku_item.spu.id,

        img_query=SKUImage.objects.filter(sku=sku_item)
        if img_query:
            data["detail_image"]=img_query[0]
        else:
            data["detail_image"]=""

        attr_value_query=sku_item.sale_attr_value.all()
        data["sku_sale_attr_val_id"]=[i.id for i in attr_value_query]
        data["sku_sale_attr_val_names"]=[i.name for i in attr_value_query]
        attr_name_query=SPUSaleAttr.objects.filter(spu=sku_item.spu)
        data["sku_sale_attr_id"]=[i.id for i in attr_name_query]
        data["sku_sale_attr_names"]=[i.name for i in attr_name_query]

        sku_all_sale_attr_vals_id={}
        sku_all_sale_attr_vals_name={}
        for id in data["sku_sale_attr_id"]:
            sku_all_sale_attr_vals_id[id]=[]
            sku_all_sale_attr_vals_name[id]=[]
            item_query=SaleAttrValue.objects.filter(spu_sale_attr=id)
            for item in item_query:
                sku_all_sale_attr_vals_id[id].append(item.id)
                sku_all_sale_attr_vals_name[id].append(item.name)
        data["sku_all_sale_attr_vals_id"]=  sku_all_sale_attr_vals_id
        data["sku_all_sale_attr_vals_name"]=  sku_all_sale_attr_vals_name
        spec={}
        spec_value_query=SKUSpecValue.objects.filter(sku=sku_item)
        for item in spec_value_query:
            spec[item.spu_spec.name]=item.name
        data["spec"]=spec
        result = {"code": 200, "data": data,
                  "base_url": settings.PIC_URL}
        return JsonResponse(result)

