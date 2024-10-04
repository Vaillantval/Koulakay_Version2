from django import template
import re

register = template.Library()


@register.filter
def replace(value:str, arg:str):
    """
    Replacing filter
    Use `{{ "aaa"|replace:"a,c|b" }}`
    """
    if len(arg.split('|')) != 2:
        return value

    what, to = arg.split('|')

    whats = what.split(',')

    if len(whats) > 1:
        for what in whats:
            value = value.replace(what, to)
        return value
        
    return value.replace(what, to)


@register.filter
def remove_language_prefix(text):
    # Define a regular expression pattern to match any language prefix followed by a slash
    pattern = re.compile(r'\b([a-z]{2})/')

    # Replace language prefixes with an empty string
    result = re.sub(pattern, '', text)

    return result