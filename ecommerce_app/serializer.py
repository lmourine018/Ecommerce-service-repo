from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Product, Customer, Order, OrderItem


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'children']

    def get_children(self, obj):
        return CategorySerializer(obj.children.all(), many=True).data


class ProductSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all())
    categories_name = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'stock', 'categories', 'categories_name']

    def get_categories_name(self, obj):
        return [category.name for category in obj.categories.all()]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id','first_name', 'last_name', 'email', 'phone', 'created_at', 'last_login']
        read_only_fields = ['created_at', 'last_login']

    def validate_email(self, value):
        """Ensure email uniqueness"""
        customer = self.instance
        if Customer.objects.filter(email=value).exclude(pk=customer.pk if customer else None).exists():
            raise serializers.ValidationError("A customer with this email already exists.")
        return value



class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_detail', 'quantity', 'unit_price', 'line_total']
        read_only_fields = ['line_total']

    def get_line_total(self, obj):
        return obj.line_total()


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    customer_detail = CustomerSerializer(source='customer', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'customer_detail',
                  'shipping_address','items']
        read_only_fields = ['total', 'placed_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                OrderItem.objects.create(order=instance, **item_data)

        return instance
