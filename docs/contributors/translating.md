# Translating GTG

Like many other open source software, GTG uses gettext to deal with translations.
Basically, [`po/gtg.pot`][gtg-pot] is a template you copy to `po/<lang>.po` and do the translation in.
You can use [GNOME Translation Editor][gtranslator], [Poedit][poedit], any text editor, or other applications to do the translation in.
For existing translations, you would use the old language as a basis, but it is likely not updated to the latest strings.
Because of that, you may need to update the translation files manually.

[gtg-pot]: ../../po/gtg.pot
[gtranslator]: https://wiki.gnome.org/Apps/Gtranslator/
[poedit]: https://poedit.net/
[gettext-plural]: https://www.gnu.org/software/gettext/manual/html_node/Translating-plural-forms.html#Translating-plural-forms

# Updating the translation files

1. Follow the [readme][readme] to pull GTG and install the dependencies, especially meson and gettext.
2. Run `./launch.sh` in the repository root at least once. The folder `.local_build` should've been generated and GTG should run. Exit GTG.
3. Run `ninja -C .local_build gtg-pot gtg-update-po` to update the translation files.

[readme]: ../../README.md

After that, you can then use the updated translation files and translate the missing strings.

# Testing the changes

Testing the changes is useful since you can then see your translation in action and see potentially mistranslation due to missing context.

[Setup the environment][readme] and then simply run `LC_ALL=<lang>.UTF-8 LANGUAGE=<lang>.UTF-8 ./launch.sh` in the repository root to compile the translations and run GTG with the `<lang>` language.
For example, `LC_ALL=de_DE.UTF-8 LANGUAGE=de_DE.UTF-8 ./launch.sh` would run GTG with the German translation.
You don't need the `LC_ALL=<lang>.UTF-8 LANGUAGE=<lang>.UTF-8` part if you run the system in the destination language anyway.
You can use the `C` language to run without any translations: `LC_ALL=C.UTF-8 LANGUAGE=C.UTF-8 ./launch.sh`

## Testing error handler dialog

There is the error handler dialog which is used when an unhandled exception occurs.
Optimally it would never show up, but if it does, then it asks the user to report the error.
Under normal circumstances you won't be able to make it show up, but for translation testing here is how to make it show up.

Activate the developer console plugin, then open the developer console (under the main menu button) and paste:

```python
import GTG.gtk.errorhandler; GTG.gtk.errorhandler.do_error_dialog(Exception("Exception description"), "This is English only because it is for developers", True)
```

There is a variation when the error isn't recoverable and continuing isn't an option (currently when something happens at startup):

```python
import GTG.gtk.errorhandler; GTG.gtk.errorhandler.do_error_dialog(Exception("Exception description"), "This is English only because it is for developers", False)
```

# Submitting

Done translating and it looks good?
Then consider sending the correct `.po`-file to the project.

## Using git (with a pull/merge request)

Update the repository to get the newest changes:

    git fetch --all

Create a new branch (assumes that origin is the upstream repository, which is the default if you clone the upstream repository):

    git switch -c my-translation-branch origin/master
    # If git switch isn't available, use:
    git branch my-translation-branch origin/master
    git checkout my-translation-branch

Add and commit the translation file:

    git add po/<lang>.po
    git commit -m "Updated translation for <lang>"

Fork the upstream repository if you haven't.
You then need to add the repository to git:

    git remote add fork https://clone-url-of-your-forked-repo

Then push to your forked repo:

    git push fork my-translation-branch

Then finally you can create a pull/merge request via the web interface.

You may want to reset the not modified translation files to prevent git showing you a lot of uncommited files that could interfere when switching branches.
Make sure to this AFTER COMMITING YOUR CHANGES!

    git checkout -- po # drop uncommited translation changes

# Potential errors

* Not removing the `#, fuzzy` line/part, which causes the translation not to apply
* During launching, it might complain about certain files not being found in [`po/POTFILES.in`][POTFILES.IN].
  It is safe to remove the lines from that file and re-run until it works.
  It would be useful to comment about that if you're submitting your translation, just in case.

[POTFILES.IN]: ../../po/POTFILES.in
