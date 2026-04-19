from __future__ import annotations

from django import forms
from django.urls import reverse_lazy

from .models import Account, Category, Transaction


class DateInput(forms.DateInput):
    input_type = 'date'


class TransactionForm(forms.ModelForm):
    kind = forms.ChoiceField(
        choices=Category.Kind.choices,
        label='種別',
        widget=forms.Select(attrs={
            'class': 'form-input',
            'hx-get': reverse_lazy('ledger:category_options'),
            'hx-target': '#id_category',
            'hx-swap': 'innerHTML',
            'hx-trigger': 'change',
        }),
    )

    field_order = ['date', 'account', 'kind', 'category', 'amount', 'description', 'memo']

    class Meta:
        model = Transaction
        fields = ['date', 'account', 'category', 'amount', 'description', 'memo']
        widgets = {
            'date': DateInput(attrs={'class': 'form-input'}),
            'account': forms.Select(attrs={'class': 'form-input'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '1', 'min': '1'}),
            'description': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '例: スーパー、給与、電気代'}),
            'memo': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': '任意メモ'}),
        }
        labels = {
            'date': '日付',
            'account': '口座',
            'category': 'カテゴリ',
            'amount': '金額',
            'description': '摘要',
            'memo': 'メモ',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = Account.objects.filter(is_active=True).order_by('name')
        for field in self.fields.values():
            field.help_text = ''

        # POST データ → 既存インスタンスの種別 → デフォルト（支出）の優先順で kind を決定
        if self.data.get('kind') in Category.Kind.values:
            kind = self.data['kind']
        elif self.instance and self.instance.pk:
            kind = self.instance.category.kind
        else:
            kind = Category.Kind.EXPENSE

        self.fields['kind'].initial = kind
        self.fields['category'].queryset = Category.objects.filter(
            is_active=True, kind=kind
        ).order_by('name')

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get('kind')
        category = cleaned.get('category')
        if kind and category and category.kind != kind:
            raise forms.ValidationError(
                '種別とカテゴリが一致しません。種別を変更したときはカテゴリを再選択してください。'
            )
        return cleaned


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'opening_balance', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '例: 三菱UFJ、現金'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-input', 'step': '1', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': '任意メモ'}),
        }
        labels = {
            'name': '口座名',
            'opening_balance': '初期残高',
            'notes': 'メモ',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = ''
        if self.instance and self.instance.pk:
            self.fields['opening_balance'].widget.attrs['readonly'] = True
            self.fields['opening_balance'].help_text = '初期残高は残高計算に影響するため変更できません。'

    def clean_name(self):
        name = self.cleaned_data['name']
        qs = Account.objects.filter(name=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'「{name}」は既に使われています。別の名前を入力してください。')
        return name

    def clean_opening_balance(self):
        if self.instance and self.instance.pk:
            return self.instance.opening_balance
        return self.cleaned_data['opening_balance']


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'kind', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '例: 食費、交通費、給与'}),
            'kind': forms.Select(attrs={'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': '任意メモ'}),
        }
        labels = {
            'name': 'カテゴリ名',
            'kind': '区分',
            'notes': 'メモ',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = ''
        if self.instance and self.instance.pk:
            self.fields['kind'].widget.attrs['disabled'] = True

    def clean_name(self):
        name = self.cleaned_data['name']
        qs = Category.objects.filter(name=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'「{name}」は既に使われています。別の名前を入力してください。')
        return name

    def clean_kind(self):
        if self.instance and self.instance.pk:
            return self.instance.kind
        return self.cleaned_data['kind']
