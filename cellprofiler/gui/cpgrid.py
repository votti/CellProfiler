"""cpgrid.py - wx.grid helpers for cellprofiler
"""

import StringIO

import wx
import wx.grid

from cellprofiler.gui import draw_bevel, BV_UP, BV_DOWN

BU_NORMAL = "normal"
BU_PRESSED = "pressed"

class GridButtonRenderer(wx.grid.PyGridCellRenderer):
    """Render a cell as a button

    The value of a cell should be organized like this: "key:state"
    where "key" is the key for the image to paint and "state" is the
    state of the button: "normal" or "pressed"
    GridButtonRenderer takes a dictionary organized as key: bitmap. This
    dictionary holds the images to render per key.
    """

    def __init__(self, bitmap_dictionary, bevel_width=2):
        super(GridButtonRenderer,self).__init__()
        self.__bitmap_dictionary = bitmap_dictionary
        self.__bevel_width = bevel_width

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        dc.SetClippingRect(rect)
        dc.Clear()
        dc.DestroyClippingRegion()
        bitmap = self.get_bitmap(grid, attr, dc, row, col)
        state = self.get_state(grid, row, col)
        if state is not None:
            bv     = ((state == BU_NORMAL and BV_UP) or
                      BV_DOWN)
            rect   = draw_bevel(dc, rect, self.__bevel_width, bv)
        else:
            bw = self.__bevel_width
            rect = wx.Rect(rect.Left+bw, rect.Top+bw, rect.width-2*bw, rect.height-2*bw)
        dc.SetClippingRect(rect)
        if bitmap:
            dc.DrawBitmap(bitmap, rect.Left, rect.Top,True)
        dc.DestroyClippingRegion()

    def GetBestSize(self, grid, attr, dc, row, col):
        """Return the size of the cell's button"""
        bitmap = self.get_bitmap(grid, attr, dc, row, col)
        if bitmap:
            size = bitmap.Size
        else:
            size = wx.Size(0,0)
        return wx.Size(size[0]+2*self.__bevel_width,
                       size[1]+2*self.__bevel_width)

    def Clone(self):
        return GridButtonRenderer(self.__bitmap_dictionary, self.__bevel_width)

    def get_bitmap(self, grid, attr, dc, row, col):
        """Get a cell's bitmap

        grid - the parent wx.grid
        attr - an instance of wx.grid.GriddCellAttr which provides rendering info
        dc   - the device context to be used for printing
        row,col - the coordinates of the cell to be rendered
        """
        value = grid.GetCellValue(row,col)
        key = value.split(':')[0]
        if self.__bitmap_dictionary.has_key(key):
            bitmap = self.__bitmap_dictionary[key]
            return bitmap
        return None

    def get_state(self, grid, row, col):
        """Get a cell's press-state

        grid - the grid control
        row,col - the row and column of the cell
        """
        value = grid.GetCellValue(row,col)
        values = value.split(':')
        if len(values) < 2:
            return None
        return values[1]

    def set_cell_value(self, grid, row, col, key, state):
        """Set a cell's value in a grid

        grid    - the grid control
        row,col - the cell coordinates
        key     - the keyword for the bitmap
        state   - either BU_NORMAL or BU_PRESSED
        """
        value = "%s:%s"%(key,state)
        grid.SetCellValue(row,col,value)
        grid.ForceRefresh()

    def set_cell_state(self, grid, row, col, state):
        key = grid.GetCellValue(row,col).split(':')[0]
        self.set_cell_value(grid, row,col,key,state)

EVT_GRID_BUTTON_TYPE = wx.NewEventType()
EVT_GRID_BUTTON = wx.PyEventBinder(EVT_GRID_BUTTON_TYPE)

class GridButtonClickedEvent(wx.PyCommandEvent):
    """Indicates that a grid button has been clicked"""
    def __init__(self, grid, row, col):
        super(GridButtonClickedEvent,self).__init__(EVT_GRID_BUTTON_TYPE,
                                                    grid.Id)
        self.SetEventObject(grid)
        self.SetEventType(EVT_GRID_BUTTON_TYPE)
        self.__row = row
        self.__col = col

    def get_col(self):
        """Column of clicked cell"""
        return self.__col

    def get_row(self):
        """Row of clicked cell"""
        return self.__row

    col = property(get_col)
    row = property(get_row)

def hook_grid_button_column(grid, col, bitmap_dictionary, bevel_width=2,
                            hook_events=True):
    """Attach hooks to a grid to make a column display grid buttons

    grid - the grid in question
    col  - the index of the column to modify
    bitmap_dictionary - a dictionary of bitmaps suitable for GridButtonRenderer
    """
    renderer = GridButtonRenderer(bitmap_dictionary, bevel_width)
    ui_dictionary = { "selected_row":None }
    event_handler = wx.EvtHandler()
    width = 0
    for bitmap in bitmap_dictionary.values():
        width = max(bitmap.Width,width)
    width += bevel_width * 2
    grid.SetColSize(col, width)

    def on_left_down(event):
        x = event.GetX()
        y = event.GetY()
        coords = grid.XYToCell(x,y)
        if coords and coords.Col == col:
            row = coords.Row
            if renderer.get_state(grid,row,col) == BU_NORMAL:
                ui_dictionary["selected_row"] = row
                renderer.set_cell_state(grid,row,col, BU_PRESSED)
                grid.GridWindow.CaptureMouse()
                event.Skip()
        else:
            if event_handler.NextHandler:
                event_handler.NextHandler.ProcessEvent(event)

    def on_mouse_move(event):
        if (ui_dictionary["selected_row"] is not None and
            grid.GridWindow.HasCapture()):
            x = event.GetX()
            y = event.GetY()
            coords = grid.XYToCell(x,y)
            row = ui_dictionary["selected_row"]
            selection_state = BU_NORMAL
            if coords and coords.Col == col and coords.Row == row:
                selection_state = BU_PRESSED
            if renderer.get_state(grid, row, col) != selection_state:
                renderer.set_cell_state(grid, row, col, selection_state)
        if event_handler.NextHandler:
            event_handler.NextHandler.ProcessEvent(event)

    def on_capture_lost(event):
        if ui_dictionary["selected_row"] is not None:
            renderer.set_cell_state(grid, ui_dictionary["selected_row"],col,
                                    BU_NORMAL)
            ui_dictionary["selected_row"] = None
        else:
            if event_handler.NextHandler:
                event_handler.NextHandler.ProcessEvent(event)

    def on_left_up(event):
        if (ui_dictionary["selected_row"] is not None and
            grid.GridWindow.HasCapture()):
            row = ui_dictionary["selected_row"]
            if renderer.get_state(grid, row, col) == BU_PRESSED:
                renderer.set_cell_state(grid, row, col, BU_NORMAL)
                grid.AddPendingEvent(GridButtonClickedEvent(grid,row,col))
            ui_dictionary["selected_row"] = None
            grid.GridWindow.ReleaseMouse()
            event.Skip()
        else:
            if event_handler.NextHandler:
                event_handler.NextHandler.ProcessEvent(event)

    col_attr = wx.grid.GridCellAttr()
    col_attr.SetReadOnly(True)
    col_attr.SetRenderer(renderer)
    grid.SetColAttr(col, col_attr)
    if hook_events:
        grid.GridWindow.PushEventHandler(event_handler)
        event_handler.Bind(wx.EVT_LEFT_DOWN, on_left_down, grid.GridWindow)
        event_handler.Bind(wx.EVT_LEFT_UP, on_left_up, grid.GridWindow)
        event_handler.Bind(wx.EVT_MOTION, on_mouse_move, grid.GridWindow)
        event_handler.Bind(wx.EVT_MOUSE_CAPTURE_LOST, on_capture_lost, grid.GridWindow)
    return renderer, width

