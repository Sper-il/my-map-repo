import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import networkx as nx
import numpy as np
import pickle
import os
import math
import matplotlib.pyplot as plt
from datetime import datetime
import json
import time
import glob
import requests
import polyline

# Danh sách quận/huyện
DISTRICTS = {
    "Quận 1": "District 1, Ho Chi Minh City, Vietnam",
    "Quận 2": "District 2, Ho Chi Minh City, Vietnam",
    "Quận 3": "District 3, Ho Chi Minh City, Vietnam",
    "Quận 4": "District 4, Ho Chi Minh City, Vietnam",
    "Quận 5": "District 5, Ho Chi Minh City, Vietnam",
    "Quận 6": "District 6, Ho Chi Minh City, Vietnam",
    "Quận 7": "District 7, Ho Chi Minh City, Vietnam",
    "Quận 8": "District 8, Ho Chi Minh City, Vietnam",
    "Quận 9": "District 9, Ho Chi Minh City, Vietnam",
    "Quận 10": "District 10, Ho Chi Minh City, Vietnam",
    "Quận 11": "District 11, Ho Chi Minh City, Vietnam",
    "Quận 12": "District 12, Ho Chi Minh City, Vietnam",
    "Quận Bình Thạnh": "Binh Thanh District, Ho Chi Minh City, Vietnam",
    "Quận Gò Vấp": "Go Vap District, Ho Chi Minh City, Vietnam",
    "Quận Phú Nhuận": "Phu Nhuan District, Ho Chi Minh City, Vietnam",
    "Quận Tân Bình": "Tan Binh District, Ho Chi Minh City, Vietnam",
    "Quận Tân Phú": "Tan Phu District, Ho Chi Minh City, Vietnam",
    "Quận Bình Tân": "Binh Tan District, Ho Chi Minh City, Vietnam",
    "TP. Thủ Đức": "Thu Duc City, Ho Chi Minh City, Vietnam"
}

