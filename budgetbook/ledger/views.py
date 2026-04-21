from __future__ import annotations

import csv
from calendar import monthrange
from datetime import date
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import AccountForm, CategoryForm, TransactionForm
from .models import Account, Category, Transaction


def parse_month(month_str: str | None) -> date:
    today = date.today()
    if not month_str:
        return date(today.year, today.month, 1)
    try:
        year, month = month_str.split('-')
        return date(int(year), int(month), 1)
    except (TypeError, ValueError):
        return date(today.year, today.month, 1)


def shift_month(target: date, offset: int) -> date:
    year = target.year + ((target.month - 1 + offset) // 12)
    month = ((target.month - 1 + offset) % 12) + 1
    return date(year, month, 1)


def month_end(target: date) -> date:
    return date(target.year, target.month, monthrange(target.year, target.month)[1])


def month_param(target: date) -> str:
    return target.strftime('%Y-%m')


def clamp_future_month(target: date) -> date:
    today = date.today()
    current_month = date(today.year, today.month, 1)
    return min(target, current_month)


def default_transaction_date(target: date) -> date:
    today = date.today()
    if today.year == target.year and today.month == target.month:
        return today
    return target


def parse_year(year_str: str | None) -> int:
    today = date.today()
    if not year_str:
        return today.year
    try:
        return int(year_str)
    except (TypeError, ValueError):
        return today.year


def clamp_future_year(year: int) -> int:
    return min(year, date.today().year)


TRANSACTIONS_PER_PAGE = 20


def parse_filters(params: dict) -> dict:
    filters = {}
    q = params.get('q', '').strip()
    if q:
        filters['q'] = q
    account = params.get('account', '').strip()
    if account:
        try:
            filters['account'] = int(account)
        except (TypeError, ValueError):
            pass
    category = params.get('category', '').strip()
    if category:
        try:
            filters['category'] = int(category)
        except (TypeError, ValueError):
            pass
    return filters


def build_filter_query_string(filters: dict) -> str:
    parts = []
    if filters.get('q'):
        parts.append(f"q={quote(filters['q'])}")
    if filters.get('account'):
        parts.append(f"account={filters['account']}")
    if filters.get('category'):
        parts.append(f"category={filters['category']}")
    return '&'.join(parts)


def _build_daily_trend(target_month: date) -> list[dict]:
    start = target_month
    end = shift_month(target_month, 1)
    num_days = monthrange(target_month.year, target_month.month)[1]

    rows = (
        Transaction.objects
        .filter(date__gte=start, date__lt=end)
        .values('date')
        .annotate(
            income=Coalesce(
                Sum('amount', filter=Q(category__kind=Category.Kind.INCOME)),
                Value(0, output_field=IntegerField()),
            ),
            expense=Coalesce(
                Sum('amount', filter=Q(category__kind=Category.Kind.EXPENSE)),
                Value(0, output_field=IntegerField()),
            ),
        )
        .order_by('date')
    )

    by_day = {row['date']: row for row in rows}
    result = []
    for d in range(1, num_days + 1):
        key = date(target_month.year, target_month.month, d)
        row = by_day.get(key)
        inc = row['income'] if row else 0
        exp = row['expense'] if row else 0
        result.append({
            'label': f'{d}日',
            'income': inc,
            'expense': exp,
            'net': inc - exp,
        })
    return result


def get_dashboard_context(target_month: date, page: int = 1, filters: dict | None = None) -> dict:
    start = target_month
    end = shift_month(target_month, 1)

    base_qs = Transaction.objects.select_related('account', 'category')
    monthly_qs = base_qs.filter(date__gte=start, date__lt=end)

    income = monthly_qs.filter(category__kind=Category.Kind.INCOME).aggregate(
        total=Coalesce(Sum('amount'), Value(0, output_field=IntegerField()))
    )['total']
    expense = monthly_qs.filter(category__kind=Category.Kind.EXPENSE).aggregate(
        total=Coalesce(Sum('amount'), Value(0, output_field=IntegerField()))
    )['total']
    net = income - expense

    expense_by_category = list(
        monthly_qs.filter(category__kind=Category.Kind.EXPENSE)
        .values('category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total', 'category__name')[:8]
    )

    account_balances = list(
        Account.objects.filter(is_active=True)
        .annotate(
            income_total=Coalesce(
                Sum(
                    'transaction__amount',
                    filter=Q(
                        transaction__category__kind=Category.Kind.INCOME,
                        transaction__date__lte=month_end(target_month),
                    ),
                ),
                Value(0, output_field=IntegerField()),
            ),
            expense_total=Coalesce(
                Sum(
                    'transaction__amount',
                    filter=Q(
                        transaction__category__kind=Category.Kind.EXPENSE,
                        transaction__date__lte=month_end(target_month),
                    ),
                ),
                Value(0, output_field=IntegerField()),
            ),
        )
        .order_by('name')
    )

    for account in account_balances:
        account.current_balance = account.opening_balance + account.income_total - account.expense_total

    all_accounts = list(Account.objects.filter(is_active=True).order_by('name'))
    all_categories = list(Category.objects.filter(is_active=True).order_by('kind', 'name'))

    if not filters:
        filters = {}
    filtered_qs = monthly_qs
    if filters.get('q'):
        filtered_qs = filtered_qs.filter(description__icontains=filters['q'])
    if filters.get('account'):
        filtered_qs = filtered_qs.filter(account_id=filters['account'])
    if filters.get('category'):
        filtered_qs = filtered_qs.filter(category_id=filters['category'])

    is_filtered = bool(filters)
    filter_qs = build_filter_query_string(filters)

    paginator = Paginator(filtered_qs.order_by('-date', '-id'), TRANSACTIONS_PER_PAGE)
    page_obj = paginator.get_page(page)

    next_month = shift_month(target_month, 1)
    prev_month_param = month_param(shift_month(target_month, -1))
    next_month_param_val = None if target_month >= clamp_future_month(next_month) else month_param(next_month)

    prev_month_url = f"month={prev_month_param}"
    if filter_qs:
        prev_month_url += f"&{filter_qs}"
    next_month_url = None
    if next_month_param_val:
        next_month_url = f"month={next_month_param_val}"
        if filter_qs:
            next_month_url += f"&{filter_qs}"

    return {
        'target_month': target_month,
        'month_param': month_param(target_month),
        'previous_month_query': prev_month_url,
        'next_month_query': next_month_url,
        'income': income,
        'expense': expense,
        'net': net,
        'page_obj': page_obj,
        'expense_by_category': expense_by_category,
        'account_balances': account_balances,
        'has_accounts': bool(all_accounts),
        'has_categories': bool(all_categories),
        'filter_q': filters.get('q', ''),
        'filter_account': filters.get('account', ''),
        'filter_category': filters.get('category', ''),
        'filter_qs': filter_qs,
        'is_filtered': is_filtered,
        'all_accounts': all_accounts,
        'all_categories': all_categories,
        'daily_trend': _build_daily_trend(target_month),
    }


def build_form_context(
    target_month: date,
    form: TransactionForm | None = None,
    transaction: Transaction | None = None,
) -> dict:
    mp = month_param(target_month)
    if transaction:
        if form is None:
            form = TransactionForm(instance=transaction)
        return {
            'form': form,
            'month_param': mp,
            'form_action': f"{reverse('ledger:transaction_update', args=[transaction.pk])}?month={mp}",
            'form_title': '取引を編集',
            'submit_label': '更新する',
            'cancel_url': f"{reverse('ledger:transaction_create')}?month={mp}",
            'transaction': transaction,
        }
    if form is None:
        form = TransactionForm(initial={'date': default_transaction_date(target_month)})
    return {
        'form': form,
        'month_param': mp,
        'form_action': f"{reverse('ledger:transaction_create')}?month={mp}",
        'form_title': '取引を追加',
        'submit_label': '保存する',
        'cancel_url': f"{reverse('ledger:transaction_create')}?month={mp}",
    }


def render_dashboard_bundle(request: HttpRequest, target_month: date, flash_message: str) -> HttpResponse:
    context = get_dashboard_context(target_month, page=1)
    context.update(build_form_context(target_month))
    context['flash_message'] = flash_message
    return render(request, 'ledger/partials/transaction_bundle.html', context)


@login_required
@require_http_methods(['GET'])
def category_options(request: HttpRequest) -> HttpResponse:
    kind = request.GET.get('kind', Category.Kind.EXPENSE)
    if kind not in Category.Kind.values:
        kind = Category.Kind.EXPENSE
    categories = Category.objects.filter(is_active=True, kind=kind).order_by('name')
    return render(request, 'ledger/partials/category_options.html', {'categories': categories})


@login_required
@require_http_methods(['GET'])
def transaction_export(request: HttpRequest) -> HttpResponse:
    target_month = clamp_future_month(parse_month(request.GET.get('month')))
    start = target_month
    end = shift_month(target_month, 1)

    transactions = (
        Transaction.objects.select_related('account', 'category')
        .filter(date__gte=start, date__lt=end)
        .order_by('date', 'id')
    )

    filename = f'kakeibo-{month_param(target_month)}.csv'
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')  # UTF-8 BOM（Excel で開いたとき文字化けしない）

    writer = csv.writer(response)
    writer.writerow(['日付', '種別', '口座', 'カテゴリ', '金額', '摘要', 'メモ'])
    for tx in transactions:
        writer.writerow([
            tx.date.strftime('%Y-%m-%d'),
            tx.category.get_kind_display(),
            tx.account.name,
            tx.category.name,
            tx.amount,
            tx.description,
            tx.memo,
        ])

    return response


@login_required
@require_http_methods(['GET'])
def dashboard(request: HttpRequest) -> HttpResponse:
    target_month = clamp_future_month(parse_month(request.GET.get('month')))
    page = request.GET.get('page', 1)
    filters = parse_filters(request.GET)
    context = get_dashboard_context(target_month, page=page, filters=filters)
    if request.htmx:
        return render(request, 'ledger/partials/dashboard_content.html', context)
    context.update(build_form_context(target_month))
    return render(request, 'ledger/dashboard.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def transaction_create(request: HttpRequest) -> HttpResponse:
    target_month = clamp_future_month(parse_month(request.GET.get('month') or request.POST.get('month')))
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render_dashboard_bundle(request, target_month, '取引を保存しました。')
            return redirect(f"{reverse('ledger:dashboard')}?month={month_param(target_month)}")
        status = 422 if request.htmx else 200
        context = build_form_context(target_month, form=form)
        return render(request, 'ledger/partials/transaction_form_panel.html', context, status=status)

    context = build_form_context(target_month)
    return render(request, 'ledger/partials/transaction_form_panel.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def transaction_update(request: HttpRequest, pk: int) -> HttpResponse:
    transaction = get_object_or_404(Transaction.objects.select_related('category'), pk=pk)
    target_month = clamp_future_month(parse_month(request.GET.get('month') or request.POST.get('month') or month_param(transaction.date.replace(day=1))))

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render_dashboard_bundle(request, target_month, '取引を更新しました。')
            return redirect(f"{reverse('ledger:dashboard')}?month={month_param(target_month)}")
        status = 422 if request.htmx else 200
        context = build_form_context(target_month, form=form, transaction=transaction)
        return render(request, 'ledger/partials/transaction_form_panel.html', context, status=status)

    context = build_form_context(target_month, transaction=transaction)
    return render(request, 'ledger/partials/transaction_form_panel.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def transaction_delete(request: HttpRequest, pk: int) -> HttpResponse:
    transaction = get_object_or_404(Transaction.objects.select_related('account', 'category'), pk=pk)
    target_month = clamp_future_month(parse_month(request.GET.get('month') or request.POST.get('month') or month_param(transaction.date.replace(day=1))))

    if request.method == 'POST':
        transaction.delete()
        if request.htmx:
            return render_dashboard_bundle(request, target_month, '取引を削除しました。')
        return redirect(f"{reverse('ledger:dashboard')}?month={month_param(target_month)}")

    return render(
        request,
        'ledger/partials/transaction_delete_confirm.html',
        {
            'transaction': transaction,
            'month_param': month_param(target_month),
            'delete_action': f"{reverse('ledger:transaction_delete', args=[transaction.pk])}?month={month_param(target_month)}",
            'cancel_url': f"{reverse('ledger:transaction_create')}?month={month_param(target_month)}",
        },
    )


# ---------------------------------------------------------------------------
# Settings: Account & Category management
# ---------------------------------------------------------------------------

def _settings_context() -> dict:
    return {
        'accounts': Account.objects.order_by('-is_active', 'name'),
        'categories': Category.objects.order_by('-is_active', 'kind', 'name'),
    }


@login_required
@require_http_methods(['GET'])
def settings_page(request: HttpRequest) -> HttpResponse:
    context = _settings_context()
    context['account_form'] = AccountForm()
    context['category_form'] = CategoryForm()
    return render(request, 'ledger/settings.html', context)


def _render_account_list(request: HttpRequest, flash: str = '') -> HttpResponse:
    context = {
        'accounts': Account.objects.order_by('-is_active', 'name'),
        'account_form': AccountForm(),
        'flash_message': flash,
    }
    return render(request, 'ledger/partials/account_list.html', context)


def _render_account_form_page(request: HttpRequest, form: AccountForm, *, page_title: str, form_action: str, submit_label: str) -> HttpResponse:
    return render(request, 'ledger/settings_form_page.html', {
        'form': form,
        'page_title': page_title,
        'form_action': form_action,
        'submit_label': submit_label,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def account_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '口座を追加しました。')
            return redirect('ledger:settings')
        return _render_account_form_page(
            request, form,
            page_title='口座を追加',
            form_action=reverse('ledger:account_create'),
            submit_label='追加する',
        )
    return _render_account_form_page(
        request, AccountForm(),
        page_title='口座を追加',
        form_action=reverse('ledger:account_create'),
        submit_label='追加する',
    )


@login_required
@require_http_methods(['GET', 'POST'])
def account_update(request: HttpRequest, pk: int) -> HttpResponse:
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'「{account.name}」を更新しました。')
            return redirect('ledger:settings')
        return _render_account_form_page(
            request, form,
            page_title='口座を編集',
            form_action=reverse('ledger:account_update', args=[pk]),
            submit_label='更新する',
        )
    return _render_account_form_page(
        request, AccountForm(instance=account),
        page_title='口座を編集',
        form_action=reverse('ledger:account_update', args=[pk]),
        submit_label='更新する',
    )


@login_required
@require_http_methods(['POST'])
def account_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    account = get_object_or_404(Account, pk=pk)
    account.is_active = not account.is_active
    account.save(update_fields=['is_active'])
    label = '有効' if account.is_active else '無効'
    return _render_account_list(request, f'「{account.name}」を{label}にしました。')


def _render_category_list(request: HttpRequest, flash: str = '') -> HttpResponse:
    context = {
        'categories': Category.objects.order_by('-is_active', 'kind', 'name'),
        'category_form': CategoryForm(),
        'flash_message': flash,
    }
    return render(request, 'ledger/partials/category_list.html', context)


def _render_category_form_page(request: HttpRequest, form: CategoryForm, *, page_title: str, form_action: str, submit_label: str) -> HttpResponse:
    return render(request, 'ledger/settings_form_page.html', {
        'form': form,
        'page_title': page_title,
        'form_action': form_action,
        'submit_label': submit_label,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def category_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'カテゴリを追加しました。')
            return redirect('ledger:settings')
        return _render_category_form_page(
            request, form,
            page_title='カテゴリを追加',
            form_action=reverse('ledger:category_create'),
            submit_label='追加する',
        )
    return _render_category_form_page(
        request, CategoryForm(),
        page_title='カテゴリを追加',
        form_action=reverse('ledger:category_create'),
        submit_label='追加する',
    )


@login_required
@require_http_methods(['GET', 'POST'])
def category_update(request: HttpRequest, pk: int) -> HttpResponse:
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'「{category.name}」を更新しました。')
            return redirect('ledger:settings')
        return _render_category_form_page(
            request, form,
            page_title='カテゴリを編集',
            form_action=reverse('ledger:category_update', args=[pk]),
            submit_label='更新する',
        )
    return _render_category_form_page(
        request, CategoryForm(instance=category),
        page_title='カテゴリを編集',
        form_action=reverse('ledger:category_update', args=[pk]),
        submit_label='更新する',
    )


@login_required
@require_http_methods(['POST'])
def category_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    category = get_object_or_404(Category, pk=pk)
    category.is_active = not category.is_active
    category.save(update_fields=['is_active'])
    label = '有効' if category.is_active else '無効'
    return _render_category_list(request, f'「{category.name}」を{label}にしました。')


# ---------------------------------------------------------------------------
# Annual summary
# ---------------------------------------------------------------------------

def _build_annual_summary(year: int) -> list[dict]:
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)

    rows = (
        Transaction.objects
        .filter(date__gte=start, date__lt=end)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(
            income=Coalesce(
                Sum('amount', filter=Q(category__kind=Category.Kind.INCOME)),
                Value(0, output_field=IntegerField()),
            ),
            expense=Coalesce(
                Sum('amount', filter=Q(category__kind=Category.Kind.EXPENSE)),
                Value(0, output_field=IntegerField()),
            ),
        )
        .order_by('month')
    )

    by_month = {row['month']: row for row in rows}
    result = []
    for m in range(1, 13):
        key = date(year, m, 1)
        row = by_month.get(key)
        inc = row['income'] if row else 0
        exp = row['expense'] if row else 0
        result.append({
            'month': m,
            'month_param': f'{year}-{m:02d}',
            'label': f'{m}月',
            'income': inc,
            'expense': exp,
            'net': inc - exp,
        })
    return result


@login_required
@require_http_methods(['GET'])
def expense_breakdown(request: HttpRequest) -> HttpResponse:
    today = date.today()
    year = clamp_future_year(parse_year(request.GET.get('year')))
    target_month = clamp_future_month(parse_month(request.GET.get('month')))

    expense_qs = Transaction.objects.filter(category__kind=Category.Kind.EXPENSE)

    # 月間集計
    m_start = target_month
    m_end = shift_month(target_month, 1)
    monthly_rows = list(
        expense_qs.filter(date__gte=m_start, date__lt=m_end)
        .values('category_id', 'category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    monthly_total = sum(r['total'] for r in monthly_rows)
    for r in monthly_rows:
        r['pct'] = round(r['total'] / monthly_total * 100, 1) if monthly_total else 0

    # 年間集計
    y_start = date(year, 1, 1)
    y_end = date(year + 1, 1, 1)
    yearly_rows = list(
        expense_qs.filter(date__gte=y_start, date__lt=y_end)
        .values('category_id', 'category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    yearly_total = sum(r['total'] for r in yearly_rows)
    for r in yearly_rows:
        r['pct'] = round(r['total'] / yearly_total * 100, 1) if yearly_total else 0

    next_month = shift_month(target_month, 1)
    return render(request, 'ledger/expense_breakdown.html', {
        'year': year,
        'target_month': target_month,
        'month_param': month_param(target_month),
        'prev_month_param': month_param(shift_month(target_month, -1)),
        'next_month_param': month_param(next_month) if target_month < clamp_future_month(next_month) else None,
        'prev_year': year - 1,
        'next_year': year + 1 if year < today.year else None,
        'monthly_rows': monthly_rows,
        'monthly_total': monthly_total,
        'yearly_rows': yearly_rows,
        'yearly_total': yearly_total,
    })


@login_required
@require_http_methods(['GET'])
def annual(request: HttpRequest) -> HttpResponse:
    year = clamp_future_year(parse_year(request.GET.get('year')))
    months = _build_annual_summary(year)

    total_income = sum(m['income'] for m in months)
    total_expense = sum(m['expense'] for m in months)
    total_net = total_income - total_expense

    today = date.today()
    prev_year = year - 1
    next_year = year + 1 if year < today.year else None

    return render(request, 'ledger/annual.html', {
        'year': year,
        'months': months,
        'total_income': total_income,
        'total_expense': total_expense,
        'total_net': total_net,
        'prev_year': prev_year,
        'next_year': next_year,
        'annual_trend': months,
    })
