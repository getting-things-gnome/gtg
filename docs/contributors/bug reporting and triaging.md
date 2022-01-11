# General principles and rules regarding support

Bug reports and feature requests need to go on [GTG's official/upstream issue tracker](https://github.com/getting-things-gnome/gtg/issues) on GitHub, not anywhere else. Reporting your bugs upstream (here), tested with our Flatpak packages (or with your own checkout from our git repository) is the only way to get them investigated by us.
* Nobody among the GTG maintainers will look at bug reports in downstream (Linux distros) bug trackers. Distro bug trackers are where bug reports go to die.
* Our Flatpak packages (whether the latest stable version, or the nightly dev snapshot), or a manual git checkout, are the only "officially" supported testing/QA/bug reporting platform.
* Bugs reportedly occurring with the git version (with the "reproducible-in-git" tag) have a higher chance of being fixed, as the difference between the current state of the development and the bug are minimal.
* In some rare cases where an issue occurs on your computer but not ours, if you suspect the issue might have something to do with your data file specifically (especially true for performance issues or potential "race conditions"), you might want to share your `gtg_data.xml` file with us so we can try it on our computers. To protect your privacy, you can execute the `scripts/anonymize_task_file.py` file, which will conveniently generate a copy of your data file where every character has been replaced by the letter "m". You can specify a data file as an argument, or it will try to find your data file from the default locations otherwise.

GitHub has a rather simplistic issue tracker with an open-ended, flexible workflow.
Below are some clarifications on how we use it.

# Statuses

* **Open**: the bug (or feature request) has not been solved yet, nor has it been found to be invalid or rejected. Help is always welcome. For a feature request, if after a very long time nobody offered to help, we may close the request.

* **Closed**: the issue has been fixed (and targetted to the next milestone), or found to be invalid (not a bug), out of scope ("wontfix"), or the bug reporter did not provide the requested information ("needinfo") in a timely manner.

# Labels: more precise statuses

First, see the dynamic [list of issue labels](https://github.com/getting-things-gnome/gtg/labels) and their descriptions. They serve to indicate statuses, components, priorities, etc. They are mostly self-explanatory, and that page allows you to easily click and search for related issues.

In particular, "[low-hanging-fruit](https://github.com/getting-things-gnome/gtg/labels/low-hanging-fruit)" and "[patch-or-wont-happen](https://github.com/getting-things-gnome/gtg/labels/patch-or-wont-happen)" are labels that indicate issues that require new contributors to step in, or the issue is unlikely to get fixed. See [CONTRIBUTING.md](https://github.com/getting-things-gnome/gtg/blob/master/CONTRIBUTING.md) for an explanation and tips to get started.

## "Priority" labels

Unlike the statuses, the priorities tags/labels are more up to our appreciation. They are just there to give a rough order of priorities, but are not set in stone.

* **Critical**: GTG arguably cannot be released without solving this issue. This include crashes, tracebacks, *very* odd behaviour, or things that are messing with our ability to be productive in developing GTG, or negatively affecting the new contributors experience. As we are closer to the release, more bugs become criticals.

* **High**: Bug that might be critical for *some* users or that give a bad user experience.

* **Medium**: ideally we want to fix that bug; it might not make it in the next release. We will try.

* **Low**: we'd like to have that.

* **Enhancement**: a feature request (such as an idea for a plugin) and this feature is clearly not critical for GTG (almost none of them are). If it's not assigned to someone, it probably won't happen until someone takes an initiative.

# Milestones: roadmap of future releases

See https://github.com/getting-things-gnome/gtg/milestones

Milestones serve as our dynamic roadmap (and also complement release notes). They can change, and it rarely makes sense to plan more than 1 or 2 releases in advance. Ensure that each newly fixed issue is targeted at the nearest unreleased milestone.

# "Assigned" to

If you assign a bug to yourself, it means that you *definitely* plan to work on that bug in the near future or that you already have a branch.

If you want to work on a bug assigned to somebody else, and they are stuck and would like you to take over, assign the ticket to yourself—or better, just work on the code and get it done faster than we can "assign" the ticket to you. In any case, be sure to sure to contact the person working on it before to avoid duplicate work.

Assigning the bug to someone else is the kind of thing that only maintainers or experienced contributors would do. This would be when you know that person X has some time, willingness, and expertise to fix a particular issue; or when there's a bug in a plugin, it could be assigned to the plugin author.

If a bug is assigned to you, be sure to reply as quickly as possible. If you cannot fix the bug or you don't plan to work on GTG for some time, please communicate it as soon as possible (use the comments of the bug).


------------------------
# Old Launchpad statuses

This list serves mostly for historical purposes, and to explain what we don't/can't do anymore.

* **New**: this is replaced by the "Open" status in GitHub, which does not distinguish between "New", "Confirmed", or "Triaged".
  
  > "the bug has not been accepted or clarified enough. Maybe you just have to wait. If you want that specific bug to be confirmed, you might help by adding a precise way to reproduce the bug or, if it's a feature request, by clarifying the feature (mockups, usecases). If this is a feature request which is not clear, we usually set the Importance to Wishlist and leave the status to New."

* **Confirmed**: the closest approximation is the "reproducible-in-git" status we use to indicate whether the bug has been tested to affect the latest development version. If we can't reproduce the bug, then it would be tagged "needinfo".
  
  > "the bug has been accepted as a bug we want to see fixed. It doesn't mean that we plan to work on it soon. See the importance field for that. It also doesn't mean that we agreed on a solution (even if the original bug describes a particular solution). It only means that we acknowledge that there is a problem that need to be adressed. If you work on one of those bug in your branch, you have no guarantee that it will be accepted."

* **Triaged**: much like "confirmed", this does not make much sense in this day and age. We either leave a bug/feature ticket open, or we close it.
  
  > "the bug has been accepted and a particular solution reached the consensus. This solution should be described in the main summary of the bug. Solving a Triaged bug is just a matter of coding according to the bug description. No further reading nor discussion should be needed. If the proposed solution implies a modification of the core UI (not plugin), it should have been approved by Bertrand, our UI manager."

* **In progress**: this is replaced by "assigning" issues to people. If nobody is assigned, and there is no mention of someone working on it in a branch, assume nobody is working on it.
  
  > "someone is actively working on that bug (see the assigned to field). Also use this status if the bug is fixed in your branch and then do a merge request a link the branch to that bug."

* **Fix Committed**: with GitHub, we just close the tickets and target them to the next release's milestone to indicate things that have been resolved.
  
  > "The bug has been fixed in the trunk (not in your branch). When changing to this status, always add the revision number that fixes that particular bug. You also have to be sure that the bug is targeted for the next release. Indeed, if the fix is in the trunk, it will be in the next release. Don't forget to do that! Also, every Fix Committed bug should be assigned to someone. If multiple people have worked to fix a bug, use the last one that will commit the fix."

* **Fix Released**: unfortunately, GitHub does not have this notion of half-open tickets. Tickets are either open or closed, and when a release comes out then all the issues that were targetted to it can be considered "released".
  
  > "On a given release, all the Fix Committed bugs are switched to that state."
