from django.urls import path
from .views import cadastro_view
from django.contrib.auth import views as auth_views
from .views import LoginPerfilView

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginPerfilView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='accounts:login'
    ), name='logout'),
    path('cadastro/', cadastro_view, name='cadastro'),
]