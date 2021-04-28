from django.db import models
from django.forms.utils import flatatt
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.translation import ugettext as _
from django import forms
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ModelFormAdminView
from xadmin.util import vendor


class ForeignKeySearchWidget(forms.Widget):
    template_name = None

    def __init__(self, rel, admin_view, attrs=None, using=None):
        self.rel = rel
        self.admin_view = admin_view
        self.db = using
        super(ForeignKeySearchWidget, self).__init__(attrs)

    def build_attrs(self, base_attrs=None, extra_attrs=None, **kwargs):
        if base_attrs is None:
            base_attrs = {}
        to_opts = self.rel.model._meta
        if "class" not in base_attrs:
            base_attrs['class'] = 'select-search'
        else:
            base_attrs['class'] = base_attrs['class'] + ' select-search'
        base_attrs['data-search-url'] = self.admin_view.get_admin_url(
            '%s_%s_changelist' % (to_opts.app_label, to_opts.model_name))
        base_attrs['data-placeholder'] = _('Search %s') % to_opts.verbose_name
        base_attrs['data-choices'] = '?'
        if self.rel.limit_choices_to:
            for i in list(self.rel.limit_choices_to):
                base_attrs['data-choices'] += "&_p_%s=%s" % (i, self.rel.limit_choices_to[i])
            base_attrs['data-choices'] = format_html(base_attrs['data-choices'])
        base_attrs.update(kwargs)
        return super(ForeignKeySearchWidget, self).build_attrs(base_attrs, extra_attrs=extra_attrs)

    def render(self, name, value, attrs=None, **kwargs):
        if attrs is None:
            attrs = {}
        context = self.get_context(name, value, attrs)
        output = [format_html('<select{0}>', flatatt(context['widget']['attrs']))]
        if value:
            output.append(format_html('<option selected="selected" value="{0}">{1}</option>', value, self.label_for_value(value)))
        output.append('</select>')
        return mark_safe('\n'.join(output))

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        model = self.rel.model
        try:
            obj = model._default_manager.using(self.db).get(**{key: value})
            return '%s' % escape(Truncator(obj).words(14, truncate='...'))
        except (ValueError, model.DoesNotExist):
            return ""

    @property
    def media(self):
        return vendor('select.js', 'select.css', 'xadmin.widget.select.js')


class ForeignKeySelectWidget(ForeignKeySearchWidget):

    def build_attrs(self, base_attrs=None, **kwargs):
        if base_attrs is None:
            base_attrs = {}
        attrs = super(ForeignKeySelectWidget, self).build_attrs(base_attrs, **kwargs)
        if "class" not in attrs:
            attrs['class'] = 'select-preload'
        else:
            attrs['class'] = attrs['class'] + ' select-preload'
        attrs['data-placeholder'] = _('Select %s') % self.rel.model._meta.verbose_name
        return attrs


class RelateFieldPlugin(BaseAdminPlugin):

    def get_field_style(self, attrs, db_field, style, **kwargs):
        # search able fk field
        if style in ('fk-ajax', 'fk-select') and isinstance(db_field, models.ForeignKey):
            if (db_field.remote_field.model in self.admin_view.admin_site._registry) and \
                    self.has_model_perm(db_field.remote_field.model, 'view'):
                db = kwargs.get('using')
                widget = (style == 'fk-ajax' and ForeignKeySearchWidget or ForeignKeySelectWidget)
                return dict(attrs or {}, widget=widget(db_field.remote_field, self.admin_view, using=db))
        return attrs


site.register_plugin(RelateFieldPlugin, ModelFormAdminView)
