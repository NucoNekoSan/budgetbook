from django.core.validators import MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        abstract = True


class Account(TimeStampedModel):
    name = models.CharField('口座名', max_length=100, unique=True)
    opening_balance = models.IntegerField(
        '初期残高',
        default=0,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField('有効', default=True)
    notes = models.TextField('メモ', blank=True)

    class Meta:
        verbose_name = '口座'
        verbose_name_plural = '口座'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Category(TimeStampedModel):
    class Kind(models.TextChoices):
        INCOME = 'income', '収入'
        EXPENSE = 'expense', '支出'

    name = models.CharField('カテゴリ名', max_length=100, unique=True)
    kind = models.CharField('区分', max_length=10, choices=Kind.choices)
    is_active = models.BooleanField('有効', default=True)
    notes = models.TextField('メモ', blank=True)

    class Meta:
        verbose_name = 'カテゴリ'
        verbose_name_plural = 'カテゴリ'
        ordering = ['kind', 'name']

    def __str__(self) -> str:
        return f'{self.get_kind_display()} | {self.name}'


class Transaction(TimeStampedModel):
    date = models.DateField('日付')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name='口座')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='カテゴリ')
    amount = models.IntegerField(
        '金額',
        validators=[MinValueValidator(1)],
    )
    description = models.CharField('摘要', max_length=120)
    memo = models.TextField('メモ', blank=True)

    class Meta:
        verbose_name = '取引'
        verbose_name_plural = '取引'
        ordering = ['-date', '-id']

    def __str__(self) -> str:
        return f'{self.date} {self.description} {self.amount}'

    @property
    def kind(self) -> str:
        return self.category.kind
