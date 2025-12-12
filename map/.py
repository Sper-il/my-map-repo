import streamlit as st
import osmnx as ox
import folium
from streamlit_folium import st_folium
import pandas as pd
import warnings
import pickle
import os
import hashlib
import json
from datetime import datetime, timedelta
import numpy as np
import math
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

# Ẩn cảnh báo
warnings.filterwarnings('ignore')

# Cấu hình trang web (title, layout)
st.set_page_config(
    page_title="Bản Đồ Giao Thông TP.HCM",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ẩn các phần tử mặc định của Streamlit (Menu, Footer)
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Cấu hình OSMnx
ox.settings.timeout = 1000
ox.settings.use_cache = True
ox.settings.log_console = False

# Tạo thư mục cache nếu chưa tồn tại
CACHE_DIR = "map_cache"
MAP_CACHE_DIR = os.path.join(CACHE_DIR, "folium_maps")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(MAP_CACHE_DIR, exist_ok=True)

# DANH SÁCH QUẬN/HUYỆN
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
    "Toàn Thành Phố (Rất Chậm 🐢)": "Ho Chi Minh City, Vietnam"
}

# Biến toàn cục để cache trong bộ nhớ
_MEMORY_CACHE = {}
_FOLIUM_MAP_CACHE = {}
_PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL

# Hằng số cho tính toán nhanh
_EARTH_RADIUS = 6371000
_DEG_TO_RAD = math.pi / 180.0


@lru_cache(maxsize=1000)
def haversine_distance(lat1, lon1, lat2, lon2):
    """Tính khoảng cách Haversine với caching"""
    lat1_rad = lat1 * _DEG_TO_RAD
    lon1_rad = lon1 * _DEG_TO_RAD
    lat2_rad = lat2 * _DEG_TO_RAD
    lon2_rad = lon2 * _DEG_TO_RAD

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return _EARTH_RADIUS * c


def calculate_route_length_fast(coords):
    """Tính chiều dài thực tế của tuyến đường từ tọa độ"""
    if len(coords) < 2:
        return 0.0

    total_distance = 0.0
    prev_lat, prev_lon = coords[0]
    for i in range(1, len(coords)):
        curr_lat, curr_lon = coords[i]
        total_distance += haversine_distance(prev_lat, prev_lon, curr_lat, curr_lon)
        prev_lat, prev_lon = curr_lat, curr_lon

    return total_distance


def calculate_total_length_parallel(edges, max_workers=4):
    """Tính tổng chiều dài của tất cả các tuyến đường sử dụng parallel processing"""
    if len(edges) == 0:
        return 0.0

    total_length_m = 0.0

    if len(edges) > 1000:
        progress_bar = st.progress(0)

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for idx, row in edges.iterrows():
                if hasattr(row.geometry, 'coords'):
                    try:
                        coords = [(lat, lon) for lon, lat in row.geometry.coords]
                        if len(coords) >= 2:
                            futures.append(executor.submit(calculate_route_length_fast, coords))
                    except:
                        continue

            for i, future in enumerate(as_completed(futures)):
                try:
                    total_length_m += future.result()
                except Exception:
                    continue

                if len(edges) > 1000 and (i % 100 == 0 or i == len(futures) - 1):
                    progress = (i + 1) / len(futures)
                    progress_bar.progress(progress)

    finally:
        if len(edges) > 1000:
            progress_bar.empty()

    return total_length_m / 1000


