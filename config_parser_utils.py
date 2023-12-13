from conf import Conf
from config_tree import ConfigTree, Node
from xml.etree import ElementTree as ET
import configparser
import json
import yaml
import javalang


def is_config_file(project, filepath):
    conf = Conf()
    for suf in conf.config_file_suffix:
        if project == "zookeeper" and ("xdoc" in filepath or "zookeeperAdmin" in filepath):
            return False
        if filepath.endsWith(suf):
            return True
    return False


def clean_namespace(input):
    if input.startswith("{"):
        end_index = input.rfind("}")
        if end_index == -1:
            raise Exception("error: no } found for " + input)
        else:
            return input[end_index + 1:]
    else:
        return input


def build_tree_xml(root):
    root_node = Node(clean_namespace(root.tag))
    if len(root.getchildren()) == 0:
        root_node.value = root.text
    tree = ConfigTree(root_node)
    for child in root.getchildren():
        tree.add_tree(0, build_tree_xml(child))
    return tree


def parse_xml(filepath, filename):
    tree = ET.parse(filepath)
    root = tree.getroot()
    parsed_tree = build_tree_xml(root)
    new_tree = ConfigTree(Node(filename))
    new_tree.add_tree(0, parsed_tree)
    new_tree.traverse_tree_first_order()


def parse_properties(filepath, filename):
    file = open(filepath)
    tree = ConfigTree(Node(filename))
    for line in file:
        line.strip("\n")
        if line.startswith("#"):
            continue
        line = line.split("=")
        if len(line) == 2:
            key = line[0].strip()
            value = line[1].strip()
            key_list = key.split(".")
            new_key_list = [{"name": filename, "value": value}]
            for i in range(len(key_list)):
                if i == len(key_list) - 1:
                    new_key_list.append({"name": key_list[i], "value": value})
                else:
                    new_key_list.append({"name": key_list[i], "value": None})
            tree.add_node_by_path(new_key_list)
    tree.traverse_tree_first_order()


def build_tree_dict(subtree, filename):
    tree = ConfigTree(Node(filename))
    if not isinstance(subtree, dict):
        tree.node_list[0].value = subtree
    else:
        for key in subtree:
            tree.add_tree(0, build_tree_dict(subtree[key], key))
    return tree


def parse_json(filepath, filename):
    file = json.load(open(filepath, "r"))
    if isinstance(file, list):
        if len(file) != 1:
            raise Exception("Error: json list len != 1, " + filepath)
        else:
            subtree = file[0]
    elif isinstance(file, dict):
        subtree = file
    else:
        raise Exception("Error: json can not be parsed as a dict")
    tree = build_tree_dict(subtree, filename)
    tree.traverse_tree_first_order()
    return tree


def parse_yml(filepath, filename):
    f = open(filepath, "r")
    subtree = yaml.load(f.read(), Loader=yaml.FullLoader)
    if not isinstance(subtree, dict):
        raise Exception("Error: yaml can not be parsed as a dict")
    tree = build_tree_dict(subtree, filename)
    tree.traverse_tree_first_order()
    return tree


def parse_java(filepath, filename):
    file = open(filepath, "r").read()
    ast = javalang.parse.parse(file)
    tree = ConfigTree(Node(filename))
    for f in ast.types[0].fields:
        if "javalang.tree.Literal" in str(type(f.declarators[0].initializer)):
            tree.add_tree(0, ConfigTree(Node(f.declarators[0].name, f.declarators[0].initializer.value)))
    tree.traverse_tree_first_order()
    return tree


def parse_configuration_tree(filepath, filename):
    try:
        if filepath.endswith(".xml"):
            parse_xml(filepath, filename)
        if filepath.endswith(".properties"):
            parse_properties(filepath, filename)
        if filepath.endswith(".json"):
            parse_json(filepath, filename)
        if filepath.endswith(".yaml") or filepath.endswith(".yml"):
            parse_yml(filepath, filename)
        if filepath.endswith("Config.java") or filepath.endswith("Configuration.java"):
            parse_java(filepath, filename)
    except Exception as e:
        print("Error parsing", filepath)
        print(e)
        return None
    # if filepath.endswith(".xml"):
    #     parse_xml(filepath, filename)
    # if filepath.endswith(".properties"):
    #     parse_properties(filepath, filename)
    # if filepath.endswith(".json"):
    #     parse_json(filepath, filename)
    # if filepath.endswith(".yaml") or filepath.endswith(".yml"):
    #     parse_yml(filepath, filename)
    # if filepath.endswith("Config.java") or filepath.endswith("Configuration.java"):
    #     parse_java(filepath, filename)

if __name__ == "__main__":
    parse_configuration_tree("./example/pom.xml", "pom.xml")
    parse_configuration_tree("./example/log4j2.properties", "log4j2.properties")
    parse_configuration_tree("./example/interpreter-setting.json", "interpreter-setting.json")
    parse_configuration_tree("./example/manual.yaml", "manual.yaml")
    parse_configuration_tree("./example/Config.java", "Config.java")