# config_fixed.py - Cấu hình tối ưu FIXED
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import streamlit as st

@dataclass
class AppConfig:
    """Cấu hình toàn bộ ứng dụng - ĐÃ SỬA LỖI DATACLASS"""
    
    # ==================== HIỆU SUẤT ====================
    MAX_EDGES_DISPLAY: int = 200
    MAX_VERTICES: int = 50
    CLICK_DEBOUNCE_MS: int = 300
    SAMPLE_SIZE: int = 1000
    MEMORY_CACHE_SIZE: int = 50
    
    # ==================== BẢN ĐỒ ====================
    DEFAULT_LOCATION: Tuple[float, float] = (10.7769, 106.7009)
    DEFAULT_ZOOM: int = 12
    
    # Sử dụng field() cho các giá trị mutable
    OSM_LAYOUT_CONFIG: Dict = field(default_factory=lambda: {
        'network_type': 'drive',
        'simplify': True,
        'retain_all': False,
        'truncate_by_edge': True
    })
    
    # ==================== THUẬT TOÁN ====================
    ALGORITHMS: List[str] = field(default_factory=lambda: [
        "shortest_path",
        "mst_prim", 
        "mst_kruskal",
        "bfs",
        "dfs",
        "eulerian_path",
        "graph_coloring",
        "connected_components"
    ])
    
    # ==================== CACHE ====================
    CACHE_DIR: str = "map_cache"
    GRAPH_CACHE_DIR: str = "graph_cache"
    
    # ==================== MÀU SẮC ====================
    COLOR_PALETTE: Dict = field(default_factory=lambda: {
        'vertex': '#4a86e8',
        'vertex_highlight': '#ff9900',
        'edge': '#333333',
        'edge_highlight': '#ff3300',
        'mst_edge': '#6aa84f',
        'path': '#e06666',
        'visited': '#93c47d',
        'bipartite_a': '#ff9999',
        'bipartite_b': '#99ccff',
        'flow_edge': '#ff9900',
        'osm_edge': '#3388ff',
        'user_edge': '#00cc66'
    })
    
    def __post_init__(self):
        """Khởi tạo sau khi tạo object"""
        # Đảm bảo thư mục cache tồn tại
        self.ensure_directories()
    
    @classmethod
    def ensure_directories(cls):
        """Tạo thư mục cache nếu chưa có"""
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
        os.makedirs(cls.GRAPH_CACHE_DIR, exist_ok=True)
    
    @classmethod
    def get_instance(cls):
        """Lấy instance duy nhất của config"""
        if 'app_config' not in st.session_state:
            st.session_state.app_config = AppConfig()
        return st.session_state.app_config

# Tạo instance
config = AppConfig.get_instance()

# Danh sách quận/huyện TP.HCM (đặt bên ngoài class để tránh lỗi)
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
    "TP. Thủ Đức": "Thu Duc City, Ho Chi Minh City, Vietnam",
    "Huyện Bình Chánh": "Binh Chanh District, Ho Chi Minh City, Vietnam",
    "Huyện Củ Chi": "Cu Chi District, Ho Chi Minh City, Vietnam",
    "Huyện Nhà Bè": "Nha Be District, Ho Chi Minh City, Vietnam",
    "Huyện Hóc Môn": "Hoc Mon District, Ho Chi Minh City, Vietnam",
    "Huyện Cần Giờ": "Can Gio District, Ho Chi Minh City, Vietnam",
    "Toàn Thành Phố": "Ho Chi Minh City, Vietnam"
}