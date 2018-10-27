import logging
import github
import os

log = logging.getLogger(__name__)

object_types = {
        'directory' : '040000', # aka directory
        'file' : '100644',
        'executable' : '100755',
        # XXX: we do not support submodules or symlinks
        # https://developer.github.com/v3/git/trees/#create-a-tree
}

# A helper class for our DFS traversal of the tree data structure
class TreeObj:
    def __init__(self, path, tree):
        self.path = path
        self.tree = tree
        self.visited = False

# a helper class for storing git blobs
class GitBlob:
    def __init__(self, path, ty, content):
        self.path = path
        self.ty = ty
        self.content = content

"""
    File data structure
    {
        "blobs" : ['file1', 'file2'],
        "trees" : {
            "attachments" : {
                "blobs" : ['file3'],
                "trees" : {
                 ...
                }
            },
            "src" : {
                "blobs" : ['pwn.c'],
                "trees" : {}
            },
        }
    }

WARNING: This will assume a blank working tree, meaning all existing files
will be deleted.
"""
def create_git_tree(repo, directory):
    object_tree = { "blobs" : [], "trees" : {} }

    # counters
    file_bytes = 0
    file_count = 0
    directory_count = 0

    log.info("Building file system tree for '%s'", directory)

    # Walk the filesystem and build a tree structure
    for root, dirs, files in os.walk(directory):
        file_objects = []
        components = root.split(os.sep)

        # skip leading and any blank components
        components = components[1:len(components)]
        components = filter(lambda x: x != "", components)

        # each call is for one directory
        directory_count += 1

        # top-level directory
        if len(components) == 0:
            level = object_tree
        else:
            base = object_tree

            # drill down in the tree to the level we're at
            for component in components:
                if component not in base["trees"]:
                    base["trees"][component] = { "blobs" : [], "trees" : {} }

                base = base["trees"][component]

            level = base

        # for each file at the current level
        for f in files:
            path = os.path.join(root, f)
            ty = object_types['executable'] if os.access(path, os.X_OK) else object_types['file']

            # read in all of the file contents (this could be deferred for streaming)
            contents = ""
            try:
                with open(path, 'rb') as fp:
                    contents = fp.read()
                    file_bytes += len(contents)
                    file_count += 1
            except IOError:
                log.error("Unable to open file '%s' for reading", path)
                return None

            # create a tree element for this
            level["blobs"] += [GitBlob(f, ty, content=contents)]

    log.info('Walked %d directories and %d files (total bytes %d)',
            directory_count, file_count, file_bytes)
    log.info('Creating git trees...')

    # rewalk the data structure and build the tree nodes
    # do this using DFS to build the bottom most trees first
    stack = [TreeObj("", object_tree)]

    while len(stack):
        node = stack.pop()

        # if we haven't visited the node and it has child directories
        if not node.visited and len(node.tree["trees"]):
            node.visited = True

            # we're at a leaf directory node
            stack.append(node)
            for name, tree in node.tree["trees"].iteritems():
                stack.append(TreeObj(name, tree))
        # otherwise, process the directory node
        else:
            # map all directories to git tree elements
            elements = map(lambda x: github.InputGitTreeElement(x[0],
                object_types["directory"], 'tree', sha=x[1]["obj"].sha), node.tree["trees"].items())

            # upload our blobs :)
            for blob in node.tree["blobs"]:
                import base64
                try:
                    git_blob = repo.create_git_blob(base64.encodestring(blob.content).strip(), 'base64')
                    elements += [github.InputGitTreeElement(blob.path, blob.ty, 'blob', sha=git_blob.sha)]
                except github.GithubExeception as e:
                    log.error("Failed to upload git blob for file '%s'", blob.path)
                    log.error("Reason: %s", e)
                    # XXX: can we roll back trees/blobs created before the failure?
                    return None

            # git trees CANNOT be empty
            if len(elements) == 0:
                elements += [github.InputGitTreeElement(".keep", object_types["file"], 'blob', content="")]

            # talk to the API and create the damn tree
            try:
                new_tree = repo.create_git_tree(elements)
            except github.GithubException as e:
                log.error("Failed to create a git tree object for node '%s'", node.path)
                log.error("Reason: %s", e)
                # XXX: can we roll back trees created before the failure?
                return None

            node.tree["obj"] = new_tree

    return object_tree["obj"]
