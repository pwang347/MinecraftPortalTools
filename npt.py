from collections import namedtuple
import math
import argparse
import json

# Type definitions
Portal = namedtuple("Portal", ["label", "position", "is_nether"])
Position = namedtuple("Position", ["x", "y", "z"])

# Parse CLI arguments
parser = argparse.ArgumentParser(
    prog='python npt.py',
    description='Show all portal connections and test new portals.',
)
subparsers = parser.add_subparsers(help='The command to execute.', dest='command', required=True)
parser_show_connections = subparsers.add_parser('show_connections', help='Show all portal connections')
parser_show_connections.add_argument('-p', '--portal', help="Show only information for a specific portal")

parser.add_argument('-d', '--data', default='./data/mcandy_portals.json', help="The JSON data to load.")
args = parser.parse_args()

# Load the portal data
portals = []
with open(args.data, "r") as file:
    data = json.loads(file.read())
    
    if "overworld_portals" not in data or "nether_portals" not in data:
        raise Exception("Invalid data format: expected to have a top-level JSON object with keys 'overworld_portals' and 'nether_portals'")
    
    overworld_portals = data["overworld_portals"]
    nether_portals = data["nether_portals"]

    def validate_portal_json(portal):
        if "label" not in portal:
            raise Exception(f"Missing label for portal: {portal}")
        if "position" not in portal:
            raise Exception(f"Missing position for portal: {portal}")
        position = portal["position"]
        if "x" not in position or not isinstance(position["x"], int):
            raise Exception(f"Position must have property 'x' that is an integer for portal: {portal}")
        if "y" not in position or not isinstance(position["y"], int):
            raise Exception(f"Position must have property 'y' that is an integer for portal: {portal}")
        if "z" not in position or not isinstance(position["z"], int):
            raise Exception(f"Position must have property 'z' that is an integer for portal: {portal}")

    for portal in overworld_portals:
        validate_portal_json(portal)
        portals.append(Portal(label=portal["label"], position=Position(x=portal["position"]["x"], y=portal["position"]["y"], z=portal["position"]["z"]), is_nether=False))
    for portal in nether_portals:
        validate_portal_json(portal)
        portals.append(Portal(label=portal["label"], position=Position(x=portal["position"]["x"], y=portal["position"]["y"], z=portal["position"]["z"]), is_nether=True))

def get_converted_coordinates(portal):
    if portal.is_nether:
        return convert_to_overworld(portal.position)
    else:
        return convert_to_nether(portal.position)

def convert_to_nether(pos):
    return Position(x=math.floor(pos.x / 8), y=pos.y, z=math.floor(pos.z / 8))

def convert_to_overworld(pos):
    return Position(x=math.floor(pos.x * 8), y=pos.y, z=math.floor(pos.z * 8))

def valid_portal_destination(portal, pos):
    threshold = 128 if portal.is_nether else 16
    converted_pos = get_converted_coordinates(portal)

    return abs(converted_pos.x - pos.x) <= threshold and abs(converted_pos.z - pos.z) <= threshold

def euclidean_dist(pos1, pos2):
    return math.sqrt(math.pow(pos2.x - pos1.x, 2) + math.pow(pos2.y - pos1.y, 2) + math.pow(pos2.z - pos1.z, 2))

def find_valid_portal_connections(portal):
    valid = []
    for p in portals:
        if p == portal:
            continue
        if portal.is_nether == p.is_nether:
            continue
        if valid_portal_destination(portal, p.position):
            valid.append(p)
    return valid

def find_nether_connection(portal):
    valid = find_valid_portal_connections(portal)
    if len(valid) == 0:
        return None
    
    converted_pos = get_converted_coordinates(portal)
    first = valid.pop(0)
    destination = first
    min_dist = euclidean_dist(converted_pos, first.position)
    for p in valid:
        dist = euclidean_dist(converted_pos, p.position)
        if dist < min_dist:
            min_dist = dist
            destination = p
    
    return destination

def get_portal_by_name(name, error=False):
    for p in portals:
        if p.label == name:
            return p
    if error:
        raise Exception(f"{name} is not a known portal.")
    return None

def print_connections(target=None):
    overworld_portals = list(filter(lambda p: p.is_nether == False, portals))
    nether_portals = list(filter(lambda p: p.is_nether == True, portals))

    connections = {}
    bidirectional = []

    for portal in overworld_portals:
        connection = find_nether_connection(portal)
        connections[portal.label] = connection.label if connection else f"New portal near {get_converted_coordinates(portal)}"
    
    for portal in nether_portals:
        connection = find_nether_connection(portal)
        existing_conn = connections[connection.label]
        if existing_conn == portal.label:
            del connections[connection.label]
            bidirectional.append([connection.label, portal.label])
        else:
            connections[portal.label] = connection.label if connection else f"New portal near {get_converted_coordinates(portal)}"
    
    if target:
        to_remove = []
        for key in connections.keys():
            if key != target.label and connections[key] != target.label:
                to_remove.append(key)
        for key in to_remove:
            del connections[key]

        bidirectional = list(filter(lambda p: p[0] == target.label or p[1] == target.label, bidirectional))

    print("-----------------------")
    print("Bi-directional portals:")
    print("-----------------------")
    for left, right in bidirectional:
        print(left + " <-> " + right)
    print("\n")

    print("-----------------------")
    print("Overworld portals:")
    print("-----------------------")
    for portal in overworld_portals:
        if portal.label not in connections:
            continue
        print(portal.label + " -> " + connections[portal.label])
    print("\n")

    print("-----------------------")
    print("Nether portals:")
    print("-----------------------")
    for portal in nether_portals:
        if portal.label not in connections:
            continue
        print(portal.label + " -> " + connections[portal.label])
    print("\n")

if args.command == "show_connections":
    if args.portal:
        portal = get_portal_by_name(args.portal, True)
        print(portal)
        print_connections(portal)
    else:
        print_connections()
