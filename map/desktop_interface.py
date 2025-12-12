import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import math
from collections import deque
import heapq

class Graph:
    def __init__(self, directed=False):
        self.adj_list = {}
        self.vertices = {}
        self.edges = []
        self.directed = directed
        self.next_vertex_id = 0
    
    def add_vertex(self, x, y, name=None):
        vertex_id = f"V{self.next_vertex_id}"
        self.next_vertex_id += 1
        if name is None:
            name = vertex_id
        self.vertices[vertex_id] = {'id': vertex_id, 'name': name, 'x': x, 'y': y}
        self.adj_list[vertex_id] = []
        return vertex_id
    
    def add_edge(self, u, v, weight=1):
        if u not in self.adj_list:
            self.adj_list[u] = []
        if v not in self.adj_list:
            self.adj_list[v] = []
        
        # Kiểm tra cạnh đã tồn tại
        for edge in self.adj_list[u]:
            if edge[0] == v:
                return False
        
        self.adj_list[u].append((v, weight))
        self.edges.append((u, v, weight))
        
        if not self.directed:
            self.adj_list[v].append((u, weight))
        
        return True

class GraphApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ứng dụng Quản lý Đồ thị - Desktop")
        self.root.geometry("1200x700")
        
        self.graph = Graph(directed=False)
        self.selected_vertex = None
        self.selected_edge = None
        self.mode = "add_vertex"
        self.directed = False
        
        self.setup_ui()
    
    def setup_ui(self):
        # Setup UI tương tự như trong file giaodien.py
        # Giữ nguyên code giao diện desktop từ file cũ
        pass
    
    # Các phương thức khác giữ nguyên từ file giaodien.py

def main():
    root = tk.Tk()
    app = GraphApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()