class SimpleTrafficMap:
    """Lớp bản đồ đơn giản, dễ chạy"""
    
    def __init__(self):
        self.cache_dir = "map_cache"
        self.selected_points = []  # [(lat, lon, name), ...]
        self.selected_edges = []   # [(u, v, weight), ...]
        self.vertex_names = {}     # {id: name}
        self.edit_mode = "add_vertex"
        self.edge_start_point = None
        self.traffic_graph = None
        self.algorithm_result = None
        self.algorithm_history = []  # Lưu lịch sử thuật toán
        self.vertex_counter = 0
        self.last_click_coords = None
        self.loaded_routes = []  # Các route đã load từ cache
        self.current_route = None  # Route hiện tại đang xem
        self.route_progress = 0  # Tiến trình di chuyển trên route (0-100)
        self.max_vertices = 15  # Giới hạn tối đa 15 đỉnh
        self.selected_location = None  # Vị trí đã chọn trên bản đồ
        self.animation_node = None # Biến lưu đỉnh đang animation
        self.osrm_cache = {} # Cache đường đi thực tế để không gọi API nhiều lần
        
        # Cờ kiểm soát hiển thị đường cong (OSRM) hay đường thẳng (Chim bay)
        self.show_curved_path = False 
        
        # Lưu trữ kết quả theo thời gian
        self.saved_results = {}  # {timestamp: result_data}
        
        # Tạo thư mục cache
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Tính khoảng cách Haversine"""
        R = 6371000
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2)**2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def get_osrm_geometry(self, lat1, lon1, lat2, lon2):
        """Lấy geometry đường đi thực tế từ OSRM (Đã Fix Timeout & Headers)"""
        key = f"{lat1:.4f},{lon1:.4f}_{lat2:.4f},{lon2:.4f}"
        if key in self.osrm_cache:
            return self.osrm_cache[key]
            
        try:
            # Sử dụng OSRM public API
            url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=polyline"
            
            # Thêm Header giả lập trình duyệt để tránh bị chặn
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Tăng timeout lên 5 giây để chờ phản hồi từ server free
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 'Ok' and len(data['routes']) > 0:
                    encoded_polyline = data['routes'][0]['geometry']
                    decoded_points = polyline.decode(encoded_polyline)
                    self.osrm_cache[key] = decoded_points
                    return decoded_points
            else:
                print(f"OSRM Error: Status {response.status_code}")
                
        except Exception as e:
            print(f"Lỗi kết nối OSRM: {e}")
            
        # Nếu lỗi thì trả về đường thẳng
        return [[lat1, lon1], [lat2, lon2]]
    
    def add_vertex(self, lat, lon, name=None):
        """Thêm đỉnh mới - giới hạn tối đa 15 đỉnh"""
        if len(self.selected_points) >= self.max_vertices:
            return None, f"Đã đạt giới hạn tối đa {self.max_vertices} đỉnh!"
        
        if name is None or name.strip() == "":
            name = f"Đỉnh {self.vertex_counter}"
            self.vertex_counter += 1
        
        vertex_id = len(self.selected_points)
        self.selected_points.append((lat, lon, name))
        self.vertex_names[vertex_id] = name
        
        # Reset cache
        self.traffic_graph = None
        self.algorithm_result = None
        
        # Cập nhật vertex counter
        self.vertex_counter = len(self.selected_points)
        
        return vertex_id, f"✅ Đã thêm đỉnh {name} (ID: {vertex_id}) tại ({lat:.4f}, {lon:.4f})"
    
    def add_edge(self, u, v, weight=None):
        """Thêm cạnh mới"""
        if u == v:
            return False, "Không thể thêm cạnh từ một đỉnh đến chính nó"
        
        if u >= len(self.selected_points) or v >= len(self.selected_points):
            return False, "Đỉnh không tồn tại"
        
        # Kiểm tra cạnh đã tồn tại
        for edge_u, edge_v, _ in self.selected_edges:
            if (edge_u == u and edge_v == v) or (edge_u == v and edge_v == u):
                return False, "Cạnh đã tồn tại"
        
        # Tính trọng số
        if weight is None:
            lat1, lon1, _ = self.selected_points[u]
            lat2, lon2, _ = self.selected_points[v]
            distance = self.haversine_distance(lat1, lon1, lat2, lon2)
            weight = round(distance / 1000, 2)
        
        self.selected_edges.append((u, v, weight))
        
        # Reset cache
        self.traffic_graph = None
        self.algorithm_result = None
        
        return True, f"✅ Đã thêm cạnh {self.vertex_names[u]}-{self.vertex_names[v]} với trọng số {weight} km"
    
    def remove_vertex(self, vertex_id):
        """Xóa đỉnh"""
        if vertex_id < 0 or vertex_id >= len(self.selected_points):
            return False, "Đỉnh không tồn tại"
        
        # Xóa đỉnh
        vertex_name = self.vertex_names.get(vertex_id, f"Đỉnh {vertex_id}")
        del self.selected_points[vertex_id]
        
        # Xóa các cạnh liên quan
        self.selected_edges = [
            (u, v, w) for u, v, w in self.selected_edges 
            if u != vertex_id and v != vertex_id
        ]
        
        # Cập nhật IDs cho các đỉnh còn lại
        new_points = []
        new_edges = []
        new_names = {}
        
        # Tạo mapping từ ID cũ sang ID mới
        id_mapping = {}
        for old_id, (lat, lon, name) in enumerate(self.selected_points):
            new_id = len(new_points)
            id_mapping[old_id] = new_id
            new_points.append((lat, lon, name))
            new_names[new_id] = name
        
        # Cập nhật các cạnh với ID mới
        for u, v, w in self.selected_edges:
            if u in id_mapping and v in id_mapping:
                new_u = id_mapping[u]
                new_v = id_mapping[v]
                new_edges.append((new_u, new_v, w))
        
        self.selected_points = new_points
        self.selected_edges = new_edges
        self.vertex_names = new_names
        
        # Reset counter
        self.vertex_counter = len(self.selected_points)
        
        # Reset cache
        self.traffic_graph = None
        self.algorithm_result = None
        
        return True, f"✅ Đã xóa đỉnh {vertex_name}"
    
    def remove_edge(self, edge_index):
        """Xóa cạnh"""
        if edge_index < 0 or edge_index >= len(self.selected_edges):
            return False, "Cạnh không tồn tại"
        
        u, v, weight = self.selected_edges[edge_index]
        u_name = self.vertex_names.get(u, f"Đỉnh {u}")
        v_name = self.vertex_names.get(v, f"Đỉnh {v}")
        
        self.selected_edges.pop(edge_index)
        
        # Reset cache
        self.traffic_graph = None
        self.algorithm_result = None
        
        return True, f"✅ Đã xóa cạnh {u_name}-{v_name}"
    
    def find_nearest_vertex(self, lat, lon, max_distance=100):
        """Tìm đỉnh gần nhất trong khoảng cách cho phép"""
        if not self.selected_points:
            return None
        
        nearest_vertex = None
        min_distance = float('inf')
        
        for i, (point_lat, point_lon, _) in enumerate(self.selected_points):
            distance = self.haversine_distance(lat, lon, point_lat, point_lon)
            if distance < min_distance and distance <= max_distance:
                min_distance = distance
                nearest_vertex = i
        
        return nearest_vertex
    
    def load_routes_from_cache(self):
        """Đọc các route từ thư mục cache"""
        self.loaded_routes = []
        
        # Tìm tất cả file JSON trong thư mục cache
        json_files = glob.glob(os.path.join(self.cache_dir, "*.json"))
        
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Kiểm tra cấu trúc dữ liệu
                if 'vertices' in data and 'edges' in data:
                    route_name = os.path.basename(file_path).replace('.json', '')
                    
                    # Chuyển đổi dữ liệu
                    vertices = []
                    edges = []
                    vertex_names = {}
                    
                    for v_data in data['vertices']:
                        vertices.append((v_data['lat'], v_data['lon'], v_data['name']))
                        vertex_names[v_data['id']] = v_data['name']
                    
                    for e_data in data['edges']:
                        edges.append((e_data['from'], e_data['to'], e_data['weight']))
                    
                    self.loaded_routes.append({
                        'name': route_name,
                        'vertices': vertices,
                        'edges': edges,
                        'vertex_names': vertex_names,
                        'file_path': file_path
                    })
                    
            except Exception as e:
                print(f"Không thể đọc file {file_path}: {str(e)}")
    
    def load_route(self, route_index):
        """Load route từ cache"""
        if route_index < 0 or route_index >= len(self.loaded_routes):
            return False, "Route không tồn tại"
        
        route = self.loaded_routes[route_index]
        
        # Cập nhật dữ liệu hiện tại
        self.selected_points = route['vertices'].copy()
        self.selected_edges = route['edges'].copy()
        self.vertex_names = route['vertex_names'].copy()
        self.vertex_counter = len(self.selected_points)
        self.current_route = route['name']
        
        # Reset cache
        self.traffic_graph = None
        self.algorithm_result = None
        
        return True, f"✅ Đã tải route '{route['name']}' với {len(self.selected_points)} đỉnh và {len(self.selected_edges)} cạnh"
    
    def create_simple_map(self):
        """Tạo bản đồ đơn giản với các điểm đánh dấu"""
        # Tạo bản đồ với TP.HCM
        m = folium.Map(
            location=[10.7769, 106.7009],
            zoom_start=12,
            tiles='OpenStreetMap',
            control_scale=True
        )
        
        # Thêm layer control
        folium.LayerControl().add_to(m)
        
        # Hiển thị vị trí đã chọn nếu có
        if self.selected_location:
            lat, lon = self.selected_location
            folium.Marker(
                location=[lat, lon],
                popup=f"<b>📍 Vị trí đã chọn</b><br>Click 'Thêm đỉnh' để thêm",
                tooltip="Vị trí đã chọn",
                icon=folium.Icon(color='green', icon='info-sign', prefix='fa')
            ).add_to(m)
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=15,
                color='green',
                fill=True,
                fill_color='green',
                fill_opacity=0.7,
                popup=f"<b>📍 Vị trí đã chọn</b><br>Tọa độ: ({lat:.4f}, {lon:.4f})"
            ).add_to(m)
        
        # --- CẤU HÌNH MÀU SẮC ĐỘNG (DYNAMIC COLORS) ---
        active_algo_type = self.algorithm_result.get('type') if self.algorithm_result else None
        
        # Mặc định
        algo_glow_color = '#39FF14' 
        
        # Đổi màu theo thuật toán
        if active_algo_type == 'shortest_path':
            algo_glow_color = '#FF4500' # OrangeRed/Red for Dijkstra
        elif active_algo_type == 'hamiltonian':
            algo_glow_color = '#FFD700' # Gold for Hamiltonian
        elif active_algo_type in ['mst_prim', 'mst_kruskal']:
            algo_glow_color = '#1E90FF' # Blue for MST
        elif active_algo_type in ['fleury', 'hierholzer']:
            algo_glow_color = '#FF00FF' # Purple for Euler

        # Lấy start_node và end_node từ kết quả thuật toán (nếu có)
        start_node = None
        end_node = None
        if self.algorithm_result and self.algorithm_result.get('type') == 'shortest_path':
            start_node = self.algorithm_result.get('start')
            end_node = self.algorithm_result.get('end')

        # Thêm các đỉnh đã có
        for i, (lat, lon, name) in enumerate(self.selected_points):
            icon_color = 'blue'
            is_animated_node = False
            
            # Animation Logic (Sử dụng màu động)
            if self.animation_node is not None and i == self.animation_node:
                is_animated_node = True
                icon_color = 'green' 
                
                # Hiệu ứng GLOW
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=30,
                    color=algo_glow_color,
                    fill=True,
                    fill_color=algo_glow_color,
                    fill_opacity=0.5,
                    popup="⚡ Active Node"
                ).add_to(m)
                
            elif self.edit_mode == "add_edge" and self.edge_start_point == i:
                icon_color = 'orange'
            elif i == start_node and self.algorithm_result and self.algorithm_result.get('type') == 'shortest_path':
                icon_color = 'green'  # Điểm bắt đầu
            elif i == end_node and self.algorithm_result and self.algorithm_result.get('type') == 'shortest_path':
                icon_color = 'red'  # Điểm kết thúc
            
            # Xác định loại đỉnh cho popup
            vertex_type = '📍 Điểm'
            if i == start_node:
                vertex_type = '🚀 Bắt đầu'
            elif i == end_node:
                vertex_type = '🏁 Kết thúc'
            
            # Thêm marker
            popup_html = f"""
            <div style="font-family: Arial; width: 200px;">
                <h4 style="margin: 0; color: #333;">{name}</h4>
                <hr style="margin: 5px 0;">
                <p style="margin: 5px 0;"><b>ID:</b> {i}</p>
                <p style="margin: 5px 0;"><b>Tọa độ:</b><br>
                {lat:.4f}, {lon:.4f}</p>
                <p style="margin: 5px 0;"><b>Loại:</b> {vertex_type}</p>
                <p style="margin: 5px 0;"><b>Trạng thái:</b> {'⚡ ACTIVE' if is_animated_node else 'Đã đánh dấu'}</p>
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Click để xem {name}",
                icon=folium.Icon(color=icon_color, icon='info-sign', prefix='fa')
            ).add_to(m)
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=10,
                color=icon_color,
                fill=True,
                fill_color=icon_color,
                fill_opacity=0.7,
                popup=f"<b>{name}</b><br>ID: {i}"
            ).add_to(m)
    
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=10,
                color=icon_color,
                fill=True,
                fill_color=icon_color,
                fill_opacity=0.7,
                popup=f"<b>{name}</b><br>ID: {i}<br>{'🚀 Bắt đầu' if i == start_node else ('🏁 Kết thúc' if i == end_node else '📍 Điểm')}"
            ).add_to(m)
        
        # Thêm các cạnh
        for u, v, weight in self.selected_edges:
            if u < len(self.selected_points) and v < len(self.selected_points):
                point1 = self.selected_points[u]
                point2 = self.selected_points[v]
                mid_lat, mid_lon = (point1[0] + point2[0]) / 2, (point1[1] + point2[1]) / 2
                
                edge_color = 'gray'
                edge_weight = 2
                draw_real_path_for_this_edge = False # Cờ xác định vẽ OSRM cho cạnh này
                
                if self.algorithm_result:
                    # 1. Dijkstra (Red)
                    if self.algorithm_result['type'] == 'shortest_path':
                        path = self.algorithm_result.get('path', [])
                        path_edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
                        if (u, v) in path_edges or (v, u) in path_edges:
                            edge_color = 'red'
                            edge_weight = 4
                            # NẾU BẬT CHẾ ĐỘ THỰC TẾ VÀ LÀ CẠNH TRONG PATH -> VẼ CONG
                            if self.show_curved_path:
                                draw_real_path_for_this_edge = True 
                            
                            # Animation Color
                            if self.animation_node is not None and len(path) > 1:
                                try:
                                    idx = path.index(self.animation_node)
                                    if idx > 0:
                                        prev_node = path[idx-1]
                                        if (u == prev_node and v == self.animation_node) or (v == prev_node and u == self.animation_node):
                                            edge_color = algo_glow_color
                                            edge_weight = 6
                                except: pass
                    
                    # 2. Hamiltonian (Gold)
                    elif self.algorithm_result['type'] == 'hamiltonian':
                        cycle = self.algorithm_result.get('cycle', [])
                        cycle_edges = [(cycle[i], cycle[i+1]) for i in range(len(cycle)-1)]
                        if (u, v) in cycle_edges or (v, u) in cycle_edges:
                            edge_color = '#FFD700'  # Gold
                            edge_weight = 4
                            
                    # 3. MST (Blue)
                    elif self.algorithm_result['type'] in ['mst_prim', 'mst_kruskal']:
                        mst_edges = [(edge[0], edge[1]) for edge in self.algorithm_result.get('edges', [])]
                        if (u, v) in mst_edges or (v, u) in mst_edges:
                            edge_color = 'blue'
                            edge_weight = 4
                            
                    # 4. Euler (Purple)
                    elif self.algorithm_result['type'] in ['fleury', 'hierholzer']:
                         circuit = self.algorithm_result.get('circuit', [])
                         circuit_edges = [(circuit[i], circuit[i+1]) for i in range(len(circuit)-1)]
                         if (u, v) in circuit_edges or (v, u) in circuit_edges:
                             edge_color = 'purple'
                             edge_weight = 4

                # LOGIC LẤY TỌA ĐỘ VẼ DÂY
                locations = []
                if draw_real_path_for_this_edge:
                    # Gọi OSRM để lấy đường cong thực tế
                    locations = self.get_osrm_geometry(point1[0], point1[1], point2[0], point2[1])
                else:
                    # Đường thẳng (chim bay)
                    locations = [[point1[0], point1[1]], [point2[0], point2[1]]]

                folium.PolyLine(
                    locations=locations,
                    color=edge_color,
                    weight=edge_weight,
                    opacity=0.8,
                    popup=f"<b>Cạnh {self.vertex_names[u]}-{self.vertex_names[v]}</b><br>Khoảng cách: {weight} km<br>Trạng thái: {'Trong đường đi' if edge_color != 'gray' else 'Không được chọn'}",
                    tooltip=f"{weight} km"
                ).add_to(m)
                
                folium.Marker(
                    location=[mid_lat, mid_lon],
                    icon=folium.DivIcon(html=f'<div style="font-size: 10pt; color: white; background: {edge_color}; padding: 3px 6px; border-radius: 10px; border: 1px solid #333; text-align: center; font-weight: bold; box-shadow: 2px 2px 4px rgba(0,0,0,0.3);">{weight} km</div>')
                ).add_to(m)
        
        m.add_child(folium.LatLngPopup())
        return m
    
    def create_traffic_graph(self):
        """Tạo đồ thị từ các điểm"""
        if len(self.selected_points) < 2:
            return None
        
        G = nx.Graph()
        
        # Thêm đỉnh
        for i, (lat, lon, name) in enumerate(self.selected_points):
            G.add_node(i, pos=(lon, lat), lat=lat, lon=lon, name=name)
        
        # Thêm cạnh
        for u, v, weight in self.selected_edges:
            if u < len(self.selected_points) and v < len(self.selected_points):
                G.add_edge(u, v, weight=weight)
        
        self.traffic_graph = G
        return G
    
    def run_algorithm(self, algorithm_type, **kwargs):
        """Chạy thuật toán"""
        # QUAN TRỌNG: Khi chạy thuật toán mới -> Reset chế độ hiển thị đường cong về mặc định (False)
        self.show_curved_path = False 
        
        # Tạo đồ thị
        self.create_traffic_graph()
        
        if self.traffic_graph is None or self.traffic_graph.number_of_nodes() < 2:
            return None, "Cần ít nhất 2 đỉnh"
        
        if self.traffic_graph.number_of_edges() < 1:
            return None, "Cần ít nhất 1 cạnh"
        
        try:
            result = {
                'type': algorithm_type,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'vertex_names': self.vertex_names.copy(),
                'num_vertices': len(self.selected_points),
                'num_edges': len(self.selected_edges)
            }
            
            if algorithm_type == "shortest_path":
                start_node = kwargs.get('start_node', 0)
                end_node = kwargs.get('end_node', 1)
                
                if nx.is_weighted(self.traffic_graph):
                    path = nx.dijkstra_path(self.traffic_graph, start_node, end_node)
                    length = nx.dijkstra_path_length(self.traffic_graph, start_node, end_node)
                else:
                    path = nx.shortest_path(self.traffic_graph, start_node, end_node)
                    length = len(path) - 1
                
                # Check cycle for Dijkstra
                has_cycle = (start_node == end_node)
                
                # Tính tổng trọng số
                total_weight = 0
                edge_details = []
                edge_path = []  # Danh sách cạnh theo thứ tự
                for i in range(len(path)-1):
                    u, v = path[i], path[i+1]
                    if self.traffic_graph.has_edge(u, v):
                        weight = self.traffic_graph[u][v].get('weight', 1)
                        total_weight += weight
                        edge_path.append((u, v, weight))
                        edge_details.append({
                            'Cạnh': f"{self.vertex_names.get(u, u)}-{self.vertex_names.get(v, v)}",
                            'Trọng số': weight,
                            'Từ đỉnh': self.vertex_names.get(u, u),
                            'Đến đỉnh': self.vertex_names.get(v, v)
                        })
                
                result.update({
                    'path': path,
                    'edge_path': edge_path,
                    'length': length,
                    'total_weight': total_weight,
                    'edge_details': edge_details,
                    'start': start_node,
                    'end': end_node,
                    'has_cycle': has_cycle,
                    'cycle_msg': "Điểm đầu trùng điểm cuối" if has_cycle else "Điểm đầu khác điểm cuối"
                })
                
            elif algorithm_type == "hamiltonian":
                start_node = kwargs.get('start_node', 0)
                
                # Tìm chu trình Hamiltonian
                try:
                    # Sử dụng thuật toán backtracking cho đồ thị nhỏ
                    cycle = self.find_hamiltonian_cycle(start_node)
                    
                    if cycle:
                        # Tính tổng trọng số
                        total_weight = 0
                        edge_details = []
                        edge_path = []
                        for i in range(len(cycle)-1):
                            u, v = cycle[i], cycle[i+1]
                            if self.traffic_graph.has_edge(u, v):
                                weight = self.traffic_graph[u][v].get('weight', 1)
                                total_weight += weight
                                edge_path.append((u, v, weight))
                                edge_details.append({
                                    'Cạnh': f"{self.vertex_names.get(u, u)}-{self.vertex_names.get(v, v)}",
                                    'Trọng số': weight,
                                    'Từ đỉnh': self.vertex_names.get(u, u),
                                    'Đến đỉnh': self.vertex_names.get(v, v)
                                })
                        
                        result.update({
                            'cycle': cycle,
                            'edge_path': edge_path,
                            'cycle_found': True,
                            'total_weight': total_weight,
                            'edge_details': edge_details,
                            'start': start_node,
                            'length': len(cycle) - 1,
                            'has_cycle': True,
                            'cycle_msg': "Chu trình Hamiltonian tìm thấy"
                        })
                    else:
                        return None, "❌ Không tìm thấy chu trình Hamiltonian!"
                        
                except Exception as e:
                    return None, f"Lỗi khi tìm chu trình Hamiltonian: {str(e)}"
                
            elif algorithm_type in ["fleury", "hierholzer"]:
                start_node = kwargs.get('start_node', 0)
                
                # --- KIỂM TRA ĐIỀU KIỆN EULER ---
                odd_degree_nodes = [node for node, degree in self.traffic_graph.degree() if degree % 2 == 1]
                
                # Để hiển thị sau này
                result['odd_degree_nodes'] = odd_degree_nodes
                
                if len(odd_degree_nodes) not in [0, 2]:
                    error_msg = f"❌ **Không thỏa điều kiện Euler!**\nSố đỉnh bậc lẻ: {len(odd_degree_nodes)} (phải là 0 hoặc 2).\nCác đỉnh bậc lẻ:\n"
                    for node in odd_degree_nodes:
                        name = self.vertex_names.get(node, f"Đỉnh {node}")
                        degree = self.traffic_graph.degree(node)
                        error_msg += f"- **{name}** (Bậc {degree})\n"
                    return None, error_msg
                
                if not nx.is_connected(self.traffic_graph):
                    return None, "❌ **Lỗi liên thông:** Đồ thị bị đứt đoạn."
                
                circuit = []
                is_circuit = (len(odd_degree_nodes) == 0) # 0 đỉnh lẻ => Chu trình
                
                if is_circuit:
                     circuit_edges = list(nx.eulerian_circuit(self.traffic_graph)) # List of edges
                     circuit = [edge[0] for edge in circuit_edges] + [circuit_edges[-1][1]]
                else:
                    circuit_edges = list(nx.eulerian_path(self.traffic_graph))
                    circuit = [edge[0] for edge in circuit_edges] + [circuit_edges[-1][1]]

                # Tính tổng trọng số
                total_weight = 0
                edge_details = []
                edge_path = []
                for u, v in circuit_edges:
                    if self.traffic_graph.has_edge(u, v):
                        weight = self.traffic_graph[u][v].get('weight', 1)
                        total_weight += weight
                        edge_path.append((u, v, weight))
                        edge_details.append({
                            'Cạnh': f"{self.vertex_names.get(u, u)}-{self.vertex_names.get(v, v)}",
                            'Trọng số': weight,
                            'Từ đỉnh': self.vertex_names.get(u, u),
                            'Đến đỉnh': self.vertex_names.get(v, v)
                        })

                result.update({
                    'circuit': circuit,
                    'edge_path': edge_path,
                    'edges_path': circuit_edges,
                    'length': len(circuit_edges),
                    'total_weight': total_weight,
                    'edge_details': edge_details,
                    'has_cycle': is_circuit,
                    'cycle_msg': "Tạo thành chu trình khép kín" if is_circuit else "Đường đi hở (không phải chu trình)"
                })
                
                # Tạo bảng trace log
                trace_log = []
                step_count = 1
                current_u = circuit[0]
                
                for i in range(len(circuit)-1):
                    next_v = circuit[i+1]
                    u_name = self.vertex_names.get(current_u, str(current_u))
                    v_name = self.vertex_names.get(next_v, str(next_v))
                    
                    trace_log.append({
                        "Bước": step_count,
                        "Đỉnh đang xét": u_name,
                        "Chọn cạnh": f"{u_name} -> {v_name}",
                        "Trọng số": self.traffic_graph[current_u][next_v].get('weight', 1) if self.traffic_graph.has_edge(current_u, next_v) else "N/A",
                        "Trạng thái": "Đi cạnh này"
                    })
                    
                    current_u = next_v
                    step_count += 1
                    
                result['trace_df'] = pd.DataFrame(trace_log)

            elif algorithm_type == "mst_prim":
                start_node = kwargs.get('start_node', 0)
                
                # Tạo MST bằng Prim với đỉnh bắt đầu
                mst_edges = []
                visited = {start_node}
                edges = []
                
                # Thêm tất cả các cạnh từ đỉnh bắt đầu
                for v in self.traffic_graph.neighbors(start_node):
                    weight = self.traffic_graph[start_node][v].get('weight', 1)
                    edges.append((weight, start_node, v))
                
                # Sắp xếp theo trọng số
                edges.sort()
                
                while edges and len(visited) < self.traffic_graph.number_of_nodes():
                    weight, u, v = edges.pop(0)
                    
                    if v not in visited:
                        visited.add(v)
                        mst_edges.append((u, v, weight))
                        
                        # Thêm các cạnh từ v mới thêm vào
                        for w in self.traffic_graph.neighbors(v):
                            if w not in visited:
                                new_weight = self.traffic_graph[v][w].get('weight', 1)
                                edges.append((new_weight, v, w))
                        
                        # Sắp xếp lại
                        edges.sort()
                
                # Tính tổng trọng số
                total_weight = sum(weight for _, _, weight in mst_edges)
                
                # Tạo danh sách cạnh chi tiết
                edge_details = []
                edge_path = []
                for u, v, weight in mst_edges:
                    edge_path.append((u, v, weight))
                    edge_details.append({
                        'Cạnh': f"{self.vertex_names.get(u, u)}-{self.vertex_names.get(v, v)}",
                        'Trọng số': weight,
                        'Từ đỉnh': self.vertex_names.get(u, u),
                        'Đến đỉnh': self.vertex_names.get(v, v)
                    })
                
                result.update({
                    'edges': mst_edges,
                    'edge_path': edge_path,
                    'edge_details': edge_details,
                    'total_weight': total_weight,
                    'start': start_node,
                    'has_cycle': False,
                    'cycle_msg': "Cây khung không chứa chu trình"
                })
                
            elif algorithm_type == "mst_kruskal":
                # Sắp xếp các cạnh theo trọng số
                edges = []
                for u, v, data in self.traffic_graph.edges(data=True):
                    weight = data.get('weight', 1)
                    edges.append((weight, u, v))
                
                edges.sort()
                
                # Union-Find
                parent = {node: node for node in self.traffic_graph.nodes()}
                rank = {node: 0 for node in self.traffic_graph.nodes()}
                
                def find(x):
                    if parent[x] != x:
                        parent[x] = find(parent[x])
                    return parent[x]
                
                def union(x, y):
                    rootX = find(x)
                    rootY = find(y)
                    
                    if rootX != rootY:
                        if rank[rootX] < rank[rootY]:
                            parent[rootX] = rootY
                        elif rank[rootX] > rank[rootY]:
                            parent[rootY] = rootX
                        else:
                            parent[rootY] = rootX
                            rank[rootX] += 1
                        return True
                    return False
                
                mst_edges = []
                for weight, u, v in edges:
                    if union(u, v):
                        mst_edges.append((u, v, weight))
                        if len(mst_edges) == self.traffic_graph.number_of_nodes() - 1:
                            break
                
                # Tính tổng trọng số
                total_weight = sum(weight for _, _, weight in mst_edges)
                
                # Tạo danh sách cạnh chi tiết
                edge_details = []
                edge_path = []
                for u, v, weight in mst_edges:
                    edge_path.append((u, v, weight))
                    edge_details.append({
                        'Cạnh': f"{self.vertex_names.get(u, u)}-{self.vertex_names.get(v, v)}",
                        'Trọng số': weight,
                        'Từ đỉnh': self.vertex_names.get(u, u),
                        'Đến đỉnh': self.vertex_names.get(v, v)
                    })
                
                result.update({
                    'edges': mst_edges,
                    'edge_path': edge_path,
                    'edge_details': edge_details,
                    'total_weight': total_weight,
                    'has_cycle': False,
                    'cycle_msg': "Cây khung không chứa chu trình"
                })

            # Lưu kết quả vào lịch sử và saved_results
            self.algorithm_result = result
            self.algorithm_history.append(result)
            
            # Lưu với timestamp làm key
            timestamp_key = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.saved_results[timestamp_key] = result
            
            return result, None
            
        except Exception as e:
            return None, f"Lỗi: {str(e)}"

    def find_hamiltonian_cycle(self, start_node):
        """Tìm chu trình Hamiltonian bằng backtracking"""
        n = self.traffic_graph.number_of_nodes()
        
        # Tạo danh sách kề với trọng số
        adj_list = {}
        for u in range(n):
            adj_list[u] = []
            for v in self.traffic_graph.neighbors(u):
                weight = self.traffic_graph[u][v].get('weight', 1)
                adj_list[u].append((v, weight))
        
        path = [start_node]
        visited = set([start_node])
        
        def backtrack(current):
            # Nếu đã đi qua tất cả các đỉnh
            if len(path) == n:
                # Kiểm tra có cạnh từ đỉnh cuối về đỉnh đầu không
                for neighbor, _ in adj_list[current]:
                    if neighbor == start_node:
                        path.append(start_node)
                        return True
                return False
            
            # Thử các đỉnh kề chưa visited
            for neighbor, weight in sorted(adj_list[current], key=lambda x: x[1]):
                if neighbor not in visited:
                    path.append(neighbor)
                    visited.add(neighbor)
                    
                    if backtrack(neighbor):
                        return True
                    
                    # Backtrack
                    path.pop()
                    visited.remove(neighbor)
            
            return False
        
        if backtrack(start_node):
            return path
        return None

    def simulate_route_progress(self, progress):
        """Mô phỏng tiến trình di chuyển trên route"""
        # Giữ lại logic cũ
        return None, None, progress

