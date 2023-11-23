from commit import Commit
from conf import Conf


class Issue:
    def __init__(self, key=None, id=None, summary=None, description=None, priority=None, create_time=None, update_time=None, fix_commits=None,
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

    def to_dict(self):
        d = self.__dict__
        d["fix_commits"] = [c.to_dict() for c in self.fix_commits]
        d["buggy_commits"] = [c.to_dict() for c in self.buggy_commits]
        return d

    def load_from_dict(self, d):
        self.key = d["key"]
        self.id = d["id"]
        self.summary = d["summary"]
        self.description = d["description"]
        self.priority = d["priority"]
        self.create_time = d["create_time"]
        self.update_time = d["update_time"]
        self.fix_commits = []
        self.buggy_commits = []
        for commit_info in d["fix_commits"]:
            commit = Commit()
            commit.load_from_dict(commit_info)
            self.fix_commits.append(commit)
        for commit_info in d["buggy_commits"]:
            commit = Commit()
            commit.load_from_dict(commit_info)
            self.buggy_commits.append(commit)
