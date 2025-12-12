import streamlit as st
import networkx as nx
import pandas as pd
import numpy as np
import json
import os
from graph_utils import GraphUtils
import matplotlib.pyplot as plt
class BasicGraphFunctions:
    def __init__(self):
        self.graph_utils = GraphUtils()
    
    def basic_section(self):
        """Phần chức năng cơ bản"""
        st.sidebar.header("🎯 Phần Cơ Bản")
        basic_option = st.sidebar.selectbox(
            "Chọn chức năng:",
            [
                "1. Vẽ đồ thị trực quan",
                "2. Lưu đồ thị",
                "3. Tìm đường đi ngắn nhất",
                "4. Duyệt đồ thị (BFS & DFS)",
                "5. Kiểm tra đồ thị 2 phía",
                "6. Chuyển đổi biểu diễn đồ thị"
            ],
            key="basic_option"
        )
        
        st.markdown(f"## {basic_option}")
        
        if "1." in basic_option or "Vẽ" in basic_option:
            self.draw_graph_section()
        elif "2." in basic_option or "Lưu" in basic_option:
            self.save_load_section()
        elif "3." in basic_option or "Tìm đường" in basic_option:
            self.shortest_path_section()
        elif "4." in basic_option or "Duyệt" in basic_option:
            self.traversal_section()
        elif "5." in basic_option or "2 phía" in basic_option:
            self.bipartite_section()
        elif "6." in basic_option or "Chuyển đổi" in basic_option:
            self.conversion_section()
    
    def draw_graph_section(self):
        """Chức năng 1: Vẽ đồ thị trực quan"""
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("📝 Nhập đồ thị")
            
            # Tab cho các phương pháp nhập
            input_tab1, input_tab2, input_tab3 = st.tabs(["Tự động tạo", "Nhập thủ công", "Đồ thị mẫu"])
            
            with input_tab1:
                st.write("**Tạo đồ thị ngẫu nhiên:**")
                
                graph_type = st.radio("Loại đồ thị:", 
                                     ["Vô hướng", "Có hướng"],
                                     key="random_graph_type")
                weighted = st.checkbox("Có trọng số", key="random_weighted")
                
                col_size = st.columns(2)
                with col_size[0]:
                    n_nodes = st.slider("Số đỉnh:", 3, 50, 10, key="random_nodes")
                with col_size[1]:
                    edge_prob = st.slider("Xác suất cạnh:", 0.1, 1.0, 0.3, 0.1, key="random_prob")
                
                if st.button("🎲 Tạo đồ thị ngẫu nhiên", use_container_width=True):
                    with st.spinner("Đang tạo đồ thị..."):
                        G = self.graph_utils.generate_random_graph(
                            n_nodes=n_nodes,
                            graph_type='directed' if graph_type == "Có hướng" else 'undirected',
                            weighted=weighted,
                            edge_probability=edge_prob
                        )
                        st.session_state.graph = G
                        st.success(f"✅ Đã tạo đồ thị với {G.number_of_nodes()} đỉnh và {G.number_of_edges()} cạnh")
            
            with input_tab2:
                st.write("**Nhập đồ thị thủ công:**")
                
                input_method = st.selectbox("Phương pháp nhập:",
                                           ["Ma trận kề", "Danh sách cạnh"],
                                           key="manual_method")
                
                if input_method == "Ma trận kề":
                    st.info("Nhập ma trận kề (mỗi dòng là một hàng, số cách nhau bởi dấu cách)")
                    default_matrix = "0 1 0 1 0\n1 0 1 0 1\n0 1 0 1 0\n1 0 1 0 1\n0 1 0 1 0"
                    matrix_input = st.text_area("Ma trận:", default_matrix, height=150)
                    
                    if st.button("📊 Tạo từ ma trận", use_container_width=True):
                        try:
                            rows = matrix_input.strip().split('\n')
                            matrix = [list(map(float, row.split())) for row in rows]
                            n = len(matrix)
                            
                            # Tạo đồ thị
                            G = nx.DiGraph() if st.checkbox("Đồ thị có hướng", key="matrix_directed") else nx.Graph()
                            
                            for i in range(n):
                                for j in range(n):
                                    if matrix[i][j] != 0:
                                        G.add_edge(i, j, weight=matrix[i][j])
                            
                            st.session_state.graph = G
                            st.success(f"✅ Đã tạo đồ thị từ ma trận {n}x{n}")
                        except Exception as e:
                            st.error(f"❌ Lỗi: {str(e)}")
                
                else:  # Danh sách cạnh
                    st.info("Mỗi dòng: đỉnh1 đỉnh2 [trọng số]")
                    default_edges = "0 1 5\n1 2 3\n2 3 7\n3 4 2\n4 0 4\n0 2 6\n1 3 4"
                    edges_input = st.text_area("Danh sách cạnh:", default_edges, height=150)
                    
                    if st.button("🔗 Tạo từ danh sách cạnh", use_container_width=True):
                        try:
                            edges = []
                            for line in edges_input.strip().split('\n'):
                                parts = line.strip().split()
                                if len(parts) >= 2:
                                    u, v = parts[0], parts[1]
                                    weight = float(parts[2]) if len(parts) > 2 else 1.0
                                    edges.append((u, v, weight))
                            
                            G = nx.DiGraph() if st.checkbox("Đồ thị có hướng", key="edges_directed") else nx.Graph()
                            
                            for u, v, w in edges:
                                G.add_edge(u, v, weight=w)
                            
                            st.session_state.graph = G
                            st.success(f"✅ Đã tạo đồ thị với {len(edges)} cạnh")
                        except Exception as e:
                            st.error(f"❌ Lỗi: {str(e)}")
            
            with input_tab3:
                st.write("**Chọn đồ thị mẫu:**")
                
                sample_graphs = {
                    "Đồ thị đầy đủ K5": nx.complete_graph(5),
                    "Đồ thị vòng C6": nx.cycle_graph(6),
                    "Đồ thị sao S7": nx.star_graph(6),
                    "Đồ thị lưới 4x4": nx.grid_2d_graph(4, 4),
                    "Đồ thị Petersen": nx.petersen_graph(),
                    "Đồ thị cân đối": nx.balanced_tree(3, 3)
                }
                
                selected_sample = st.selectbox("Chọn mẫu:", list(sample_graphs.keys()))
                
                if st.button("📋 Sử dụng mẫu này", use_container_width=True):
                    G = sample_graphs[selected_sample]
                    
                    # Thêm trọng số ngẫu nhiên
                    for u, v in G.edges():
                        G[u][v]['weight'] = round(np.random.uniform(1, 10), 1)
                    
                    st.session_state.graph = G
                    st.success(f"✅ Đã tải đồ thị mẫu: {selected_sample}")
        
        with col2:
            st.subheader("🎨 Đồ thị trực quan")
            
            if st.session_state.graph is not None:
                G = st.session_state.graph
                
                # Hiển thị thông tin
                stats = self.graph_utils.get_graph_statistics(G)
                
                st.markdown(f"""
                <div class="graph-info">
                    <b>📊 Thông tin đồ thị:</b><br>
                    • <b>Số đỉnh:</b> {stats['num_nodes']}<br>
                    • <b>Số cạnh:</b> {stats['num_edges']}<br>
                    • <b>Loại:</b> {"Có hướng" if stats['is_directed'] else "Vô hướng"}<br>
                    • <b>Có trọng số:</b> {"Có" if stats['is_weighted'] else "Không"}<br>
                    • <b>Bậc trung bình:</b> {stats.get('avg_degree', 'N/A'):.2f}<br>
                    • <b>Độ liên thông:</b> {"Có" if stats['is_connected'] else "Không"}
                </div>
                """, unsafe_allow_html=True)
                
                # Tùy chọn hiển thị
                display_col1, display_col2 = st.columns(2)
                with display_col1:
                    layout_type = st.selectbox("Bố cục:", ["Spring", "Circular", "Kamada-Kawai", "Random"], key="layout_type")
                with display_col2:
                    node_size = st.slider("Kích thước đỉnh:", 100, 1000, 500, key="node_size")
                
                # Tính toán vị trí
                if layout_type == "Spring":
                    pos = nx.spring_layout(G, seed=42)
                elif layout_type == "Circular":
                    pos = nx.circular_layout(G)
                elif layout_type == "Kamada-Kawai":
                    pos = nx.kamada_kawai_layout(G)
                else:
                    pos = nx.random_layout(G)
                
                # Vẽ đồ thị
                fig = self.graph_utils.draw_graph(G, pos=pos, 
                                                 title=f"Đồ thị ({stats['num_nodes']} đỉnh, {stats['num_edges']} cạnh)",
                                                 node_size=node_size)
                st.pyplot(fig)
                
                # Xem trước dữ liệu
                with st.expander("📋 Xem trước dữ liệu"):
                    tab1, tab2, tab3 = st.tabs(["Ma trận kề", "Danh sách kề", "Danh sách cạnh"])
                    
                    with tab1:
                        matrix, nodes = self.graph_utils.create_adjacency_matrix(G)
                        st.dataframe(pd.DataFrame(matrix, index=nodes, columns=nodes))
                    
                    with tab2:
                        adj_list = self.graph_utils.create_adjacency_list(G)
                        for node, neighbors in adj_list.items():
                            neighbor_str = ", ".join([f"{n}({w})" for n, w in neighbors])
                            st.write(f"**{node}:** {neighbor_str}")
                    
                    with tab3:
                        edges = self.graph_utils.create_edge_list(G)
                        st.dataframe(pd.DataFrame(edges, columns=["Đỉnh 1", "Đỉnh 2", "Trọng số"]))
            else:
                st.info("👈 Vui lòng tạo hoặc nhập đồ thị từ bên trái")
                st.image("https://via.placeholder.com/600x400/1E90FF/FFFFFF?text=ĐỒ+THỊ+TRỰC+QUAN", 
                        caption="Khu vực hiển thị đồ thị")
    
    def save_load_section(self):
        """Chức năng 2: Lưu và tải đồ thị"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💾 Lưu đồ thị")
            
            if st.session_state.graph is not None:
                st.write("**Tùy chọn lưu:**")
                
                save_format = st.selectbox("Định dạng:", 
                                          ["JSON (NetworkX)", "CSV - Ma trận kề", 
                                           "CSV - Danh sách cạnh", "CSV - Danh sách kề"],
                                          key="save_format")
                
                filename = st.text_input("Tên file:", "graph", key="save_filename")
                
                if st.button("💾 Lưu đồ thị", use_container_width=True):
                    try:
                        G = st.session_state.graph
                        
                        if save_format == "JSON (NetworkX)":
                            success, message = self.graph_utils.save_graph_to_file(G, f"{filename}.json")
                        elif save_format == "CSV - Ma trận kề":
                            csv_data = self.graph_utils.export_to_csv(G, 'adjacency')
                            with open(f"{filename}_matrix.csv", 'w', encoding='utf-8') as f:
                                f.write(csv_data)
                            success, message = True, f"Đã lưu ma trận kề vào {filename}_matrix.csv"
                        elif save_format == "CSV - Danh sách cạnh":
                            csv_data = self.graph_utils.export_to_csv(G, 'edges')
                            with open(f"{filename}_edges.csv", 'w', encoding='utf-8') as f:
                                f.write(csv_data)
                            success, message = True, f"Đã lưu danh sách cạnh vào {filename}_edges.csv"
                        else:  # Danh sách kề
                            csv_data = self.graph_utils.export_to_csv(G, 'adjacency_list')
                            with open(f"{filename}_adjlist.csv", 'w', encoding='utf-8') as f:
                                f.write(csv_data)
                            success, message = True, f"Đã lưu danh sách kề vào {filename}_adjlist.csv"
                        
                        if success:
                            st.success(message)
                            # Hiển thị nội dung file
                            with st.expander("📄 Xem nội dung file"):
                                try:
                                    with open(f"{filename}.json" if save_format == "JSON (NetworkX)" else 
                                             f"{filename}_matrix.csv" if "Ma trận" in save_format else
                                             f"{filename}_edges.csv" if "cạnh" in save_format else
                                             f"{filename}_adjlist.csv", 'r', encoding='utf-8') as f:
                                        content = f.read()
                                    st.code(content[:2000] + ("..." if len(content) > 2000 else ""))
                                except:
                                    st.warning("Không thể đọc nội dung file")
                        else:
                            st.error(message)
                            
                    except Exception as e:
                        st.error(f"❌ Lỗi khi lưu: {str(e)}")
            else:
                st.warning("Chưa có đồ thị để lưu. Vui lòng tạo đồ thị trước.")
        
        with col2:
            st.subheader("📂 Tải đồ thị")
            
            st.write("**Tải từ file:**")
            
            uploaded_file = st.file_uploader("Chọn file đồ thị", 
                                            type=['json', 'csv', 'txt'],
                                            key="upload_file")
            
            if uploaded_file is not None:
                try:
                    file_ext = uploaded_file.name.split('.')[-1].lower()
                    
                    if file_ext == 'json':
                        # Đọc file JSON
                        content = uploaded_file.getvalue().decode('utf-8')
                        data = json.loads(content)
                        G = nx.node_link_graph(data)
                        st.session_state.graph = G
                        st.success(f"✅ Đã tải đồ thị từ {uploaded_file.name}")
                        
                    elif file_ext == 'csv':
                        # Đọc file CSV
                        content = uploaded_file.getvalue().decode('utf-8')
                        lines = content.strip().split('\n')
                        
                        # Phát hiện định dạng
                        if ',' in content:
                            # CSV với dấu phẩy
                            import io
                            df = pd.read_csv(io.StringIO(content))
                            
                            if len(df.columns) >= 2:
                                # Giả định là danh sách cạnh
                                G = nx.Graph()
                                for _, row in df.iterrows():
                                    if len(df.columns) >= 3:
                                        G.add_edge(str(row[0]), str(row[1]), weight=float(row[2]))
                                    else:
                                        G.add_edge(str(row[0]), str(row[1]))
                                st.session_state.graph = G
                                st.success(f"✅ Đã tải đồ thị từ {uploaded_file.name} (danh sách cạnh)")
                        
                    # Hiển thị thông tin đồ thị
                    if st.session_state.graph is not None:
                        G = st.session_state.graph
                        st.info(f"""
                        **Thông tin đồ thị đã tải:**
                        - Số đỉnh: {G.number_of_nodes()}
                        - Số cạnh: {G.number_of_edges()}
                        - Loại: {'Có hướng' if nx.is_directed(G) else 'Vô hướng'}
                        """)
                        
                        # Hiển thị đồ thị nhỏ
                        fig = self.graph_utils.draw_graph(G, title=f"Đồ thị: {uploaded_file.name}", figsize=(6, 5))
                        st.pyplot(fig)
                        
                except Exception as e:
                    st.error(f"❌ Lỗi khi đọc file: {str(e)}")
            
            # Tải từ URL
            st.write("**Tải từ URL (ví dụ):**")
            url_examples = [
                "https://raw.githubusercontent.com/networkx/networkx/main/examples/drawing/simple_path.json",
                "https://raw.githubusercontent.com/gephi/gephi/master/modules/plugin-examples/src/main/resources/org/gephi/io/importer/plugin/file/example.gexf"
            ]
            
            selected_url = st.selectbox("Chọn ví dụ:", url_examples, key="url_select")
            
            if st.button("🌐 Tải từ URL", use_container_width=True):
                with st.spinner("Đang tải từ URL..."):
                    try:
                        import requests
                        response = requests.get(selected_url)
                        if response.status_code == 200:
                            # Xử lý dựa trên loại file
                            if selected_url.endswith('.json'):
                                data = response.json()
                                G = nx.node_link_graph(data)
                                st.session_state.graph = G
                                st.success("✅ Đã tải đồ thị từ URL")
                    except Exception as e:
                        st.error(f"❌ Lỗi khi tải từ URL: {str(e)}")
    
    def shortest_path_section(self):
        """Chức năng 3: Tìm đường đi ngắn nhất"""
        if st.session_state.graph is None:
            st.warning("Vui lòng tạo hoặc tải đồ thị trước.")
            return
        
        G = st.session_state.graph
        nodes = list(G.nodes())
        
        st.subheader("🔍 Tìm đường đi ngắn nhất")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("**Cài đặt thuật toán:**")
            
            algorithm = st.selectbox(
                "Chọn thuật toán:",
                ["Dijkstra (có trọng số)", "Bellman-Ford", "BFS (không trọng số)", "A* Search"],
                key="shortest_algo"
            )
            
            if algorithm == "A* Search":
                st.info("A* cần hàm heuristic. Ở đây dùng khoảng cách Euclidean nếu có tọa độ.")
            
            # Chọn đỉnh
            col_start, col_end = st.columns(2)
            with col_start:
                start_node = st.selectbox("Đỉnh bắt đầu:", nodes, key="start_node", index=0)
            with col_end:
                end_node = st.selectbox("Đỉnh kết thúc:", nodes, key="end_node", 
                                       index=min(1, len(nodes)-1))
            
            if st.button("📍 Tìm đường đi", use_container_width=True):
                try:
                    if start_node == end_node:
                        st.warning("Đỉnh bắt đầu và kết thúc giống nhau!")
                        return
                    
                    # Thực hiện thuật toán
                    if "Dijkstra" in algorithm:
                        if nx.is_weighted(G):
                            path = nx.dijkstra_path(G, start_node, end_node)
                            length = nx.dijkstra_path_length(G, start_node, end_node)
                        else:
                            path = nx.shortest_path(G, start_node, end_node)
                            length = len(path) - 1
                    
                    elif "Bellman" in algorithm:
                        if nx.is_weighted(G):
                            try:
                                path = nx.bellman_ford_path(G, start_node, end_node)
                                length = nx.bellman_ford_path_length(G, start_node, end_node)
                            except nx.NetworkXUnbounded:
                                st.error("Đồ thị có chu trình âm!")
                                return
                        else:
                            path = nx.shortest_path(G, start_node, end_node)
                            length = len(path) - 1
                    
                    elif "BFS" in algorithm:
                        path = nx.shortest_path(G, start_node, end_node)
                        length = len(path) - 1
                    
                    else:  # A* Search
                        # Cần tọa độ cho heuristic
                        try:
                            # Thử lấy tọa độ từ thuộc tính node
                            if all('pos' in G.nodes[n] for n in [start_node, end_node]):
                                def heuristic(u, v):
                                    pos_u = G.nodes[u]['pos']
                                    pos_v = G.nodes[v]['pos']
                                    return ((pos_u[0] - pos_v[0])**2 + (pos_u[1] - pos_v[1])**2)**0.5
                                path = nx.astar_path(G, start_node, end_node, heuristic=heuristic)
                                length = nx.astar_path_length(G, start_node, end_node, heuristic=heuristic)
                            else:
                                path = nx.shortest_path(G, start_node, end_node)
                                length = nx.shortest_path_length(G, start_node, end_node)
                        except:
                            path = nx.shortest_path(G, start_node, end_node)
                            length = nx.shortest_path_length(G, start_node, end_node)
                    
                    st.session_state.path_result = {
                        'path': path,
                        'length': length,
                        'start': start_node,
                        'end': end_node,
                        'algorithm': algorithm
                    }
                    
                    st.success(f"✅ Tìm thấy đường đi!")
                    
                except nx.NetworkXNoPath:
                    st.error("❌ Không có đường đi giữa hai đỉnh này!")
                except Exception as e:
                    st.error(f"❌ Lỗi: {str(e)}")
        
        with col2:
            st.write("**Kết quả:**")
            
            if 'path_result' in st.session_state:
                result = st.session_state.path_result
                
                # Hiển thị đường đi
                st.markdown(f"""
                <div class="algorithm-card">
                    <h4>📊 Kết quả đường đi</h4>
                    <p><b>Thuật toán:</b> {result['algorithm']}</p>
                    <p><b>Từ:</b> {result['start']} → <b>Đến:</b> {result['end']}</p>
                    <p><b>Đường đi:</b> {" → ".join(map(str, result['path']))}</p>
                    <p><b>Độ dài/trọng số:</b> {result['length']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Hiển thị đồ thị với đường đi được đánh dấu
                path_edges = [(result['path'][i], result['path'][i+1]) 
                             for i in range(len(result['path'])-1)]
                
                fig = self.graph_utils.draw_graph(
                    G, 
                    title=f"Đường đi từ {result['start']} đến {result['end']}",
                    highlight_path=path_edges,
                    highlight_nodes=result['path']
                )
                st.pyplot(fig)
                
                # Tìm tất cả các đường đi ngắn nhất
                if st.button("🔍 Tìm tất cả đường đi ngắn nhất"):
                    all_paths = self.graph_utils.find_all_shortest_paths(G, result['start'], result['end'])
                    if all_paths:
                        st.write(f"**Tìm thấy {len(all_paths)} đường đi ngắn nhất:**")
                        for i, path in enumerate(all_paths, 1):
                            st.write(f"{i}. {' → '.join(map(str, path))}")
                    else:
                        st.info("Chỉ có một đường đi ngắn nhất duy nhất.")
            else:
                st.info("👈 Nhấn nút 'Tìm đường đi' để xem kết quả")
    
    def traversal_section(self):
        """Chức năng 4: Duyệt đồ thị (BFS & DFS)"""
        if st.session_state.graph is None:
            st.warning("Vui lòng tạo hoặc tải đồ thị trước.")
            return
        
        G = st.session_state.graph
        
        st.subheader("🔍 Duyệt đồ thị (BFS & DFS)")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("**Cài đặt duyệt:**")
            
            algorithm = st.radio(
                "Chọn thuật toán duyệt:",
                ["BFS (Breadth-First Search)", "DFS (Depth-First Search)"],
                key="traversal_algo"
            )
            
            start_node = st.selectbox(
                "Đỉnh bắt đầu:",
                list(G.nodes()),
                key="traversal_start"
            )
            
            if st.button("🚀 Thực hiện duyệt", use_container_width=True):
                try:
                    if algorithm == "BFS (Breadth-First Search)":
                        traversal = list(nx.bfs_edges(G, source=start_node))
                        order = list(nx.bfs_tree(G, source=start_node).nodes())
                    else:
                        traversal = list(nx.dfs_edges(G, source=start_node))
                        order = list(nx.dfs_tree(G, source=start_node).nodes())
                    
                    st.session_state.traversal_result = {
                        'edges': traversal,
                        'order': order,
                        'algorithm': algorithm,
                        'start': start_node
                    }
                    
                    st.success(f"✅ Đã duyệt {len(order)} đỉnh")
                    
                except Exception as e:
                    st.error(f"❌ Lỗi: {str(e)}")
        
        with col2:
            st.write("**Kết quả duyệt:**")
            
            if 'traversal_result' in st.session_state:
                result = st.session_state.traversal_result
                
                # Hiển thị thông tin
                st.markdown(f"""
                <div class="algorithm-card">
                    <h4>📊 Kết quả {result['algorithm']}</h4>
                    <p><b>Đỉnh bắt đầu:</b> {result['start']}</p>
                    <p><b>Thứ tự duyệt:</b> {" → ".join(map(str, result['order']))}</p>
                    <p><b>Số đỉnh đã duyệt:</b> {len(result['order'])}</p>
                    <p><b>Số cạnh đã duyệt:</b> {len(result['edges'])}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Hiển thị chi tiết từng bước
                with st.expander("📝 Xem chi tiết từng bước duyệt"):
                    for i, (u, v) in enumerate(result['edges'], 1):
                        st.write(f"**Bước {i}:** {u} → {v}")
                
                # Hiển thị đồ thị với các cạnh đã duyệt
                fig = self.graph_utils.draw_graph(
                    G,
                    title=f"{result['algorithm']} từ đỉnh {result['start']}",
                    highlight_path=result['edges'],
                    highlight_nodes=result['order']
                )
                st.pyplot(fig)
                
                # Thống kê
                col_stats1, col_stats2 = st.columns(2)
                with col_stats1:
                    st.metric("Số đỉnh đã duyệt", len(result['order']))
                with col_stats2:
                    st.metric("Số cạnh đã duyệt", len(result['edges']))
            else:
                st.info("👈 Nhấn nút 'Thực hiện duyệt' để xem kết quả")
    
    def bipartite_section(self):
        """Chức năng 5: Kiểm tra đồ thị 2 phía"""
        if st.session_state.graph is None:
            st.warning("Vui lòng tạo hoặc tải đồ thị trước.")
            return
        
        G = st.session_state.graph
        
        st.subheader("🎭 Kiểm tra đồ thị 2 phía (Bipartite)")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("**Thông tin kiểm tra:**")
            
            is_bipartite = nx.is_bipartite(G)
            
            if is_bipartite:
                st.success("✅ Đồ thị là đồ thị 2 phía (bipartite)")
                
                # Tìm các tập đỉnh
                try:
                    set_a, set_b = nx.bipartite.sets(G)
                    
                    st.session_state.bipartite_result = {
                        'is_bipartite': True,
                        'set_a': list(set_a),
                        'set_b': list(set_b)
                    }
                    
                    st.write(f"**Tập A:** {', '.join(map(str, sorted(set_a)))}")
                    st.write(f"**Tập B:** {', '.join(map(str, sorted(set_b)))}")
                    st.write(f"**Tổng:** {len(set_a) + len(set_b)} đỉnh")
                    
                except Exception as e:
                    st.error(f"❌ Không thể phân tách tập đỉnh: {str(e)}")
            else:
                st.error("❌ Đồ thị KHÔNG phải là đồ thị 2 phía")
                
                # Tìm chu trình lẻ
                try:
                    odd_cycle = nx.find_cycle(G)
                    st.write(f"**Chu trình lẻ tìm thấy:** {odd_cycle}")
                except:
                    st.info("Không tìm thấy chu trình rõ ràng")
        
        with col2:
            st.write("**Trực quan hóa:**")
            
            if is_bipartite and 'bipartite_result' in st.session_state:
                result = st.session_state.bipartite_result
                
                # Tô màu các đỉnh theo tập
                color_map = []
                for node in G.nodes():
                    if node in result['set_a']:
                        color_map.append(self.graph_utils.color_palette['bipartite_a'])
                    else:
                        color_map.append(self.graph_utils.color_palette['bipartite_b'])
                
                # Vẽ đồ thị
                fig, ax = plt.subplots(figsize=(10, 8))
                pos = nx.spring_layout(G, seed=42)
                
                nx.draw_networkx_nodes(G, pos, node_color=color_map, 
                                      node_size=500, alpha=0.9, ax=ax)
                nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold', ax=ax)
                nx.draw_networkx_edges(G, pos, width=1, alpha=0.7, ax=ax)
                
                # Vẽ trọng số nếu có
                if nx.is_weighted(G):
                    edge_labels = nx.get_edge_attributes(G, 'weight')
                    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, 
                                                font_size=9, ax=ax)
                
                ax.set_title("Đồ thị 2 phía (Bipartite Graph)", fontsize=16, fontweight='bold')
                ax.axis('off')
                plt.tight_layout()
                
                st.pyplot(fig)
                
                # Thêm chú thích
                st.markdown("""
                **Chú thích màu sắc:**
                - <span style="color:#ff9999">● Đỏ</span>: Tập A
                - <span style="color:#99ccff">● Xanh</span>: Tập B
                
                **Đặc điểm đồ thị 2 phía:**
                - Có thể phân chia đỉnh thành 2 tập không giao nhau
                - Mọi cạnh nối một đỉnh từ tập A với một đỉnh từ tập B
                - Không có cạnh nối 2 đỉnh trong cùng một tập
                - Ứng dụng: Ghép cặp, lập lịch, phân công công việc
                """, unsafe_allow_html=True)
            else:
                st.info("Đồ thị không phải 2 phía, không thể phân tách tập đỉnh")
    
    def conversion_section(self):
        """Chức năng 6: Chuyển đổi biểu diễn đồ thị"""
        if st.session_state.graph is None:
            st.warning("Vui lòng tạo hoặc tải đồ thị trước.")
            return
        
        G = st.session_state.graph
        
        st.subheader("🔄 Chuyển đổi biểu diễn đồ thị")
        
        # Tab cho các dạng biểu diễn
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Ma trận kề", 
            "📋 Danh sách kề", 
            "🔗 Danh sách cạnh",
            "📈 Thống kê"
        ])
        
        with tab1:
            st.write("### Ma trận kề")
            
            matrix, nodes = self.graph_utils.create_adjacency_matrix(G)
            df_matrix = pd.DataFrame(matrix, index=nodes, columns=nodes)
            
            # Hiển thị với màu sắc
            st.dataframe(df_matrix.style.background_gradient(cmap='Blues'), 
                        use_container_width=True, height=400)
            
            # Nút tải xuống
            csv_matrix = df_matrix.to_csv()
            st.download_button(
                label="📥 Tải ma trận kề (CSV)",
                data=csv_matrix,
                file_name="adjacency_matrix.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with tab2:
            st.write("### Danh sách kề")
            
            adj_list = self.graph_utils.create_adjacency_list(G)
            
            # Hiển thị dạng bảng
            adj_data = []
            for node, neighbors in adj_list.items():
                neighbor_str = ", ".join([f"{n}({w})" for n, w in neighbors]) if neighbors else "Không có"
                adj_data.append([node, neighbor_str])
            
            df_adj = pd.DataFrame(adj_data, columns=["Đỉnh", "Các đỉnh kề (trọng số)"])
            st.dataframe(df_adj, use_container_width=True, height=400)
            
            # Hiển thị dạng JSON
            with st.expander("📄 Xem dạng JSON"):
                st.json(adj_list)
            
            # Nút copy
            if st.button("📋 Copy danh sách kề (JSON)", use_container_width=True):
                adj_str = json.dumps(adj_list, indent=2, ensure_ascii=False)
                st.code(adj_str, language='json')
        
        with tab3:
            st.write("### Danh sách cạnh")
            
            edges = self.graph_utils.create_edge_list(G)
            
            # Hiển thị bảng
            df_edges = pd.DataFrame(edges, columns=["Đỉnh nguồn", "Đỉnh đích", "Trọng số"])
            st.dataframe(df_edges, use_container_width=True, height=400)
            
            # Thống kê cạnh
            col_edge1, col_edge2, col_edge3 = st.columns(3)
            with col_edge1:
                st.metric("Tổng số cạnh", len(edges))
            with col_edge2:
                if edges:
                    avg_weight = sum(w for _, _, w in edges) / len(edges)
                    st.metric("Trọng số trung bình", f"{avg_weight:.2f}")
            with col_edge3:
                if edges:
                    max_weight = max(w for _, _, w in edges)
                    st.metric("Trọng số lớn nhất", f"{max_weight:.2f}")
            
            # Nút tải xuống
            csv_edges = df_edges.to_csv(index=False)
            st.download_button(
                label="📥 Tải danh sách cạnh (CSV)",
                data=csv_edges,
                file_name="edge_list.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with tab4:
            st.write("### 📈 Thống kê đồ thị")
            
            stats = self.graph_utils.get_graph_statistics(G)
            
            # Hiển thị metrics
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            with col_stat1:
                st.metric("Số đỉnh", stats['num_nodes'])
            with col_stat2:
                st.metric("Số cạnh", stats['num_edges'])
            with col_stat3:
                st.metric("Bậc trung bình", f"{stats.get('avg_degree', 0):.2f}")
            with col_stat4:
                st.metric("Độ dày", f"{stats['density']:.4f}")
            
            # Thêm metrics
            col_stat5, col_stat6, col_stat7, col_stat8 = st.columns(4)
            with col_stat5:
                st.metric("Có hướng", "Có" if stats['is_directed'] else "Không")
            with col_stat6:
                st.metric("Có trọng số", "Có" if stats['is_weighted'] else "Không")
            with col_stat7:
                st.metric("Liên thông", "Có" if stats['is_connected'] else "Không")
            with col_stat8:
                if 'max_degree' in stats:
                    st.metric("Bậc lớn nhất", stats['max_degree'])
            
            # Phân bố bậc (nếu có đủ đỉnh)
            if stats['num_nodes'] > 0:
                st.write("**Phân bố bậc của đỉnh:**")
                degrees = [deg for _, deg in G.degree()]
                degree_counts = pd.Series(degrees).value_counts().sort_index()
                
                col_chart1, col_chart2 = st.columns([2, 1])
                with col_chart1:
                    st.bar_chart(degree_counts)
                with col_chart2:
                    st.dataframe(degree_counts.reset_index().rename(
                        columns={'index': 'Bậc', 0: 'Số đỉnh'}
                    ))
            
            # Kiểm tra đặc điểm đặc biệt
            st.write("**Kiểm tra đặc điểm:**")
            
            col_check1, col_check2 = st.columns(2)
            with col_check1:
                try:
                    if not stats['is_directed']:
                        is_eulerian = nx.is_eulerian(G)
                        st.write(f"• Đồ thị Euler: **{'Có' if is_eulerian else 'Không'}**")
                        
                        is_planar = nx.check_planarity(G)[0]
                        st.write(f"• Đồ thị phẳng: **{'Có' if is_planar else 'Không'}**")
                except:
                    pass
            
            with col_check2:
                try:
                    if not stats['is_directed'] and stats['is_connected']:
                        diameter = nx.diameter(G)
                        st.write(f"• Đường kính: **{diameter}**")
                        
                        avg_path_length = nx.average_shortest_path_length(G)
                        st.write(f"• Khoảng cách TB: **{avg_path_length:.2f}**")
                except:
                    pass