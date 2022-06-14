from django.db import models
from utils.basemodel import BaseModel

# Create your models here.

class UserProfile(BaseModel):
    username=models.CharField(
        max_length=11,verbose_name="用户名",
        unique=True
    )
    password=models.CharField(max_length=32)
    phone=models.CharField(max_length=11)
    email=models.EmailField()
    is_active=models.BooleanField(
        default=False,verbose_name="是否激活"
    )

    class Meta:
        db_table="user_user_profile"


class Address(BaseModel):
    user_profile=models.ForeignKey(
        UserProfile,on_delete=models.CASCADE)
    receiver=models.CharField(
        verbose_name="收件人",max_length=10)
    address=models.CharField(verbose_name="收件地址",max_length=100)
    postcode=models.CharField(verbose_name="邮编",max_length=6)
    receiver_mobile=models.CharField(verbose_name="手机号",max_length=11)
    tag=models.CharField(verbose_name="标签",max_length=11)
    is_default=models.BooleanField(verbose_name="是否为默认地址",default=False)
    is_active=models.BooleanField(verbose_name="是否删除",default=True)



    class Meta:
        db_table = "user_address"


class WeiBoProfile(BaseModel):
    # 微博表
    # 外键: 用户表和微博表 1:1 关系
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True)
    wuid = models.CharField(verbose_name="微博uid", max_length=10, db_index=True, unique=True)
    access_token = models.CharField(verbose_name="微博授权令牌", max_length=32)

    class Meta:
        db_table = "user_weibo_profile"