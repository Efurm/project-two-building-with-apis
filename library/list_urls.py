from django.urls import path

from . import list_views

app_name = "lists"

urlpatterns = [
    path("", list_views.list_index, name="index"),
    path("<int:pk>/", list_views.list_detail, name="detail"),
    path("<int:pk>/rename/", list_views.rename_list, name="rename"),
    path("<int:pk>/delete/", list_views.delete_list, name="delete"),
    path("<int:pk>/items/add/", list_views.add_item, name="add_item"),
    path("<int:pk>/items/<int:entry_pk>/remove/", list_views.remove_item, name="remove_item"),
]
