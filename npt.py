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

parser_check_portal = subparsers.add_parser("check_new_portal", help="Checks if a portal can be constructed")
parser_check_portal.add_argument('overworld_coords', help='Overworld coordinates in x/y/z')
parser_check_portal.add_argument('nether_coords', help='Nether coordinates in x/y/z or - to use the converted coordinate on the nether roof')
parser_check_portal.add_argument('-t', '--threshold', help='Number of blocks to check around the input', type=int, default=0)

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

def get_connections():
    overworld_portals = list(filter(lambda p: p.is_nether == False, portals))
    nether_portals = list(filter(lambda p: p.is_nether == True, portals))

    connections = {}

    for portal in overworld_portals:
        connection = find_nether_connection(portal)
        connections[portal.label] = connection.label if connection else f"New portal near {get_converted_coordinates(portal)}"
    
    for portal in nether_portals:
        connection = find_nether_connection(portal)
        connections[portal.label] = connection.label if connection else f"New portal near {get_converted_coordinates(portal)}"
    
    return connections

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
        existing_conn = connections[connection.label] if connection.label in connections else None
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

def parse_coords(coords_string):
    [x,y,z] = coords_string.split("/")
    return Position(x=int(x), y=int(y), z=int(z))

def check_new_portal(overworld_pos, nether_pos, silent=False):
    def print_if(str=''):
        if not silent:
            print(str)

    print_if("Checking portals...")
    print_if(f"Overworld: {overworld_pos}")
    print_if(f"Nether: {nether_pos}")
    print_if()

    converted = convert_to_nether(overworld_pos)
    if nether_pos.x > converted.x + 16 or nether_pos.x < converted.x - 16 or nether_pos.z > converted.z + 16 or nether_pos.z < converted.z - 16:
        print_if("VIOLATION: Invalid nether position. Must be within 16 XZ blocks after converting the overworld position.")
        return False
    
    for portal in portals:
        if portal.is_nether == False and portal.position.x == overworld_pos.x and portal.position.y == overworld_pos.y and portal.position.z == overworld_pos.z:
            print_if(f"VIOLATION: Collision with portal {portal.label}")
            return False
        elif portal.is_nether == True and portal.position.x == nether_pos.x and portal.position.y == nether_pos.y and portal.position.z == nether_pos.z:
            print_if(f"VIOLATION: Collision with portal {portal.label}")
            return False

    connections = get_connections()
    overworld_portal = Portal(label="NEW PORTAL (overworld)", position=overworld_pos, is_nether=False)
    nether_portal = Portal(label="NEW PORTAL (nether)", position=nether_pos, is_nether=True)
    portals.append(overworld_portal)
    portals.append(nether_portal)
    new_connections = get_connections()
    portals.pop()
    portals.pop()

    del new_connections["NEW PORTAL (overworld)"]
    del new_connections["NEW PORTAL (nether)"]

    violations = []
    for key in connections.keys():
        if connections[key] != new_connections[key]:
            old = f"{key} -> {connections[key]}"
            new = f"{key} -> {new_connections[key]}"
            violations.append([old, new])
    
    if len(violations) > 0:
        counter = 0
        for violation in violations:
            counter+=1
            print_if(f"VIOLATION #{counter}")
            print_if(f"Old: {violation[0]}")
            print_if(f"New: {violation[1]}")
            print_if()
        return False
    
    print_if("OK")
    return True

if args.command == "show_connections":
    if args.portal:
        portal = get_portal_by_name(args.portal, True)
        print(portal)
        print_connections(portal)
    else:
        print_connections()
elif args.command == "check_new_portal":
    overworld_pos = parse_coords(args.overworld_coords)
    nether_pos = convert_to_nether(overworld_pos) if args.nether_coords == "-" else parse_coords(args.nether_coords)
    if args.nether_coords == "-":
        nether_pos = Position(x=nether_pos.x, y=128, z=nether_pos.z)

    valid_overworld_positions = []
    if check_new_portal(overworld_pos, nether_pos, args.threshold):
        valid_overworld_positions.append(overworld_pos)
    
    if args.threshold:
        for x in range(-args.threshold, args.threshold+1):
            for y in (-args.threshold, args.threshold+1):
                for z in (-args.threshold, args.threshold+1):
                    new_pos = Position(x=overworld_pos.x + x, y=overworld_pos.y + y, z=overworld_pos.z + z)
                    if check_new_portal(new_pos, nether_pos, silent=True):
                        valid_overworld_positions.append(new_pos)

        if len(valid_overworld_positions) > 0:
            for valid_position in valid_overworld_positions:
                print(f"VALID: Overworld {valid_position.x}/{valid_position.y}/{valid_position.z} <-> Nether {nether_pos.x}/{nether_pos.y}/{nether_pos.z}")
        else:
            print("No valid positions found")
