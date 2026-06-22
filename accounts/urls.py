from django.urls import path
from .views import ativar_conta_view, cadastro_view, email_verification_sent_view
from django.contrib.auth import views as auth_views
from .views import LoginPerfilView

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginPerfilView.as_view(), name='login'),
    path(
        'senha/esqueci/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url='done/',
        ),
        name='password_reset',
    ),
    path(
        'senha/esqueci/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'senha/redefinir/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/accounts/senha/redefinir/done/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'senha/redefinir/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='accounts:login'
    ), name='logout'),
    path('cadastro/', cadastro_view, name='cadastro'),
    path(
        'cadastro/verifique-email/',
        email_verification_sent_view,
        name='email_verification_sent',
    ),
    path(
        'cadastro/ativar/<uidb64>/<token>/',
        ativar_conta_view,
        name='email_verification_confirm',
    ),
]
