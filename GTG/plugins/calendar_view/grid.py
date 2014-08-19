class Rect():
    """
    Class representing a rectangle, where:
    - x is the initial horizontal position of the rect (col inside a grid).
    - y is the initial vertical position of the rect (row inside a grid).
    - w is the width of the rect in grid cells.
    - h is the height of the rect in grid cells.
    """
    def __init__(self, x, y, width, height, id=1):
        self.id = id
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __str__(self):
        return "%s %s %s %s" % (self.x, self.y, self.width, self.height)


class Cell():
    """ This class represents a single cell of a Grid. """
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
    """
    This class contains rows and columns forming a grid, where rectangles can
    be added into it.
    """
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
        """ Adds a row at the end of the grid. """
        self.grid.append([])
        i = self.num_rows
        for j in range(self.num_cols):
            self.grid[i].append(Cell(i, j))
        self.num_rows += 1

    def add_column(self):
        """ Adds a column at the end of the grid. """
        j = self.num_cols
        for i in range(self.num_rows):
            self.grid[i].append(Cell(i, j))
        self.num_cols += 1

    def remove_row(self, row_index):
        """ Removes row given by @row_index from the grid. """
        self.grid.remove(self.grid[row_index])
        self.num_rows -= 1

    def remove_col(self, col_index):
        """ Removes column given by @col_index from the grid. """
        for i in range(self.num_rows):
            del self.grid[i][col_index]
        self.num_cols -= 1

    def is_row_empty(self, row):
        """ Returns whether or not @row is empty. """
        for j in range(self.num_cols):
            if not self.grid[row][j].is_free():
                return False
        return True

    def is_col_empty(self, col):
        """ Returns whether or not @col is empty. """
        for i in range(self.num_rows):
            if not self.grid[i][col].is_free():
                return False
        return True

    def num_occupied_rows_in_col(self, col):
        """ Returns the number or occupied cells in column number @col. """
        occupied_rows = 0
        for i in range(self.num_rows):
            if not self.grid[i][col].is_free():
                occupied_rows += 1
        return occupied_rows

    def last_occupied_row_in_col(self, col):
        """
        Returns the index of the last occupied cell in column number @col.
        Ex:   col: 0
                 -----
           row 0:  x
           row 1:  -
           row 2:  x  <-- last occupied row
           row 3:  -

        @param col: integer, the index of the col being considered.
        @return last_row: integer, the row index of the last occupied cell in
                          this column.
        """
        # find last occupied row index inside this col
        if self.num_rows == 0:
            return 0
        last_row = self.num_rows - 1
        while(last_row >= 0 and self.grid[last_row][col].is_free()):
            last_row -= 1
        return last_row

    def clear_cols(self):
        """ Removes all columns from the grid. """
        while self.num_cols > 0:
            self.remove_col(0)

    def clear_rows(self):
        """ Removes all rows from the grid. """
        while self.num_rows > 0:
            self.remove_row(0)

    def remove_from_grid(self, x, y, w, h, remove_empty_rows=True,
                         remove_empty_cols=False):
        """
        Removes the rectangle given by (@x, @y, @w, @y) from the grid.
        It also may or may not remove empty rows and/or columns that become
        empty after the remotion of the rectangle.

        @param x: integer, the initial row inside a grid.
        @param y: integer, the initial col inside a grid.
        @param w: integer, the width in grid cells.
        @param h: integer, the height in grid cells.
        @param remove_empty_rows: bool, whether or not we should remove empty
                                  rows after removing this rectangle from the
                                  grid. Default = True.
        @param remove_empty_cols: bool, whether or not we should remove empty
                                  cols after removing this rectangle from the
                                  grid. Default = False.
        """
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
        """
        Removes the rectangle given by (@x, @y, @w, @y) from the grid.
        It does not check if the cells correspondent to this rectangle were
        occupied or not, nor that they all were being used by the same
        rectangle.

        @param rect: a Rect object, the rectangle we want to remove.
        """
        for i in range(rect.y, rect.y + rect.height):
            for j in range(rect.x, rect.x + rect.width):
                self.grid[i][j].release()

    def find_single_row_to_add(self, x, width):
        """
        Finds a single row to fit @width cells starting on column @x inside the
        grid. This function looks for the first row inside the grid that can
        fit this one-line rectangle, and if there isn't such row, it will
        return the index to a new row, so it can be created later.

        @param x: integer, the initial col we want to start the insertion.
        @param width: integer, the width in grid cells.
        @return row: integer, the index of the row the insertion should occur.
        """
        row = 0
        can_fit = False
        for i in range(self.num_rows):
            can_fit = True
            for j in range(x, x + width):
                cell = self.grid[i][j]
                if not cell.is_free():
                    # does not fit inside row i
                    can_fit = False
                    break
            if can_fit:
                row = i
                break
        if not can_fit:
            row = self.num_rows
        return row

    def add_to_grid(self, x, w, id=1):
        """
        Finds a single row to fit @w cells starting on column @x inside the
        grid. If there isn't enough space in any row inside the grid to insert
        this rectangle, a new row will be created at the end of the grid and
        the rectangle will be added to it.
        See find_single_row_to_add for more details.

        @param x: integer, the initial col we want to start the insertion.
        @param width: integer, the width in grid cells.
        @param id: the id of the rectangle being added.
        @return: a 4-tuple of integers, containing the position the rectangle
                 was added to, in the order: (x, y, w, h).
        """
        rect = Rect(x, 0, w, 1)
        rect.y = self.find_single_row_to_add(rect.x, rect.width)
        while(rect.x + rect.width > self.num_cols):
            self.add_col()
        while(rect.y + rect.height > self.num_rows):
            self.add_row()

        self.add_to_pos(rect, id)
        return rect.x, rect.y, rect.width, rect.height

    def add_to_pos(self, rect, id=1):
        """
        Adds the rectangle given by (@x, @y, @w, @y) to the grid, using @id as
        the identifier.
        It does not check if the cells correspondent to this rectangle are
        free or not.

        @param rect: a Rect object, the rectangle we want to add.
        @param id: the id of the rectangle being added.
        """
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
