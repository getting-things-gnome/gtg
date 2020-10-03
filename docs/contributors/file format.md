# XML File Format Specification

This document specifices the XML file format for GTG data (task, tags, etc).


## Location and files

GTG saves all data in one file: `[XDG_DATA]/data/gtg/gtg_data.xml`. If the
file doesn't exist, GTG will try to load the different quick backups and
if that fails too it will create an empty file. The data file is
UTF-8 encoded.

**Backups** are stored in the `backups` folder next to the data file. GTG
creates a backup every time the file is saved, up to 10 versions. These
files are called `gtg_data.xml.bak.0`, `gtg_data.xml.bak.1` and so on. It also makes daily backups, there's no limit to these.


**Versioning** code is stored in the `versioning.py` module. We maintain
support for n-1 versions, with n being the current version of the file
format. File format versions don't necessarily follow GTG versions and they
can be found in the root tag of the data file.


## Full Example

```xml
<gtgData appVersion="0.5" xmlVersion="2">
	<taglist>
		<tag id="7171ff82-119a-4933-8277-a8ef5ce6a3e2" color="E9B96E" name="GTG"/>
		<tag id="140f74ea-b2f1-4b0f-b72b-0e85f471bb98" color="cdd3854e56d8" icon="emblem-shared-symbolic.symbolic" name="life"/>
		<tag id="94669f60-2f8e-4b16-b87f-c1d46ade4536" color="c96a52131cd2" name="errands"/>
		<tag id="46890bc2-c924-4146-8279-472099abc0b1" color="c96a52131cd2" name="other_errands"/>
	</taglist>

	<searchList>
		<savedSearch id="4796b97b-3690-4e74-a056-4153061958df" name="Urgent in tasks" query="urgent">
	</searchList>

	<tasklist>
		<task id="2fdcd50f-0106-48b2-9f16-db2f8dbbf044" status="Active">
			<title>Learn How To Use Subtasks</title>

			<tags>
				<tag>7171ff82-119a-4933-8277-a8ef5ce6a3e2</tag>
				<tag>46890bc2-c924-4146-8279-472099abc0b1</tag>
				<tag>94669f60-2f8e-4b16-b87f-c1d46ade4536</tag>
			</tags>

			<subtasks>
				<sub>a957c32a-6293-46f7-a305-1caccdfbe34c</sub>
			</subtasks>

			<dates>
				<added>2020-04-10T20:48:11</added>
				<modified>2020-04-10T20:37:02</modified>
				<start>2020-05-10T00:00:00</start>
			</dates>

			<recurring enabled="true">
    			<term>Monday</term>
			</recurring>

			<content><![CDATA[ @GTG, @errands, @home_renovation
            This is an example of a task with some content.

			Here's a subtask
			{! a957c32a-6293-46f7-a305-1caccdfbe34c !}
]]>
            </content>

			</task>
			<task id="a957c32a-6293-46f7-a305-1caccdfbe34c" status="Active">
				<title>An empty task</title>
				   <tags />

				   <subtasks />


	   		       <dates>
				       <added>2020-04-10T20:48:11</added>
					   <modified>2020-04-10T20:59:02</modified>
                       <fuzzyDue>someday</fuzzyDue>
			        </dates>

					<recurring enabled="false" />

			        <content />
			</task>
	</tasklist>
</gtgData>

```

## Tags

### `<gtgData>`

The root tag for the file.


| Attribute           | Description                                  |
|---------------------|----------------------------------------------|
| appVersion          | GTG version that generated this file         |
| xmlVersion          | File format version                          |


### `<tagList>`

Contains task tags. Every tag is stored, even if it doesn't have any
custom attributes.

- Only one per file. Always present.


### `<tag>`

A single task tag.

- Contained inside taglist.
- Zero or more per file.


| Attribute           | Description                                  |
|---------------------|----------------------------------------------|
| id                  | Tag UUID. Always present.                    |
| name                | Tag name (without @). Always present.        |
| color               | Custom color (in hex)                        |
| icon                | Custom icon name                             |



### `<searchList>`

List of saved searches.

- Only one per file. Always present.


### `<savedSearch>`

A saved search

- Zero or more per file.


| Attribute           | Description                                  |
|---------------------|----------------------------------------------|
| id                  | Search UUID. Always present.                 |
| name                | Search name (for display) 					 |
| query               | Search query								 |
| icon                | Custom icon name                             |


### `<taskList>`

List of tasks. Contains task tags.

- Only one per file. Always present.


### `<task>`

A single task. Can be also be a subtask.

- Contained inside tasklist.
- Zero or more per file.
- Both attributes are always present.


| Attribute           | Description                                  |
|---------------------|----------------------------------------------|
| id                  | Task UUID. 								     |
| status              | Task status: [Active/Done/Dismissed]		 |


### `<title>`

The task title.

- Only one per task tag. Always present.


### `<tags>`

List of tags applied to the task.

- Only one per task tag. Always present
- List can be empty
- Contains `tag` tags. These contain UUIDs for tags listed in `taglist`


### `<subtasks>`

List of subtasks. These are other tasks parented to this task.

- Only one per task tag. Always present
- List can be empty
- Contains `sub` tags. These contain UUIDs for tasks listed in `tasklist`


### `<dates>`

This tag contains tags for the different dates related to the task.

- Only one per task tag. Always present
- Dates are stored in ISO 8601 format
- Fuzzy dates accept the following values: `Now`, `Soon`, `Someday`


| Tag         | Description                             | Always present  |
|-------------|-----------------------------------------| --------------- |
| added       | When the task was created               | YES             |
| modified    | When the task was last modified         | YES             |
| start       | Specific start date set for the task    | NO              |
| fuzzyStart  | Fuzzy Start date set for the task  	    | NO              |
| due         | Specific Due date set for the task      | NO              |
| fuzzyDue    | Fuzzy Due date set for the task  	    | NO              |


### `<recurring>`

Tasks can be repeatable. This tag defines how whether they repeat and how
often.

- Only one per task tag. Always present
- Includes a `<term>` tag for how often to repeat the task
- The recurring term accepts strings. Values can be `day`, `other-day`, week
days (`Wednesday`, `Monday`, etc), single int values for a day in the month
(24, 12, etc.) or 4 digit ints for a day in a year (eg, 0925 for September
25)
- Includes a boolean `enabled` attribue


### `<content>`

The tasks content. The text is encapsulated in a CDATA container.
The contents are stored in _GTG-flavored_ markdown. At the moment this
includes the following tags:


| Tag                 | Description                                  |
|---------------------|----------------------------------------------|
| `{! [Task UUID] !}` | Link to a subtask identified by [Task UUID]  |
| `@Tag-name`         | A GTG tag applied to the task                |
| `#Subheading`       | A subheading								 |


- Only one per task tag. Always present.
- Can be empty


## Mapping of Gtk Text Tags to/from content

Task contents are serialized into several parts of the XML, depending on
whether they add subtasks or tags. See the modules `text_tags.py` and
`taskview.py` for more information.


| Gtk Text Tag        | In XML                                       	  |
|---------------------|---------------------------------------------------|
| `SubtaskTag`        | A `sub` tag and a `{! subtask !}` tag in content  |
| `TaskTagTag`        | A `tag` in the task `tags`, and in `taglist`      |
| `TitleTag`          | The `title` tag inside `task` 					  |


