'''
Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
Date: 2025-04-11 10:08:37
LastEditors: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditTime: 2025-04-23 11:27:26
FilePath: \code\client_browserV5\images_plugin.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
#!/usr/bin/env python
import os
from PIL import Image
import io
import wx

class ThumbnailFrame(wx.Frame):
    def __init__(self, parent, title, image_folder, image_path):
        super().__init__(parent, title=title, size=(800, 600))
        
        self.panel = wx.ScrolledWindow(self)
        self.panel.SetScrollbars(1, 1, 1, 1)
        
        self.grid_sizer = wx.GridSizer(rows=0, cols=1, hgap=10, vgap=10)
        self.panel.SetSizer(self.grid_sizer)
        
        # load image
        self.load_images(image_folder, image_path)
        #self.image_path = image_path
        
    def load_images_folder(self, folder_path):
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_path = os.path.join(folder_path, filename)
                try:
                    with Image.open(image_path) as img:
                        img.thumbnail((150, 150))
                        # change images wx.Bitmap
                        width, height = img.size
                        img_data = io.BytesIO()
                        img.save(img_data, format='PNG')
                        img_data = img_data.getvalue()
                        wx_image = wx.Image(io.BytesIO(img_data))
                        bitmap = wx_image.ConvertToBitmap()
                        
                        img_button = wx.BitmapButton(self.panel, bitmap=bitmap)
                        img_button.SetToolTip(filename)
                        
                        self.grid_sizer.Add(img_button, 0, wx.ALL, 5)
                except Exception as e:
                    print(f"Error loading image {filename}: {str(e)}")
        
        self.panel.Layout()
        
    def load_images(self, filename_list, image_cache_path):
        for filename in filename_list:
            #if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            #    image_path = filename
            if filename[0].lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = filename[0]
                #image_path = "./_cache/" + image_path
                image_path = image_cache_path + image_path
                
                try:
                    # 使用PIL打开图片并调整大小
                    with Image.open(image_path) as img:
                        # 调整图片大小为缩略图
                        img.thumbnail((750, 500))
                        # 转换为wx.Bitmap
                        width, height = img.size
                        img_data = io.BytesIO()
                        img.save(img_data, format='PNG')
                        img_data = img_data.getvalue()
                        wx_image = wx.Image(io.BytesIO(img_data))
                        bitmap = wx_image.ConvertToBitmap()
                        
                        img_button = wx.BitmapButton(self.panel, bitmap=bitmap)
                        #img_button.SetToolTip(filename)
                        self.grid_sizer.Add(img_button, 0, wx.ALL, 5)
                except Exception as e:
                    print(f"Error loading image {filename}: {str(e)}")
        
        self.panel.Layout()
