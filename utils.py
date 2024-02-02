import hashlib


def get_index_name(project, info):
    return project + '-' + info


def get_hash_sha256(content):
    sha256_hash = hashlib.new('sha256')
    sha256_hash.update(content.encode())
    return sha256_hash.hexdigest()[:10]