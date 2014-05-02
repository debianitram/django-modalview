from django.middleware.csrf import get_token
from django.template.loader import render_to_string
from django.http.response import HttpResponse
from django.views.generic.base import (ContextMixin, View, 
									TemplateResponseMixin)

from django_modalview.generic.component import (ModalButton, GET_TEMPLATE,
												 GET_TEMPLATE_CONTENT,
												 BASE_TEMPLATE)
from django_modalview.generic.response import ModalJsonResponse, ModalHttpResponse


class ModalContextMixin(ContextMixin):
		"""
			A default modal context mixin that passes the keyword arguments 
			received by get_context_modal_data as the modal template context.
		"""

	def __init__(self, title=None, description=None, icon=None, *args,
				**kwargs):
		super(ContextMixin, self).__init__(*args, **kwargs)
		self.title = "title"
		self.response = None
		self.icon = icon
		self.description = "description"
		self.close_button = ModalButton('Close', button_type='primary')
		self.content_template_name = None
		self.base_template_name = BASE_TEMPLATE

	def _generate_modal_context(self):
		return {
			'title': self.title,
			'description': self.description,
			'button_close': self.close_button,
			'content_template_name': self.content_template_name,
			'base_template_name': self.base_template_name,
			'icon': self.icon,
			'response': self.response,
		}


	def get_context_modal_data(self, **kwargs):
		kwargs.update(self._generate_modal_context())
		return kwargs


class ModalView(View):
	"""
		Parent class of all the ModalView. Extends the Django generic View
		to override the dispatch method and to overload the get method.
	"""
	def __init__(self, *args, **kwargs):
		super(ModalView, self).__init__(*args, **kwargs)
		self.is_ajax = None

	def dispatch(self, request, *args, **kwargs):
		self.is_ajax = request.is_ajax()
		return super(ModalView, self).dispatch(request, *args, **kwargs)

	def get(self, request, *args, **kwargs):
		context = self.get_context_modal_data(**kwargs)
		return self.render_to_response(
			is_ajax=self.is_ajax,
			context=context
		)

class ModalTemplateMixin(TemplateResponseMixin):
	"""
		Mixin use to render a template. A modal view can be called by a 
		simple Http request or by an Ajax request. The type of the response is 
		different for these two cases. 
	"""
	json_response_class = ModalJsonResponse
	http_response_class = HttpResponse

	def _valid_template(self):
		if not self.is_ajax:
			self.template_name = GET_TEMPLATE

	def _get_content(self, context):
		"""
			Add the csrf_token_value because the mixin use render_to_string
			and not render.
		"""
		self._valid_template()
		context.update({
			"csrf_token_value":get_token(self.request)
		})
		return render_to_string(self.get_template_names(), context)

	def get_response(self, is_ajax):
		if is_ajax:
			return ModalTemplateMixin.json_response_class
		else:
			return ModalTemplateMixin.http_response_class

	def render_to_response(self, is_ajax, context):
		context.update(self.get_context_data())
		ResponseClass = self.get_response(is_ajax)
		return ResponseClass(self._get_content(context))


class ModalUtilMixin(object):
	"""
		Mixin that permit to launch a method with a modal button.
	"""
	def __init__(self, *args, **kwargs):
		super(ModalUtilMixin, self).__init__(*args, **kwargs)
		self.util_kwargs = {}

	def get_util(self, func_name, *args, **kwargs):
		if hasattr(self, func_name):
			util_kwargs = self.get_util_kwargs(**kwargs)
			getattr(self,func_name)(*args, **util_kwargs)
		else:
			raise Exception("You should implement one method name"\
							" {name}!".format(name=func_name))

	def get_util_kwargs(self, *args, **kwargs):
		kwargs.update(self.request.GET)
		self.util_kwargs.update(**kwargs)
		return self.util_kwargs


class BaseModalView(ModalContextMixin, ModalView):
	"""
		A base view to handle a simple modal
	"""

	def __init__(self, *args, **kwargs):
		super(BaseModalTemplateView, self).__init__(*args, **kwargs)
		self.template_name = GET_TEMPLATE
		self.content_template_name = GET_TEMPLATE_CONTENT


class ModalTemplateView(ModalTemplateMixin, BaseModalView):
	"""
		A view that display a simple modal
	"""


class ModalTemplateUtilView(ModalUtilMixin, ModalTemplateView):
	"""
		A view that display a modal and that is able to handle an util method.
		A new button is displayed in the modal to run the tool.
	"""
	def __init__(self, button=None, *args, **kwargs):
		super(ModalTemplateUtilView, self).__init__(*args, **kwargs)
		self.util_button = button if button else ModalButton('Run test')
		self.util_name = 'util'

	def dispatch(self, request, *args, **kwargs):
		self.util_button.url = request.META['PATH_INFO'] +'?util=true'
		return super(ModalTemplateUtilView, self).dispatch(request, *args,
															 **kwargs)

	def get_context_modal_data(self, **kwargs):
		kwargs.update({
			'util_button': self.util_button
		})
		return super(ModalTemplateUtilView,
						self).get_context_modal_data(**kwargs)

	def get(self, request, *args, **kwargs):
		get_dict = self.request.GET 
		if get_dict.get('util'):
			self.get_util(self.util_name, **self.kwargs)
			self.template_name = self.content_template_name

		return super(ModalTemplateUtilView, self).get(request, *args,
						**kwargs)

