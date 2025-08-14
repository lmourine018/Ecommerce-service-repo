import pytest
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ecommerce_app.models import Category, Product, Customer, Order, OrderItem


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def category():
    return Category.objects.create(name="Electronics")


@pytest.fixture
def product(category):
    product = Product.objects.create(name="Laptop (Test)", price=1000)
    product.categories.add(category)  # ✅ Link category to product
    return product

@pytest.fixture
def customer(db, django_user_model):
    user = django_user_model.objects.create_user(username="john", password="pass1234")
    return Customer.objects.create(user=user, first_name="John", phone="0712345678")


@pytest.fixture
def order(customer, product):
    order = Order.objects.create(customer=customer)
    OrderItem.objects.create(order=order, product=product, quantity=1, unit_price =100)
    return order


# ---------------- Category Tests ----------------
@pytest.mark.django_db
def test_list_categories(api_client, category):
    url = reverse("category-list")  # Adjust name to your urls.py
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["name"] == "Electronics"


@pytest.mark.django_db
def test_create_category(api_client):
    parent = Category.objects.create(name="Electronics", slug="electronics")
    payload = {"name": "Books", "slug": "books", "parent": parent.id}
    url = reverse("category-list")
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Category.objects.filter(name="Books").exists()

@pytest.mark.django_db
def test_create_product(api_client, category):
    url = reverse("product-list")
    payload = {"name": "Phone", "price": 500, "description": "Desc", "stock": 5, "categories": [category.id]}
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Product.objects.filter(name="Phone").exists()

@pytest.mark.django_db
def test_list_products(api_client, product):
    url = reverse("product-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["name"] == "Laptop (Test)"


@pytest.mark.django_db
@patch("ecommerce_app.views.sms.send")
@patch("ecommerce_app.views.send_mail")
def test_create_order(mock_send_mail, mock_sms_send, api_client, customer, product):
    url = reverse("order-list")
    payload = {
        "customer": customer.id,
        "shipping_address": "123 Main St",
        "items": [
            {
                "product": product.id,
                "quantity": 10,
                "unit_price": 100
            }
        ]
    }
    response = api_client.post(url, payload, format="json")
    print(response.json())  # helpful for debugging if still failing
    assert response.status_code == status.HTTP_201_CREATED
    mock_sms_send.assert_called()
    mock_send_mail.assert_called()
@pytest.mark.django_db
def test_get_order_detail(api_client, order):
    url = reverse("order-detail", args=[order.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == order.id


# ---------------- Average Price ----------------
@pytest.mark.django_db
def test_average_price(api_client, category, product):
    url = reverse("average-price", args=[category.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["average_price"] == product.price
