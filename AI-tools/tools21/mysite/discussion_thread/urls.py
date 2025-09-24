from django.urls import path
from .views import PostListView, PostDetailView, CreatePostView, add_comment

urlpatterns = [
    path('', PostListView.as_view(), name='post-list'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('post/new/', CreatePostView.as_view(), name='post-create'),
    path('post/<int:pk>/comment/', add_comment, name='add-comment'),
]