class CacheManager:
    """Quản lý cache cho ứng dụng với tối ưu hóa tốc độ"""

    @staticmethod
    def get_cache_key(place_name):
        """Tạo key cache từ tên địa điểm"""
        cache_string = f"{place_name}"
        return hashlib.md5(cache_string.encode()).hexdigest()

    @staticmethod
    def get_folium_cache_key(place_name, edges_hash=None):
        """Tạo key cache cho bản đồ Folium"""
        if edges_hash:
            cache_string = f"folium_{place_name}_{edges_hash}"
        else:
            cache_string = f"folium_{place_name}"
        return hashlib.md5(cache_string.encode()).hexdigest()

    @staticmethod
    def get_cache_info_path():
        """Lấy đường dẫn file thông tin cache"""
        return os.path.join(CACHE_DIR, "cache_info.json")

    @staticmethod
    def get_cache_file_path(cache_key, compressed=True):
        """Lấy đường dẫn file cache dữ liệu"""
        if compressed:
            return os.path.join(CACHE_DIR, f"{cache_key}.pkl.gz")
        else:
            return os.path.join(CACHE_DIR, f"{cache_key}.pkl")

    @staticmethod
    def get_folium_cache_path(cache_key):
        """Lấy đường dẫn file cache bản đồ Folium"""
        return os.path.join(MAP_CACHE_DIR, f"{cache_key}.html")

    @staticmethod
    def get_metadata_file_path(cache_key):
        """Lấy đường dẫn file metadata"""
        return os.path.join(CACHE_DIR, f"{cache_key}_meta.json")

    @staticmethod
    def load_cache_info():
        """Tải thông tin cache từ file"""
        info_path = CacheManager.get_cache_info_path()
        if os.path.exists(info_path):
            try:
                with open(info_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    @staticmethod
    def save_cache_info(cache_info):
        """Lưu thông tin cache vào file"""
        info_path = CacheManager.get_cache_info_path()
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(cache_info, f, ensure_ascii=False, indent=2)

    @staticmethod
    def is_cache_valid(cache_key, max_age_days=30):
        """Kiểm tra cache còn hợp lệ không"""
        meta_path = CacheManager.get_metadata_file_path(cache_key)
        if not os.path.exists(meta_path):
            return False

        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            created_time = datetime.fromisoformat(metadata.get('created_at', '2000-01-01'))
            age = datetime.now() - created_time

            return age.days < max_age_days
        except:
            return False

    @staticmethod
    def is_folium_cache_valid(cache_key, max_age_days=30):
        """Kiểm tra cache bản đồ Folium còn hợp lệ không"""
        cache_path = CacheManager.get_folium_cache_path(cache_key)
        if not os.path.exists(cache_path):
            return False

        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
            age = datetime.now() - mod_time
            return age.days < max_age_days
        except:
            return False

    @staticmethod
    def update_cache_metadata(cache_key, place_name, edges_count, total_length_km, compressed=True):
        """Cập nhật metadata cho cache"""
        cache_file_path = CacheManager.get_cache_file_path(cache_key, compressed)
        file_size_kb = 0
        if os.path.exists(cache_file_path):
            file_size_kb = os.path.getsize(cache_file_path) / 1024

        metadata = {
            'place_name': place_name,
            'edges_count': edges_count,
            'total_length_km': total_length_km,
            'created_at': datetime.now().isoformat(),
            'size_kb': file_size_kb,
            'compressed': compressed
        }

        meta_path = CacheManager.get_metadata_file_path(cache_key)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        cache_info = CacheManager.load_cache_info()
        cache_info[cache_key] = {
            'name': place_name,
            'count': edges_count,
            'total_length_km': total_length_km,
            'created': metadata['created_at'],
            'size_kb': metadata['size_kb'],
            'compressed': compressed
        }
        CacheManager.save_cache_info(cache_info)

    @staticmethod
    def save_cache_data(cache_key, edges, compressed=True):
        """Lưu dữ liệu cache với tối ưu hóa"""
        cache_file_path = CacheManager.get_cache_file_path(cache_key, compressed)

        try:
            if compressed:
                with gzip.open(cache_file_path, 'wb') as f:
                    pickle.dump(edges, f, protocol=_PICKLE_PROTOCOL)
            else:
                with open(cache_file_path, 'wb') as f:
                    pickle.dump(edges, f, protocol=_PICKLE_PROTOCOL)

            return True
        except Exception as e:
            st.warning(f"⚠️ Lỗi khi lưu cache: {e}")
            return False

    @staticmethod
    def load_cache_data(cache_key, compressed=True):
        """Tải dữ liệu cache với tối ưu hóa"""
        cache_file_path = CacheManager.get_cache_file_path(cache_key, compressed)

        if not os.path.exists(cache_file_path):
            return None

        try:
            if compressed:
                with gzip.open(cache_file_path, 'rb') as f:
                    return pickle.load(f)
            else:
                with open(cache_file_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            try:
                os.remove(cache_file_path)
                meta_path = CacheManager.get_metadata_file_path(cache_key)
                if os.path.exists(meta_path):
                    os.remove(meta_path)
            except:
                pass
            st.warning(f"⚠️ Cache bị lỗi, đã xóa và sẽ tải lại: {e}")
            return None

    @staticmethod
    def save_folium_map(cache_key, folium_map):
        """Lưu bản đồ Folium dưới dạng HTML"""
        try:
            cache_path = CacheManager.get_folium_cache_path(cache_key)
            folium_map.save(cache_path)

            meta_path = os.path.join(MAP_CACHE_DIR, f"{cache_key}_meta.json")
            metadata = {
                'created_at': datetime.now().isoformat(),
                'size_kb': os.path.getsize(cache_path) / 1024
            }
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            st.warning(f"⚠️ Lỗi khi lưu bản đồ: {e}")
            return False

    @staticmethod
    def load_folium_map(cache_key):
        """Tải bản đồ Folium từ cache HTML"""
        try:
            cache_path = CacheManager.get_folium_cache_path(cache_key)

            if not os.path.exists(cache_path):
                return None

            with open(cache_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            return html_content
        except Exception as e:
            st.warning(f"⚠️ Lỗi khi đọc bản đồ: {e}")
            return None

    @staticmethod
    def get_edges_hash(edges):
        """Tạo hash cho edges để xác định xem bản đồ có cần vẽ lại không"""
        if edges is None or edges.empty:
            return "empty"

        try:
            hash_data = {
                'shape': edges.shape,
                'total_length': edges.attrs.get('total_length_km', 0) if hasattr(edges, 'attrs') else 0,
                'columns': list(edges.columns) if hasattr(edges, 'columns') else [],
                'count': len(edges)
            }

            return hashlib.md5(json.dumps(hash_data, sort_keys=True, default=str).encode()).hexdigest()
        except:
            return "error"


def get_graph_data(place_name):
    """Lấy dữ liệu đồ thị từ cache hoặc OSM - Luôn lấy chi tiết nhất"""
    cache_key = CacheManager.get_cache_key(place_name)
    compressed = True

    # 1. Kiểm tra cache trong bộ nhớ
    if cache_key in _MEMORY_CACHE:
        edges, metadata = _MEMORY_CACHE[cache_key]
        st.info(f"⚡ Đang tải từ bộ nhớ: {metadata['edges_count']} tuyến đường")
        return edges

    # 2. Kiểm tra cache trên đĩa
    if CacheManager.is_cache_valid(cache_key):
        try:
            with st.spinner("🚀 Đang đọc dữ liệu từ cache (nhanh)..."):
                edges = CacheManager.load_cache_data(cache_key, compressed)

                if edges is not None:
                    meta_path = CacheManager.get_metadata_file_path(cache_key)
                    if os.path.exists(meta_path):
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    else:
                        total_length_km = calculate_total_length_parallel(edges)
                        metadata = {
                            'edges_count': len(edges),
                            'total_length_km': total_length_km
                        }

                    _MEMORY_CACHE[cache_key] = (edges, metadata)

                    st.success(f"✅ Đã tải từ cache: {len(edges)} tuyến đường")
                    return edges
        except Exception as e:
            st.warning(f"⚠️ Lỗi khi đọc cache: {e}. Đang tải mới từ internet...")

    # 3. Nếu không có cache hợp lệ, tải từ OSM
    return download_and_cache_data(place_name, cache_key, compressed)


def download_and_cache_data(place_name, cache_key, compressed=True):
    """Tải dữ liệu từ OSM và lưu vào cache - LUÔN LẤY CHI TIẾT NHẤT"""

    # LUÔN sử dụng bộ lọc chi tiết nhất cho tất cả khu vực
    custom_filter = '["highway"~"motorway|trunk|primary|secondary|tertiary|residential|service|living_street|unclassified|pedestrian|footway|path"]'

    if "Ho Chi Minh City, Vietnam" in place_name:
        st.info("🌆 Đang tải dữ liệu chi tiết cho toàn TP.HCM...")
    else:
        st.info("🔍 Đang tải dữ liệu chi tiết (tất cả loại đường)...")

    try:
        with st.spinner(f"🌐 Đang tải dữ liệu từ OpenStreetMap cho {place_name}..."):
            if custom_filter:
                G = ox.graph_from_place(
                    place_name,
                    network_type='drive',
                    simplify=True,
                    custom_filter=custom_filter
                )
            else:
                G = ox.graph_from_place(
                    place_name,
                    network_type='drive',
                    simplify=True
                )

        nodes, edges = ox.graph_to_gdfs(G)

        # Tính tổng chiều dài các tuyến đường với parallel processing
        with st.spinner("📏 Đang tính toán chiều dài đường..."):
            total_length_km = calculate_total_length_parallel(edges)

        # Lưu vào cache
        if CacheManager.save_cache_data(cache_key, edges, compressed):
            CacheManager.update_cache_metadata(cache_key, place_name, len(edges), total_length_km, compressed)

            metadata = {
                'place_name': place_name,
                'edges_count': len(edges),
                'total_length_km': total_length_km,
                'created_at': datetime.now().isoformat(),
                'size_kb': os.path.getsize(CacheManager.get_cache_file_path(cache_key, compressed)) / 1024,
                'compressed': compressed
            }
            _MEMORY_CACHE[cache_key] = (edges, metadata)

            st.success(f"💾 Đã lưu cache: {len(edges)} tuyến đường, {total_length_km:.1f} km")

        return edges

    except Exception as e:
        st.error(f"❌ Lỗi khi tải dữ liệu: {e}")
        return None


class HCMTrafficMap:
    def __init__(self):
        self.cache_info = CacheManager.load_cache_info()
        self.current_edges_hash = None

    def create_sidebar(self):
        st.sidebar.title("⚙️ Tùy Chọn")

        # Hiển thị thông tin cache
        self.display_cache_info()

        # Thêm nút xóa cache
        st.sidebar.markdown("---")
        col1, col2, col3 = st.sidebar.columns(3)

        with col1:
            if st.button("🗑️ Xóa tất cả", help="Xóa tất cả dữ liệu đã lưu"):
                self.clear_all_cache()

        with col2:
            if st.button("🗑️ Cache Q1", help="Chỉ xóa cache của Quận 1"):
                self.clear_district1_cache()

        with col3:
            if st.button("🗑️ Bản đồ", help="Xóa cache bản đồ Folium"):
                self.clear_folium_cache()

        # Tạo danh sách lựa chọn + Mục tùy chỉnh
        options = list(DISTRICTS.keys()) + ["🔍 Nhập địa điểm tùy chỉnh..."]

        selection = st.sidebar.selectbox(
            "Chọn khu vực:",
            options,
            index=0
        )

        # Hiển thị thông tin đặc biệt cho Quận 2
        if selection == "Quận 2":
            st.sidebar.markdown("---")
            st.sidebar.info("""
            **Thông tin Quận 2:**
            - Trung tâm hành chính mới
            - Khu đô thị Thủ Thiêm
            - Nhiều đường cao tốc mới
            - Kết nối với Quận 1 qua cầu Thủ Thiêm
            """)

        # Tùy chọn tải lại bản đồ
        st.sidebar.markdown("---")
        self.force_reload = st.sidebar.checkbox(
            "🔄 Tải lại bản đồ",
            value=False,
            help="Buộc tải lại bản đồ từ đầu (bỏ qua cache bản đồ)"
        )

        # Xử lý logic chọn
        if selection == "🔍 Nhập địa điểm tùy chỉnh...":
            st.sidebar.markdown("---")
            custom_input = st.sidebar.text_input(
                "Gõ tên địa điểm (VD: Thu Duc City, Sân bay Tân Sơn Nhất):",
                "Ben Thanh Market"
            )

            display_name = custom_input

            input_lower = custom_input.lower()
            if "vietnam" not in input_lower and "hcmc" not in input_lower and "hồ chí minh" not in input_lower:
                place_query = custom_input + ", Ho Chi Minh City, Vietnam"
                st.sidebar.caption("Đã tự động thêm `, Ho Chi Minh City, Vietnam` vào tìm kiếm.")
            else:
                place_query = custom_input

            return place_query, display_name
        else:
            return DISTRICTS[selection], selection

    def display_cache_info(self):
        """Hiển thị thông tin cache trong sidebar"""
        total_size = sum(info.get('size_kb', 0) for info in self.cache_info.values())
        total_length = sum(info.get('total_length_km', 0) for info in self.cache_info.values())
        compressed_count = sum(1 for info in self.cache_info.values() if info.get('compressed', False))

        folium_cache_count = 0
        folium_cache_size = 0
        if os.path.exists(MAP_CACHE_DIR):
            folium_files = [f for f in os.listdir(MAP_CACHE_DIR) if f.endswith('.html')]
            folium_cache_count = len(folium_files)
            for file in folium_files:
                folium_cache_size += os.path.getsize(os.path.join(MAP_CACHE_DIR, file)) / 1024

        st.sidebar.markdown(f"### 📊 Thông tin Cache")
        st.sidebar.markdown(f"**Số khu vực:** {len(self.cache_info)}")
        st.sidebar.markdown(f"**Số bản đồ:** {folium_cache_count}")
        st.sidebar.markdown(f"**Tổng dung lượng:** {(total_size + folium_cache_size):.1f} KB")
        st.sidebar.markdown(f"**Tổng chiều dài:** {total_length:.1f} km")

        if self.cache_info:
            st.sidebar.markdown("**Top 5 cache lớn nhất:**")
            sorted_cache = sorted(self.cache_info.items(),
                                  key=lambda x: x[1].get('size_kb', 0),
                                  reverse=True)[:5]

            for cache_key, info in sorted_cache:
                name = info.get('name', 'Unknown')[:20] + "..." if len(info.get('name', '')) > 20 else info.get('name',
                                                                                                                'Unknown')
                count = info.get('count', 0)
                length = info.get('total_length_km', 0)
                size = info.get('size_kb', 0)
                st.sidebar.caption(f"• {name}: {count} đường, {length:.1f} km, {size:.1f} KB")

            if len(self.cache_info) > 5:
                st.sidebar.caption(f"... và {len(self.cache_info) - 5} khu vực khác")

    def clear_all_cache(self):
        """Xóa tất cả file cache trong thư mục cache"""
        try:
            global _MEMORY_CACHE, _FOLIUM_MAP_CACHE
            _MEMORY_CACHE.clear()
            _FOLIUM_MAP_CACHE.clear()

            cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith(('.pkl', '.json', '.gz'))]
            deleted_count = 0

            for file in cache_files:
                try:
                    os.remove(os.path.join(CACHE_DIR, file))
                    deleted_count += 1
                except:
                    pass

            if os.path.exists(MAP_CACHE_DIR):
                map_files = [f for f in os.listdir(MAP_CACHE_DIR) if f.endswith(('.html', '.json'))]
                for file in map_files:
                    try:
                        os.remove(os.path.join(MAP_CACHE_DIR, file))
                        deleted_count += 1
                    except:
                        pass

            CacheManager.save_cache_info({})

            st.sidebar.success(f"✅ Đã xóa {deleted_count} file cache")
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"❌ Lỗi khi xóa cache: {e}")

    def clear_district1_cache(self):
        """Xóa cache của Quận 1"""
        try:
            district1_key = CacheManager.get_cache_key("District 1, Ho Chi Minh City, Vietnam")

            global _MEMORY_CACHE, _FOLIUM_MAP_CACHE
            if district1_key in _MEMORY_CACHE:
                del _MEMORY_CACHE[district1_key]

            folium_keys = [k for k in _FOLIUM_MAP_CACHE.keys() if district1_key in k]
            for f_key in folium_keys:
                del _FOLIUM_MAP_CACHE[f_key]

            cache_files = os.listdir(CACHE_DIR)
            deleted_count = 0

            for file in cache_files:
                file_path = os.path.join(CACHE_DIR, file)
                if file.endswith(('.pkl', '.json', '.gz')):
                    if district1_key in file:
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                        except:
                            pass

            if os.path.exists(MAP_CACHE_DIR):
                map_files = os.listdir(MAP_CACHE_DIR)
                for file in map_files:
                    file_path = os.path.join(MAP_CACHE_DIR, file)
                    if district1_key in file:
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                        except:
                            pass

            cache_info = CacheManager.load_cache_info()
            if district1_key in cache_info:
                del cache_info[district1_key]
            CacheManager.save_cache_info(cache_info)

            st.sidebar.success(f"✅ Đã xóa {deleted_count} file cache Quận 1")
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"❌ Lỗi khi xóa cache Quận 1: {e}")

    def clear_folium_cache(self):
        """Xóa cache bản đồ Folium"""
        try:
            global _FOLIUM_MAP_CACHE
            _FOLIUM_MAP_CACHE.clear()

            if os.path.exists(MAP_CACHE_DIR):
                map_files = [f for f in os.listdir(MAP_CACHE_DIR) if f.endswith(('.html', '.json'))]
                deleted_count = 0

                for file in map_files:
                    try:
                        os.remove(os.path.join(MAP_CACHE_DIR, file))
                        deleted_count += 1
                    except:
                        pass

                st.sidebar.success(f"✅ Đã xóa {deleted_count} file cache bản đồ")
                st.rerun()
            else:
                st.sidebar.info("ℹ️ Không có cache bản đồ để xóa")

        except Exception as e:
            st.sidebar.error(f"❌ Lỗi khi xóa cache bản đồ: {e}")

    def load_data(self, place_query, display_name):
        try:
            with st.spinner(f"🚀 Đang tải dữ liệu chi tiết: {display_name}..."):
                edges = get_graph_data(place_query)

            if edges is not None:
                cache_key = CacheManager.get_cache_key(place_query)
                if cache_key in _MEMORY_CACHE:
                    edges_data, metadata = _MEMORY_CACHE[cache_key]
                    total_length_km = metadata.get('total_length_km', 0)
                else:
                    with st.spinner("📏 Đang tính toán chiều dài..."):
                        total_length_km = calculate_total_length_parallel(edges)

                # Thống kê đơn giản
                if not edges.empty and 'highway' in edges.columns:
                    st.sidebar.markdown("---")
                    st.sidebar.markdown("### 📈 Thống kê đường")

                    # Tổng số đường
                    st.sidebar.caption(f"**Tổng số tuyến đường:** {len(edges)}")

                    # Tổng chiều dài
                    st.sidebar.caption(f"**Tổng chiều dài:** {total_length_km:.1f} km")

                st.success(f"✅ Đã tải: {display_name} ({len(edges)} tuyến đường, {total_length_km:.1f} km)")
                st.info("🔍 Đang ở chế độ chi tiết (tất cả loại đường)")

                edges.attrs['total_length_km'] = total_length_km
                self.current_edges_hash = CacheManager.get_edges_hash(edges)

            return edges

        except Exception as e:
            st.error(f"❌ Không tìm thấy địa điểm '{display_name}'!")
            st.info(f"💡 Lỗi chi tiết: {e}")
            st.info("💡 Lỗi này xảy ra khi OpenStreetMap không nhận ra tên bạn gõ. Hãy thử gõ tiếng Anh không dấu nhé!")
            return None

    def create_map(self, edges, place_query, display_name, force_reload=False):
        """Tạo bản đồ Folium, sử dụng cache nếu có"""

        folium_cache_key = CacheManager.get_folium_cache_key(
            place_query,
            self.current_edges_hash
        )

        global _FOLIUM_MAP_CACHE
        if not force_reload and folium_cache_key in _FOLIUM_MAP_CACHE:
            st.info(f"⚡ Đang tải bản đồ từ bộ nhớ...")
            return _FOLIUM_MAP_CACHE[folium_cache_key]

        if not force_reload and CacheManager.is_folium_cache_valid(folium_cache_key):
            try:
                with st.spinner("🚀 Đang tải bản đồ từ cache (rất nhanh)..."):
                    html_content = CacheManager.load_folium_map(folium_cache_key)
                    if html_content:
                        m = folium.Map(location=[10.7769, 106.7009], zoom_start=14)
                        _FOLIUM_MAP_CACHE[folium_cache_key] = m
                        m._html = html_content

                        meta_path = os.path.join(MAP_CACHE_DIR, f"{folium_cache_key}_meta.json")
                        if os.path.exists(meta_path):
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                                m.cache_size_kb = metadata.get('size_kb', 0)
                        else:
                            m.cache_size_kb = 0

                        st.success(f"✅ Đã tải bản đồ từ cache ({m.cache_size_kb:.1f} KB)")
                        return m
            except Exception as e:
                st.warning(f"⚠️ Lỗi khi đọc cache bản đồ: {e}. Đang tạo bản đồ mới...")

        return self._create_new_map(edges, place_query, display_name, folium_cache_key)

    def _create_new_map(self, edges, place_query, display_name, folium_cache_key):
        """Tạo bản đồ mới và lưu vào cache"""
        if not edges.empty:
            bounds = edges.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2
        else:
            center_lat, center_lon = 10.7769, 106.7009

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=14,
            tiles='OpenStreetMap',
            prefer_canvas=True
        )

        # MÀU DUY NHẤT CHO TẤT CẢ CÁC LOẠI ĐƯỜNG
        UNIFIED_COLOR = '#3388ff'  # Màu xanh dương

        count = 0
        max_edges = 100000  # Giới hạn cao cho chi tiết
        total_displayed_length = 0.0

        if len(edges) > 1000:
            progress_bar = st.progress(0)
        total_edges = min(len(edges), max_edges)

        for idx, row in edges.iterrows():
            if count >= max_edges:
                break
            try:
                hw = row.get('highway')
                if isinstance(hw, list):
                    hw = hw[0] if hw else 'default'
                elif not hw:
                    hw = 'default'

                # Điều chỉnh độ dày đường dựa trên loại đường
                if hw in ['motorway', 'trunk']:
                    weight = 4.0
                elif hw == 'primary':
                    weight = 3.5
                elif hw == 'secondary':
                    weight = 3.0
                elif hw == 'tertiary':
                    weight = 2.5
                elif hw in ['residential', 'living_street']:
                    weight = 2.0
                elif hw in ['service', 'unclassified']:
                    weight = 1.5
                elif hw in ['pedestrian', 'footway']:
                    weight = 1.0
                else:
                    weight = 1.5

                if hasattr(row.geometry, 'coords'):
                    coords = [(lat, lon) for lon, lat in row.geometry.coords]
                    route_length_m = calculate_route_length_fast(coords)
                    total_displayed_length += route_length_m

                    if route_length_m >= 1000:
                        length_display = f"{route_length_m / 1000:.2f} km"
                    else:
                        length_display = f"{route_length_m:.0f} m"

                    # Tạo popup với thông tin chi tiết
                    popup_text = f"""
                    <div style="font-family: Arial; font-size: 12px; min-width: 200px;">
                        <b>📍 Tên đường:</b> {row.get('name', 'Không có tên')}<br>
                        <b>🚦 Loại đường:</b> {hw}<br>
                        <b>📏 Chiều dài:</b> {length_display}<br>
                        <b>🔢 Số điểm:</b> {len(coords)}
                    </div>
                    """

                    folium.PolyLine(
                        locations=coords,
                        color=UNIFIED_COLOR,
                        weight=weight,
                        opacity=0.8,
                        popup=folium.Popup(popup_text, max_width=300),
                        tooltip=f"{row.get('name', 'Đường không tên')} ({hw}) - {length_display}"
                    ).add_to(m)
                    count += 1

                    if len(edges) > 1000 and (count % 1000 == 0 or count == total_edges):
                        progress = count / total_edges
                        progress_bar.progress(progress)

            except Exception:
                continue

        if len(edges) > 1000:
            progress_bar.empty()

        # THÊM ĐIỂM ĐẶC BIỆT CHO TỪNG KHU VỰC
        landmarks = []

        if "District 1" in place_query or display_name == "Quận 1":
            landmarks = [
                ("🏪 Chợ Bến Thành", 10.772, 106.698),
                ("🎭 Nhà hát Thành phố", 10.777, 106.703),
                ("📮 Bưu điện Trung tâm", 10.780, 106.699),
                ("🏛️ Dinh Độc Lập", 10.777, 106.695),
                ("🚢 Bến Bạch Đằng", 10.773, 106.706),
                ("🕌 Nhà thờ Đức Bà", 10.780, 106.699)
            ]
        elif "District 2" in place_query or display_name == "Quận 2":
            landmarks = [
                ("🌉 Cầu Thủ Thiêm", 10.783, 106.720),
                ("🏢 Trung tâm hành chính", 10.787, 106.730),
                ("🏙️ Khu đô thị Thủ Thiêm", 10.775, 106.725),
                ("🛒 Vincom Mega Mall", 10.802, 106.747),
                ("🏨 Riverside", 10.795, 106.735)
            ]

        for name, lat, lon in landmarks:
            folium.Marker(
                location=[lat, lon],
                popup=name,
                icon=folium.Icon(color='red', icon='info-sign', prefix='fa')
            ).add_to(m)

        # Thông tin hiển thị
        m.total_displayed_length_km = total_displayed_length / 1000
        m.total_displayed_edges = count

        # Lưu bản đồ vào cache
        if CacheManager.save_folium_map(folium_cache_key, m):
            st.info(f"💾 Đã lưu bản đồ vào cache")
            _FOLIUM_MAP_CACHE[folium_cache_key] = m

        return m


