---
layout: post
title:  "Hosting a Blog the GitOps Way"
description: How to set up a blog which is entirely driven and controlled by git. No database, no manual deployments, no manual updates.
---
**Thanks to static site generators a blog can easily be driven and controlled by markdown files in a git repository. This way it is not necessary to set up a content management system including a database ever worrying to end up hosting yet another hacked Wordpress instance. Instead one can focus on the content and publish by simply pushing to the main branch.**

In the last couple of years I have been testing many new tools or, packages. Some turned out to be not really beneficial for the purpose I had in mind. But others found a permanent place in my toolbox. I used them more often, recommended them to colleagues and in some cases even created a tutorial or provided a training. Then at some point I realized that such things are worth sharing with a wider community than just the people working behind locked doors of my company. So there must be a blog.

But how does one manage a blog these days? I've been experimenting with wordpress and at least one other PHP based content management system years ago. At the time these were good tools. When I did some research for available blog engines or content management systems (CMS), I found out that the seasoned veterans like Wordpress or Drupal are still there. They need a webspace with PHP and a database, of course. Installation means copying the source code. Updating means overwriting the source code in place. This works. I have done it before. Others do it regularly. But I also recall a lot of pain with unsuccessfull updates of similar systems, e.g. Nextcloud. And not updating is not an option because the big CMS systems are well-known for being the target (see e.g. [here](https://www.imperva.com/blog/cms-security-tips/) or [here](https://www.wpwhitesecurity.com/why-malicious-hacker-target-wordpress/)). There are more modern systems, e.g. the nodejs application Ghost. I think this is a really good choice. However it is not so different from the "admin" perspective. It is still a stateful service that needs to be managed. And actually in the recent years I have learned that it is well possible to have the full configuration of any service under version control in a github repository and separate it cleanly from the data. That was what I wanted. And actually I had in mind writing the blog posts in Markdown, so also this could be put under version control and there would basically no data be left. So what for do I need a database then?

Inspired by a colleague who suggested to "simply put some markdown files on github" I remembered that there is "github-pages", a feature of github which allows to publish certain content on static websites. We use that often at work to host the documentation rendered from source code. I did some more research on the web and hit a [blog post by Ciaran O'Donnel](https://ciaranodonnell.dev/posts/switching-to-github-io/#what-blog-engines-have-i-tried) which describes very detailed Ciaran's process of choosing a blog engine and how he ended up using github's built-in capabilites. I decided to give it a try.

## Static site generators



## Setting up a blog with Github-pages and Jekyll
### Initial steps
- github account
- repository
- Set up local ruby environment
#### Setting up jekyll for local previews

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

### Configure the blog
- repository layout
- configs
- themes
- additional features (comments, tags, categories, ...)
    - tags (clickable)
    - code snippets
    - comments via staticman

## Publishing the git-ops way
- general process: push to main -> webpage
- updates, database backups
  - right, none of these are necessary. 
  - The configuration is code. The content is code.
- drafts
- working remotely
- In theory: colaborating and reviewing


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





