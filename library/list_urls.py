from django.urls import path

from . import list_views

app_name = "lists"

urlpatterns = [
    path("", list_views.list_index, name="index"),
    path("<int:pk>/", list_views.list_detail, name="detail"),
    path("<int:pk>/rename/", list_views.rename_list, name="rename"),
    path("<int:pk>/delete/", list_views.delete_list, name="delete"),
    path("<int:pk>/visibility/", list_views.set_visibility, name="visibility"),
    path("<int:pk>/share/", list_views.share_add, name="share_add"),
    path("<int:pk>/share/<int:user_pk>/remove/", list_views.share_remove, name="share_remove"),
    path("<int:pk>/items/add/", list_views.add_item, name="add_item"),
    path("<int:pk>/items/<int:entry_pk>/remove/", list_views.remove_item, name="remove_item"),
]
