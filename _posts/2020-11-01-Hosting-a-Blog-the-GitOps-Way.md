---
layout: post
title:  "Hosting a Blog the GitOps Way"
description: How to set up a blog which is entirely driven and controlled by git. No database, no manual deployments, no manual updates.
---
**Thanks to static site generators a blog can easily be driven and controlled by markdown files in a git repository. This way it is not necessary to set up a content management system including a database ever worrying to end up hosting yet another hacked Wordpress instance. Instead one can focus on the content and publish by simply pushing to the main branch.**

In the last couple of years I have been testing many new tools or, packages. Some turned out to be not really beneficial for the purpose I had in mind. But others found a permanent place in my toolbox.

Inspired by a colleague who suggested to simply put some markdown files on github I looked

[Ciaran O'Donnell](https://ciaranodonnell.dev/)

## Some subheading

At some point, you’ll want to include images, downloads, or other digital assets along with your text content. One common solution is to create a folder in the root of the project directory called something like assets, into which any images, files or other resources are placed. Then, from within any post, they can be linked to using the site’s root as the path for the asset to include. The best way to do this depends on the way your site’s (sub)domain and path are configured, but here are some simple examples in Markdown:

Including an image asset in a post:
{% raw %}
```html
<ul>
  {% for post in site.posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
    </li>
  {% endfor %}
</ul>
```
{% endraw %}

At some point, you’ll want to include images, downloads, or other digital assets along with your text content. One common solution is to create a folder in the root of the project directory called something like assets, into which any images, files or other resources are placed. Then, from within any post, they can be linked to using the site’s root as the path for the asset to include. The best way to do this depends on the way your site’s (sub)domain and path are configured, but here are some simple examples in Markdown.


## What I need

 - Blog posts:
    - Title
    - Summary
    - date
    - tags (clickable)
    - code snippets
    - comments via staticman


## Setting up jekyll for local previews

Jekyll is a ruby package. So you need a ruby environment with the necessary dependencies to generate the blog as html page. Take a look at the [jekyll documentation](https://jekyllrb.com/docs/step-by-step/) for a detailed guide on how to set things up. To set up a fresh working environment for this blog only the following commands are necessary (this is for arch linux):

```bash
# Install ruby
sudo pacman -Sy base-devel ruby ruby-bundler
# Clone the repository
git clone https://github.com/chr1st1ank/blog.git
cd clone
# Install the dependencies from the Gemfile:
bundle install
```

The last command installs all the ruby dependencies ("gems") from the Gemfile. This step may take a while because the dependencies are compiled from source code.

https://jekyllrb.com/docs/github-pages/
