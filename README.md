# Portable Challenges Plugin

Compatable with CTFd v2.2.2

This plugin provides the ability to import and export challneges in a portable, human-readble format (currently YAML, with JSON if there is popular demand). 

### Objectives
* Allow challenges to be saved outside of the database
* Allow for source control on challenges
* Allow for easy human editing of challenges offline
* Enable rapid deployment of challenges to a CTFd instance

### Installation
Simple clone this repsitory into the plugins folder of your CTFd deployment and start the server. This plugin will automatically be loaded.

### Usage
Once the plugin is loaded, it will be available in 'Plugins' menu in Admin Panel. It's also available at '/admin/transfer' enpoint, or through the CLI.

#### Web endpoints
There are two endpoints which are associated with this plugin. 

* **`/admin/yaml`**: This is where the file transfer takes place. It supports two methods.
  * `GET`: Will send, as an attachment, a compressed tarball archive containing all of the currently configured challenges and their files
  * `POST`: Requires a tarball archive, optional compressed with gzip or bz2, to be attached in the 'file' field. This will unpack the archive and add any challeneges which are not already in the database. The archive should contain the challenge spec as 'challenges.yaml' at the root directory of the archive, and no paths should reach into directories above the archive (e.g. ../../etc/passwd would trigger an error) A challenge is not added if it is an exact replica of an existing challenge including name, category, files, keys, etc...

* **`/admin/transfer`**: This is the front-end for the import/export system. It provides a simple inferface by which the endpoint described above can be accessed

### Notes
* The plugin does not remove the existing challenges from the database. It adds new challenges and, in case a duplicate challenge exists, it updates the existing one. Duplicate challenges are found by name. 
* YAML represents the “wanted” status of specified challenges, i.e. fields that are not specified in YAML, are removed from a duplicate challenge.
* The following script can be used to generate a tar.gz archive ready to import (having YAML specification in 'challenges.yaml' and the required files in directory 'files'): 
```
tar -czvf chall.tar.gz challenges.yaml files
```

### YAML Specification
The YAML file is a single document (starting with "---") containing the list of challenges. 

Following is the list of top level keys with their usage.

**name** (required)
* Type: Single line text
* Usage: Specify the title which will appear to the user at the top of the challenge and on the challenge page

**category** (required)
* Type: Single line text
* Usage: Specify the category the challenge will appear a part of

**description** (required)
* Type: Multiline text
* Usage: The the body text of the challenge. If HTML tags are used, they will be rendered.

**tags**
* Type: List of single line text items
* Usage: Specify searchable tags that indicate attributes of this challenge
* Default: Empty list

**type**
* Type: Enum {standard, dynamic}
* Usage: Determines the type of the challenge
* Default: standard

**value** (required)
* Type: Positive integer
* Usage: The amount of point awarded for completion of the problem. _Note:_ For dynamic challenges this field represents the 'initial value'. 'Current value' will be calculated based on the initial value, decay and the number of submissions (same behavior as updating the field from the UI). 

**files**
* Type: List of file paths (single line text)
* Usage: Specify paths to static files which should be included in challenge. On import these files will be uploaded. The filenames will remain the same on upload put the directories in the path will be replaced with a single directory with a random hexadecimal name. The file paths should be relative to the YAML file by default, but this can be changed by using command line arguments with the import tool.
* Default: Empty list

**flags** (required)
* Type: List of flag objects

  **flag**
  * Type: Single line text
  * Usage: The flag/key text
  
  **type**
  * Type: Enum {regex, static}
  * Usage: Specify whether the text should be compared to what the user enters directly, or as a regular expression
  * Default: static

**hidden**
* Type: Boolean {true, false}
* Usage: Set to true if this challenge should not display to the user
* Default: false

**hints**
* Type: List of hint objects

  **content**
  * Type: Single line text
  * Usage: The content of the hint
 
  **cost**
  * Type: Positive integer
  * Usage: The amount of points the hint costs

**prerequisites** 
* Type: List of the names of the prerequisite challenges.
* Usage: Prerequisits can be challenges that either already exist or are being created with current YAML. Non-existing challenge names are skipped.

**minimum** (required for dynamic challenges)
* Type: Positive integer
* Usage: The lowest that the challenge can be worth

**decay** (required for dynamic challenges)
* Type: Positive integer
* Usage: The amount of solves before the challenge reaches its minimum value

**max_attempts** 
* Type: Non-negative integer 
* Usage: Maximum amount of attempts users receive for a dynamic challenge. Leave at 0 for unlimited
* Default: 0 for unlimited

### Example YAML File
A sample valid YAML file can be found [here](https://github.com/sathovsepyan/ctfd-portable-challenges-plugin/blob/master/challenges_sample.yaml). It looks like this: 

```YAML
---
challs:
- category: category1
  description: Description of challenge 1
  flags:
  - flag: flag1
  files:
  - files\4c2af694c9653ae663c3de98681ff0eb\test1.txt
  name: chall1
  type: standard
  value: 100
- category: category2
  decay: 10
  description: Description of challenge 2
  flags:
  - flag: ^[a-zA-Z0-9_]*$
    type: regex
  hidden: true
  tags:
  - tag1
  - tag2
  minimum: 10
  name: dchall2
  type: dynamic
  value: 100
  hints:
  - content: hint content
    cost: 10
  prerequisites:
  - chall1
  
```

#### Command line interface _(only compatible with older CTFd versions)_
The `importer.py` and `exporter.py` scripts can be called directly from the CLI. This is much prefered if the archive you are uploading/downloading is saved on the server because it will not need to use the network.

The help dialog follows:
```
usage: importer.py [-h] [--app-root APP_ROOT] [-d DB_URI] [-F DST_ATTACHMENTS] [-i IN_FILE] [--skip-on-error] [--move]

Import CTFd challenges and their attachments to a DB from a YAML formated
specification file and an associated attachment directory

optional arguments:
  -h, --help           show this help message and exit
  --app-root APP_ROOT  app_root directory for the CTFd Flask app (default: 2 directories up from this script)
  -d DB_URI            URI of the database where the challenges should be stored
  -F DST_ATTACHMENTS   directory where challenge attachment files should be stored
  -i IN_FILE           name of the input YAML file (default: challenges.yaml)
  --skip-on-error      If set, the importer will skip the importing challenges which have errors rather than halt.
  --move               if set the import proccess will move files rather than copy them

```
```
usage: exporter.py [-h] [--app-root APP_ROOT] [-d DB_URI] [-F SRC_ATTACHMENTS] [-o OUT_FILE] [-O DST_ATTACHMENTS] [--tar] [--gz]

Export a DB full of CTFd challenges and theirs attachments into a portable
YAML formated specification file and an associated attachment directory

optional arguments:
  -h, --help           show this help message and exit
  --app-root APP_ROOT  app_root directory for the CTFd Flask app (default: 2 directories up from this script)
  -d DB_URI            URI of the database where the challenges are stored
  -F SRC_ATTACHMENTS   directory where challenge attachment files are stored
  -o OUT_FILE          name of the output YAML file (default: challenges.yaml)
  -O DST_ATTACHMENTS   directory for output challenge attachments (default: [OUT_FILENAME].d)
  --tar                if present, output to tar file
  --gz                 if present, compress the tar file (only used if '--tar'is on)
```
