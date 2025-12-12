import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import json
import numpy as np
from io import BytesIO
import plotly.graph_objects as go
import plotly.express as px
from matplotlib.patches import FancyArrowPatch
import matplotlib.patches as patches

class GraphUtils:
    def __init__(self):
        self.color_palette = {
            'vertex': '#4a86e8',
            'vertex_highlight': '#ff9900',
            'edge': '#333333',
            'edge_highlight': '#ff3300',
            'mst_edge': '#6aa84f',
            'path': '#e06666',
            'visited': '#93c47d',
            'bipartite_a': '#ff9999',
            'bipartite_b': '#99ccff',
            'flow_edge': '#ff9900'
        }
    
    def save_graph_to_file(self, graph, filename):
        """Lưu đồ thị ra file JSON"""
        try:
            data = nx.node_link_data(graph)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True, f"Đã lưu đồ thị vào {filename}"
        except Exception as e:
            return False, f"Lỗi khi lưu file: {str(e)}"
    
    def load_graph_from_file(self, filename):
        """Đọc đồ thị từ file JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return nx.node_link_graph(data), "Đã tải đồ thị thành công"
        except Exception as e:
            return None, f"Lỗi khi đọc file: {str(e)}"
    
    def create_adjacency_matrix(self, G):
        """Tạo ma trận kề"""
        nodes = list(G.nodes())
        n = len(nodes)
        matrix = [[0] * n for _ in range(n)]
        node_to_idx = {node: i for i, node in enumerate(nodes)}
        
        for u, v, data in G.edges(data=True):
            weight = data.get('weight', 1)
            i, j = node_to_idx[u], node_to_idx[v]
            matrix[i][j] = weight
            if not G.is_directed():
                matrix[j][i] = weight
        
        return matrix, nodes
    
    def draw_graph(self, G, pos=None, title="Đồ thị", highlight_path=None, 
                   highlight_nodes=None, node_size=500, figsize=(10, 8), 
                   edge_labels=True, show_weights=True, directed=None):
        """Vẽ đồ thị với matplotlib"""
        fig, ax = plt.subplots(figsize=figsize)
        
        if pos is None:
            pos = nx.spring_layout(G, seed=42)
        
        # Xác định loại đồ thị
        if directed is None:
            is_directed = nx.is_directed(G)
        else:
            is_directed = directed
        
        # Chuẩn bị màu sắc cho nodes
        node_colors = []
        for node in G.nodes():
            if highlight_nodes and node in highlight_nodes:
                node_colors.append(self.color_palette['vertex_highlight'])
            else:
                node_colors.append(self.color_palette['vertex'])
        
        # Vẽ các node
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                              node_size=node_size, ax=ax, alpha=0.9)
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold', ax=ax)
        
        # Chuẩn bị màu sắc và độ dày cho edges
        edge_colors = []
        edge_widths = []
        edge_styles = []
        
        for u, v in G.edges():
            if highlight_path and ((u, v) in highlight_path or (v, u) in highlight_path):
                edge_colors.append(self.color_palette['edge_highlight'])
                edge_widths.append(3)
                edge_styles.append('solid')
            else:
                edge_colors.append(self.color_palette['edge'])
                edge_widths.append(1)
                edge_styles.append('solid')
        
        # Vẽ các edge
        if is_directed:
            nx.draw_networkx_edges(G, pos, edge_color=edge_colors, 
                                  width=edge_widths, ax=ax, alpha=0.7,
                                  arrows=True, arrowsize=20, 
                                  connectionstyle='arc3,rad=0.1')
        else:
            nx.draw_networkx_edges(G, pos, edge_color=edge_colors, 
                                  width=edge_widths, ax=ax, alpha=0.7)
        
        # Vẽ trọng số nếu có
        if show_weights and edge_labels and nx.is_weighted(G):
            edge_labels_dict = nx.get_edge_attributes(G, 'weight')
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels_dict, 
                                        font_size=9, ax=ax, label_pos=0.5)
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        ax.margins(0.1)
        plt.tight_layout()
        return fig
    
    def draw_animated_bfs_dfs(self, G, traversal_sequence, title="Duyệt đồ thị"):
        """Vẽ animation BFS/DFS"""
        fig, ax = plt.subplots(figsize=(10, 8))
        pos = nx.spring_layout(G, seed=42)
        
        # Vẽ đồ thị ban đầu
        nx.draw(G, pos, with_labels=True, node_color='lightblue', 
               node_size=500, ax=ax, font_weight='bold')
        
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.axis('off')
        
        return fig
    
    def create_adjacency_list(self, G):
        """Tạo danh sách kề"""
        adj_list = {}
        for node in G.nodes():
            neighbors = []
            for neighbor, data in G[node].items():
                weight = data.get('weight', 1)
                neighbors.append((neighbor, weight))
            adj_list[node] = neighbors
        return adj_list
    
    def create_edge_list(self, G):
        """Tạo danh sách cạnh"""
        edges = []
        for u, v, data in G.edges(data=True):
            weight = data.get('weight', 1)
            edges.append((u, v, weight))
        return edges
    
    def get_graph_statistics(self, G):
        """Lấy thống kê về đồ thị"""
        stats = {
            'num_nodes': G.number_of_nodes(),
            'num_edges': G.number_of_edges(),
            'is_directed': nx.is_directed(G),
            'is_weighted': nx.is_weighted(G),
            'density': nx.density(G),
            'is_connected': nx.is_connected(G) if not nx.is_directed(G) else nx.is_strongly_connected(G)
        }
        
        # Tính bậc trung bình
        if stats['num_nodes'] > 0:
            degrees = [deg for _, deg in G.degree()]
            stats['avg_degree'] = sum(degrees) / len(degrees)
            stats['max_degree'] = max(degrees)
            stats['min_degree'] = min(degrees)
        
        # Thêm thông tin khác nếu có thể tính
        try:
            if stats['is_connected'] and not stats['is_directed']:
                stats['diameter'] = nx.diameter(G)
                stats['avg_path_length'] = nx.average_shortest_path_length(G)
        except:
            pass
        
        return stats
    
    def export_to_csv(self, G, format_type='adjacency'):
        """Xuất đồ thị ra CSV"""
        if format_type == 'adjacency':
            matrix, nodes = self.create_adjacency_matrix(G)
            df = pd.DataFrame(matrix, index=nodes, columns=nodes)
        elif format_type == 'edges':
            edges = self.create_edge_list(G)
            df = pd.DataFrame(edges, columns=['Node1', 'Node2', 'Weight'])
        elif format_type == 'adjacency_list':
            adj_list = self.create_adjacency_list(G)
            data = []
            for node, neighbors in adj_list.items():
                neighbor_str = ', '.join([f"{n}({w})" for n, w in neighbors])
                data.append([node, neighbor_str])
            df = pd.DataFrame(data, columns=['Node', 'Neighbors'])
        
        return df.to_csv(index=False)
    
    def generate_random_graph(self, n_nodes=10, graph_type='undirected', 
                            weighted=False, edge_probability=0.3):
        """Tạo đồ thị ngẫu nhiên"""
        if graph_type == 'undirected':
            G = nx.erdos_renyi_graph(n_nodes, edge_probability)
        else:
            G = nx.erdos_renyi_graph(n_nodes, edge_probability, directed=True)
        
        if weighted:
            for u, v in G.edges():
                G[u][v]['weight'] = round(np.random.uniform(1, 10), 2)
        
        return G
    
    def find_all_shortest_paths(self, G, source, target):
        """Tìm tất cả các đường đi ngắn nhất"""
        try:
            if nx.is_weighted(G):
                return list(nx.all_shortest_paths(G, source, target, weight='weight'))
            else:
                return list(nx.all_shortest_paths(G, source, target))
        except:
            return []
    
    def create_traffic_graph(self, vertices, connections=None):
        """Tạo đồ thị giao thông từ danh sách đỉnh"""
        G = nx.Graph()
        
        # Thêm các đỉnh
        for i, vertex in enumerate(vertices):
            G.add_node(i, 
                      pos=(vertex['lon'], vertex['lat']),
                      lat=vertex['lat'],
                      lon=vertex['lon'],
                      name=vertex.get('name', f'Đỉnh {i}'))
        
        # Thêm các cạnh nếu có kết nối
        if connections:
            for conn in connections:
                u, v, weight = conn
                G.add_edge(u, v, weight=weight)
        else:
            # Tự động tạo cạnh dựa trên khoảng cách
            for i in range(len(vertices)):
                for j in range(i + 1, len(vertices)):
                    # Tính khoảng cách Euclidean (đơn giản hóa)
                    lat1, lon1 = vertices[i]['lat'], vertices[i]['lon']
                    lat2, lon2 = vertices[j]['lat'], vertices[j]['lon']
                    
                    # Tính khoảng cách (đơn vị: đơn vị tọa độ)
                    distance = np.sqrt((lat1-lat2)**2 + (lon1-lon2)**2)
                    
                    # Thêm cạnh nếu khoảng cách hợp lý
                    if distance < 0.05:  # Ngưỡng 0.05 độ
                        G.add_edge(i, j, weight=round(distance * 100, 2))
        
        return G