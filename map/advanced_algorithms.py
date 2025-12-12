import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
import folium
from streamlit_folium import st_folium
import requests
import polyline 

matplotlib.use('Agg')

# --- IMPORT MODULE ---
# Import file bản đồ tích hợp (File quan trọng nhất chứa V4.7)
from integrated_traffic_map import show_integrated_traffic_map

# Class hỗ trợ routing (Giữ nguyên logic cũ như yêu cầu)
class RealTimeRouting:
    def __init__(self):
        self.osm_base_url = "https://router.project-osrm.org/route/v1/"
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
    
    def format_distance(self, meters):
        if meters < 1000: return f"{meters:.0f} mét"
        else: return f"{meters/1000:.2f} km"
    
    def format_duration(self, seconds):
        if seconds < 60: return f"{seconds:.0f} giây"
        elif seconds < 3600: return f"{seconds/60:.0f} phút"
        else:
            h = int(seconds / 3600)
            m = int((seconds % 3600) / 60)
            return f"{h} giờ {m} phút"

def setup_page():
    st.set_page_config(
        page_title="Ứng dụng Lý thuyết Đồ thị", 
        page_icon="🗺️", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    # CSS tùy chỉnh giao diện
    st.markdown("""
    <style>
        .main-header {
            text-align: center; color: white; padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px; margin-bottom: 20px;
        }
        .traffic-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 15px; border-radius: 10px; border-left: 5px solid #FF6B6B;
        }
        /* Ẩn mặc định của Streamlit và Footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def init_session_state():
    """Khởi tạo session state để tránh lỗi reset biến"""
    if 'routing_engine' not in st.session_state:
        st.session_state.routing_engine = RealTimeRouting()

def create_sidebar():
    st.sidebar.markdown("""
    <div style='text-align: center; padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;'>
        <h3 style='color: white; margin: 0;'>📊 ỨNG DỤNG</h3>
        <p style='color: white; margin: 0; font-size: 14px;'>Lý Thuyết Đồ Thị & Bản Đồ</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    section = st.sidebar.radio("**CHỌN PHẦN CHÍNH:**", ["🏠 Trang chủ", "🗺️ Bản đồ Tích hợp"])
    st.sidebar.markdown("---")
    
    st.sidebar.markdown(f"*Phiên bản: 5.0 Real-Road & Animation*")
    st.sidebar.markdown(f"*Thời gian: {datetime.now().strftime('%H:%M')}*")
    
    return section

def show_home_page():
    st.markdown("""
    <div class="main-header">
        <h1>📊 ỨNG DỤNG LÝ THUYẾT ĐỒ THỊ</h1>
        <p style="color:white;">Tích hợp bản đồ & Tìm đường thực tế</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎯 Chức năng:")
        st.markdown("- **Vẽ đồ thị:** Thêm đỉnh/cạnh trực quan.\n- **Thuật toán:** Dijkstra, Prim, Kruskal, Fleury, Hierholzer.\n- **Animation:** Minh họa thuật toán tự động trên đường thật.")
        if st.button("🗺️ Mở Bản đồ Tích hợp", type="primary"):
            st.info("Vui lòng chọn menu bên trái.")
            
    with c2:
        st.markdown("""
        <div class="traffic-card">
        <h4>📍 REAL-TIME ROUTING (OSRM)</h4>
        <ul>
            <li>Đường đi cong theo thực tế (GeoJSON)</li>
            <li>Chế độ: Ô tô, Xe máy, Xe đạp, Đi bộ</li>
            <li>Tránh đường cấm/một chiều</li>
            <li>Đã tối ưu kết nối Server</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

def main():
    setup_page()
    init_session_state()
    section = create_sidebar()
    
    if section == "🏠 Trang chủ":
        show_home_page()
    elif section == "🗺️ Bản đồ Tích hợp":
        show_integrated_traffic_map()
    

if __name__ == "__main__":
    main()