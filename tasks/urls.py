from django.contrib.auth import views as auth_views
from django.urls import path
from django.contrib import admin
from . import views
urlpatterns = [
	path('', views.index, name="list"),
	path('update_task/<str:pk>/', views.updateTask, name="update_task"),
	path('delete_task/<str:pk>/', views.deleteTask, name="delete"),
	path('add_watchlist/<str:provider>/', views.add_watchlist, name="add_watchlist"),
	path(
		'login/',
		auth_views.LoginView.as_view(
			template_name='tasks/login.html',
		),
		name="login",
	),
	path(
		'logout/',
		auth_views.LogoutView.as_view(
			template_name='tasks/logout.html',
		),
		name="logout",
	),
	path('register/', views.register_view, name="register"),
	path('fc/authorize/', views.fc_authorize, name="fc_authorize"),
	path('callback', views.fc_callback, name="fc_callback"),
	path('fc/logout/', views.fc_logout, name="fc_logout"),
	path('logout-callback', views.fc_logout_callback, name="fc_logout_callback"),
	path('admin/', admin.site.urls),
]
