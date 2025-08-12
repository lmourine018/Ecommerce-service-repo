from django.db import models
from django.utils.text import slugify
from decimal import Decimal
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, related_name='children', on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (('parent', 'slug'),)
        ordering = ('name',)

    def __str__(self):
        return self.name if not self.parent else f"{self.parent} > {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            # Ensure slug uniqueness under same parent
            counter = 1
            while Category.objects.filter(parent=self.parent, slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_ancestors(self):
        """Return a list of ancestors from root down to parent (excluding self)."""
        node = self
        ancestors = []
        while node.parent is not None:
            node = node.parent
            ancestors.append(node)
        return ancestors[::-1]

    def get_descendants(self):
        """Return a flat list of all descendant Category instances (recursive)."""
        descendants = []
        children = list(self.children.all())
        for child in children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def get_tree(self):
        """Return nested dict representing subtree rooted at this category."""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'children': [child.get_tree() for child in self.children.all().order_by('name')]
        }


class Product(models.Model):
    """Product that can belong to multiple categories (including deep categories)."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    categories = models.ManyToManyField(Category, related_name='products', blank=True)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    oidc_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ('last_name', 'first_name')

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    customer = models.ForeignKey(Customer, related_name='orders', on_delete=models.PROTECT)
    placed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_address = models.TextField(blank=True)

    class Meta:
        ordering = ('-placed_at',)

    def __str__(self):
        return f"Order #{self.pk} — {self.customer} — {self.status}"

    @property
    def total(self):
        items = self.items.all()
        total = sum((item.unit_price * item.quantity) for item in items)
        return total

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='+', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = (('order', 'product'),)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} @ {self.unit_price}"

    def line_total(self):
        return self.unit_price * self.quantity