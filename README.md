# blog

My personal blog about software engineering hosted on [blog.krudewig-online.de](https://blog.krudewig-online.de).

## Setting up jekyll locally

This blog uses Jekyll, the static web page generator of github.

Jekyll is a ruby package. So you need a ruby environment with the necessary dependencies to generate the blog as html page. Take a look at the [jekyll documentation](https://jekyllrb.com/docs/step-by-step/01-setup/) for a detailed guide on how to set things up. To set up a fresh working environment for this blog only the following commands are necessary (this is for arch linux):

```bash
# Install ruby
sudo pacman -Sy base-devel ruby ruby-bundler

# Clone the repository
git clone https://github.com/chr1st1ank/blog.git
cd blog

# Install the dependencies from the Gemfile:
bundle install
```
The last command installs all the ruby dependencies ("gems") from the Gemfile. This step may take a while because the dependencies are compiled from source code.

## Build process for local preview

For local development do one of the following:
- Build the static pages: `bundle exec jekyll build --future`
- Serve the pages on a local webserver: `bundle exec jekyll serve -P 8080`
- Or serve the pages with apache2 from docker: `docker run -it -v $(pwd)/_site:/usr/local/apache2/htdocs -p8080:80 httpd`

In the latter case the result is available at http://127.0.0.1:8080/

# When finished check for broken links
```shell
wget --spider -r -nd -nv -H -l 1 -w 0.1 http://127.0.0.1:8080
```
