GTG uses [Git](https://git-scm.com) for versioning. It might be useful to take a look at [this Git tutorial](https://learnxinyminutes.com/docs/git/) first.


# Getting the code

Get the latest version of the GTG code [on GitHub](https://github.com/getting-things-gnome/gtg). We suggest forking the master branch at first (you can do this with the GitHub web interface). Then clone the forked repository from GitHub to your local computer:

    $ git clone https://github.com/YOUR_GITHUB_USERNAME/gtg.git

Launch GTG with debugging data (so it doesn't mess with your data):

    $ cd path/to/gtg
    $ ./launch.sh


# Working on the feature in a branch

You have your local copy of the code, so now, create a local branch of your local branch:

    $ cd path/to/gtg
    $ git checkout -b cool_new_feature

When working with GitHub, it's a good idea to keep your local *master* branch as a pristine copy of master on GitHub.

Work on your desired improvements.
You can then "add" (choose) and "commit" (save) your changes:

    $ git add changed_file_1_to_include changed_file_2_to_include_too
    $ git commit

Pro tip: using a graphical tool like [gitg](https://wiki.gnome.org/Apps/Gitg/), which not only lets you see visually the relationship between the various branches, but also lets you select which lines of which files you want to "stage" to commit, making it INCREDIBLY easier, and letting you make much cleaner, smaller, "atomic" commits. Check out the [Meld](https://meldmerge.org/) tool, too.

If your branch is solving specific reported issue, please include the number of the issue in the commit message or the pull request description. This will enable others to quickly navigate to the issue being solved. For example, this is a proper Git commit message:

    Make the Task Editor remember its width and height

    The signals were not being correctly interpreted,
    and the data was not saved before closing.

    This fixes GitHub issue #123

Refer to https://chris.beams.io/posts/git-commit/ (for example) for best practices for writing great Git commit messages.


# What if the original master branch has changed?

If the "master" branch has been updated while you were hacking, you can update your local master branch every now and then:

    $ git checkout master  # switch to your local master branch
    $ git pull --rebase origin master  # update your local master branch to match
    $ git checkout cool_new_feature  # go back to your branch

You can then merge modifications from your local "master" branch to your local feature branch (while you are inside "cool_new_feature") with:

    $ git merge master

Or if you know what you're doing,

    $ git rebase -i master

You may be interested in this video to understand how Git's interactive rebase works: https://youtube.com/watch?v=6WU4jKti_vo


# Submitting your changes for review

When you have done some changes or solved a bug, check that everything works, that your code meets our quality standards (see our "coding best practices" document, and don't forget to run the test suite and to check your code's compliance with the tools mentioned in our coding best practices), then "add" and "commit" the changes (again, Gitg makes it much easier and safer).

Afterwards, you need to push your work to your own fork on GitHub (where cool_new_feature is the name of your local branch which you changed.):

    $ git push origin cool_new_feature

When you have pushed your changes to your own repository on GitHub, you can do a pull request to merge your work with the original GTG master. To do this, go to your account on GitHub and click on "New Pull Request". Create a pull request and comment on the corresponding bug (open one at https://github.com/getting-things-gnome/gtg/issues/new if there wasn't one already).

See also our "coding best practices" guide included in our docs/contributors/ folder, as well as the [Git tips & tricks from the Pitivi project](https://gitlab.gnome.org/GNOME/pitivi/-/blob/master/docs/Git.md) as complementary reading.
