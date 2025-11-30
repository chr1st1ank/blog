# frozen_string_literal: true

source "https://rubygems.org"

git_source(:github) {|repo_name| "https://github.com/#{repo_name}" }

gem 'github-pages', group: :jekyll_plugins

# Constrain dependencies to be compatible with Ruby 3.1.x
gem 'activesupport', '< 8.0'

group :jekyll_plugins do
    gem "jekyll-include-cache"
    gem "rouge"
end
