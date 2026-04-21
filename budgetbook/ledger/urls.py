from django.urls import path

from . import views

app_name = 'ledger'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('categories/options/', views.category_options, name='category_options'),
    path('transactions/export/', views.transaction_export, name='transaction_export'),
    path('transactions/new/', views.transaction_create, name='transaction_create'),
    path('transactions/<int:pk>/edit/', views.transaction_update, name='transaction_update'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),

    path('annual/', views.annual, name='annual'),
    path('expense-breakdown/', views.expense_breakdown, name='expense_breakdown'),

    path('settings/', views.settings_page, name='settings'),
    path('settings/accounts/new/', views.account_create, name='account_create'),
    path('settings/accounts/<int:pk>/edit/', views.account_update, name='account_update'),
    path('settings/accounts/<int:pk>/toggle/', views.account_toggle, name='account_toggle'),
    path('settings/accounts/<int:pk>/delete/', views.account_delete, name='account_delete'),
    path('settings/categories/new/', views.category_create, name='category_create'),
    path('settings/categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('settings/categories/<int:pk>/toggle/', views.category_toggle, name='category_toggle'),
    path('settings/categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
]