if __name__ == "__main__":
    import wx.lib.inspection
    IMG_RABBIT = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00(\x00\x00\x00(\x10\x02\x00\x00\x00S\x0c\xf3y\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x00H\x00\x00\x00H\x00F\xc9k>\x00\x00\x00\tvpAg\x00\x00\x00(\x00\x00\x00(\x00\xa3p\x94\xf8\x00\x00"\xa7IDATh\xde\x05\xc1\x05@\x95\xd7\x02\x00\xe0\x13\x7f\xdd\xbe4\x08*N\xec\xee\x9e\xad\xb3\x9dN\xd4\xd9\xc1lgw\xb7\xb3gL\xf7\xd4\xcd\xee\xee\x9a\xdd\x81\x89\x81\x18\x08\xd2\xdc\xfe\xfb\x9c\xf3\xbe\x0f\xae[|4\xae\xe7\x0c\xf4;\xca\x80\x16c1\x18\x0c\x16\x18\xbf\x9b\xeb\xcd\x15,\xc8\xf6\xb3\xca\xb0\'\xb8\n"\xe9\xdft;}\x0f{\xc3\xbeL\x04\xab\xc0R\x16\x07\xe6\x82\x1d4\x9f\xb4\xa6>\xc3bV#\x06\x89`\x91\xac\x17\xbc\xcd\xaf\xe5Ns]\xb9\xb9\xa8?z\x8b\xf3\xf0)\xf4\t.G\x08m\xa5yl?\xebM\x1f1\x08\x8e\x82<\xb6\x0e\x16\xc3{\xa0:*\x01/\xa3Q\xb0\x10\xa6\xb3\xeb \x08t6\x82N o\xe9&s\x06]\xcet\xb6\x03\xac\x80G\xc0nn-\x8a\x01=\xd0f\xf8\x02\xa9p&\xbc\x82\x9bB\x11,\xe1\xfa\x81O \x1f\xde\xa7\x91\xec\xa6i\xb2W\xec\xb5\t\xc1P\xb6\x85\x15\xa2\xd1\xf0\x14>\x0f:\xb1\xf1\x98\xc2D\xb4\x0c?\xc1\x8b\xf9\xadp.\xb9N\rC\xc0?5\xe8\x1d\xaa\xd2\x00\xe5\xa3f\xfc\x07P\xc8\x00:\x02\x0e\xb0\xcf\xa0\x15,\r\x0e\xc3\x1e\x10\xb3\xc9\xe0\x19<\x05\x1e\x83\xcd`\x01h\xc2f\xc3\xbe\xa02\xe8\xc0j\xb2\x0ed\xa49\xc5,OV\xd3\xc1\xa4\x80\xc62\x83\xa6\xb2z\xe0\x04}\x0c\x9a\xe2tP\x17Z\xe06\xb8\x0f\xd4#[\xd9o\xd4\xc1\xde\xb2\xae\xb4)\xe5H.\xe9D\x82\xa4;\xa9K\xca\x81^\xe4G\xf0\'Xa\xf6\x067\xc1`\xf6\x18ua}8U\xa8\x866[t\xdc\x06V\xe6\x87B\x02\x17\x82\xcal\x06xf\xd6d\xa3\xd8Ls4H\x05\xafP4\x94\x99\x8d\x7f\t1{\x08v\xb3\xc9\xcc\xc2\x0e\xc2+\xac\x1f\xb0\xa2O@\x81<\xac\x06\xea\xc3\x07\xb0\x0f\xec\nO\xc3\x85\x90\x80\xa9l-\xe8\x07_\xb3\xa1t\x08\xc9C\xb4\x055\xd8\x03\xba\x81\xa6\x81\xcf\xc0F\x0f@\x07\x1a\x00\xbe\xe3\xd6X\x05K\xe0%\\\rn\x82!\xee\x14\x8a\x83\xb9\x1cD\rQM\xf4\x13\x8c\x02\xbf\x82\xb9\xa0#\x88\x04\xab\xa8\rT\x03\x90~\x87\x0f\xd9~z\r\x8c\xa2\xf5\xcc\xeb\xc6\x00:\x8d\xac\xa2&\xfeBWX\xbe\xdb\'\xe0\xd9\xb1\x99\xe1_D\xe5\x87\xa4\xc8\x9dRn9O\xc4vQM:\x1fv\x88_R\xa6\x97s\x04\xf6\x94\xd2\xdc[9\x94\xe8\x8b\xa8/f\x94\xfb\x12=F\x1c_\xa1_\xect\xcb\x81\xca-\xe2\xc6XfV\xbe\x1e\xf9T\xbaV\xfe\xb2\xed\n\x0f\xa3v@?\x1b*\xdc3%3\xcb|B\xa7\xd3\xb34\x12Vf{Ay\x18d\x00=\x82*KD\xb5\xe050\x0f\x16\x00\x9d\xedb\xc3\xe8=\x96\xca.\xd2\xb9Dg\x83H;\xb2\x1a\xbc\xe7HI\xa2\x90\x8ad\x13\x89\xd0\xf6\x03\x01\x84P\x07$\xa3p\xf0\x03\xea\x81\x86\x80\xd5p\x08\xe8\x02W\xa2<<\x94k\xc3\xaa\x83\xb3d<\xc9\xa4\x13X:\xebcT\xc3[\xe8v\\\x8f\x9d\x81\x8dAC\xa6\xb0tP\xc4F\xc3Y(\x9d\xf5\xe5\xcb\xe3W\xce\xe9\xee\xcdR\xbf\xc4q\xd1el\xb3\xcb\x1d\xb6M\x94FD\xfb\xf1{\xd8MhB)\x89\xa5\xdd\xcd\\s\x97\x99\xa3\xaf\xd1Vj\xb3`M\xf8\x145\x12\xba\xe0\x91BUlg\xdd\xe8K\xbc\t\x9d\xe2n\xe1\x01\xfcF~;\x9d\x8e\xba\x19U\nU\x9d|.\x9b{0x\xf1\xc3r\x7fu35\xa7\x16}\xc3bh\'\x94\x0c\x9b\x80?`-\xf8\x1f\xdc\xc3\xa2X\'\xb8\x17<\x06y\xc0Fg\xb2\x07\xac&\xadL\x9f\x81\x8e\x80\x87\xcd\xe1W\xf23\xe1P_\xdc\xaeJ\xaf\xa2\xaa\n\x18\x0c\x1a\xb1\xae4\x9e\xf5\xa7\x01\xd8\x1b\x9eb\x03\xb0\x0b>\x86a\xf8\x7fp\x0f\xfe\x8a\x9e\xa0\xcb\xb0\x01L\x81\x1e\xf8\x0e\x9c\x02\xd7\xe9\x00\x1a\xcf\xd2\xcda,\x99\x9d\xa49H\xc6:hl\x19(\xf4\xb4U\x88H\xb5\x86\x959^\xaeqt\x9bf;\xcb\x92\xc8\xb5\xf5\xd6E\xb4\xb7m\x8a\x9e\xc0\xb5!\xdd`6\xeeG\xe6\x81\x95\\\x0fv\x14\xfc\x08\'\x91r\xac\'\xa0\xe6z&hu\xe4\x8b*\xf6\xd7\xf6\xfc\xee}\xe4G\xc5c|q\xeaNy\xa9\\\xcahg8\x8d-`\x18\x18\x88j\xba;K\xd1\xd1\xc5\x8eM\x16\x10y\t\xec\xc0Gp\xc9\xe0?j\x8f\xc2\x1d\x0c\x82\xe9\xd4\x8fO\xa1n\xdc\x19\xb0\x12,G\'\xe8\x00\xf0\x18\xb4\xa2:+\x0f\xffG\'\xb0\xb3\xc8\xcd^\x92\x7fQ-v\x8a\xf9\xf0H\x0e\xf7\x81-\xf9Yl;p\x90R\xc0\x04\x15\x8c\'\xb8\x0e\\\x04\x9e\xc2\xeb\xb04\xdc\x03\xc6\xc1,X\xcc\xe2@.\x9cIW\xd3\x14z\xd9<M\xf2\xe9as\xa59\xc4\x9ca,7\xbdz\x0fK)\xe1\xb9\xeb|\xe4q\xc7\xd5\x1f\xe4R\xbd\xc3j\xd6\xce\t\xb3\x0b\xde\x92<7\x8a\x94\xc3\x7f\xea7\x95\x9e\x81\x89jH\x8e\x0f\xde\xd5Z\xa8DC\xc6\x0f\xe6v3\xc6\xd8o\xde U\xe5\x11\xf2p\xad\xb1\xfcA\xed\xa9\x80P\xbc\xfc2t1X\xc1\xff(P\x8a\xaf\xcb\xf7\x11\xfe\xb6=r\xf4\xb7\xf7\xb7\xdal\xcd\xedSl\xdf\xc5v\xb6\x1f\xf8!\xd63\\Yk\x11\x7f.v\xbb\xfb\x9b\xf0\x93\xefd\xb0\x9f\x11\xccO$\xf7\xcd\xbe\xfaLx\x1a\xa6pC`\x1fT\x1a\xda\xd950\x89V\xa3\x1f\x89\x0fl\x00g\xe8l0\x86\xf9\xd9\x1d6\x8bCuX\x0f\xd4\x9b5\x06\xff\x80)l2\xe4\xcc\xbe\xf0$\xea\xc0^\x80D\x88\xe9K\xb2\x1f<\x86}\xc1a\xba\x06<7\xc3\xc9\x05\xb3\x92\xde\xd28\xa6\xad7\x86\x1a\xa3\x89)\x1e\xe0\x1a\x84=\x8f\xe6\xed?\x95\x9b\x98x)\xc2U\xabG\xdc;\x97Pa\xb0\xd6\xdc\xdf\'\x90X\x1cYT7\xeb\x86o\xb3oL\xf1\x15\xbd\xb1V`\xa4h\xdf5`,49\xf2\x84\x9d\x02\x91HEM\xe8@\xda\x07\xccQkj%\xb4\x0fJ\xae\xbaUY/OVG(\x1f@\x19m\xa5~R\xfdl|4;\x07\xb2B\xd3\xe5\x0e\xc6\xbfZ\x96\xd6\xdc\x15\xe3\xcat\xbb#w\xc4\xfc\x15\x1e\xe9~f\xc5e/\xe2\x00\xfa\xc52F\xfd\x04\xba\xfb\xb6\xb3\xb3h\xa3\xf9\xb7\xd1\x19v\n\x18\xa4\x1a\xa9J\x1b\xc3S`#\xb4\x83\x8a\xe0 \x1c\xcaz\xb0\x04\xb2\x9c3\x8a\xcc\x15\xe6\x0e\xf0+\xacJ?\x811\xe8*H1\xc3\xc9&\xba\x0e\x86\xc3\xc7\xb04\xe8\n\xfe`\xf3\xc0BP\x00d3\xcc\x1c\xa1\x1f\xd1-zW]Ec\x00\x93\xcc\xa4?bo4\xff\xb7\xbc\x18\xb7\xaa\xfe\xd1\xb0:\xd2\xd9\x88cJ\xdd\xa0\xd3\xcb)\xc9\xc1\x86\xde\x95\x81|_\x9a7\xa3\xa8~\xe1\xc4\xe2\x81\x9e\xef\xde\xa5~\xc2\x1eC\x1eS\xa9\xa3\xe5\x83\xad\xab\xed\xa6\xbd\xb5}V\xd4\x94X\x16\xfeK\xe0\xabo\x8b?S.\x13\xfa\x14\x9a\x16\xb62\xfcM\xf8\x1cu\xbavK\xdfI^\x9a-I\xb4qL/\xad\x87\x02\\\xe8\xa9<\x0c\xbd\xe6\x9a\x08ml\x17\xe5/\xae\x07\xd6\xd2\xe4?GL\x8c\xe6\xa8Y{!Z,\x0e2n\xc8mX\xb9\xac\x97\xf9\xbd\xf5\x99/\x03\xb4=\xb8d\xf4\xc5\xaf\xc1\x1e\xc1\x0bV2\xca\xf6\xd3\x1a\xf45\x0b\xe2\x1f\x87u-S\xb6\xba\xae\x10\x87\xba\x9blc\x93\xe8HT\x1e\xde\xe6!\x9a\x00\x9a\xf1G\xe0}\xc6\xf8\x03p;\x88\xc0\x0b\xcdq\xe66s)\xdb`N\xe3b]\xf5\xa4\xdb%\'T\xfb\xad\x0ci}9\xfc\xaa%1\xea\x99|\xd3\xf7\xaa\xb8Ya\xbd\xbc?\xb3\xce\xe5E\xe4\xf6\xc9\xb1z&x\xf3\xbcG\x95\x89jk}\x85\xb2M\xebl\x1c\xa5&\x18\x83\xeeHo,G,\xb1\xee5\x8e>\xce<n\x1d\xac\x0f\xcf\x1bS\x8c\x92\xe6\x03\xda\x97$\xb3L\xf6\x88\x96\xa4\xe9\xa0/mJ\xea\x08?\xf2\x07\xb8r\x16(\r\xb4\xc4\x9a\xb3\xc9 \xf2\x9b\x16f(\xfa\x10m\xa4N\x8dY\x80g\x99\xe8;X@\xc2\x08\xc1:(\xc6T\\\xc6\xdd\xb3\x9e\x86\xbf\x81\t\xb4\x8f\xb9\x17\xee3z\x937\x90\xa9\x0f\xd0J\xf8\x0c4F\x07P\x14\xdb\xc7\xd9\xe7\x8be\xa3\x9b\n;p-\xeb1\xe1,\xf7\xca\xf1#\x8ec\x0e\xfe\x01?\x08\xaf\xe5/q1\x9c\x8f\xbf\x0e\xba\xa2rl\xad\x1eg\x00%\x96-#\x91\xf0DX\xbamb\xdc\xae\xd8y.1A\x04\xd7\xcdj\xe4k`O\xa0j\xd1r\xdfM\xafX\xbc\xbd\xa8Y\xf1\x8c\xe2wr\xa2rS\xbd\xc3\x96\x82u\xa87;\x0cn\xe0(\xd4\x0c\x9d\xc6\rP\x19\xf4\x11M@s\xe1`P]\xe9$g\x86\xa6\xc8\x93C\xdf\xe5\x95\xfa=\xc3\xaa\xcde3\xd9/\xe4\xaap\x82\xaf\xcc\xa5\xa2\x8a\xe8G\x14b\x06\xb8LG\xe26\xa8\x08L\x08\xd9\xe5\xd1\xaa#\xf8o\xc8\xa5\xc8\xa1n\xc1{\xc1y\xb6M\x96\x9b\xfc9\xd7&G\x92\x03;\x0b\xdc\xef\xdc\xbf\xf2i\xb6\x81\xb1+\xc4\xce\x9c_\xa6\xda\x0b`\xf7_\x80\xed\xc1\n\xee\x0f\xf8\x08M\x01\xffq\xf1\x9b\x9d\x85\xd5t\xd73\xb1U\xfc!K\x15\xeei\xd46c\xb3\xfa\xcc\xd8\x82\x15\xcc\xd0=1\xd9\xd2_\x9c\x8e\xde\xa3\xab\xb8/s\x83w4\x19\x9b\xdc\x02l\xb1\x1b6\xc3\xb6\xcc6]Lq\xc4\x05\x1a+\x17\x0bVi\xf7\xb4BC\xd1n\xeb\xf7M\xaf\xea\xd2z\xe9;\xe5yjM5\x89\x05\xc1A\x14\xd4\xa7\x93"V\x89\x07\xe0\x1f\xd0\xc9\xf8\xddp\x1a\xb7\xd5\xad\xc6Ojy\xf8\x9e\xf5\'\xf3\xd4\xd6\x9a\x10z\x19\x9a\x16\xe4\xfcP\x9c+-\xb4|\xe1\xd2\xb9:\xc2\x11\xe3w\xf3\x94Y9\xf4L\xb6\x05{*\xf3\x95{j\x17=J\x83F\x86\xd6\xceH!\x03\x94\x05\xf2\xfa\xd0U\xb5\x82\xf5O1^}\xae\xdc\x95?\xf9\xbf\x86\x92\x02\x97\xa2?\x87\x0bqm\x19t|\x12N\xc1\x02\xf1\x1a\xf7\x90}\x05\x8d\xe17\x10\x0f\xab\xc2\xf7xhz\xffAC\x07\xb2\xabf\r\xceC\xba\x19{\x8d^l\x0e\x18\x0b\x0f\x92\xa6\xd4e>#\xf1fU}\x0e\xff\x85\xcf\xc2!\\\x8c\x06\xe0,\xc7+g\xa1\xf3\xa7\xc8C\xd1\x95\xa2!\x1dOV\x1b\xa7s\x1f|\xaf\xf7\xed\xa7\xef\x97\xbe5\xfcZ\xe4\xe9\xe5}\xe6\xeb\x1e\xca\x91\xf3\xe4\xb4\x80\x19\xc4\xa1(\xefB\xdf\xc6`o\xfd\x9cy\x80$\x1b\x8f\x8dL\xdd\x85/\xa1u\x0c\xbb~wX\xad\t6\x8f\xd4\x97\xaf(\x9c\xe6\x06\xc1\xa3\x8c\x03\xd5IR\xa0}0R~\x17<*\x07\xe4fJ\x1bUPK\x1a\x11\xfa?z\x7fY\x08\x19\xb2n<3\'\x1a\xcd\xf9vB\xaa0,\xac\\DzX\xac\xfb\x803\xda\xb1\\p\xf0\x89\\]C6*\xe9\xaf\xe4o\xc1\x97\xc1\xd7\xe4\n\x1enl\xe4D\xeb7v\x80\x95F\xb3\xe5w \x00\x93\xcdg\xb8\xb7\xd1s~\xaf\xcbfes yA\x9a\x9b\xfd\x8ddT\x1fYa\x15\xc1&H\\\xa6\xe5\xba\xa5\xaex\xcb\xb2\xd7zP\xdc\xea\xfc\xe2xck\xe7\x9c\xe2<f\xcf\xc2\x97Q[\xd8\'w\xc4\xf7=\x99\r\xf3\xe7\xe4\xb4\xcb\x9eZX\xa1po\xc1\xec\xecs9\xde\xdc\x12\x85\xad<\r\xbc\xbb\x82\xefB6\xb9X\xceQ\x17\xa8\xb7\x8bS|\x99\xbe\xd2\xc1\xab\x81i\xfe\xcaD$\xc8\xec\x89\xd6\xa1\x1f\xf8\xc5ym\n\xfa\x15\x96\n\xb8\xe4m!\xb7\xd1\x84<0k\xe5\x1d\xcb\xdd\x98\xff006\xf4EI\xd2\xf6k\xf5\x8d\xdf\xd4\x87\xea_\xaa[\x1d\xa2%\xe8\x04\xdb\xf0E\xae\xad5d\xf5Ks\xc5\x86\xc2\x02\xde\x0ej\xd2\x15\xd4\r\n\xd8\xdfT\x04;@e\xd6^\x9e\xa2!%\x91\xc6\x08u\xd5LhZ\xaa\xaa\xe7\xcd\xb705X\x83\xae\x82\xab(\x85\x07\xd1\xbe\x9d\xff~G#\xf10\xae\xb5M\xb5"kI\xe1 \xb7\x8b\x1b,\x9d\x92~\x94\x06[zY\xb6\x8b\x1b\xf1An\x0c\x97\x1a\xf6\xc5\xcd\xb9o\x08.>\x8c\x7f\xe9{\xec\xbd\xe6k\xf4i\xd4\xc7\x7f\xdf\x99\xde]\x9e\xc4\xa2%E{\x8b\xeb\x17\xd7|?\xf2\xa33c\x84\xefB 2\x98\x86\xdbsK\xf0e\\\x19\xbf\xc3\xff~\xff+wY\xde.c\x80qO\xd9\x10\xb6\xde9\xc6\xb9;*&2?6\'\xf3\x97\xecR\xdf\x1d\xe8)\x06(56=\xa6[\xc4i~\x14\xcag&\xcbc\xf10\xc5xh~#\xcd\xf4\xda\xfa$}\x07\xb8\xc5^\xa3\xf2\x96\xa3\xd2|\xb1\x85\xe3\xb8\xb3\x9am\xaf\xbd\x95\xb5\xbb\xe5\x16;L\x11\x9b\x80\xfb\xe0\x08\\E\xb8&\xfc"(\xc1\x90\x12\xa9\x94\x83\xa9\xee\x84\xc0\x9f\xfc\xab\x88\xb5~\x11\xf4\x16\x97\xca98\x07\xff\x83\x1b#S#u\xe9Tx\x185@\xbf\xda\x89\xfd\xb1\xa3X\x98*b>\x93T"\x83\xd5\xb3!\xd1?\xdcs\xd7w\xb9\x08\x15\xd4\xf5\x94.\xeeR\\!\xf7Q\xce\xfe\xdc\x01\x9f\x0fd\x1cK\xaf\x90\xf3>\xe7\xf6\xf7s\x85\xdd\x8a\xbfy\xb7{w\x04f\x862\x94sj\x1b\xf5\xb4\x9a\xac}\xd0\xc3\xe9@\xf6\x15\xf8\xf8\x7f\xf8\xb7|\x17:\x8d\xb6"u\x8d\xf3\xc6z\xadP{\xa9\x1d\x0b\x8d\x08\xfc\x13\x1cU\x1c\x9b~\xe8\xe3\x97\x8c\'w&>\x8cJ\xfd\xf6d\xe5\x8b\t\xe9\x95-\x01\xdbD\xe7\xa7\xa8\xc9\x91\xb5\xdc\xd8zGZ\x87\xf3iM\x9ai\xa62;\x9dI\x9b\xc9\xc92/o\x08x\xfd7\x03&w\x1b\xa7\xa3\xe7\xc2\x07^\xc2U\xb8\xf38\x1a:p8\xaa\x0ev\x89\xf7\xf9\xd3\x1c@\x9bYK8\xce\xecmd\xd3?\xe8S\xf2\x81=\xa1\x8f\xe9\x040\x1a\xb9*8\xef9;\x85\x1b\xce[N\xbb\xb1I\t\x0f\x8e\x97\xc3\x03\x1f<\xd5eo`\xbc\xaf\x8dV\xa0\xb6\x91G\x91pz\xd4p\xfa\x1b\xfbW\x04_yb\xbc\x0b\xfd\xed\x95f\x9a\xa4?\xd5\xce\x19wh\x84J\x0c\xd3\\f\xde\'5\xe9\xaf\xe2k>UP\xa45\xd2t1\x8e\xf6e\xd1\xcc\x16\xd8\x18\xba\xa24c\x99\xf4\x08q\xc4\x0b\xd1w\xa2c\x1a\xe4\xd7\xe9X\xf7\xef\xd6\x87Z$\xb7\x9c\x90\xb0\xa7DJ\xf4e\xb6D?-\x9f\xca\x8b\xcc\x19\xf6\xcd\xfb\xfc\xf4\xf3\x88W\xf3\xac\x93\xad\xbc\xadV\xd2\xd3\xa4%e/A\x03\xcc\x07\xeb\x84\xf3b-<\xd76\xd2\xfe\xc9:^\xcc\x94\xda\x0b#\x94u\xca9\xd5\xa5\xf2\xea\\\xf5\n\x99d\x96\xd5c\xe00\xb0\x8b,\xb5t\x90\xc2pSq?L\xb4]B3\xf4?\xec\x03I{0\x1cw4s)\xa0\xf79\xb0\xd1laL\x95\x9b\x04\xd2\xb45Z+m\xbc:\xda\xf8A?\xa9\xde\x02S\xd8:\x1an\xf9\xd9r\xc1\x12\x1f\xd17fm\xcc\xe9\xe2[\x9e\xb3\xde\xd5\x9e\xea^\xc5?C\x7f\xa6wR]\xfe\xaf!\x8f\xbc-\xd4<t<\xf4$\xd0\xd1\x9f\xec\x9b\xe5\xf7\x06\xfe\xf1\x1f\x80W\xf9\x05B*\x8a\xc1\r\xb9\x83\xe6P\xe3\x85q\xc1\x9d\xed\xda\xe8jQbL\xdc\x90\xd8\x98\x98\x93\xd1\xbbbx\xd73\xc7I\xc7\xcef\x9f\x1b\x855\xd8\x12\xc1\xc2J\xb8\x1b\xe7\x7f(\xdcX\xf4\xc4X\xa3\x87\xebe\xb9]\xf8&W>\xeaj\xc4\xd3\xf0\xc5\xb1{\xa3r\xc3F\x8190\t\x9d\x02\x11`0z\x07\xbcl,\xf8\r|\x00\x8dY#\x1e\xf1\xe5\xf8\x8e\x96\x0f\x96Ib\xb8\xf5\x9eE\x10\xeb\xd0\x1al,\xd3\xb9\xb6t\x1a\xd7\x00M\xa2:\x8bQ\x96\x93\xfb\xc1\x8bt2\xfb\xcbx\x8a\xbb.j?\xb6U\x9b@w\x7f\x8co\x92\xba\xc0\xb8n\xf0\xaa\xa6\x1cV\xb1\xf9\x9fa\xd7_\xe0\x9f\xb8T\xfc\xdd\xf6\xccq/lUN\xa7\xbc\xday\xefr\'\xe7\xb5\xc9-!?Wk\xab\xa3=s}-\xbd\xe5\x02\x8b\x02_\x83\x92g\xa7\xe7\x82\xe7dv\xf3\x9c\x9b\xd9>\xfbM\xc7fG/\xc78G+\xc7_x;j\x87\xa3\xc3\x0e\xbb\xdf\x85\xa5D\xee\x89l\x1e)\n\x1aO\xf9\xbe\xa1FAK\xf0R\xc2\x86x{\x89\xc9\xb1\xe3b\x8bbkH\x011I\xa8i\xdd,\xd5\xb1\x94*1&nu\xecF\xe7!{\r\xdb\'\xd4\x00&\x81\x99\xb8&>\x8f\xd2\x80Jw\xd3=0\x19T\x87\xfb,\xfb\xa4ib-\xfb+\x9b\xc5\xba\xc8\x92l9)\x0e\xe0\xf6\xe2\xd2\xe8.\x8b\xa6M\xc1KT\x83\xb9\xb8\xdb\xb8"\x1e\x8a\x7ff\x9f\xf1\x11F\x8dp6U\xdf\x8c\x02\x05J\t9\x8d\r\xe66c\x95k\xcc\rG7\xe8\x15\xb2\xdd8\xc1M\xe7+\xa0\xb5\xdcv>\x1b\x9f\xcc\xda\x995=[\xf1\'\xf9\x87\xf9\x7f\x01\x1a<\xc4v\xd3\xcb\xac&\xed\xa0\xe6\xa8\xcd\xf4\xb1\xaa\xd38i\x14\xc9\xe7\x8c{\x86\xd5{\xc3?W\xde\xc3w\xe2/\x883\xc3\xfa9\xaf\xb98\xf7]G\x0b\xc7\xec\xb0b\xb7\x1cv\xd0\xd2\xce\xb2\xd1V\x89&\xd2e\xb0\x9c\\Y\xde\xa2\xee\xca\xbc\xff\xedH\xf6\xb5\xdc\x0e9\xae\\YX\x81\xbd\\\xc3\n\xa3\xcbg\x95Or6\xb4?q\x941j\x1b\x7f\x90\xa7"\x95\xd2\xec\x9b\x18\x0f\xdfs\x06L\xe3\xa6\xa2$\xa9\x9bu\x15\x7fZ\x8a\xb3\xa4pnn\x10_\x0fLT\xbe\xab]B\xef\xf3\xbb\x14\xa2\xfc\xc6\xdad\xf3\xa0\x92K\xe7\xb3\x92\xaa\xc6\r\xa4\xbdx\xbb\xeb\x0e<\x9e4\x03\x1c\xd6B\xd21D&\xb1u\x10(\xdd\xd5\xd1F\xb3\x80\xcb?7\x90\x1ar\x84P(\x83_.\x9c\x11\xaf\xd8W\xd8\xc7\xb8\x86z\xdf\xfb\x81\x8f\xcbkY0$\x7fDaz\xe1\xfa\xe2\xce\xfe\xd5~\xe8\xe7\xe5\xc9r\xbc\xdc\xc6o\x0f\xbc\r\x94\xd7\xfe\xd0\xe2\xf5\xff\xc2\xde\x85?\x8a\xb0\xb8xWiw\x19\xe7\x1b\xa7\xe6\xac\xed:\xe2.\xe1\x9a\x06\x96\xa3\x1d\xe88h\x8cvb?j\x82\xf7\xe3\xf1\xe6\x19c\x93\xda\xd9\xe8\xac7\xd0&q\x83\xb1\xcaut\x8eu~t\x0fwNpUt/\x05\x9f\xf1s\xfegc\x98\xe9\x00-Y\x06+D/`S\x16\xc0\x9f\xc5\xdf\xf8\xf1\xd2e\xebWi\x91e"\x86\xa8&Zd\x8a\x86\xdd\xfc\x93\x95d\x9f`gi\xb7e\x9a\x9d\xe0\x81\xb84\xff\x97x\xd7:\xc2\x12a;bo\xe5\nH\x85\xe8\xaa{\xa8X\x014q\xfc\xc2\x91\xdd\xec=8F\x8a\x8d{\xc6LzV\xff\xa85\xd6;\x1b]\xf4x#\xdf\xe8av\xd6\xfe\xa7E\xea\x0b\x02K\x03\xa5\x03\x13\xd4\x03ZI\xfd\x7f\xa4\x884\xa2I\x94\x82\xdf\xc1+\xda\x88\r\x037\xbd\xb1\xde\xba\xbe\xdd\xbeX_\xb8\xf7~D\xed\xf0\xac\xf0,\xd4\x10\xe7\xa1*\xf0:\x92\xe0\x1b\xc1!L\x126\xc9\xd5\xfd\xc5\x81\x9fI)\x9a\xc0r\x85\xb2\xd2B\xcb={K\xa7\xc7\xb9]9 \xf7SL\xe3\x90ie\xf1P\xc4\x8f\xb9\xbf\x14U\xfd\xa2=\xf7\xac\xf47\xf1q4\xd1|m\x16p\x1fQoX\xc2\xb3\xcdw\xdb\xdf\x07\x9e\x01M\xe99\xdbc\xebya\x0b\x9e\x87\xdb\xc3/\xf40\x8d \xab\xa4T\xf1\x84T\x18v\xcf=\xdbu\x8b\x9f\xce\xf7\xe5\x92\x84\xcf\xd2\xaf\x16\'\x1a\x85\xa3-\xcd\x94Wf\x16\xbc*\xae@\x07,\x9b\x10ih&\x9b\x98f\xd0\xe1\xc6z\x98\x8f$\xe0\x16\xbbH9\xd2m\xf5\x84\xf6\x87^>\xe7k^\xd5\xbc\x95\xfeY\xc12\x81\n\x96"\x8bU\n\xb8/\x87\x95r\xff$\\\x14?J3\xc52\xd2\x17i\xb1\xd2Iy\xa3\xbe+\x96\x8b\'{\xbb\x90z\xe4o\xd2\\=\xaf\xa6\xa9W\x95\xf9J\x13Eg\xeb\xe9\r\xd2\x15.b\x9f\x81\x8fu%\xe9\xb4\x14\xf6\xe00\xfe\x8d\xfb\x7f\xe1\xbe\xd8\x03\xd6L[\x81\xb3:\x9d\x81\xc2\xc0\xeb`\x866X]U,xox\xa4/s2\xc7e\x0e\xff4<\xb3\xde\xd7zyu\x8aj\x17\xae\xcbY\x9dW2/\xec\xfb\xdd\xbc\xf9y\x93\xf3\xff+\x9e\xeb\xdd,\xb7Q\x04\x9dW#\xd4gfm\xb0\x97\xddc\x8dl\x1e\xcbY\xbe\x82\xb3\x81]\xb5\x9d\xb4L\x95\xaaY\xe7q\xeb\x85\xe3\xe2\x07q\xa8%\x0fw\x12V\x08\xdd\x85\xffp\xbb]\xad\x86\xfd\x08Cg\x82W\xfdc\xb5:\xfa5\xb9kI\xb3\x94\xbfL[\xeb\x7f\xd6$\xfbC\xcf2oiO\xe7\xc0\xa8\xc0\xd4`@*a9h\xb9\x88\xf3p\x803C\xff\x86\x1e\xcb\xdb\xd8\x13\xf6\x95\x15\x13\x0b\xa1\xc4mI\x93JH1%\x1a\xc7m\x8b\x9b\xe3\\\xe7Hp\xd4\xe0\x8f\xf3k\xb93\xdc9\xfc\x17\xde\x11>\xdb\xfd\xd1}\x82%\xb2\x0b\xe4}\xf0pP\x08$\xe8\x91\xc6u\xf3)\xa3\xe0\x0b\xe8n\xf60g\x99a\xfagm\xaf\x1ab\x9dX_P`}jibI\xe2\xdb\x0b+\xf8\xaa\xc1\x07\xa11\xa1\x1c}\x94\xcei\x97\xad\xa9\x92G:\x17\x0e\xc2\xea\x87]\x8eh\x16\xde5\xfc\x88\xe3\x8c\xad\x96Eu\x9erT\xb3\xcd\xb5\x8d\xb7\x8d\xb7\xcd\r\x8e\x92\xcb)sp\x86p\x87\xdf\x161>\xaaL\xd4\xe3(\x14\xd5 v\xae\x7f\xa2V\xafX\xe7\xd8\x1a3S\x8b\x92\x86\xf3\x878\x07\x8a\xe7\xb6\x08\x1d\x84n\xfcv\xe1\x8e\xdcJ.\xad\xac\x0b4\x08\xcc\x0b\x1e\x03\xe5AYP\x83\xdc5_\x92\xbd\x80\x81S(\x86\x9b\x8a{\xe0\x93\x9e\xc3\x81l\xffzZ\xc3|\xaaU\xb1}\xb1X\xf9\x08\xb17\xb7\x0f\xf9x/\xb7\x14\xbd3\x97\x9a\x0b\xcd\xc3\xc1>f\x8a~\x93\xcf\x16z\x0b\x93\xc942\xd9\x1c\xa6\xa9Z\x91>]\xdbov5\x9bqo8/\xce\xd2C\xc6~\xb3\x879\xc6\x14I"\x1bA\xa7\xd2\x9b\xd2ni\xb2\xd4\x07\xf4\xd4\n@\xa2\xf7\x9bw\x84\x7f\x0eHd\xfb\xe8.\xd0\x0e\x1a`-\x98\x04&\xd1l\xe8\x81\xfd\xe9\x14\xf8\n\x8c6\xba\xaaw\xd4<3\xbdpv\xd1 \xdaF\xad\xa1=\xd1O\xd0\x81\xa8\x00\xdd\n\xef\r\x16\xd0\xf7\xb6\xdfm\xa7]\x01\xd6\x11\x0c\x84\xad\x11=N\xeb\x91\xb7\xd6\xed\x96\xe9\xd2T\xf7\x14\xd7\xcd\xf0\xdd\xb45\xe9Hw\x07\x82\xfe]~\xb7\xb2E\xc1J\x8e\xb4\xce\xb2]\xfa\x15T\x87"(`w\xa9\x8b\xb6\x12w\xf3\xb1|T\xe8~P\xf1\xdd\x07\x0bI\rMt}\xb2\xbd\x12\x9f\xd8\xebY\x1f\xf3]\xdc\xab\\\xd9\xb6O\x96\xca\x96,a\xa8\n\xb4\xfeZF\x91\xe0y\xe4\x89\xf7\'\x05\xcb\x07\xfb)\xe3\xf46\xea\xd5\xa03\xd89\x90W\\\xec)*~\xe0\xdb\xe2[\xe8[\xa8&hA\xed.\xf9H\xa6\xd1~\xda\x15\x8d\xa9\xc9Jc%OiA>\x92\x92`\xb0u\x88\xed\xac\xbd\xa7\xb8G\x9ca\xe9n60Es\xb3\xb2Ji\x19\xdc\x80\xbfp\xeb\x81\xa4\xfb\x8de\xda\xa7o\x07\xbe/\xca^\xe2\xcb\t\xfe\x1d\xc85V\x98U\xcc\x90\x19I\xca\x93\xaeJ?=F\xfb\xa6\xf8\xb4\x8f\xb2\x15\x99\x16\xd6\x8a\xfdn\xe4\x91\x08\xf6\x00I|\'\xe1\x1bh\x00%P\x9b|\xa23L\x13\x0cG\xa7\xc10\xf7\rw\xa1\xbb\xad\xf5\x8a\xe5\'K,\x9a\x8b\x16\xc1J\x88\xc1[`2\xd7\x06\x0b\x00G\xa7E\xccr\xef*\xd7\xbdL\x97\x04\xa9dJ|\xed\xe8\xe9%i\x89\xd4\xe8\xf1\xd10\xeaqX\x0c?_\xf0r3<\xaf<\xb3<\xe3r\xdd\xf9\x15\xf2-\xf9\xf9\x05\t\x05s\n\x93\x8a\xf2\x0b\x8f\xe4>\xcb3r\'\x15>.\xfa\\4Y\xb6\xcaY\xca1\xf27\xf3\xd2\xb6\xc1\xba!=\x18\xa5\x0f5~\xd6\xff\x89\xba\x11Y:\xe2^\xa9\x94\x84\x13\tw\xc2\x1b\x87\'F \xf0\x03\xea\x8a\xcb\xa9\x1d\x0cf\xb4\n\xab\x1a\xfe>\xe6\xa3+%,#\xfca\xb0\x8fZ\xd5w\xdbHc]\xcc\xf9\xd2L{\x03\xc7"\xde">\x96j\x14\x06\x8a\'\xe5\x16k\xaf\x0c!\xe4\xc0u\\5FT\xea\x87\xc6\xe3\xb5\xdc*\x87\xe6\xfa\x1a\xf6\xbb1HK\xd6\xea\xc9-\xd4M\xca>j\xc0\xb7 \x99\xe7\xf9?\xc4p\xb4\x05-B\xf7\x8c?\x0cI\xff9t;\xd0\xda\xdb\xd2\xd8\xaf\xff\xaa\xfe\x1av\xc9e\xd8\xcb\xba\x8b]>G\x07s"iO\xa6\xab\xf3\x95\xb2\x8a\xc3\xff\xc4\x8f\xfd\xb5<.o\xb2o\xc7\xf7\xc8\xdc\xc1\xb9\xd1\x05\xe5\n\xeb\x17\xaa\x811\x81\x01\xfeA\xea\x03\xad\xadRS\xa6r=e\xb3xP\xec\'\x16\xf1Px\xce\xbf\xcd\x18\x99\xd13\xe3D^l~\xf3\xc2U0\x11\xdd\xe7<\xee4W}g|\xa0u\xe0\xad\xb7\xb2r^\x19\x18\xba\xcb\xe5s\x83\xb8\x9a\xd6t[\xbac8w\x8d\xa7b\x1f\xb0\x0co\x15E\xdbM\xe7\x83\xa81._\xd8\xae\xe8c\x91/\xa3\x8e\x96\xa8\xcf\xe5\x8a\xeb85\xa7YQvF\x92:\xd9\xfc\xac\xacD\xa0>\x08\xb1\x0cZ\x0bLe\xc4\xa8fz\xe9!\xb9\x93\xbc]>fX\x8c\xff\x99W\x90\x80\x9es\xdf\xcd\xee\xe6D3\xca\xaf\x06\xf6\x07r|\xe1\xbe{\x9e\x18\xa3\xaaq[\xd1\xa2\xd3"\xaf\x84/\x10\x87\x88M\xc5\xb1\xa1%\nT\x92\xf0kT\x1ev\xa0A\xe2\xd2\x87\xb3B3W\x8b\x15v!\x9dZ\xb8?\xe1\x17rY|\xca\xd7\x85\xc7\xa5\x8a\xd2a>\x80\xeb\xe2-p\x9e\\]N\x0eU\xf3\x13\xdf+\x7f\xa4\x8c\xe4\xa7\xca\x03\xba\x89\xde"\x1d-\xb1\x961R\xb8m\x8a\xf5\x98%\x15\xd6\x81\r\x99\x10H\x08t\xf4\xf9\x95\x1c%)t\x94\xc3\\w|\xd6v\xd36\xd7\xd1S\xebK\xb6\xd1\xd5\xfe/\xa1\xc3jH\xff\xd5\x9c\xc4\x86\xc3}\xe8\x0e\x1e\xc8-\xe2C\xc2A&\x83\\6/P[\x1d\xef\x89\xd7\xa7\xe8\xc9J$\xe7r9\x179k\xf0\x9b\xc5\xa9b_\xfd\xa6~\xc98+/S\xa2\xe4\r\xdaZ\xbd\xb7V\x9b\xe8\xec\x1d\x1a`\xce5\xc6+\xad\xbc[\xbc\xa4\xf8\x8cvO}\x14\x9aa\xdfm\x8d\x16\xaaD\x15D\xf4\x08\x1f\x13\xba%W\x0e\xf5P\x8f\xa9?\xcb\x9d\xad\xee\x88\x83\x92\x1d\xf1 \x95!|\x11\xfd\x0f\xb6#i\xe4\x8a11\xf6v\xe4Q\xf7o4\x05f\xa0\xd3\xb0\x08\xbf\xc1)A\x1c\x1a\xaa\x96\x08\xa5\x85F\x85T\x9f\xe6\x9b\xe2\xadB6\x90\x07T\x88}\x1fW96/\xf6S\xf4\xa7\x88w\x8epG%{\x1f\xb2\xd6\x1cG\xfe\x85\xd3\xd0\x11} W\nw@\xcf\xacs\xecU\xa4\x8dx4\xdf\x92m1\xea\x92\x13\xc6k\xcf\x15\xff\x06OqpS\xa8zPH\xd8U\xe2{B\x14\\\x08\xfa\'@\xf8\x1f\xda\xc6m1V\xd06\xfai5N\xab\x19prN\x8f#\xd1^\x12\xa4\xc1 \xdf\x96\x1c1K\xe9)\xa1Ar\x8e\xcc\x8c\x8df\x15\xa3\x15\x8b\x00\xb3\xd1*\x7f)\xff?\xc1\x0c\xee\x14\xb7\x08&\xb9::/9^\x087\xf0<\xe8\x01KX\x14\x19\xe8\xcarV\xb0\x1fr.v^\xb3\xb7\xa1\x02]A\xa3\xccF4\x85,#\xb3\xe92\xb6\x93\xab%\x8c\x942b^\xc7$\xc5l&OI;\xb3\x8c\xfaQ\x9d\xae\x12\xd2[\x07\xc6\x88\x98\xd3QO\xc2\xe6\xe5\xcb\x85E\xc5O\x02\x1d\xe4\xfb\xbeG\xb1\x8d\xf8\x06Q\xfb\xa2\xa7\xc4\x8c\x8dH/Q2nj\xf4L~3\x7fS\x18`\x9c5Wi5\xe5u\xeabe\x82\xffs\xa0u@*\xe8\xedY\x90\xff\xa3\x1a\xab\xcd\xd6\x96\x93bR\xa8\xdb\xa55\xd2|\xee\x9am\xaf\x15\t\xcb\xf8\xeb\\\x051\x91F\xd0M\xc4\xa2\xad4s\x03Y\\\nw\x15\xae\xe3\x9c\x87\x9dI\xceC:0/\xb2\xd1\xfe\xc7\xa1M\xba[;\xa75\xd0\xb7\x88\xa6\xb4\\L\x17\x86\x89\x89RT\xc1\xbe\xc2\x1a\x85\xcd\xe4\xa5\xa1\x91\x9al\xbde9%\x0c\x86\xb5\xac\xdf\xa5\xce\xfeE\x81Jt\xbe\xe3\x98c\x82\xfdo\xf1\x82\xd8^r\xe8\x92\xfeL}(v\x147\nw\x1c;%\xdeZNJ#\xbf\xb0A\xda\x16\xb5\xac\xf2M\x9b\xabo\xd7Z\xa0kh\x11\xaa$$\n\xeb\x84\xca\xd2\x85\xe06\xe14\x9e\x87_\xf0\xd1E\x9c\xe7\x8e\xff\xf8\xfb\xaa\xef\xf7\xbf\xab(WS\xca\xf8\x1fy6y\x07%z\xa5D\xcb@K\xd5O\xfb>\xf7\xfb\xd4%\xd0+p*P\xc0\r\xc3\xd9\xdc(\xf0\x0e\x1e\x00u\x84i\xfc|\xae"\x7f\x96\xcb\xe4\xf2\xec\xc0\xf6\xd8y\x02\x19\xac\x9e\xd0\x04\x1d\x03\x15\xb9\xcef\x0bV\x8f\xbcG\xed\xe0v\x16\x82\xb3\xb9up$g\r\xd9\xb68f\xa3U\x86\x97t\xf2\xd5\t\xb6\xd5\xc3\xf5\x8e\xc6L\xa3\xbe\xad\xc0\xb6\xc4V\xcf%\xb9\x1a\xb9F\xd9\x1c\xb63V\xb1`]\xbe\xea_\x0ef\xb2\xfaF\x8ec\x90\xad\x8b\x94g\x8e6sM\x9f\xb6B\x7fmDs\x87\xf8\xe7\xbc\x97+\xcfO\x11\xc6r\xcd\xf97\xe2L\xf1\xb5X(\x15\x89e\xa1\x07\x85\x98\xc1\xea\xb2\x87\xc6a\xfa\x8d\xce\x96\xe2\xb9D\xbe\xaf8W\xd8\xcc\x8bt)h\t\x9aq&\xbfQjn\xbdd\xe9j\x1f\x9a_\xb1 \x90{4\xbfQ^vA=\xd8\x16v\xc1\x85,\x05\xf4\x81]\xdf\xd6};\xe4]\x1a\x897\xfd\xe6\x86\x18{\xd4\x97\xc8\xc1ao\xc3R\xc2+\x0b\x85\x96Nb\x80\xaf\x81\x97\xf0\xfb\xd0\x13\xea\xe7\xca\xa1\xd6\xac)\xf7\x10\x0c`[`\nE\xe4\x1c+E&\xd0"v\x9c\xfd\xcd\xda\xeaK9\\\x97\xbf/R\xcb<n,\xba%4\x11\x14\xb9\x95\x00\xf8\x9e\xe2}p\x18\xa4\xc0\xa3\x14\x13/\x89\x93\xeaI[\xc4\x8f\\.\xf7\x02\xd5\xe6\xe6\xe2\xab\xe8\xac\xfd\x7f\xb6\t\xd2=\xf2\x80\xacg\x0b\xe9\x00:\x9b\x05\t\xa5\xad\xa9a\xe7\x9c\xc9\xce2l\'=F\xedt\'I#\xe58\x93\x7f\x80\x0fq\xed\x05\x91\xaf,L!\x9f\x85\x0c\xb8\x17\\\x85%\x85\xb9\xe2/b\x18\xce\xe6\xbf\xf0\xbf\xd8:rEB}gC\xd7YwK\xfd\x16\xe9X5\t\xad\xc1ea\x15t\x13\xda\xf0f\xff\x1e?\x0e\xb5\x89\x1f\x1b\xfb[\xc2V{\x82\xad\x87\xb85\xeak\xd4\xd7\x08\x97\xa3\x84=`?b#\xd6\xf9\xd6*\xb0\x15xDoA\xc0\x9c`\x1f?\x8b\x1b\x0f\x1b\x83\xe3t\x1c\xddM*\xb0\x7f\xc8\x10\xa5\x8avS\xcf&\x97\xe8h\xf9\x1a<\xb0\x7f\xf7\x7f\xdb\x9c\xd6+\xb6\xd7\xce\x7f\x94[\xca\x17\xf5;8\t\xee\x82\x7f\xb3\x8efu\xc8<\xf1z\xeb\x9b\x8e\xaf\xce\x7f\xa9\x919\xe7\xf3Q\xfbt\x9bb1J\x87\x12\xc6\x95\xd8\x14W+6%\xfa\xba\x1a\xa1\xc5kg\xa1\x15\xacEAA\x15k\x8b?X\x16Y\x9e\xf2\r\xddg\\\xe3\x9c\xe3\xb9Fx<\x97\xa3\xfd\xab!\xb3\xb4\xe62\xa6\xea\x02\x00\xec0(M4\xd3o.\x92W\xca\x95d?ta\x1b\x1a\x02\xcb\xa0\xd5\xb8!\xebJ?\x82u\xc6Ns\xae\xb9\x1f\x85\xd0\x05\xc8\xd0\x02|\x1e\xdf5%\xba\x94M\t\xbc\xf1\x17\x06z\x89{D\x89\xbf\xec4\x9d\xd3l\xaf`]\x10\x05\xb3\xd0\x11\xd8\x1b6\xe6\xc7\xf0\t\xfc[\xcbV\xa9\xb2\xb4_:,M\x17\x8a\xa3\xca\xc4\x8cI\x94\x95\xaf \x10\x1a{\xff\xde\xdb\xe5\'\xdei\xe7\x95\xab\xfa\n\x8e\xf3\x08\xe3\x85&\xd2\')\xd5v\x02\x02\xf0\x1c\xac\xc9\x99\x90;2\xfb\xb7w\x97\xd2\xb7\xa5my;\xec\xc3\xc27\x1f\xb9\x1ep;\\b]\x1f\xd1\xd8}\x01\xf5\x84\xcd`)\xdfTo\x91/d\xe6\x10\x8d~\x00Ma7\xb8\x9a\x9f\xa3o2\xc6\x9b\x13\xe86\xf1O\xfc\x0c\xdf\xc4\xf1\xb0>L\x83\x82\xb1]\xafi\xfa\xed\x15l]\xed\xa9\xfaJ\xb3\xb6\xc1\x19\xdf\x08 \x8d\xc4K\xe24\xa9\x1f\xed\x01:\xd3\\\x12N\xc3\x99\x1f\x8dEu\xf0lWc\xd7H[\xc0xb<\xd5\x0f\xa0\xfd\\\x0b\x8cl\x17\xece\x1d\xbf\xd8G\xdb\xae\xd9|\xcc\xa4A\xf2X\xd8\xcd\xd7\xc7{p\x105\x80\x8f\xb1\x85[\xc6y\x84]\xc2M\xe9O\x81\n\xa5E\'a\xe69R\xdb\xf3{\xc0\xc8\xfdE\xc9A=\x8a\x9c\xc2\x0bq4}\xce\xb6\xd1\x16\xa8\n\xc7O\xe3\xd6\xe35$\x8c\x84\xe9\x1b\x8b\x1f\x14_\xc9\xc7/:\xbc\xccy\xda\xfb\xfd\xc5\x0f\x05o^\x1b\x83\xf4\x8a\xf2\xb5\xb8\x9c\x84\x96\xa5\xa6\xd8\x9f\xdb\xda\xd8\x8e\x98\xf5\xcd:\xc6\xa8@k\xe3w\xfd;l\x81n\xe0\xe3`)\xdb\x0b\xebi\xbavI\x1f\xad\xf77\xbb\x1a\x97\xd9\n\xd6\x1eL\xc0\x93\x90\x13\xda\xc1&\xb6\x0f\xb4t?pUw\x1f\xa4MY\x13:\x83\xec\xe2\x1fq\xed\xac\x83\xa4\x04kw\x7f\x83\xe0\x14\x7f1\x99@<\xa6\xc2\x07\xb9\xf3\\\x07\xbc\x1f\xb7\xc7\xb5\xcdy\xe4-J\x87\xe3\xd1\x1ctT\x88\xe5\xef\xf3\x0c}\xb37\xb3u\xd0Wh\xc9jMr\x9d|5\xdb\xa1n\xe837\\\\%V\x10\x07\xf1\xd9B\x1d\xfe_6\x16\xf4\x83-\xd8I\xf8\x0f\x1e\xe1\xe5d[^{9\x03\x1c\xcaN\xb1F\xd8\x9a\xa2~\xe2\x021\x03\xafB\xc6@\xadMhoA\x87\x9c7\x9f\x1b\xbe\xdb\x94\xc6\xa5ff\x8f\xc9\xfa\xf4e\x9bu\x85XUxS\xe6M\xe9\x8e\x89\xc7\x1cO\xec\xaa\xed\x92\xb6Z\xcbQ\x1a\xca?+\x95\x95b\xfc\x9e\xdb\xc0\xf7\xc4\x170\xe3z\xc2\x0c\x04\xe1k\xbd\x9c\xdeZ\xaf\x96_6\xff\x87|\x7f\xa0z\xa0]\xa0\r\xe9L\xa2\xcdV\x0c\xb0\r\xe6\x18\xa5\x8d\xf2-\xf4\xb7t\xd6\xe2\x14\xdb\xbb\x9e\xba\xc68\xaf\xeb\x11\xa6\xa8\xe7R?\xfd\x83\xbe\x05\x0c,\x006z\x9d\x85h$a\xf4\x1a\x9d-\xc5I\xe3\xa5\xda\x968\xf1O\xcb\t\xb6\x98v&\x1b\xc4\xc6bH\xe8l\xe9d\xb5H\xf5\xb0\xce\xeb\xfcE\x8d7\xfb\xd3\xa6\xc6A\x93\x99\x7f\x18\xa5\x8cE\xfa\t\xfd\x83\x99\xa0.\x02k\xa4\x9f\xf4Rf=<T\xf5\xeb\xfd\xd9e\xf5#\xbf^hN\x0f\xd8K8w\xa0\x8f\xb8/\xea\xf5\xa4\xeb\x1a3\xdb8\xaaG\x925d\x19i#T\xe5#\xf8\xafa^w\xaa\xfb\x9c\xb3\x95\x938F\x80\xa7\x00\xb1\xe3\xac\x0b\xa8\xca\xfa\x83}\xf0\x16,\xa2\r\xd89\xd8\x1f}\xc2\xeb\xe0\x034\x8e[\xcd\xd5\x00\x12h\x06\x92\x8dm\xc6!}b\xe1\x9fE\xff\x16\xa5\xf9k\x07r\xfd6\xee\x10\x87\xd0g\xbe!\xff7\xd7\xda\xbcj\x1e!\xf5|m\x03\xd4\x1f\xe7]\xec\xa3^\xa7c\x8b\xe3\xb3}\xa4t_L\x12\x16\xd3\x05\xecO\xa2I%-\xc4r\x8c/\xc5\x97\xe0\\x\x16^\r\x1d\x80\x07K\xd8n#\xdf\xec\xa8?66\x98\x03\xf4x\xf3\xac\xb9\xc6X\xa5\xac\xd5\x87\xca\x0f\xd9V\xfa\x92\xb6\x0064\x84\x1b\xc3\x86\xe3/\xacfh)\xd8\xffu\xa5~\x19\xd5-\xfe\x81TD\x0f\x95\\\xbd\xbcY\xd2\x9b\xca5\xc71\xf8\x02\xa7\xaf3^\xe8{\xcc~d\xbb\xf9\xc0z\xd4z\xc4:=Z\x8aN\x8e~\xaa\xfe\xa6a\x95(W\x94\xc5r\x9c\xfaV\xcdV!\xac\x03G\xc1\x1e\xec\x05\xfb\x0e\xc6\x1a\xc9\xe6\x07}\x0b\xdb\x06o\xb2\x8d`/\xc8\xd2\x17\xe9o\xf4s\xfaB\xf9\xb3\xf2$t\xd67\xd9\xff[`1L\xf7s\xa0\xad\xee\xd0-\xda@u\x9c\x16\xd44\xd7\x01W\x86\xab;\xa8\x00\xaa\x80\xa1J\x96,\xa8\xe7\xc3\x1f\x86\x85\xc2\xa6\xe1q\xdc>XLGP\xde<\xa9\xdf0J\xab\x17X\x13\xb8Qh\x00[\x93\x01\xec\'R\x8b<0\xab\xc3|h\x83w\xc9\x7f\xa43Y\xa9q:\xd5F\xe9]\xb4\xbf\xb4 Z\x86\x9a\xe0\xc9\xf02\xc9\n\x89\xf4#I\x0f0\xcd\x01W\xe7\xadevX\xd9\x18\x00\xdf@\x1f\x8d\xc5)\xe0:\xbc\xae\xec\xd1~\x96\xcfp\xca{\xe5N\xa8\x86\x12\xa5l\t\x95\xd0_\x9bs\xf4\xff\xd8\x15\x00\xd8\x06v\x9bUb2yHf\xd2\xe6\xe4*\x99H\x97\xd2\x9e\xb4\x03k\xc26\xb2+\xec*<\x86&\xa0\t\xc6OF@\xef\xa4Ein-6T54(4H\xfeQ)+\x7fBnT\x05G\x98\x95\xc8\xafdG\xce\x7fy\xb5\x0b~V\xb1\xfeT?\x8eb\xb9\xdb\xe8G\xe7\x05\xdb]\xfb\x15z\x9f:i\xbcY\xd1\xe0\xf4D\xb8\x15\xcc\xa4\xad\xcd\x81\xe6\x05\xa3\x9f\xd9D\xbe\x1f\xca\x96\xae2\xd9\xdc\x0c_\x02\xc2l\xba\xa0=\xd1W\xd9\xf6\xd9x\x1b\xa5\'Y7rC\xfb\xa8\xff\xac\xdb\xccM\xe6h6\x0b4\x83\xed\xf0n\xb3\x1aj\x1b\xba\xa1&\xd0j\xdf.\xa1xp\x9b\x8ebv\xd2\xdbLC\xb3ak\xda\xd02\x1e\x0f\xb3\xaf\xf28\xd5NE\xfd\xfe\x0f<\x91\xad\x8b\x18\x9d\xb2&\x00\x00\x00!zTXtSoftware\x00\x00x\xda\x0bH\xcc\xcc+\xd1\xf3s\rQ(3\xd634\x00\x00\'z\x04jjX\x10\xe2\x00\x00\x00\x00IEND\xaeB`\x82'
    IMG_CARROT = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00 \x08\x06\x00\x00\x00szz\xf4\x00\x00\x00\x06bKGD\x00\x00\x00\x00\x00\x00\xf9C\xbb\x7f\x00\x00\x00\tpHYs\x00\x00\x00H\x00\x00\x00H\x00F\xc9k>\x00\x00\x01\xd8IDATX\xc3\xc5W\xd1\xb1\x83 \x10\\2\xaf#\xad%%\xd8\x825\xd8BJ\xb0\x16\xa9i\xf3\x11N\x17\x04"\xea\xe4\xed\x8c\x03*pw{{\x88\x8e$q\x13\x9csk\x9fdt\xafP\x93\x7fw\x1a\xe7\x9083g\x06\xfa068q\x8b\x03\xa9\xf1\xd4\xe0\x0e\xa38\xc1\x8b\x00@\x0eX[\xbd\x00\x10ch\xf5\n\xcfH\xf2\x12\x03\x16\xb9/\xbc\xe7\x00\xb8\t\xfbT<e\x8d+"T\xea=\x80\xfe\x85l*\xdc+y0\x7f\x9c y\xde\x81j\xde\x13x\x00\x1d6\xa6\xfa\xe0\x10I<\xceF_uN"6\xe3\x90Vq\xca\x01\x8b~Gm\xc0"\xef\xcc\xa8G^+\xcd\x0e\x94\xa8Wg: \x12\xa7\xe9\x03\xd6\x8a(/\xa5@#\xd5\xbe\x0f\x0eY\xde\xbb\xf0\xbe\x7f\x01\x18c*\x9a\x1cH\xa3\xb7\x85\xcdX\xa9\xbf20\xcaD[\xf3h\x15h\xdeK\xea\xb7\xc04\xefF=F\xc4\xa50\x9d\xac\x82\xa5">3n\x82\x8b\x8c\xeb\x00\xc1!\x074z\x13X\xf4^\x14\x1f\xd5\xfa\x98,\xf4\xdc\xaf\xdd\xb4\x15\x97\xa8\xcf\xb22\x02\x98\x12Z2\xf8\xca@\xae\xecRc&\xba\xd5p0~D^U\x07J\x1b\x8eE\xace\xd7\xeb\x98\x83\xc6\x81\x83)X\x12\xf5k\xc4N\xf6\xf5\xd2\t\xe8\x14\x035\xe19\xd9\xd5H\xc6\xd1v\xf1\x1a\x98\xb1\xcf\xbf\x8c\xa9\xa6\xc0c/<\x8fmWk\xfa\x90N\xd2\x7fns\xb3\x0eX\xf4Z\xb2\xaa\x83f\xe3\x15\xec4\x90\xdb\xf1,j\xcd\xf7]\xc82\xa0\xd4W\xf3]\x9a\xdc\x82\xdc\x01\xd3\x0e\x94\xcb\xf0\xb9\xd0pv\xd5\xb1\x00\x88y\x9b\x9f\xdeG\x87\xd2\xf4|\xb7~>o\xa6\xfck\n\x9a)\xbf\x08G\x92\xe9\xf1\xfa\x8a\xca\xed\x87#\xda\x03\xa6x\xa3*\xfe\x9a\xfd\x82\xf2\x1c\xb6?\x9b\x1b\x81\x8c\x00S\x91\x92\xe4c\xad\xf9\x1fGmx\xfc\xa7q\x00x\x03\x04\xc6\x11d\xc5\x10\x93o\x00\x00\x00DzTXtComment\x00\x00x\xdasM\xc9,IMQH\xaaT\x08H,\xcdQ\x08\xceH-\xcaM\xccSH\xcb/R\x08\x0fp\xce\xc9,H,*\xd1Q\x08(M\xca\xc9LVp\xc9\xcfM\xcc\xcc\x03\x00\xd1\xc6\x12\x0b\xf8-\xaa\x0b\x00\x00\x00\x00IEND\xaeB`\x82'
    class MyFrame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None, title="Grid demo",
                              pos=wx.DefaultPosition, size=wx.DefaultSize,
                              style=wx.DEFAULT_FRAME_STYLE)
            sizer = wx.BoxSizer()
            self.SetSizer(sizer)
            bmp_rabbit,bmp_carrot = [wx.BitmapFromImage(wx.ImageFromStream(StringIO.StringIO(x)))
                                     for x in (IMG_RABBIT, IMG_CARROT)]
            d = {"rabbit":bmp_rabbit, "carrot":bmp_carrot}
            grid = wx.grid.Grid(self)
            sizer.Add(grid,1,wx.EXPAND)
            grid.CreateGrid(4,5)
            grid.SetGridLineColour(wx.BLACK)
            self.grid = grid
            for i in range(4):
                hook_grid_button_column(grid, i, d)
                for j in range(4):
                    grid.SetCellValue(i,j,(((i+j)%2==0 and "rabbit:") or "carrot:")+BU_NORMAL)
                grid.SetCellValue(i,4,"Row %d"%(i+1))
                grid.SetReadOnly(i,4)
            grid.SetColLabelSize(0)
            grid.SetRowLabelSize(0)
            self.Bind(EVT_GRID_BUTTON, self.on_grid_button, grid)
            self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK,self.on_left_click, grid)

        def on_grid_button(self, event):
            value = self.grid.GetCellValue(event.row, event.col)
            wx.MessageBox("%d,%d: %s"%(event.row, event.col, value))
            self.grid.SelectRow(event.row)
        def on_left_click(self, event):
            if event.Col == 4:
                self.grid.SelectBlock(event.Row, event.Col, event.Row, event.Col, False)

    class MyApp(wx.App):
        def OnInit(self):
            self.frame = MyFrame()
            self.SetTopWindow(self.frame)
            self.frame.Show()
            wx.lib.inspection.InspectionTool().Show()
            return 1
    app = MyApp(0)
    app.MainLoop()