def show_integrated_traffic_map():
    """Hiển thị bản đồ tích hợp đơn giản"""
    st.title("🗺️ Bản Đồ TP.HCM - Tích Hợp Thuật Toán & Đường Đi Thực Tế")
    
    # Khởi tạo session state
    if 'simple_traffic_app' not in st.session_state:
        st.session_state.simple_traffic_app = SimpleTrafficMap()
    
    # Khởi tạo state cho Animation
    if 'anim_state' not in st.session_state:
        st.session_state.anim_state = {'running': False, 'path': [], 'idx': 0}
    
    app = st.session_state.simple_traffic_app
    
    # --- LOGIC CHẠY ANIMATION TỰ ĐỘNG ---
    if st.session_state.anim_state['running']:
        idx = st.session_state.anim_state['idx']
        path = st.session_state.anim_state['path']
        
        if idx < len(path):
            app.animation_node = path[idx] # Set đỉnh cần highlight
            st.session_state.anim_state['idx'] += 1
            time.sleep(0.8) # Thời gian dừng để user nhìn thấy hiệu ứng
            st.rerun() # Rerun để cập nhật bản đồ
        else:
            st.session_state.anim_state['running'] = False
            app.animation_node = None
            st.rerun()
    # ------------------------------------

    if 'vertex_name_input' not in st.session_state:
        st.session_state.vertex_name_input = f"Đỉnh {len(app.selected_points)}"
    
    if not app.loaded_routes:
        app.load_routes_from_cache()
    
    col_sidebar, col_map, col_info = st.columns([1, 2, 1])
    
    with col_sidebar:
        st.subheader("⚙️ Tùy Chọn Bản Đồ")
        main_tab = st.radio("Chức năng chính:", ["Tạo đồ thị", "Thuật toán", "Quản lý", "Đường đi thực tế", "📜 Lịch sử kết quả"])
        
        if main_tab == "Tạo đồ thị":
            st.markdown("**✏️ Chế độ vẽ:**")
            edit_mode = st.radio("Chọn chế độ:", ["Thêm đỉnh", "Thêm cạnh"], horizontal=True, key="edit_mode")
            app.edit_mode = edit_mode.lower().replace(" ", "_")
            st.info(f"**Giới hạn:** Tối đa {app.max_vertices} đỉnh (hiện có: {len(app.selected_points)})")
            
            if edit_mode == "Thêm đỉnh":
                if app.selected_location:
                    lat, lon = app.selected_location
                    st.success(f"📍 **Vị trí đã chọn:** ({lat:.4f}, {lon:.4f})")
                else:
                    st.info("👉 Click trên bản đồ để chọn vị trí")
                
                vertex_name = st.text_input("Tên đỉnh:", value=st.session_state.vertex_name_input, key="vertex_name_input_widget")
                st.session_state.vertex_name_input = vertex_name
                
                if app.selected_location:
                    lat, lon = app.selected_location
                    if st.button("📍 Thêm đỉnh tại vị trí đã chọn", use_container_width=True, type="primary"):
                        if len(app.selected_points) >= app.max_vertices:
                            st.error(f"Đã đạt giới hạn {app.max_vertices} đỉnh!")
                        else:
                            vertex_id, msg = app.add_vertex(lat, lon, vertex_name)
                            if vertex_id is not None:
                                st.session_state.vertex_name_input = f"Đỉnh {len(app.selected_points)}"
                                app.selected_location = None
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                
                col_rand1, col_rand2 = st.columns(2)
                with col_rand1:
                    if st.button("🎲 Thêm ngẫu nhiên", use_container_width=True):
                        if len(app.selected_points) >= app.max_vertices:
                             st.error("Max vertices reached")
                        else:
                            lat = 10.7 + np.random.uniform(-0.1, 0.1)
                            lon = 106.6 + np.random.uniform(-0.1, 0.1)
                            vertex_id, msg = app.add_vertex(lat, lon, vertex_name)
                            if vertex_id: st.rerun()
                with col_rand2:
                     if st.button("📍 Thêm trung tâm", use_container_width=True):
                        if len(app.selected_points) >= app.max_vertices: st.error("Max vertices reached")
                        else:
                            vertex_id, msg = app.add_vertex(10.7769, 106.7009, vertex_name)
                            if vertex_id: st.rerun()

                if app.selected_location:
                    if st.button("🗑️ Xóa vị trí đã chọn", use_container_width=True):
                        app.selected_location = None
                        st.rerun()
                
            elif edit_mode == "Thêm cạnh":
                if len(app.selected_points) >= 2:
                    col_u, col_v = st.columns(2)
                    with col_u:
                        u = st.selectbox("Đỉnh 1:", range(len(app.selected_points)), format_func=lambda x: app.vertex_names.get(x, f"Đỉnh {x}"), key="edge_u")
                    with col_v:
                        v = st.selectbox("Đỉnh 2:", range(len(app.selected_points)), format_func=lambda x: app.vertex_names.get(x, f"Đỉnh {x}"), key="edge_v")
                    
                    distance = 1.0
                    if u != v:
                        lat1, lon1, _ = app.selected_points[u]
                        lat2, lon2, _ = app.selected_points[v]
                        distance = app.haversine_distance(lat1, lon1, lat2, lon2) / 1000
                    
                    weight = st.number_input("Trọng số (km):", min_value=0.1, value=float(round(distance, 2)) if u != v else 1.0, step=0.1, format="%.2f")
                    
                    if st.button("🔗 Thêm cạnh", use_container_width=True):
                        success, msg = app.add_edge(u, v, weight)
                        if success: st.success(msg); st.rerun()
                        else: st.error(msg)
                else:
                    st.warning("Cần ít nhất 2 đỉnh")
        
        elif main_tab == "Thuật toán":
            st.markdown("**🎯 Chọn thuật toán:**")
            algorithm_names = {
                "shortest_path": "Đường đi ngắn nhất (Dijkstra)",
                "hamiltonian": "Chu trình Hamiltonian",
                "mst_prim": "Cây khung nhỏ nhất (Prim)",
                "mst_kruskal": "Cây khung nhỏ nhất (Kruskal)",
                "fleury": "Chu trình Euler (Fleury)",
                "hierholzer": "Chu trình Euler (Hierholzer)"
            }
            algo = st.selectbox("Thuật toán:", list(algorithm_names.keys()), format_func=lambda x: algorithm_names[x])
            
            # --- HIỂN THỊ HƯỚNG DẪN THUẬT TOÁN ---
            algo_guides = {
                "shortest_path": """
                **📘 Hướng dẫn thuật toán Dijkstra:**
                - **Mục đích:** Tìm đường đi ngắn nhất giữa hai điểm
                - **Cách dùng:** Chọn đỉnh bắt đầu và đỉnh kết thúc
                - **Kết quả:** Hiển thị đường đi, tổng trọng số, danh sách cạnh đi qua
                - **Ứng dụng:** Định tuyến GPS, tối ưu hóa đường đi
                """,
                "hamiltonian": """
                **📘 Hướng dẫn thuật toán Hamiltonian:**
                - **Mục đích:** Tìm chu trình đi qua mỗi đỉnh đúng 1 lần
                - **Cách dùng:** Chọn đỉnh bắt đầu (chu trình sẽ quay về đây)
                - **Kết quả:** Hiển thị chu trình nếu tìm thấy, tổng trọng số
                - **Lưu ý:** Không phải đồ thị nào cũng có chu trình Hamiltonian
                - **Ứng dụng:** Bài toán người bán hàng (TSP), lập lịch trình
                """,
                "mst_prim": """
                **📘 Hướng dẫn thuật toán Prim:**
                - **Mục đích:** Tìm cây khung nhỏ nhất (MST)
                - **Cách dùng:** Chọn đỉnh bắt đầu bất kỳ
                - **Kết quả:** Hiển thị các cạnh trong MST, tổng trọng số
                - **Ưu điểm:** Hiệu quả với đồ thị dày (nhiều cạnh)
                - **Ứng dụng:** Thiết kế mạng lưới điện, viễn thông
                """,
                "mst_kruskal": """
                **📘 Hướng dẫn thuật toán Kruskal:**
                - **Mục đích:** Tìm cây khung nhỏ nhất (MST)
                - **Cách dùng:** Không cần chọn đỉnh bắt đầu
                - **Kết quả:** Hiển thị các cạnh trong MST, tổng trọng số
                - **Ưu điểm:** Hiệu quả với đồ thị thưa (ít cạnh)
                - **Ứng dụng:** Tương tự Prim, dùng cấu trúc Union-Find
                """,
                "fleury": """
                **📘 Hướng dẫn thuật toán Euler (Fleury):**
                - **Mục đích:** Tìm chu trình Euler đi qua mỗi cạnh đúng 1 lần
                - **Điều kiện:** Tất cả đỉnh có bậc chẵn (chu trình) hoặc đúng 2 đỉnh bậc lẻ (đường đi)
                - **Kết quả:** Hiển thị chu trình/đường đi, tổng trọng số
                - **Ứng dụng:** Bài toán người đưa thư, thu gom rác
                """,
                "hierholzer": """
                **📘 Hướng dẫn thuật toán Euler (Hierholzer):**
                - **Mục đích:** Tương tự Fleury nhưng hiệu quả hơn
                - **Điều kiện:** Giống Fleury
                - **Kết quả:** Hiển thị chu trình/đường đi, tổng trọng số
                - **Ưu điểm:** Nhanh hơn Fleury, không cần kiểm tra cầu
                """
            }
            
            if algo in algo_guides:
                with st.expander("📖 Xem hướng dẫn chi tiết"):
                    st.markdown(algo_guides[algo])
            # ---------------------------------------------
            
            params = {}
            if algo == "shortest_path" and len(app.selected_points) >= 2:
                col_start, col_end = st.columns(2)
                with col_start: start = st.selectbox("Đỉnh bắt đầu:", range(len(app.selected_points)), format_func=lambda x: app.vertex_names.get(x, f"Đỉnh {x}"), key="start_node")
                with col_end: end = st.selectbox("Đỉnh kết thúc:", range(len(app.selected_points)), format_func=lambda x: app.vertex_names.get(x, f"Đỉnh {x}"), key="end_node")
                params = {'start_node': start, 'end_node': end}
            
            elif algo == "hamiltonian":
                start = st.selectbox("Đỉnh bắt đầu (chu trình sẽ quay về đây):", range(len(app.selected_points)), format_func=lambda x: app.vertex_names.get(x, f"Đỉnh {x}"), key="hamilton_start")
                params = {'start_node': start}
            
            elif algo == "mst_prim":
                start = st.selectbox("Đỉnh bắt đầu:", range(len(app.selected_points)), format_func=lambda x: app.vertex_names.get(x, f"Đỉnh {x}"), key="prim_start")
                params = {'start_node': start}
            
            elif algo in ["fleury", "hierholzer"]:
                # Kiểm tra đỉnh bậc lẻ để gợi ý điểm xuất phát nếu cần
                start_suggestions = []
                if app.traffic_graph:
                    start_suggestions = [n for n, d in app.traffic_graph.degree() if d % 2 == 1]
                
                start_default = start_suggestions[0] if start_suggestions else 0
                start = st.selectbox("Đỉnh bắt đầu:", range(len(app.selected_points)), index=start_default if start_default < len(app.selected_points) else 0, format_func=lambda x: app.vertex_names.get(x, f"Đỉnh {x}"), key="euler_start")
                params = {'start_node': start}

            if st.button("🚀 Chạy thuật toán", use_container_width=True, type="primary"):
                result, error = app.run_algorithm(algo, **params)
                if result:
                    st.success(f"✅ Thuật toán {algorithm_names[algo]} chạy thành công!")
                    
                    # --- HIỂN THỊ KẾT QUẢ CHI TIẾT ---
                    st.markdown("---")
                    st.subheader("📊 Kết quả chi tiết")
                    
                    # Hiển thị thông tin chung
                    col_res1, col_res2, col_res3 = st.columns(3)
                    
                    with col_res1:
                        if 'total_weight' in result:
                            st.metric("Tổng trọng số", f"{result['total_weight']:.2f} km")
                    
                    with col_res2:
                        if 'length' in result:
                            st.metric("Số cạnh", result['length'])
                    
                    with col_res3:
                        if 'has_cycle' in result:
                            st.metric("Chu trình", "Có" if result['has_cycle'] else "Không")
                    
                    # Hiển thị đường đi/chu trình
                    if algo == "shortest_path":
                        path = result.get('path', [])
                        path_names = [app.vertex_names.get(node, node) for node in path]
                        st.markdown(f"**Đường đi:** {' → '.join(map(str, path_names))}")
                    
                    elif algo == "hamiltonian":
                        cycle = result.get('cycle', [])
                        cycle_names = [app.vertex_names.get(node, node) for node in cycle]
                        st.markdown(f"**Chu trình Hamiltonian:** {' → '.join(map(str, cycle_names))}")
                    
                    elif algo in ["fleury", "hierholzer"]:
                        circuit = result.get('circuit', [])
                        circuit_names = [app.vertex_names.get(node, node) for node in circuit]
                        st.markdown(f"**Chu trình/Đường đi Euler:** {' → '.join(map(str, circuit_names))}")
                    
                    # Hiển thị danh sách cạnh chi tiết
                    if 'edge_details' in result and result['edge_details']:
                        st.markdown("**📋 Các cạnh đi qua:**")
                        edge_df = pd.DataFrame(result['edge_details'])
                        st.dataframe(edge_df, use_container_width=True)
                    
                    # --- AUTO ANIMATION TRIGGER ---
                    nodes_to_animate = []
                    if 'path' in result:
                        nodes_to_animate = result['path']
                    elif 'cycle' in result:
                        nodes_to_animate = result['cycle']
                    elif 'circuit' in result:
                        nodes_to_animate = result['circuit']
                    
                    if nodes_to_animate:
                        st.session_state.anim_state = {
                            'running': True,
                            'path': nodes_to_animate,
                            'idx': 0
                        }
                        st.rerun()
                    # -----------------------------
                else:
                    st.error(f"❌ {error}")
            
            # --- HIỂN THỊ KẾT QUẢ HIỆN TẠI ---
            if app.algorithm_result and app.algorithm_result.get('type') == algo:
                st.markdown("---")
                st.markdown("**🎯 Kết quả hiện tại trên bản đồ:**")
                
                # Hiển thị thông tin nhanh
                if 'total_weight' in app.algorithm_result:
                    st.info(f"**Tổng trọng số:** {app.algorithm_result['total_weight']:.2f} km")
                
                if algo == "shortest_path":
                    start = app.algorithm_result.get('start')
                    end = app.algorithm_result.get('end')
                    if start is not None and end is not None:
                        st.info(f"**Đường đi từ:** {app.vertex_names.get(start, start)} → {app.vertex_names.get(end, end)}")

        elif main_tab == "📜 Lịch sử kết quả":
            st.markdown("**📚 Lịch sử kết quả thuật toán:**")
            
            if not app.saved_results:
                st.info("Chưa có kết quả nào được lưu. Hãy chạy thuật toán để lưu kết quả.")
            else:
                # Hiển thị danh sách kết quả đã lưu
                for timestamp, result in sorted(app.saved_results.items(), reverse=True):
                    algo_type = result.get('type', 'unknown')
                    algo_name = {
                        'shortest_path': 'Dijkstra',
                        'hamiltonian': 'Hamiltonian',
                        'mst_prim': 'Prim',
                        'mst_kruskal': 'Kruskal',
                        'fleury': 'Fleury',
                        'hierholzer': 'Hierholzer'
                    }.get(algo_type, algo_type)
                    
                    with st.expander(f"{algo_name} - {result.get('timestamp', timestamp)}"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Thuật toán:** {algo_name}")
                            st.write(f"**Thời gian:** {result.get('timestamp', 'N/A')}")
                            if 'total_weight' in result:
                                st.write(f"**Tổng trọng số:** {result['total_weight']:.2f} km")
                            if 'length' in result:
                                st.write(f"**Số cạnh:** {result['length']}")
                        
                        with col2:
                            if st.button("📊 Xem kết quả", key=f"view_{timestamp}"):
                                app.algorithm_result = result
                                st.rerun()
                        
                        # Hiển thị đường đi nếu có
                        if 'path' in result:
                            path = result['path']
                            path_names = [app.vertex_names.get(node, node) for node in path]
                            st.write(f"**Đường đi:** {' → '.join(map(str, path_names))}")
                        elif 'cycle' in result:
                            cycle = result['cycle']
                            cycle_names = [app.vertex_names.get(node, node) for node in cycle]
                            st.write(f"**Chu trình:** {' → '.join(map(str, cycle_names))}")
                        elif 'circuit' in result:
                            circuit = result['circuit']
                            circuit_names = [app.vertex_names.get(node, node) for node in circuit]
                            st.write(f"**Chu trình Euler:** {' → '.join(map(str, circuit_names))}")
                        
                        # Nút xóa
                        if st.button("🗑️ Xóa kết quả này", key=f"delete_{timestamp}"):
                            del app.saved_results[timestamp]
                            st.rerun()
                
                # Nút xóa tất cả
                if st.button("🗑️ Xóa tất cả kết quả", use_container_width=True):
                    app.saved_results = {}
                    app.algorithm_history = []
                    st.rerun()

        elif main_tab == "Quản lý":
            st.markdown("**🗃️ Quản lý đồ thị:**")
            col_info1, col_info2 = st.columns(2)
            with col_info1: st.metric("Số đỉnh", len(app.selected_points))
            with col_info2: st.metric("Số cạnh", len(app.selected_edges))
            
            # Xóa đỉnh
            if app.selected_points:
                st.markdown("**🗑️ Xóa đỉnh:**")
                vertex_options = [f"{app.vertex_names.get(i, f'Đỉnh {i}')} (ID: {i})" for i in range(len(app.selected_points))]
                selected_vertex = st.selectbox("Chọn đỉnh để xóa:", range(len(vertex_options)), format_func=lambda x: vertex_options[x], key="delete_vertex")
                if st.button("🗑️ Xóa đỉnh đã chọn", use_container_width=True, type="secondary"):
                    success, msg = app.remove_vertex(selected_vertex)
                    if success: st.success(msg); st.rerun()

            # Xóa tất cả
            if st.button("🗑️ Xóa Tất Cả", use_container_width=True, type="secondary"):
                app.selected_points = []; app.selected_edges = []; app.vertex_names = {}; app.traffic_graph = None; app.algorithm_result = None; st.session_state.vertex_name_input = "Đỉnh 0"; st.rerun()
            
            # Tải cache
            st.markdown("---")
            st.markdown("**📂 Tải từ cache:**")
            if app.loaded_routes:
                 route_options = [r['name'] for r in app.loaded_routes]
                 if route_options:
                     s_route = st.selectbox("Chọn route:", range(len(route_options)), format_func=lambda x: route_options[x])
                     if st.button("📥 Tải route", use_container_width=True):
                         app.load_route(s_route); st.rerun()

            # Export JSON
            if app.selected_points:
                st.markdown("---")
                if st.button("📋 Xuất dữ liệu JSON", use_container_width=True):
                    import json
                    graph_data = {"vertices": [{"id": i, "name": n, "lat": lat, "lon": lon} for i, (lat, lon, n) in enumerate(app.selected_points)], "edges": [{"from": u, "to": v, "weight": w} for u, v, w in app.selected_edges]}
                    st.code(json.dumps(graph_data, indent=2), language='json')

        elif main_tab == "Đường đi thực tế":
             st.markdown("**🚗 Chế độ Đường Thực Tế (Google Maps Style)**")
             
             if app.algorithm_result and app.algorithm_result.get('type') == 'shortest_path':
                 # Hiển thị thông tin cơ bản
                 path = app.algorithm_result.get('path', [])
                 st.success(f"Đã tìm thấy đường đi: {len(path)} đỉnh")
                 
                 st.info("💡 Mặc định thuật toán hiển thị đường thẳng (màu đỏ) để thể hiện kết nối đồ thị.")
                 st.markdown("👉 Nhấn nút dưới đây để chuyển sang chế độ **Đường đi thực tế** (uốn lượn theo bản đồ):")
                 
                 if st.button("▶️ Hiển thị đường thực tế (OSRM)", use_container_width=True, type="primary"):
                     app.show_curved_path = True
                     st.rerun()
                     
                 if app.show_curved_path:
                     st.success("✅ Đang hiển thị đường đi thực tế trên bản đồ!")
             else:
                 st.warning("⚠️ Vui lòng chạy thuật toán **'Đường đi ngắn nhất'** ở tab Thuật toán trước.")
                 st.markdown("Chức năng này chỉ khả dụng sau khi bạn đã tìm được đường đi ngắn nhất giữa 2 điểm.")
    
    with col_map:
        # Tạo và hiển thị bản đồ
        m = app.create_simple_map()
        
        # Hiển thị bản đồ với callback
        map_data = st_folium(
            m,
            width=700,
            height=500,
            returned_objects=["last_clicked", "last_object_clicked"],
            key="main_map"
        )
        
        # Xử lý click trên bản đồ
        if map_data and map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            
            # Kiểm tra xem click mới có khác click cũ không
            current_click = (lat, lon)
            if current_click != app.last_click_coords:
                app.last_click_coords = current_click
                
                # Lưu vị trí đã click
                app.selected_location = (lat, lon)
                st.rerun()

    with col_info:
        st.subheader("ℹ️ Hướng dẫn sử dụng")
        
        st.markdown("""
        **📌 Cách thêm đỉnh:**
        1. Chọn chế độ 'Thêm đỉnh'
        2. Click trên bản đồ để chọn vị trí
        3. Nhập tên đỉnh (tùy chọn)
        4. Bấm nút 'Thêm đỉnh'
        
        **✏️ Cách thêm cạnh:**
        1. Chọn chế độ 'Thêm cạnh'
        2. Chọn 2 đỉnh từ danh sách
        3. Bấm nút 'Thêm cạnh'
        
        **🎯 Chạy thuật toán:**
        1. Chọn tab 'Thuật toán'
        2. Chọn thuật toán cần chạy
        3. Xem hướng dẫn chi tiết
        4. Bấm nút 'Chạy thuật toán'
        
        **📜 Xem lịch sử:**
        1. Chọn tab 'Lịch sử kết quả'
        2. Xem các kết quả đã chạy
        3. Bấm 'Xem kết quả' để hiển thị lại
        
        **📊 Kết quả:**
        - Đường đi/chu trình tìm được
        - Tổng trọng số
        - Danh sách các cạnh đi qua
        - Animation tự động
        """)
        
        st.markdown("---")
        if app.selected_points:
             with st.expander(f"Danh sách {len(app.selected_points)} đỉnh"):
                for i, (lat, lon, name) in enumerate(app.selected_points):
                    st.write(f"**{name}**: ({lat:.4f}, {lon:.4f})")

if __name__ == "__main__":
    show_integrated_traffic_map()