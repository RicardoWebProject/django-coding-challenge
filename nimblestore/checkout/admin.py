from django.contrib import admin

from .models import Order, OrderItem, Product


class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "price", "stock_quantity"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["unit_price"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "created_at", "updated_at"]
    list_filter = ["status"]
    inlines = [OrderItemInline]


admin.site.register(Product, ProductAdmin)

