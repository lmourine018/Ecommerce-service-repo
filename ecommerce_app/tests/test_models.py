import pytest
from decimal import Decimal
from django.contrib.auth.models import User
# Use absolute import instead of relative import
from ecommerce_app.models import Category, Product, Customer, Order, OrderItem

print(">>> Starting test_models.py import")

@pytest.mark.django_db
class TestCategoryModel:

    def test_str_without_parent(self):
        cat = Category.objects.create(name="Electronics")
        assert str(cat) == "Electronics"

    def test_str_with_parent(self):
        parent = Category.objects.create(name="Electronics")
        child = Category.objects.create(name="Phones", parent=parent)
        assert str(child) == "Electronics > Phones"

    def test_slug_generation_and_uniqueness(self):
        parent = Category.objects.create(name="Electronics")
        cat1 = Category.objects.create(name="Phones", parent=parent)
        cat2 = Category.objects.create(name="Phones", parent=parent)
        assert cat1.slug == "phones"
        assert cat2.slug.startswith("phones-")
        assert Category.objects.filter(parent=parent).count() == 2

    def test_get_ancestors(self):
        root = Category.objects.create(name="Root")
        child = Category.objects.create(name="Child", parent=root)
        grandchild = Category.objects.create(name="Grandchild", parent=child)

        ancestors = grandchild.get_ancestors()
        assert ancestors == [root, child]

    def test_get_descendants(self):
        root = Category.objects.create(name="Root")
        child = Category.objects.create(name="Child", parent=root)
        grandchild = Category.objects.create(name="Grandchild", parent=child)

        descendants = root.get_descendants()
        assert set(descendants) == {child, grandchild}

    def test_get_tree_structure(self):
        root = Category.objects.create(name="Root")
        child = Category.objects.create(name="Child", parent=root)
        tree = root.get_tree()
        assert tree["name"] == "Root"
        assert tree["children"][0]["name"] == "Child"


@pytest.mark.django_db
class TestProductModel:

    def test_str(self):
        product = Product.objects.create(name="Laptop", description="High-end laptop", price=Decimal("999.99"))
        assert str(product) == "Laptop (High-end laptop)"


@pytest.mark.django_db
class TestCustomerModel:

    def test_str(self):
        user = User.objects.create_user(username="testuser")
        customer = Customer.objects.create(
            user=user,
            first_name="John",
            last_name="Doe",
            email="john@example.com"
        )
        assert str(customer) == "John Doe <john@example.com>"


@pytest.mark.django_db
class TestOrderAndOrderItem:

    def test_order_str_and_total(self):
        user = User.objects.create_user(username="testuser")
        customer = Customer.objects.create(
            user=user, first_name="John", last_name="Doe", email="john@example.com"
        )
        product1 = Product.objects.create(name="Laptop", price=Decimal("1000.00"))
        product2 = Product.objects.create(name="Mouse", price=Decimal("50.00"))

        order = Order.objects.create(customer=customer, status="pending")

        OrderItem.objects.create(order=order, product=product1, quantity=1, unit_price=Decimal("1000.00"))
        OrderItem.objects.create(order=order, product=product2, quantity=2, unit_price=Decimal("50.00"))

        assert str(order).startswith("Order #")
        assert order.total == Decimal("1100.00")

    def test_order_item_str_and_line_total(self):
        user = User.objects.create_user(username="testuser")
        customer = Customer.objects.create(
            user=user, first_name="John", last_name="Doe", email="john@example.com"
        )
        product = Product.objects.create(name="Keyboard", price=Decimal("75.00"))
        order = Order.objects.create(customer=customer)
        item = OrderItem.objects.create(order=order, product=product, quantity=3, unit_price=Decimal("75.00"))

        assert str(item) == "3 x Keyboard @ 75.00"
        assert item.line_total() == Decimal("225.00")