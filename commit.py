import uuid


def get_method_code(source_code, start_line, end_line):
    try:
        if source_code is not None:
            code = ('\n'.join(source_code.split('\n')[int(start_line) - 1: int(end_line)]))
            return code
        else:
            return None
    except Exception as e:
        print(f'Problem while extracting method code from the changed file contents: {e}')
        pass


def changed_methods_both(file):
    """
    Return the list of methods that were changed.
    :return: list of methods
    """
    new_methods = file.methods
    old_methods = file.methods_before
    added = file.diff_parsed["added"]
    deleted = file.diff_parsed["deleted"]

    methods_changed_new = {
        y
        for x in added
        for y in new_methods
        if y.start_line <= x[0] <= y.end_line
    }
    methods_changed_old = {
        y
        for x in deleted
        for y in old_methods
        if y.start_line <= x[0] <= y.end_line
    }
    return methods_changed_new, methods_changed_old


def get_methods(file, file_change_id):
    """
    returns the list of methods in the file.
    """
    file_methods = []
    if file.changed_methods:
        methods_after, methods_before = changed_methods_both(file)  # in source_code_after/_before
        if methods_before:
            for mb in methods_before:
                # filtering out code not existing, and (anonymous)
                # because lizard API classifies the code part not as a correct function.
                # Since, we did some manual test, (anonymous) function are not function code.
                # They are also not listed in the changed functions.
                if file.source_code_before is not None and mb.name != '(anonymous)':
                    method_before_code = get_method_code(file.source_code_before, mb.start_line, mb.end_line)
                    method_before_row = {
                        'method_change_id': uuid.uuid4().fields[-1],
                        'file_change_id': file_change_id,
                        'name': mb.name,
                        'signature': mb.long_name,
                        'parameters': mb.parameters,
                        'start_line': mb.start_line,
                        'end_line': mb.end_line,
                        'code': method_before_code,
                        'nloc': mb.nloc,
                        'complexity': mb.complexity,
                        'token_count': mb.token_count,
                        'top_nesting_level': mb.top_nesting_level,
                        'before_change': 'True',
                    }
                    file_methods.append(method_before_row)

        if methods_after:
            for mc in methods_after:
                if file.source_code is not None and mc.name != '(anonymous)':
                    # changed_method_code = ('\n'.join(file.source_code.split('\n')[int(mc.start_line) - 1: int(mc.end_line)]))
                    changed_method_code = get_method_code(file.source_code, mc.start_line, mc.end_line)
                    changed_method_row = {
                        'method_change_id': uuid.uuid4().fields[-1],
                        'file_change_id': file_change_id,
                        'name': mc.name,
                        'signature': mc.long_name,
                        'parameters': mc.parameters,
                        'start_line': mc.start_line,
                        'end_line': mc.end_line,
                        'code': changed_method_code,
                        'nloc': mc.nloc,
                        'complexity': mc.complexity,
                        'token_count': mc.token_count,
                        'top_nesting_level': mc.top_nesting_level,
                        'before_change': 'False',
                    }
                    file_methods.append(changed_method_row)
    if file_methods:
        return file_methods
    else:
        return None


def get_files(commit):
    """
    returns the list of files of the commit.
    """
    commit_files = []
    commit_methods = []
    for file in commit.modified_files:
        file_change_id = uuid.uuid4().fields[-1]
        file_row = {
            'file_change_id': file_change_id,  # filename: primary key
            'hash': commit.hash,                    # hash: foreign key
            'filename': file.filename,
            'old_path': file.old_path,
            'new_path': file.new_path,
            'change_type': str(file.change_type).split(".")[-1],        # i.e. added, deleted, modified or renamed
            'diff': file.diff,                      # diff of the file as git presents it (e.g. @@xx.. @@)
            'diff_parsed': file.diff_parsed,        # diff parsed in a dict containing added and deleted lines lines
            'num_lines_added': file.added_lines,        # number of lines added
            'num_lines_deleted': file.deleted_lines,    # number of lines removed
            'code_after': file.source_code,
            'code_before': file.source_code_before,
            'nloc': file.nloc,
            'complexity': file.complexity,
            'token_count': file.token_count,
        }
        commit_files.append(file_row)
        file_methods = get_methods(file, file_change_id)
        if file_methods is not None:
            commit_methods.extend(file_methods)
    return commit_files, commit_methods


def get_commit_row(commit):
    commit_row = {
        'hash': commit.hash,
        'author': commit.author.name,
        'author_date': commit.author_date.timestamp(),
        'author_timezone': commit.author_timezone,
        'committer': commit.committer.name,
        'committer_date': commit.committer_date.timestamp(),
        'committer_timezone': commit.committer_timezone,
        'msg': commit.msg,
        'merge': commit.merge,
        'parents': commit.parents,
        'num_lines_added': commit.insertions,
        'num_lines_deleted': commit.deletions,
        'dmm_unit_complexity': commit.dmm_unit_complexity,
        'dmm_unit_interfacing': commit.dmm_unit_interfacing,
        'dmm_unit_size': commit.dmm_unit_size,
    }
    return commit_row

class Commit:
    def __init__(self, id=None, project=None, files=None, methods=None, rows=None):
        self.project = project
        self.id = id
        self.files = files
        self.methods = methods
        self.rows = rows

    def to_dict(self):
        return self.__dict__

    def load_from_dict(self, d):
        self.project = d["project"]
        self.id = d["id"]
        self.files = d["files"]
        self.methods = d["methods"]
        self.rows = d["rows"]
