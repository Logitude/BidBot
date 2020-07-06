from django import template

register = template.Library()

@register.filter(name='get')
def get(obj, key):
    try:
        return obj[key]
    except:
        return ''
