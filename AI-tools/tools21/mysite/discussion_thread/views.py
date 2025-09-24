from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Post, Comment
from .forms import CommentForm, PostForm

# List all posts
class PostListView(ListView):
    model = Post
    template_name = 'discussion_thread/post_list.html'
    context_object_name = 'posts'
    ordering = ['-created_at']

# View a single post with comments
class PostDetailView(DetailView):
    model = Post
    template_name = 'discussion_thread/post_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        return context

# Create a new post
class CreatePostView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'discussion_thread/create_post.html'
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

# Add a comment to a post
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('post-detail', pk=post.pk)
    else:
        form = CommentForm()
    return render(request, 'discussion_thread/post_detail.html', {'form': form, 'post': post})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}. You can now log in!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'discussion_thread/register.html', {'form': form})