import os
import uuid
import pytz
import datetime
import subprocess

from django.conf import settings
from django.shortcuts import render
from django.views.generic.base import View
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse


class BaseCommonView(View):

    def send_http_status(self, code):
        return HttpResponse(status=code)

    def send_error_400(self):
        return self.send_http_status(400)

    def send_error_403(self):
        return self.send_http_status(403)

    def send_error_404(self):
        return self.send_http_status(404)

    def render(self, template, **kwargs):
        return render(self.request, template, kwargs)

    def ajax_success(self, data=None, message=None):
        return self.ajax_response(result='success', message=message or '操作成功', data=data)

    def ajax_fail(self, message=None):
        return self.ajax_response(result='fail', message=message or '系统异常')

    def ajax_response(self, result=None, data=None, message=None):
        return JsonResponse({
            'result': result,
            'data': data,
            'message': message,
        })

    def ajax_form_errors(self, form_errors):
        return JsonResponse({'result': 'fail', 'err_msg': form_errors})

    def get_base_context(self, request, form_initial=None):
        query = (request.GET if '?' in request.get_full_path() else form_initial) or {}

        # 分页
        context = {k: int(query.get(k) or v) for k, v in self.pagination_fields.items()}
        context['start_count'] = context['per_page'] * (context['page'] - 1)
        context['base_url'] = self.get_base_url(request, query=query)

        # 检索条件
        SearchForm = getattr(self.__class__, 'SearchForm', None)
        if SearchForm:
            form_instance = SearchForm(query)
            context['form'] = form_instance

        return context

    def get_query_filter(self, form_instance, except_fields=None):
        if form_instance is None:
            return {}
        _except_fields = list(self.pagination_fields.keys())
        _except_fields.extend(except_fields) if except_fields else None
        form_data = form_instance.cleaned_data if form_instance.is_valid() else form_instance.data
        return {k: v for k, v in form_data.items() if
                (v not in [None, '']) and (k not in _except_fields) and (not k.endswith('_exclude'))} if form_instance else None

    def get_exclude_filter(self, form_instance):
        if not form_instance:
            return None
        form_data = form_instance.cleaned_data if form_instance.is_valid() else form_instance.data
        exclude_filter = {}
        for k, v in form_data.items():
            if k.endswith('_exclude'):
                _k = k.rsplit('_exclude', 1)[0]
                exclude_filter[_k] = v
        return exclude_filter

    def get_paginator(self, base_context, model_class=None, form_instance=None, cached_objs=None, filter_except_fields=None, order_by=None):
        _form_instance = form_instance or base_context.get('form')
        if cached_objs:
            all_objs = cached_objs
        else:
            query_filter = self.get_query_filter(_form_instance, except_fields=filter_except_fields)
            all_objs = model_class.normal.filter(**query_filter)
            exclude_filter = self.get_exclude_filter(form_instance)
            if exclude_filter:
                all_objs = all_objs.exclude(**exclude_filter)
            if order_by:
                all_objs = all_objs.order_by(order_by)
        paginator = Paginator(all_objs, per_page=base_context['per_page'])
        return paginator.page(base_context['page'])

    @property
    def pagination_per_page(self):
        return 30

    @property
    def pagination_fields(self):
        return {
            'per_page': self.pagination_per_page,
            'page': 1,
        }

    def get_base_url(self, request, query=None):
        path = request.path
        _query = query or request.GET
        except_fields = ['page']
        query = '&'.join('{}={}'.format(k, v) for k, v in _query.items() if v and k not in except_fields)

        return '{}?{}'.format(path, query)

    def datetime_now(self):
        return datetime.datetime.now().astimezone(pytz.timezone('Asia/Shanghai'))

    def uuid_str(self):
        return str(uuid.uuid4()).replace('-', '')

    def run_subprocess(self, task_type, task_id):
        BASE_DIR = settings.BASE_DIR
        development_path = os.path.join(BASE_DIR, 'do_work.py')
        production_path = os.path.join(BASE_DIR, 'do_work.pyc')
        script_path = production_path if os.path.isfile(production_path) else development_path
        subprocess.Popen(['python3', script_path, task_type, task_id])


class BaseListView(BaseCommonView):
    ModelClass = None
    template_path = None

    def get(self, request):
        context = self.get_base_context(request)

        form_instance = context.get('form')
        query_filter = self.get_query_filter(form_instance)
        exclude_filter = self.get_exclude_filter(form_instance)
        _objects =  getattr(self.ModelClass, 'normal', None) or self.ModelClass.objects
        all_objs = _objects.all()
        if query_filter:
            all_objs = all_objs.filter(**query_filter)
        if exclude_filter:
            all_objs = all_objs.exclude(**exclude_filter)

        paginator = Paginator(all_objs, per_page=context['per_page'])
        paginator = paginator.page(context['page'])
        context['paginator'] = self.format_paginator(paginator)

        return self.render(self.template_path, **context)

    def format_paginator(self, paginator):
        return paginator


class BaseEditView(BaseCommonView):
    ModelClass = None
    template_path = None
    is_edit_view = False
    is_insert_view = False
    ajax_success_message = None

    def _render(self, instance=None):
        return self.render(self.template_path, form=self.EditForm(instance=instance))

    def _get_instance(self, **kwargs):
        return get_object_or_404(self.ModelClass, **kwargs)

    def get(self, request, **kwargs):
        instance = None
        if self.is_edit_view:
            instance = self._get_instance(**kwargs)
        return self._render(instance=instance)

    def post(self, request, **kwargs):
        instance = None
        if self.is_edit_view:
            instance = self._get_instance(**kwargs)

        form = self.EditForm(request.POST, instance=instance)

        if not form.changed_data:
            return self.ajax_fail(message='数据未变更')

        form_errors = form.errors
        if form_errors:
            return self.ajax_form_errors(form_errors)

        instance = form.save(commit=self.is_insert_view)
        if self.is_edit_view:
            instance.save()
        self.after_instance_save(obj_instance=instance, form_instance=form)

        return self.ajax_success(message=self.ajax_success_message)

    def after_instance_save(self, obj_instance, form_instance):
        pass
