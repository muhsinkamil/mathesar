from django.urls import include, path
from rest_framework_nested import routers

from mathesar import views
from mathesar.api.db import viewsets as db_viewsets
from mathesar.api.ui import viewsets as ui_viewsets

db_router = routers.DefaultRouter()
db_router.register(r'tables', db_viewsets.TableViewSet, basename='table')
db_router.register(r'queries', db_viewsets.QueryViewSet, basename='query')
db_router.register(r'links', db_viewsets.LinkViewSet, basename='links')
db_router.register(r'schemas', db_viewsets.SchemaViewSet, basename='schema')
db_router.register(r'databases', db_viewsets.DatabaseViewSet, basename='database')
db_router.register(r'data_files', db_viewsets.DataFileViewSet, basename='data-file')

db_table_router = routers.NestedSimpleRouter(db_router, r'tables', lookup='table')
db_table_router.register(r'records', db_viewsets.RecordViewSet, basename='table-record')
db_table_router.register(r'columns', db_viewsets.ColumnViewSet, basename='table-column')
db_table_router.register(r'constraints', db_viewsets.ConstraintViewSet, basename='table-constraint')

ui_router = routers.DefaultRouter()
ui_router.register(r'databases', ui_viewsets.DatabaseViewSet, basename='database')

urlpatterns = [
    path('api/db/v0/', include(db_router.urls)),
    path('api/db/v0/', include(db_table_router.urls)),
    path('api/ui/v0/', include(ui_router.urls)),

    # Specifying each route individually to facilitate redirection and data pre-rendering based on route
    path('', views.home, name="home"),
    path('<db_name>/', views.db_home, name="db_home"),
    path('<db_name>/schemas/', views.schemas, name="schemas"),
    path('<db_name>/<int:schema_id>/', views.schema_home, name="schema_home"),
]
