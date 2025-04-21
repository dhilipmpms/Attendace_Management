from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add-member/', views.add_member, name='add_member'),
    path('add-session/', views.add_session, name='add_session'),
    path('mark-attendance/<int:session_id>/', views.mark_attendance, name='mark_attendance'),
    path('calendar/', views.calendar_view, name='calendar_view'),
    path('attendance/<str:date>/', views.attendance_detail, name='attendance_detail'),
    path('members/', views.member_list, name='member_list'),
    path('members/edit/<int:member_id>/', views.edit_member, name='edit_member'),
]
