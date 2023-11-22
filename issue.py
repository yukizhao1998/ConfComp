from commit import Commit
from conf import Conf


class Issue:
    def __init__(self, key, id, summary, description, priority, create_time, update_time, fix_commits=None,
                 buggy_commits=None):
        self.key = key
        self.id = id
        self.summary = summary
        self.description = description
        self.priority = priority
        self.create_time = create_time
        self.update_time = update_time
        self.fix_commits = fix_commits
        self.buggy_commits = buggy_commits

    def set_fix_commits(self, fix_commits):
        self.fix_commits = fix_commits

    def set_buggy_commits(self, buggy_commits):
        self.buggy_commits = buggy_commits

    def conf_related(self):
        return False