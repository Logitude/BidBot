from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'nations_mabiweb_bidbot'
urlpatterns = [
    path('', TemplateView.as_view(template_name='nations_mabiweb_bidbot/home.html'), name='home'),
    path('about/', TemplateView.as_view(template_name='nations_mabiweb_bidbot/about.html'), name='about'),
    path('howto/', TemplateView.as_view(template_name='nations_mabiweb_bidbot/howto.html'), name='howto'),
    path('add-username/', views.add_mabiweb_username, name='add_mabiweb_username'),
    path('verify-username/', views.verify_mabiweb_username, name='verify_mabiweb_username'),
    path('verify-username-failure/', views.verify_mabiweb_username_failure, name='verify_mabiweb_username_failure'),
    path('remove-username/', views.remove_mabiweb_username, name='remove_mabiweb_username'),
    path('initiate/', views.initiate, name='initiate'),
    path('initiate-failure/', views.initiate_failure, name='initiate_failure'),
    path('<int:pk>/bid/', views.bid, name='bid'),
    path('<int:pk>/rank/', views.rank, name='rank'),
    path('<int:pk>/confirm/', views.confirm, name='confirm'),
    path('<int:pk>/', views.results, name='results'),
]
