class Rect():
    def __init__(self, x, y, width, height, id=1):
        self.id = id
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __str__(self):
        return "%s %s %s %s" % (self.x, self.y, self.width, self.height)


class Cell():
    def __init__(self, x, y, obj_id=0):
        x = x
        y = y
        self.free = True
        self.object_id = obj_id
        if obj_id:
            self.free = False

    def is_free(self):
        return self.free

    def occupy(self, id=None):
        if self.is_free():
            self.object_id = id
            self.free = False
            return True
        else:
            print("Cell already occupied!")
            return False

    def release(self):
        self.object_id = 0
        self.free = True
        return True

    def __str__(self):
        return str(self.object_id)


class Grid():
    def __init__(self, num_rows=0, num_cols=0):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.grid = []
        for i in range(self.num_rows):
            self.grid.append([])
            for j in range(self.num_cols):
                self.grid[i].append(Cell(i, j))

    def __getitem__(self, index):
        return self.grid[index]

    def add_row(self):
        self.grid.append([])
        i = self.num_rows
        for j in range(self.num_cols):
            self.grid[i].append(Cell(i, j))
        self.num_rows += 1

    def add_column(self):
        j = self.num_cols
        for i in range(self.num_rows):
            self.grid[i].append(Cell(i, j))
        self.num_cols += 1

    def remove_row(self, row_index):
        self.grid.remove(self.grid[row_index])
        self.num_rows -= 1

    def remove_col(self, col_index):
        for i in range(self.num_rows):
            del self.grid[i][col_index]
        self.num_cols -= 1

    def is_row_empty(self, row):
        for j in range(self.num_cols):
            if not self.grid[row][j].is_free():
                return False
        return True

    def is_col_empty(self, col):
        for i in range(self.num_rows):
            if not self.grid[i][col].is_free():
                return False
        return True

    def num_occupied_rows_in_col(self, col):
        occupied_rows = 0
        for i in range(self.num_rows):
            if not self.grid[i][col].is_free():
                occupied_rows += 1
        return occupied_rows

    def last_occupied_row_in_col(self, col):
        # find last occupied row index inside this col
        if self.num_rows == 0:
            return 0
        last_row = self.num_rows - 1
        while(last_row >= 0 and self.grid[last_row][col].is_free()):
            last_row -= 1
        return last_row

    def clear_cols(self):
        while self.num_cols > 0:
            self.remove_col(0)

    def clear_rows(self):
        while self.num_rows > 0:
            self.remove_row(0)

    def remove_from_grid(self, x, y, w, h, remove_empty_rows=True,
                         remove_empty_cols=False):
        rect = Rect(x, y, w, h)
        self.remove_from_pos(rect)

        if remove_empty_rows:
            to_remove = []
            for i in range(rect.y, rect.y + rect.height):
                if self.is_row_empty(i):
                    to_remove.append(i)
            for i in to_remove:
                self.remove_row(i)

        if remove_empty_cols:
            to_remove = []
            for j in range(rect.x, rect.x + rect.width):
                if self.is_col_empty(j):
                    to_remove.append(j)
            for j in to_remove:
                self.remove_col(j)

    def remove_from_pos(self, rect):
        for i in range(rect.y, rect.y + rect.height):
            for j in range(rect.x, rect.x + rect.width):
                self.grid[i][j].release()

    def find_single_row_to_add(self, x, width):
        row = 0
        can_fit = False
        for i in range(self.num_rows):
            can_fit = True
            for j in range(x, x + width):
                cell = self.grid[i][j]
                if not cell.is_free():
                    # print "cannot fit row", i
                    can_fit = False
                    break
            if can_fit:
                row = i
                break
        if not can_fit:
            row = self.num_rows
        # print "will be in row", row
        return row

    def add_to_grid(self, x, w, id=1):
        rect = Rect(x, 0, w, 1)
        rect.y = self.find_single_row_to_add(rect.x, rect.width)
        while(rect.x + rect.width > self.num_cols):
            self.add_col()
        while(rect.y + rect.height > self.num_rows):
            self.add_row()

        self.add_to_pos(rect, id)
        return rect.x, rect.y, rect.width, rect.height

    def add_to_pos(self, rect, id=1):
        for i in range(rect.y, rect.y + rect.height):
            for j in range(rect.x, rect.x + rect.width):
                self.grid[i][j].occupy(id)

    def __str__(self):
        string = ""
        for i in range(self.num_rows):
            for j in range(self.num_cols):
                string += "%s " % self.grid[i][j]
            string += "\n"
        return string
