# Occasional contributors, developers, and maintainers

There are three levels of insanity: contributors (anyone), developers (addicts!) and maintainers (mysterious ancient beings).

You don't need to be a "developer" or "maintainer" to contribute to the project.

* With decentralized version control systems like Git, you don't need direct commit access to the main master branch to land your patches; you tell us about your plans/ideas and then work on them on your own branch, then simply ask for your branch to be reviewed when it's ready; if it indeed improves things and respects the standards mentioned in our coding style document, then it can get merged fairly quickly.

* If you end up doing this so often and with such high quality contributions that we can't be bothered to review your changes anymore, then we'll be happy to give you developer "direct commit" access.

* Maintainers are pretty much the same thing as regular developers, just that they have administrative rights over the project's infrastructure (boring stuff, really). Pretty much nobody needs to be a maintainer/administrator, except those who intend to stick around for years and have a gluttony for pain.

So if you simply want to contribute to the project, get started with [CONTRIBUTING.md](https://github.com/getting-things-gnome/gtg/blob/master/CONTRIBUTING.md) and read the contents of the docs/contributors/ folder.

# Abilities of GTG developers (a.k.a. frequent contributors)

GTG developers are frequent contributors who have requested more hands-on project management powers and responsibilities, such as:

 * "direct commit" access to the main "master" branch (and any other branch) of GTG;
 * full admin powers on the bugs database (assigning, targeting, changing statuses, etc.);
 * ability to make releases;
 * ability to review and approve/reject merge requests from contributors and developers;
 * getting an email notification for everything that is going on in the project's issue tracker (say goodbye to your Inbox Zero, fool!);
 * achieving fame, glory, and seeing tons of people wanting to name their firstborn child in your honor.

## Becoming a regular developer

You are contributing more and more to GTG and you think that having those superpowers would improve your ability to help the project move faster? Then find one of the GTG maintainers and ask them.

Of course, we have to know you and trust you for your contributions. If you contribute code, we should have confidence that you are now a GTG master and that you've fully understood our coding rules. It usually means that your latest patches were all merged without any need to resubmit them.

Also, it has to make sense for you.

* Some GTG heavy contributors decide to not claim the title/roles of GTG "developers" because they don't feel the need for it and they are happy to work on their own branch and undergo a systematic peer-review process.

* Being an established regular developer also means that bugs can be assigned to you because the others are too lazy… er… "feel that you are the best for this task", watch out ;-)

* If you are a plugin developer, it can be convenient for you to have access to the trunk so you can maintain your plugins if you are doing that frequently, but if you want to commit to a previously unknown part of code, we would ask that you submit a patch / undergo peer-review through a merge request.

The fact that you have all the abilities listed above doesn't mean that you _should_ use them. When in doubt, ask! Developer privileges simply means that we trust your judgement, meaning that you know "What you can do without risk" vs "What you should ask advice for".

As a rule of thumb, changes to the UI behaviour or to the internal API should be agreed on in an issue ticket.

When closing a bug as fixed, you have to assign that bug to the next release. When this release comes out, we then know what was fixed in a particular release. If an unexpected intermediate release happens, we simply rename the milestone and add new ones (or we can retarget issues).

# Responsibilities of a GTG maintainer

A maintainer is the same thing as a developer, but they have a few more responsibilities, so they generally look like this:

![](https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Eero_J%C3%A4rnefelt_-_Under_the_Yoke_%28Burning_the_Brushwood%29_-_Google_Art_Project.jpg/605px-Eero_J%C3%A4rnefelt_-_Under_the_Yoke_%28Burning_the_Brushwood%29_-_Google_Art_Project.jpg)

While maintainers can be active developers, fundamentally the goal of maintainers is to provide support to developers and make it easier for contributors to join the project and be productive. Essentially, maintainers provide tools and knowledge (sometimes historical). This means they might be coding less, and spending more time answering questions and dealing with things like:

* Administering the GitHub projects/subprojects
    * Enabled/disabled modules
    * Team members & permissions
    * Integration with external infrastructure
    * Defining/planning project release milestones
    * Defining the issue tracker's labels/tags
* Maintaining the website/wiki, whether infrastructure or contents
* The [OpenHub statistics page](https://www.openhub.net/p/gtg)
* Marketing, and helping with the project's overall direction
* Defining standard operating procedures and processes (ex: the release checklist, the packaging & support policy)
* Boring tasks that nobody else wants to do but would help the contributor experience, like writing this documentation page (and many others).

If you are a long-time developer and would like to help share the administrative load, you can talk with other maintainers about it. You will still earn 0$, but you will be able to call yourself an "[Elder of the Internet](https://www.youtube.com/watch?v=iDbyYGrswtg)".
