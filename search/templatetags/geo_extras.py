from django import template
import logging
from django.utils.translation import ugettext as _

register = template.Library()

debug_logger = logging.getLogger("DEBUG")

@register.filter()
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter()
def render_opening_hours(result, popover):
    try:
        oh_text = result.opening_hours.stringify_week_schedules().replace('\n', '<br/>')
    except Exception as e:
        debug_logger.error(
            "Error of HOH ({}) on rendering opening hours of the result (OSM_ID: {}).".format(
                str(e), self.osm_meta[1]
            )
        )
        return ''
    if popover:
        title = _("Horaires d'ouverture")
        oh_content = """\
            <button type="button" class="btn btn-default"\
             data-toggle="popover" title="{title}"\
             data-content="{content}" data-html="true"\
             data-placement="right">\
            <span class="glyphicon glyphicon-time inline-icon"\
             aria-hidden="true"></span>{title}</button>\
        """.format(title=title, content=oh_text)
    else:
        oh_content = '<div class="small-box">{}</div>'.format(oh_text)
    return oh_content

@register.filter()
def render_properties(result):
    return result.search_preset.render_pr(result.properties)

@register.filter()
def render_address_link(result):
    itinerary_url = (
        'https://www.openstreetmap.org/directions?'
        'engine=graphhopper_foot&route={},{};{},{}'
    ).format(
        result.user_coords[0], result.user_coords[1],
        result.coordinates[0], result.coordinates[1]
    )
    title = _("Itinéraire jusqu'à ce point")
    return """\
        <a href="{link}"><span class="glyphicon glyphicon-road inline-icon \"
        aria-hidden="true"></span>{title}</a>\
    """.format(title=title, link=itinerary_url)

@register.filter()
def render_osm_link(result):
    osm_link = "http://www.openstreetmap.org/{}/{}".format(
        result.osm_meta[0],
        result.osm_meta[1]
    )
    alt = _("Lien OSM")
    return """\
        <a href="{link}"><img class="osm-link-logo" \
        src="/static/images/osm_logo.png" alt="{alt}"></a>\
    """.format(link=osm_link, alt=alt)

@register.filter()
def render_coordinate(coord):
    """
        Returns a rounded and stringified number from a float.
        Used to render short GPS coordinates.
    """
    return str(round(coord, 5))

@register.filter()
def render_bool_js(value):
    """
        Returns a stringified boolean value, suitable for JS.
    """
    if value is True:
        return "true"
    else:
        return "false"

@register.filter()
def render_anchor(result, suffix):
    anchor = "result_{type}_{id}_{suffix}".format(
        type=result.osm_meta[0],
        id=result.osm_meta[1],
        suffix=suffix
    )
    return anchor
