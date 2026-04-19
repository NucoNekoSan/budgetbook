from django import template

register = template.Library()


@register.filter
def yen(value):
    if value in (None, ''):
        return '¥0'
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return value
    return f'¥{amount:,}'