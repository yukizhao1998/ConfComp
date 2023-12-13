class Node:
    def __init__(self, name=None, value=None, parent=None, pleftchild=None, brother=None):
        self.name = name
        self.value = value
        # self.type = type  # path, file, tag, key
        self.parent = parent
        self.pleftchild = pleftchild
        self.brother = brother
        self.valid = True

    def add_bias(self, bias):
        if self.parent:
            self.parent += bias
        if self.pleftchild:
            self.pleftchild += bias
        if self.brother:
            self.brother += bias


class ConfigTree:
    def __init__(self, node):
        self.node_list = []
        self.node_list.append(node)

    def add_node_by_path(self, path_list):
        curr_node = 0
        curr_path = 0
        if path_list[curr_path]["name"] != self.node_list[curr_node].name:
            print("Error while adding node by path:", path_list)
        curr_path += 1
        while curr_path < len(path_list):
            flag = False
            if self.node_list[curr_node].pleftchild:
                tmp_node = self.node_list[curr_node].pleftchild
                while tmp_node:
                    if self.node_list[tmp_node].name == path_list[curr_path]["name"] and \
                            self.node_list[tmp_node].value == path_list[curr_path]["value"]:
                        curr_node = tmp_node
                        flag = True
                        break
                    else:
                        tmp_node = self.node_list[tmp_node].brother
            if not flag:
                new_node = Node(name=path_list[curr_path]["name"], value=path_list[curr_path]["value"])
                self.node_list.append(new_node)
                self.add_child_edge(curr_node, len(self.node_list) - 1)
                curr_node = len(self.node_list) - 1
            curr_path += 1

    def search_node(self, path_list):
        curr_node = 0
        curr_path = 0
        while curr_path < len(path_list):
            flag = False
            if self.node_list[curr_node].pleftchild:
                tmp_node = self.node_list[curr_node].pleftchild
                while tmp_node:
                    if self.node_list[tmp_node].name == path_list[curr_path]["name"]:
                        flag = True
                        curr_node = tmp_node
                        break
            if not flag:
                return False
            else:
                curr_path += 1
        if curr_path == len(path_list):
            return curr_node

    def delete_node_by_path(self, path_list):
        node = self.search_node(path_list)
        if not node:
            return False
        else:
            parent = self.node_list[node].parent
            if self.node_list[parent].pleftchild == node:
                self.node_list[parent].pleftchild = self.node_list[node].brother
            else:
                tmp_node = self.node_list[parent].pleftchild
                while tmp_node:
                    if self.node_list[tmp_node].brother == node:
                        self.node_list[tmp_node].brother = self.node_list[node].brother
                        return True
                    else:
                        tmp_node = self.node_list[tmp_node].brother
                print("Fail to delete ", path_list)

    def add_child_edge(self, parent, child):
        self.node_list[child].parent = parent
        if self.node_list[parent].pleftchild:
            cur = self.node_list[parent].pleftchild
            while True:
                if self.node_list[cur].brother:
                    cur = self.node_list[cur].brother
                else:
                    self.node_list[cur].brother = child
                    break
        else:
            self.node_list[parent].pleftchild = child

    def add_tree(self, parent, sub_tree):
        sub_tree_root_id = len(self.node_list)
        self.node_list.extend(sub_tree.node_list)
        for id in range(sub_tree_root_id, len(self.node_list)):
            self.node_list[id].add_bias(sub_tree_root_id)
        self.add_child_edge(parent, sub_tree_root_id)

    def traverse_tree_first_order(self, root=0):
        print(self.node_list[root].name, self.node_list[root].value)
        if self.node_list[root].pleftchild:
            cur = self.node_list[root].pleftchild
            while cur:
                self.traverse_tree_first_order(cur)
                cur = self.node_list[cur].brother
