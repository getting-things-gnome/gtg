# Contributing to the User Manual
If you have an interest in contributing to GTG, but do not know how to code, then you may be interested in contributing to the user manual!

# Before You Start
Review the following sections before working on the project.
## Documentation Syntax
Like many other GNOME-based apps, the user manual is written in [Mallard XML syntax](http://projectmallard.org/). Documentation is rendered in Yelp, which is the GNOME help viewer. [This cheat sheet](https://blogs.gnome.org/shaunm/files/2012/01/mallardcheatsheet.png) is really useful when learning the syntax. The best way to learn is to use the existing files in the project.

## Documentation Style
The user manual is written in American English and can be translated to other languages. GNOME has a [documentation style guide](https://developer.gnome.org/gdp-style-guide/2.32/), which you can use to follow basic style conventions when referring to UI elements.

## Use the App!
The best way to get started is to actually use the app. Test new features, become familiar with the UI and the names of each feature (Taskview, Task Editor, etc.), and think about how documentation can help make the user's experience even better. As a potential first-time user, review the documentation while you are using the app. If something seems confusing, or you think that you can improve what is written, then that is a good place to start!

## Submitting PRs
Follow the same pull request (PR) process [that is documented here](https://github.com/getting-things-gnome/gtg/blob/master/docs/contributors/git%20workflow%20tips.md). Remember to use good, concise commit messages so that it is clear what you are updating. If your updates are due to an enhancement or bug that has an existing issue number, ensure that you reference that item in your PR.

# Updating the User Manual for a Release
About a month prior to a release, start reviewing PRs and closed issues to see if the new features affect anything in the user manual. You can review [release milestones](https://github.com/getting-things-gnome/gtg/milestones) to help you view updates in a concise list. Review closed PRs and issues in the milestone for that release. You should look for anything that affects the UI, new plugins or sync services, and new keyboard shortcuts.

## Creating Pages
If you want to create a new page, you can use an existing page as a template. This [Mallard walkthrough](http://projectmallard.org/about/learn/tenminutes.html) breaks down the difference between guide and topic pages so that you can better understand the structure of a Mallard help project.

When starting a page, ensure you declare the appropriate Mallard namespaces:

```
<page xmlns="http://projectmallard.org/1.0/"
      xmlns:its="http://www.w3.org/2005/11/its"
      xmlns:ui="http://projectmallard.org/ui/1.0/"
      type="guide" style="task 2column"
      id="gtg-page-id">
```

The `info` section contains the revision history. Any time that you update a page, ensure that you add a new line for the revision history. This section also contains links that appear on the bottom of the page (`seealso` links) and links that are used for referencing the page in the `index`. See [Referencing the Index](#indexlinks) for details on adding `index` links. Ensure you add a `credit` block to give yourself credit if you are new to the project. All pages need to have an `include` referencing `legal.xml`.
```
<info>
    <revision pkgversion="0.4.0" date="2020-11-12" status="candidate"/>
    <link type="guide" xref="index#gtg-working-task" group="sixth"/>
    <link type="seealso" xref="gtg-quickadd"/>
    <link type="seealso" xref="gtg-search-syntax"/>
    <credit type="author copyright">
         <name>Writer Name</name>
         <email its:translate="no">writer_email</email>
         <years>2020</years>
    </credit>
    <credit type="editor copyright">
         <name>Editor Name</name>
         <email its:translate="no">editor_email</email>
         <years>2020</years>
    </credit>

    <include href="legal.xml" xmlns="http://www.w3.org/2001/XInclude"/>

</info>
```
From here, add a `title`, any number of `section` blocks, and the rest of your content!

<a name="indexlinks"></a>
## Referencing the Index
Ensure that the `index` is updated to include each page. With Mallard syntax, you need to include a link on each internal page that references where it will be in the index. For example, the page called "Understanding View Modes" contains the following link in the `info` section at the top:

```
<link type="guide" xref="index#gtg-task-management" group="third"/>
```

This references the id for the Filtering and Organizing Tasks (`gtg-task-management`) section of the `index` where a link to "Understanding View Modes" will be displayed. On the `index`, the section looks like this:

 ```
 <section id="gtg-task-management" style="2column">
    <title>Filtering and Organizing Tasks</title>
    <links type="topic" style="2column" groups="
       first second
       third fourth"/>
 </section>
 ```
A link to the "Understanding View Modes" page will be listed as the third item.

## Adding Images
.png files should be saved to `gtg/docs/user_manual/C/figures/`. On the page where you are inserting the image, use the `figure` tags and include a figure title. You can also add a description in the `desc` tags.

```
<figure>
  <title>Quick Add Entry</title>
  <desc> </desc>
  <media type="image" mime="image/png" src="figures/quick_tag_entry.png"/>
</figure>
```

# Testing and Publishing
## Testing the Docs and Troubleshooting
Always run through and test the docs! Ensure you are able to open each page. One error that can occur is if you forget to close a tag, Yelp will not open the .page file.

To investigate this issue, use the below command and validate the page (replace `*.page` with the page name). You can also run this command (with `*.page`) within the `/gtg/docs/user_manual/C/` directory to validate all .page files in the user manual project.

```
yelp-check validate *.page
```

This command will output additional information about the error:

```
gtg-translate.page:19: parser error : Opening and ending tag mismatch: app line 19
```

In this example, the opening and ending tags on the `gtg-translate` page do not match on line 19. Ensure that the opening tag on this line has a corresponding ending tag (e.g., `<p>` and `</p>`).

### xmls Issue
You may run into an issue when using a table with `ui:expanded="true"` causing the page to not display.

In this instance, check to see if the page is declaring Mallard UI extension at: `xmlns:ui="http://projectmallard.org/ui/1.0/"`.

Any page that uses this `ui` element should include all of the following schemas:
```
<page xmlns="http://projectmallard.org/1.0/"
      xmlns:ui="http://projectmallard.org/ui/1.0/"
      xmlns:its="http://www.w3.org/2005/11/its"
      type="guide" style="tip"
      id="page-id">
```

## Updating `meson.build`
The [meson.build](https://github.com/getting-things-gnome/gtg/blob/master/docs/user_manual/meson.build) file that resides in the `user_manual` folder needs to contain all of the pages and media (e.g., images and videos) contained in the user manual. Ensure that all .page and .png files are listed in the `sources` or `media` sections accordingly.
## Building HTML Files
Use the following command to build an HTML version for use outside of the packaged help project (e.g., in a blog):
```
yelp-build html *.page
```
When run in the folder with all your .page files, the command will output the HTML files from Mallard.
