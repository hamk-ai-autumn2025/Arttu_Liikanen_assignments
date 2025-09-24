from django.contrib import admin
from .models import Post, Comment

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1  # how many extra empty comment fields to show

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at')
    inlines = [CommentInline]

admin.site.register(Post, PostAdmin)
admin.site.register(Comment)
