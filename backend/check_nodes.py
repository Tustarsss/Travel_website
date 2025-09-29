import json
import codecs

# Read the graph_nodes.json file with proper encoding
with codecs.open('data/generated/graph_nodes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check nodes in region 1
nodes_region_1 = [n for n in data if n['region_id'] == 1]
print(f'Number of nodes in region 1: {len(nodes_region_1)}')
print('Sample nodes from region 1:', nodes_region_1[:10])

# Check if node IDs 3 and 5 exist
node_ids = [n['id'] for n in nodes_region_1]
print(f'Node IDs in region 1: {sorted(node_ids)[:20]}...')  # Show first 20
print(f'Does node ID 3 exist? {3 in node_ids}')
print(f'Does node ID 5 exist? {5 in node_ids}')

# Also check the edges
with codecs.open('data/generated/graph_edges.json', 'r', encoding='utf-8') as f:
    edges_data = json.load(f)
    
edges_region_1 = [e for e in edges_data if e['region_id'] == 1]
print(f'Number of edges in region 1: {len(edges_region_1)}')
print('Sample edges from region 1:', edges_region_1[:5])