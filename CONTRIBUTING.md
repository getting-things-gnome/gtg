# "Can I have a pony? I want it now!"

Due to limited resources (time and people/energy), and because GTG is already a mature and useful application, non-trivial feature requests are unlikely to be implemented unless one of these two conditions are met:

* we're personally excited enough about the feature for our own use *and* can personally allocate time and energy to implement it ourselves (in which case it may be targetted to a particular milestone and "assigned" to the individual actively working on it), or...
* you can provide a patch. See also the "How do I get started?" section further below for links to issues you can work on.

If it's not targetted to a milestone, and it has the "patch-or-wont-happen" label, don't "expect" it to happen in any particular timeframe, unless someone steps forward to contribute the code for that feature.

For a better understanding of why we are taking this approach, you may read be interested in [this blog post](https://fortintam.com/blog/reducing-our-core-apps-software-inventory/). Our ability to focus and to deliver releases without ending up in [development hell](https://en.wikipedia.org/wiki/Development_hell) is strongly tied to being realistic and _not_ promising to do "everything" ourselves. That means we have to make really hard choices about what constitutes the absolute most critical issues we _must_ solve for a release to happen. There can always be more releases.

# Ways you can help

We are always looking for new people to help fix bugs (if any), improve the quality of the code, and refine the UI and performance. Your contributions make all the difference. We can't implement every feature requested by ourselves, or we would never be able to make releases in a timely manner. This is also why we have "low-hanging fruit" issues available for newcomers to tackle. So please contribute patches for the issues you care the most about.

Not a programmer but want to contribute in other ways? There's a lot to do. We also welcome help in these areas:

* Public communications (helping research & write release notes, announcements and status updates, sharing those with journalists or on social media and public forums, etc.)
* Documentation (improving the user manual or contributors' documentation, maintaining the wiki contents)
* Testing and troubleshooting, researching & analyzing potential technical solutions. Take a look at our "bug reporting and triaging" guide in the [docs/contributors/](docs/contributors) subfolder.
* Helping maintain our official Flatpak packages, packaging for various Linux distributions (and keeping those packages up to date!)
* Translating & localizing the app and its user manual
* Convincing your programmer friends to send us patches for your favorite issues ;)

# "Cool! How do I get started?"

1. If you haven't already, read through the [README.md](README.md) file to get your development version of GTG up and running.

2. Determine what issue/task you'd like to work on first. To make it easy for you to **find what to work on**, in our issue tracker, we use two labels in particular to identify areas where you are encouraged to contribute:
  * Issues tagged "[low-hanging-fruit](https://github.com/getting-things-gnome/gtg/labels/low-hanging-fruit)" are issues or tasks that are "easy picks" suitable for new contributors to tackle. They could be documentation and marketing tasks, or coding tasks meant for people who are either beginner programmers or who need some practice to get accustomed to the GTG codebase.
  * Issues tagged "[patch-or-wont-happen](https://github.com/getting-things-gnome/gtg/labels/patch-or-wont-happen)" are features that have been requested and that the core GTG maintainers would like, but lack time/energy, and they are harder than "low-hanging-fruit". These issues require you to step up and contribute a patch or they "will not happen" on their own.
  * If your issue/work item is not already reported, you can file a new one to propose your idea and/or seek help/advice in implementing it.

3. Check out our contributors documentation in the [docs/contributors/](docs/contributors) subfolder. For issues involving code, you will be interested  will need to be relatively comfortable with using Git. See the "Git workflow tips" and "coding guide" in that folder.

4. Tell us about your plans to tackle a particular issue, then roll up your sleeves and dive in!

5. Use Git to commit (save) and push (publish) your changes and send a merge request (or tell us where to find your code/branch somehow) in a ticket in our issue tracker.
