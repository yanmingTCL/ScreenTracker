import wx
import sqlite3
import wx.grid as gridlib
from io import BytesIO
from PIL import Image

class DatabaseBrowser(wx.Frame):
    def __init__(self, *args, **kw):
        super(DatabaseBrowser, self).__init__(*args, **kw)
        self.InitUI()
        self.conn = None
        self.image_timestamps = []
        self.current_image_index = -1
        self.selected_event_rows = set()  # 存储选中的事件行索引
        
        self.click_positions = []  # 存储鼠标点击位置 [(x, y), ...]
        self.current_image_size = (0, 0)  # 存储当前图像的原始尺寸
        self.display_image_size = (0, 0)  # 存储当前显示图像的尺寸
                
    def InitUI(self):
        panel = wx.Panel(self)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 顶部：打开数据库按钮
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_open = wx.Button(panel, label="Open Database")
        self.btn_open.Bind(wx.EVT_BUTTON, self.OnOpen)
        hbox1.Add(self.btn_open, flag=wx.LEFT, border=10)
        vbox.Add(hbox1, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=10)
        
        # 中间：图像显示和控制区域 + 文本事件表格
        main_panel = wx.Panel(panel)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 左侧：图像显示区域 - 显著放大
        left_panel = wx.Panel(main_panel)
        left_vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 图像显示控件 (放大图像区域)
        self.image_panel = wx.Panel(left_panel, style=wx.SIMPLE_BORDER)
        #self.image_panel = wx.ScrolledWindow(left_panel, style=wx.SIMPLE_BORDER) # | wx.HSCROLL | wx.VSCROLL)
        self.image_panel.SetMinSize((650, 350))  # 稍大尺寸
        #self.image_panel.SetScrollRate(80, 80)  # 设置滚动步长
        #self.image_panel.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        #self.image_panel.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)        
        
        self.image_ctrl = wx.StaticBitmap(self.image_panel)
        
        # 放置StaticBitmap使其居中
        sizer = wx.BoxSizer()
        sizer.Add(self.image_ctrl, 1, wx.ALIGN_CENTER | wx.ALL, 10)
        self.image_panel.SetSizer(sizer)
        
        left_vbox.Add(self.image_panel, 1, wx.EXPAND | wx.ALL, 10)
        
        # 图像导航按钮
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_prev = wx.Button(left_panel, label="Pre")
        self.btn_prev.Bind(wx.EVT_BUTTON, self.OnPrevImage)
        self.btn_prev.Disable()
        btn_sizer.Add(self.btn_prev, flag=wx.ALL, border=5)
        
        self.image_scroll = wx.ScrollBar(left_panel, style=wx.SB_HORIZONTAL)
        self.image_scroll.SetMinSize((300, -1))
        self.image_scroll.SetScrollbar(0, 1, 100, 1)  # 初始值
        self.image_scroll.Bind(wx.EVT_SCROLL, self.OnImageScroll)
        btn_sizer.Add(self.image_scroll, 1, wx.EXPAND | wx.ALL, 5)
        
        self.btn_next = wx.Button(left_panel, label="Next")
        self.btn_next.Bind(wx.EVT_BUTTON, self.OnNextImage)
        self.btn_next.Disable()
        btn_sizer.Add(self.btn_next, flag=wx.ALL, border=5)
        
        left_vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER)
        
        # 图像信息标签
        info_sizer = wx.BoxSizer(wx.VERTICAL)
        self.timestamp_label = wx.StaticText(left_panel, label="Timestamp: N/A")
        info_sizer.Add(self.timestamp_label, flag=wx.ALL, border=5)
        #self.user_id_label = wx.StaticText(left_panel, label="User ID: N/A")
        #info_sizer.Add(self.user_id_label, flag=wx.ALL, border=5)
        left_vbox.Add(info_sizer, 0, wx.ALIGN_CENTER)
        
        left_panel.SetSizer(left_vbox)
        main_sizer.Add(left_panel, 1, wx.EXPAND | wx.ALL, 5)
        
        # 右侧：文本事件表格 (固定大小并添加滚动条)
        right_panel = wx.Panel(main_panel)
        right_vbox = wx.BoxSizer(wx.VERTICAL)
        
        st_events = wx.StaticText(right_panel, label="Text Events:")
        right_vbox.Add(st_events, 0, wx.ALL, 5)
        
        # 创建带滚动条的容器
        scrolled = wx.ScrolledWindow(right_panel, style=wx.VSCROLL | wx.HSCROLL)
        scrolled.SetMinSize((300, 150))  # 固定大小
        
        # 创建grid
        self.grid = gridlib.Grid(scrolled)
        self.grid.CreateGrid(0, 3)  # 三列：选择列、时间戳、事件
        self.grid.SetColLabelValue(0, "invalid")
        self.grid.SetColLabelValue(1, "Timestamp")
        self.grid.SetColLabelValue(2, "Event")
        
        # 设置选择列为复选框
        attr = gridlib.GridCellAttr()
        attr.SetRenderer(gridlib.GridCellBoolRenderer())
        attr.SetEditor(gridlib.GridCellBoolEditor())
        self.grid.SetColAttr(0, attr)
        
        # 固定列宽
        self.grid.SetColSize(0, 40)    # 选择列
        self.grid.SetColSize(1, 150)   # 时间戳列
        self.grid.SetColSize(2, 150)   # 事件列
        
        #self.grid.Bind(gridlib.EVT_GRID_CELL_CHANGED, self.OnEventSelected)
        
        # 添加grid到带滚动条的容器
        scrolled_sizer = wx.BoxSizer(wx.VERTICAL)
        scrolled_sizer.Add(self.grid, 1, wx.EXPAND | wx.ALL, 5)
        scrolled.SetSizer(scrolled_sizer)
        scrolled.SetScrollRate(10, 10)  # 设置滚动速率
        right_vbox.Add(scrolled, 1, wx.EXPAND | wx.ALL, 5)
              
        # save_btn = wx.Button(right_panel, label="Save")
        # save_btn.Bind(wx.EVT_BUTTON, self.OnSave)
        # right_vbox.Add(save_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)   
        # 在表格下方添加复选框和Save按钮（水平排列）
        hbox_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.check_all = wx.CheckBox(right_panel, label="Check All")
        self.check_all.Bind(wx.EVT_CHECKBOX, self.OnCheckAll)
        hbox_buttons.Add(self.check_all, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        save_btn = wx.Button(right_panel, label="Save")
        save_btn.Bind(wx.EVT_BUTTON, self.OnSave)
        hbox_buttons.Add(save_btn, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        right_vbox.Add(hbox_buttons, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
        

        # 在Save按钮下方添加任务信息显示
        st_task = wx.StaticText(right_panel, label="Task Information:")
        right_vbox.Add(st_task, 0, wx.ALL, 5)
        self.task_info_text = wx.TextCtrl(right_panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.task_info_text.SetMinSize((-1, 150))  # 设置文本框高度
        right_vbox.Add(self.task_info_text, 1, wx.EXPAND | wx.ALL, 5)
                
                
        right_panel.SetSizer(right_vbox)
        main_sizer.Add(right_panel, 0, wx.EXPAND | wx.ALL, 5)
        main_panel.SetSizer(main_sizer)
        vbox.Add(main_panel, 1, wx.EXPAND)
        
        # # 底部：任务信息显示
        # bottom_panel = wx.Panel(panel)
        # bottom_sizer = wx.BoxSizer(wx.VERTICAL)
        # st_task = wx.StaticText(bottom_panel, label="Task Information:")
        # bottom_sizer.Add(st_task, 0, wx.ALL, 5)
        # self.task_info_text = wx.TextCtrl(bottom_panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        # bottom_sizer.Add(self.task_info_text, 1, wx.EXPAND | wx.ALL, 5)
        # bottom_panel.SetSizer(bottom_sizer)
        # vbox.Add(bottom_panel, 0.5, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(vbox)
        self.SetTitle('Database Browser')
        self.SetSize(1200, 800)
        self.Maximize(True)
        self.Centre()

    def OnOpen(self, event):
        with wx.FileDialog(self, "Open SQLite file", wildcard="SQLite files (*.db)|*.db",
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            path = fileDialog.GetPath()
            self.conn = sqlite3.connect(path)
            
            # 新增：确保text_events表有invalid列
            cursor = self.conn.cursor()
            try:
                # 检查表是否存在并获取列信息
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='text_events'")
                if cursor.fetchone():
                    cursor.execute("PRAGMA table_info(text_events)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    # 如果不存在invalid列则添加
                    if "invalid" not in columns:
                        cursor.execute("ALTER TABLE text_events ADD COLUMN invalid INTEGER DEFAULT 0")
                        self.conn.commit()
            except sqlite3.Error as e:
                wx.MessageBox(f"Database error: {e}", "Error", wx.OK | wx.ICON_ERROR)
            
            self.LoadImageTimestamps()
            self.LoadTaskInfo()

    def OnSave(self, event):
        """保存所有事件的选择状态到数据库"""
        if not self.conn:
            wx.MessageBox("Please open a database first", "Error", wx.OK | wx.ICON_ERROR)
            return
            
        try:
            num_rows = self.grid.GetNumberRows()
            for row in range(num_rows):
                # 获取当前行的选择状态、时间戳和事件内容
                is_selected = self.grid.GetCellValue(row, 0) == "1"
                timestamp = self.grid.GetCellValue(row, 1)
                event_text = self.grid.GetCellValue(row, 2)
                
                # 更新数据库
                cursor = self.conn.cursor()
                cursor.execute("UPDATE text_events SET invalid = ? WHERE timestamp = ? AND event = ?",
                              (1 if is_selected else 0, timestamp, event_text))
            
            self.conn.commit()
            wx.MessageBox(f"Successfully saved {num_rows} events", "Success", wx.OK | wx.ICON_INFORMATION)
        except sqlite3.Error as e:
            wx.MessageBox(f"Database error: {e}", "Error", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            wx.MessageBox(f"Unexpected error: {e}", "Error", wx.OK | wx.ICON_ERROR)
        
    def OnCheckAll(self, event):
        """处理全选复选框事件"""
        check_all = self.check_all.GetValue()
        num_rows = self.grid.GetNumberRows()
        
        # 设置表格中所有行的选择状态
        for row in range(num_rows):
            self.grid.SetCellValue(row, 0, "1" if check_all else "0")
        
        # 刷新表格显示
        self.grid.ForceRefresh()
                 
    def OnMouseWheel(self, event):
        """处理鼠标滚轮事件，实现水平滚动切换图片"""
        rotation = event.GetWheelRotation()
        
        if rotation > 0:  # 左滚动
            self.OnPrevImage(None)
        elif rotation < 0:  # 滚动
            self.OnNextImage(None)

    def OnImageScroll(self, event):
        """处理图像滚动条事件"""
        if not self.image_timestamps:
            return
            
        # 获取滚动条位置
        pos = self.image_scroll.GetThumbPosition()
        
        # 计算新的图像索引
        total_images = len(self.image_timestamps)
        if total_images > 0:
            # 将滚动条位置映射到图像索引
            new_index = int(pos * (total_images - 1) / self.image_scroll.GetRange())
            
            # 确保索引在有效范围内
            new_index = max(0, min(new_index, total_images - 1))
            
            # 如果索引改变，更新当前图像
            if new_index != self.current_image_index:
                self.current_image_index = new_index
                self.ShowCurrentImage()
            
    def LoadImageTimestamps(self):
        """加载所有图像时间戳"""
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT timestamp, user_id FROM image_data ORDER BY timestamp")
            self.image_timestamps = cursor.fetchall()
            
            if self.image_timestamps:
                self.current_image_index = 0
                self.ShowCurrentImage()
                self.btn_prev.Enable()
                self.btn_next.Enable()
                #total_images = len(self.image_timestamps)
                #thumb_size = min(10, total_images)  # 滑块大小设置为10或总图像数（取较小值）
                #self.image_scroll.SetScrollbar(0, thumb_size, total_images, thumb_size)
            else:
                wx.MessageBox("No images found in database", "Info", wx.OK | wx.ICON_INFORMATION)

    # def ShowCurrentImage(self):
    #     """显示当前索引的图像"""
    #     if not self.image_timestamps or self.current_image_index < 0:
    #         return
            
    #     timestamp, user_id = self.image_timestamps[self.current_image_index]
        
    #     # 更新标签
    #     self.timestamp_label.SetLabel(f"Timestamp: {timestamp}")
    #     #self.user_id_label.SetLabel(f"User ID: {user_id}")
        
    #     # 加载并显示图像
    #     cursor = self.conn.cursor()
    #     cursor.execute("SELECT screenshot FROM image_data WHERE timestamp=?", (timestamp,))
    #     row = cursor.fetchone()
    #     if row and row[0]:
    #         image_data = row[0]
            
    #         # 从字节数据创建图像
    #         img = Image.open(BytesIO(image_data))
    #         if img.mode != 'RGB':
    #             img = img.convert('RGB')
    #         wx_img = wx.Image(img.size[0], img.size[1])
    #         wx_img.SetData(img.tobytes())
            
    #         # 缩放以适应面板
    #         panel_width, panel_height = self.image_panel.GetSize()
    #         aspect_ratio = wx_img.GetWidth() / wx_img.GetHeight()
            
    #         if aspect_ratio > 1:  # 宽图
    #             new_width = min(panel_width - 20, wx_img.GetWidth())
    #             new_height = new_width / aspect_ratio
    #         else:  # 高图
    #             new_height = min(panel_height - 20, wx_img.GetHeight())
    #             new_width = new_height * aspect_ratio
                
    #         wx_img = wx_img.Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)
            
    #         # 显示图像
    #         self.image_ctrl.SetBitmap(wx.Bitmap(wx_img))
        
    #     # 显示该图像时间戳范围内的文本事件
    #     self.LoadTextEventsForCurrentImage()
    
    def ShowCurrentImage(self):
        """显示当前索引的图像 - 修正图像显示问题"""
        if not self.image_timestamps or self.current_image_index < 0:
            return
            
        timestamp, user_id = self.image_timestamps[self.current_image_index]
        
        # 更新标签
        self.timestamp_label.SetLabel(f"Timestamp: {timestamp}")
        #self.user_id_label.SetLabel(f"User ID: {user_id}")
        
        # 加载并显示图像
        cursor = self.conn.cursor()
        cursor.execute("SELECT screenshot FROM image_data WHERE timestamp=?", (timestamp,))
        row = cursor.fetchone()
        if row and row[0]:
            image_data = row[0]
            
            # 从字节数据创建图像
            img = Image.open(BytesIO(image_data))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            wx_img = wx.Image(img.size[0], img.size[1])
            wx_img.SetData(img.tobytes())
            
            # 修正1：获取面板的实际大小（排除边框）
            panel_width, panel_height = self.image_panel.GetClientSize()
            
            # 计算保持宽高比的最佳缩放尺寸
            img_width = wx_img.GetWidth()
            img_height = wx_img.GetHeight()
            
            # 计算缩放比例
            width_ratio = panel_width / float(img_width)
            height_ratio = panel_height / float(img_height)
            scale_ratio = min(width_ratio, height_ratio)
            
            # 计算新尺寸
            new_width = int(img_width * scale_ratio)
            new_height = int(img_height * scale_ratio)
            
            # 缩放图像
            wx_img = wx_img.Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)

            # 显示该图像时间戳范围内的文本事件
            self.click_positions = []
            self.LoadTextEventsForCurrentImage()            
            # 显示图像
            if self.click_positions:
                dc = wx.MemoryDC()
                bmp = wx.Bitmap(wx_img)
                dc.SelectObject(bmp)
                
                # 设置画笔和颜色
                dc.SetPen(wx.Pen(wx.RED, 2))
                
                # 绘制所有点击位置
                for pos in self.click_positions:
                    # 将原始坐标转换为显示坐标
                    x = int(pos[0] * scale_ratio)
                    y = int(pos[1] * scale_ratio)
                    
                    # 绘制十字标记
                    dc.DrawLine(x-10, y, x+10, y)
                    dc.DrawLine(x, y-10, x, y+10)
                
                dc.SelectObject(wx.NullBitmap)
                self.image_ctrl.SetBitmap(bmp)
            else:
                self.image_ctrl.SetBitmap(wx.Bitmap(wx_img))            
            #self.image_ctrl.SetBitmap(wx.Bitmap(wx_img))
            self.image_panel.Layout()  # 确保布局更新
        


    def OnPrevImage(self, event):
        """显示上一张图像"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.ShowCurrentImage()

    def OnNextImage(self, event):
        """显示下一张图像"""
        if self.current_image_index < len(self.image_timestamps) - 1:
            self.current_image_index += 1
            self.ShowCurrentImage()

    # def LoadTextEventsForCurrentImage(self):
    #     """加载并显示当前图像时间戳范围内的文本事件"""
    #     if not self.image_timestamps or self.current_image_index < 0 or not self.conn:
    #         return
            
    #     # 获取当前图像的时间戳
    #     current_timestamp = self.image_timestamps[self.current_image_index][0]
        
    #     # 获取前一个图像的时间戳作为起始点
    #     start_timestamp = None
    #     if self.current_image_index > 0:
    #         start_timestamp = self.image_timestamps[self.current_image_index - 1][0]
        
    #     # 构造SQL查询
    #     if start_timestamp:
    #         sql = "SELECT timestamp, event FROM text_events WHERE timestamp BETWEEN ? AND ?"
    #         params = (start_timestamp, current_timestamp)
    #     else:
    #         sql = "SELECT timestamp, event FROM text_events WHERE timestamp <= ?"
    #         params = (current_timestamp,)
        
    #     cursor = self.conn.cursor()
    #     cursor.execute(sql, params)
    #     results = cursor.fetchall()
        
    #     # 清空表格
    #     if self.grid.GetNumberRows() > 0:
    #         self.grid.DeleteRows(0, self.grid.GetNumberRows())
        
    #     # 添加新行
    #     if results:
    #         self.grid.AppendRows(len(results))
            
    #         # 设置单元格值 (只显示事件，时间戳不需要)
    #         for i, (timestamp, event) in enumerate(results):
    #             self.grid.SetCellValue(i, 1, event)  # 只显示事件文本
    #             self.grid.SetCellValue(i, 0, "0")   # 初始化为未选中

    # def OnEventSelected(self, event):
    #     """处理事件选择状态变化"""
    #     row = event.GetRow()
    #     col = event.GetCol()
        
    #     if col == 0:  # 只处理选择列的变化
    #         selected = self.grid.GetCellValue(row, 0) == "1"
    #         event_text = self.grid.GetCellValue(row, 1)
            
    #         # 更新数据库中的选中状态
    #         if self.conn and event_text != "":
    #             try:
    #                 # 确保text_events表有selected列
    #                 cursor = self.conn.cursor()
    #                 cursor.execute("PRAGMA table_info(text_events)")
    #                 columns = [col[1] for col in cursor.fetchall()]
                    
    #                 if "invalid" not in columns:
    #                     cursor.execute("ALTER TABLE text_events ADD COLUMN invalid INTEGER DEFAULT 0")
                    
    #                 # 更新选中状态 - 通过事件文本查找
    #                 cursor.execute("UPDATE text_events SET invalid = ? WHERE event = ?", 
    #                               (1 if selected else 0, event_text))
    #                 self.conn.commit()
                    
    #                 # 更新选中行集合
    #                 if selected:
    #                     self.selected_event_rows.add(row)
    #                 elif row in self.selected_event_rows:
    #                     self.selected_event_rows.remove(row)
    #             except sqlite3.Error as e:
    #                 wx.MessageBox(f"Database error: {e}", "Error", wx.OK | wx.ICON_ERROR)


    # def LoadTextEventsForCurrentImage(self):
    #     """加载并显示当前图像时间戳范围内的文本事件 - 修正事件触发问题"""
    #     if not self.image_timestamps or self.current_image_index < 0 or not self.conn:
    #         return
            
    #     # 获取当前图像的时间戳
    #     current_timestamp = self.image_timestamps[self.current_image_index][0]
        
    #     # 获取前一个图像的时间戳作为起始点
    #     start_timestamp = None
    #     if self.current_image_index > 0:
    #         start_timestamp = self.image_timestamps[self.current_image_index - 1][0]
        
    #     # 构造SQL查询
    #     if start_timestamp:
    #         sql = "SELECT timestamp, event FROM text_events WHERE timestamp BETWEEN ? AND ?"
    #         params = (start_timestamp, current_timestamp)
    #     else:
    #         sql = "SELECT timestamp, event FROM text_events WHERE timestamp <= ?"
    #         params = (current_timestamp,)
        
    #     cursor = self.conn.cursor()
    #     cursor.execute(sql, params)
    #     results = cursor.fetchall()
        
    #     # 修正2：在操作表格前解绑事件，避免触发
    #     self.grid.Unbind(gridlib.EVT_GRID_CELL_CHANGED)
        
    #     # 清空表格
    #     if self.grid.GetNumberRows() > 0:
    #         self.grid.DeleteRows(0, self.grid.GetNumberRows())
        
    #     # 添加新行
    #     if results:
    #         self.grid.AppendRows(len(results))
            
    #         # 设置单元格值 (只显示事件，时间戳不需要)
    #         for i, (timestamp, event) in enumerate(results):
    #             self.grid.SetCellValue(i, 1, event)  # 只显示事件文本
    #             self.grid.SetCellValue(i, 0, "0")   # 初始化为未选中
        
    #     # 重新绑定事件
    #     self.grid.Bind(gridlib.EVT_GRID_CELL_CHANGED, self.OnEventSelected)


    # def LoadTextEventsForCurrentImage(self):
    #     """加载文本事件 - 简化版本，假设invalid列一定存在"""
    #     if not self.image_timestamps or self.current_image_index < 0 or not self.conn:
    #         return
            
    #     # 获取当前图像的时间戳
    #     current_timestamp = self.image_timestamps[self.current_image_index][0]
        
    #     # 获取前一个图像的时间戳作为起始点
    #     start_timestamp = None
    #     if self.current_image_index > 0:
    #         start_timestamp = self.image_timestamps[self.current_image_index - 1][0]
        
    #     # 固定查询包含invalid字段
    #     if start_timestamp:
    #         sql = "SELECT timestamp, event, invalid FROM text_events WHERE timestamp BETWEEN ? AND ?"
    #     else:
    #         sql = "SELECT timestamp, event, invalid FROM text_events WHERE timestamp <= ?"
        
    #     params = (start_timestamp, current_timestamp) if start_timestamp else (current_timestamp,)
    #     cursor = self.conn.cursor()
    #     cursor.execute(sql, params)
    #     results = cursor.fetchall()
        
    #     # 在操作表格前解绑事件，避免触发
    #     #self.grid.Unbind(gridlib.EVT_GRID_CELL_CHANGED)
        
    #     # 清空表格
    #     if self.grid.GetNumberRows() > 0:
    #         self.grid.DeleteRows(0, self.grid.GetNumberRows())
        
    #     # 添加新行
    #     if results:
    #         self.grid.AppendRows(len(results))
            
    #         # 设置单元格值
    #         for i, (timestamp, event, invalid_value) in enumerate(results):
    #             self.grid.SetCellValue(i, 1, event)  # 显示事件文本
    #             self.grid.SetCellValue(i, 0, "1" if invalid_value else "0")  # 设置选中状态
                
    #             # 如果选中，添加到选中行集合
    #             if invalid_value:
    #                 self.selected_event_rows.add(i)
        
    #     # 重新绑定事件
    #     #self.grid.Bind(gridlib.EVT_GRID_CELL_CHANGED, self.OnEventSelected)
    
    
    def LoadTextEventsForCurrentImage(self):
        if not self.image_timestamps or self.current_image_index < 0 or not self.conn:
            return
            
        # 获取当前图像的时间戳
        current_timestamp = self.image_timestamps[self.current_image_index][0]
        # 获取下一个图像的时间戳作为结束点
        end_timestamp = None
        if self.current_image_index < len(self.image_timestamps) - 1:
            end_timestamp = self.image_timestamps[self.current_image_index + 1][0]
        if end_timestamp:
            sql = "SELECT timestamp, event, invalid FROM text_events WHERE timestamp >= ? AND timestamp < ?"
        else:
            sql = "SELECT timestamp, event, invalid FROM text_events WHERE timestamp >= ?"
        
        params = (current_timestamp, end_timestamp) if end_timestamp else (current_timestamp,)
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        results = cursor.fetchall()
        
        # 暂时解绑事件，避免在设置值时触发
        #self.grid.Unbind(gridlib.EVT_GRID_CELL_CHANGED)        
        # 清空表格
        if self.grid.GetNumberRows() > 0:
            self.grid.DeleteRows(0, self.grid.GetNumberRows())
        
        # 添加新行
        if results:
            self.grid.AppendRows(len(results))
            
            for i, row in enumerate(results):
                timestamp = row[0]
                event = row[1]
                invalid_value = row[2]
                
                # 分别在时间戳列和事件列显示数据
                self.grid.SetCellValue(i, 1, str(timestamp))   # 时间戳列
                self.grid.SetCellValue(i, 2, event)            # 事件列
                self.grid.SetCellValue(i, 0, "1" if invalid_value else "0")
                #if invalid_value:
                #    self.grid.SetCellValue(i, 0, "1")
                #else:
                #    self.grid.SetCellValue(i, 0, "0")
                self.grid.SetCellRenderer(i, 0, gridlib.GridCellBoolRenderer())
                
                
                # 提取鼠标点击位置 - 只处理click事件，过滤OnFocus事件
                if "click" in event.lower() and "onfocus" not in event.lower():
                    import re
                    #match = re.search(r'$(\d+),\s*(\d+)$', event)
                    match = re.search(r'\s*(\d+),(\d+)', event)
                    if match:
                        try:
                            x = int(match.group(1))
                            y = int(match.group(2))
                            self.click_positions.append((x, y))
                        except ValueError:
                            pass
        # 重新绑定事件
        #self.grid.Bind(gridlib.EVT_GRID_CELL_CHANGED, self.OnEventSelected)
           
    def OnEventSelected(self, event):
        """处理事件选择状态变化"""
        row = event.GetRow()
        col = event.GetCol()
        
        if col == 0:  # 只处理选择列的变化
            selected = self.grid.GetCellValue(row, 0) == "1"
            timestamp_str = self.grid.GetCellValue(row, 1)
            event_text = self.grid.GetCellValue(row, 2)
            
            # 更新数据库中的选中状态（包括时间戳）
            if self.conn and timestamp_str and event_text:
                try:
                    cursor = self.conn.cursor()
                    # 使用时间戳作为条件
                    cursor.execute("UPDATE text_events SET invalid = ? WHERE timestamp = ? AND event = ?", 
                                  (1 if selected else 0, timestamp_str, event_text))
                    self.conn.commit()
                except (sqlite3.Error, ValueError) as e:
                    wx.MessageBox(f"Database error: {e}", "Error", wx.OK | wx.ICON_ERROR)
                #self.LoadTextEventsForCurrentImage()

    def OnTaskDescChanged(self, event):
        """处理任务描述变化事件 - 保存到数据库"""
        if not self.conn:
            return
        new_desc = self.task_info_text.GetValue()
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE task_info SET task_description = ?", (new_desc,))
            self.conn.commit()
        except sqlite3.Error as e:
            wx.MessageBox(f"Error saving task description: {e}", "Error", wx.OK | wx.ICON_ERROR)
             
    def LoadTaskInfo(self):
        """加载并显示任务信息"""
        if not self.conn:
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM task_info")
            task_info = cursor.fetchall()
            
            if task_info:
                # 格式化任务信息
                info_text = ""
                for task in task_info:
                    task_id, db_filename, task_desc, start_time, user_id = task
                    # info_text += f"Task ID: {task_id}\n"
                    # info_text += f"Database: {db_filename}\n"
                    # info_text += f"Description: {task_desc}\n"
                    # info_text += f"Start Time: {start_time}\n"
                    # info_text += f"User ID: {user_id}\n"
                    # info_text += "-" * 40 + "\n"
                    info_text += task_desc
                
                self.task_info_text.SetValue(info_text)
            else:
                self.task_info_text.SetValue("")
                
            self.task_info_text.SetEditable(True)
            self.task_info_text.Bind(wx.EVT_TEXT, self.OnTaskDescChanged)
        except sqlite3.Error as e:
            self.task_info_text.SetValue(f"Error loading task info: {e}")

if __name__ == '__main__':
    app = wx.App(False)
    frame = DatabaseBrowser(None)
    frame.Show(True)
    app.MainLoop()