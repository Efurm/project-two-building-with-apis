from rest_framework.routers import DefaultRouter

from .views import EntryViewSet, MovieListViewSet

router = DefaultRouter()
router.register("entries", EntryViewSet, basename="entry")
router.register("lists", MovieListViewSet, basename="movielist")

urlpatterns = router.urls