def main():
    st.markdown("""
    <h1 style='text-align: center; color: #1f77b4;'>
    🗺️ BẢN ĐỒ GIAO THÔNG TP.HCM
    </h1>
    <p style='text-align: center; color: #666;'>
    Phiên bản đơn giản - Tất cả đường màu xanh dương - Chi tiết nhất
    </p>
    """, unsafe_allow_html=True)

    # Thông tin phiên bản
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🚀 Phiên bản đơn giản**")
    st.sidebar.caption("• Luôn chi tiết nhất")
    st.sidebar.caption("• Màu đường duy nhất: xanh dương")
    st.sidebar.caption("• Cache nén GZIP")
    st.sidebar.caption("• Parallel processing")

    app = HCMTrafficMap()

    # 1. Menu chọn
    place_query, display_name = app.create_sidebar()

    # 2. Tải & Vẽ
    if place_query:
        edges = app.load_data(place_query, display_name)
        if edges is not None:
            traffic_map = app.create_map(edges, place_query, display_name, app.force_reload)

            if hasattr(traffic_map, '_html'):
                st.components.v1.html(traffic_map._html, width=1400, height=700)
            else:
                st_folium(traffic_map, width=1400, height=700, returned_objects=[])

            # Lấy thông tin tổng chiều dài
            total_length_km = edges.attrs.get('total_length_km', 0)
            displayed_length_km = getattr(traffic_map, 'total_displayed_length_km', 0)
            displayed_edges = getattr(traffic_map, 'total_displayed_edges', 0)

            if hasattr(traffic_map, 'cache_size_kb'):
                st.sidebar.markdown("---")
                st.sidebar.markdown(f"**📁 Cache bản đồ:** {traffic_map.cache_size_kb:.1f} KB")

            # Hiển thị thông tin chi tiết
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"📍 Khu vực: {display_name}")
            with col2:
                st.info(f"📏 Tổng đường: {len(edges)} tuyến")
            with col3:
                st.info(f"📐 Tổng chiều dài: {total_length_km:.1f} km")

            # Màu đường thông báo
            st.info(f"🎨 Tất cả đường hiển thị màu: **#3388ff** (xanh dương)")

            # Thông tin về số lượng đã hiển thị
            if displayed_edges < len(edges):
                st.warning(
                    f"⚠️ Hiển thị {displayed_edges}/{len(edges)} tuyến đường ({displayed_length_km:.1f}/{total_length_km:.1f} km) để đảm bảo hiệu suất")

            # Thông tin đặc biệt cho từng khu vực
            if display_name == "Quận 2":
                st.info("""
                **🏙️ QUẬN 2 - KHU ĐÔ THỊ MỚI:**
                - Trung tâm hành chính Thủ Thiêm
                - Nhiều dự án cao cấp
                - Kết nối giao thông hiện đại
                - Cầu Thủ Thiêm kết nối Quận 1
                """)

            # Nút tải bản đồ về máy
            st.sidebar.markdown("---")
            if st.sidebar.button("💾 Tải bản đồ về máy"):
                safe_name = "".join(c for c in display_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                file_name = f"map_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                file_path = os.path.join(CACHE_DIR, file_name)

                try:
                    traffic_map.save(file_path)
                    st.sidebar.success(f"✅ Đã lưu: {file_name}")
                    with open(file_path, "rb") as file:
                        st.sidebar.download_button(
                            label="📥 Tải xuống ngay",
                            data=file,
                            file_name=file_name,
                            mime="text/html"
                        )
                except Exception as e:
                    st.sidebar.error(f"❌ Lỗi: {e}")


if __name__ == "__main__":
    main()