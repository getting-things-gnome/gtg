# Things to check and do before a release

1. Update the translation template file (`ninja -C .local_build/ gtg-pot` or, if you really have a reason to do so, `ninja -C .local_build/ gtg-update-po`) and notify the GNOME translation teams well in advance to request updated translations if needed, potentially by making a RC ("release candidate"), as we rarely need to make alphas/betas.
1. Check that code tests pass (run the `make check` command). See also the test suite [coverage testing](test suite - coverage testing.md)
2. AUTHORS and GTG/info.py files are up to date. To get the list of top contributors to a release, use `git shortlog -s -n previous_tag...new_tag_or_HEAD` (for example `git shortlog -s -n v0.3.1..HEAD`)
3. Retest all again
4. Update the NEWS file, and ideally prepare release notes and announcements in advance
5. Test creating tarballs (see further below)
6. Update the version number in `meson.build` (in the main directory), and the `appVersion` value in `GTG/core/versioning.py` and `GTG/core/xml.py` (the xmlVersion doesn't necessarily change, but appVersion should)
7. Update `data/org.gnome.GTG.appdata.xml.in.in` to add the new release version number, date, and planned announcement (release notes) URL. For a beta/RC release, use a separate announcement URL, version number and type (ex: `version=0.4_RC" date="2020-06-11" type=development"`). When making the final stable release, replace that release by the final version number, date and URL. Note that you cannot use dates in the future, as Flathub will not be able to handle that.
8. Tag the stable release (see below) and create the tarballs and Flatpak packages. Tagging RCs/betas is not needed.
9. Remember to update the historical wiki page at https://wiki.gnome.org/Apps/GTG/release_names

Tip: You can prepare the release commit in advance by setting both the authorship and commit date to the future planned release date and time, and keeping the commit sitting in your personal fork's branch, with a command such as: `GIT_AUTHOR_DATE='the date and time' GIT_COMMITTER_DATE='the date and time' git commit` (note that if you rebase the branch, you should also reuse that `GIT_COMMITTER_DATE` environment variable, otherwise your resulting rebased commit will have the rebase time set as the new commit date).

Git accepts various dates formats (including ISO 8601), see its [documentation on date formats](https://github.com/git/git/blob/master/Documentation/date-formats.txt).


# Release tagging (usually done by maintainers)

Tag the revision (use `git tag -a`) with `vRELEASE_NUMBER` (ex: `git tag -a v0.3.1`, `git tag -a v0.4`, etc.) when on the correct commit. `git tag` lists all the tags. As a tag description (when git prompts you for it) you can use something like `Release version 0.4` if the commit's description was `Release GTG 0.4`, for example.

In addition to `git log` to see the tag within the history, you can also use `git show the_tag_name` to see the tag's metadata/details.

When you are absolutely sure you tagged "correctly", you can use `git push --tags`.

In GitHub and GitLab, a commit named "Release version 0.4" and tagged "v0.4", for example, will correctly show up in the "Releases" section of the repository's web interface.

However, even though such a tag automatically shows up in the "releases" section, you may need to also explicitly tell GitHub to ["create" a release](https://github.com/getting-things-gnome/gtg/releases/new) out of that existing tag in order to be able to give it a nickname (such as `0.4: "You Are (Not) Done"`) and for it to be identified as the "Latest release" in the web interface.

# Creating tarballs (intended for distros)

This is now done simply like this (assuming you ran launch.sh at least once previously):

    ninja -C .local_build/ dist

...which will create the .local_build/meson-dist/gtg-VERSIONNUMBER.tar.xz tarball.
Then we need to upload the tarball to... wherever we're supposed to upload tarballs (someone should fix these instructions).

# Flatpak package (intended for users)

Someone knowledgeable please write instructions here or as a standalone file to be linked to.
