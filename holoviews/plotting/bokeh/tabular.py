from bokeh.models.widgets import DataTable, TableColumn

import param

import numpy as np
from ...core import Dataset
from ...element import ItemTable
from ..plot import GenericElementPlot
from .plot import BokehPlot
from .util import bokeh_version


class TablePlot(BokehPlot, GenericElementPlot):

    height = param.Number(default=None)

    width = param.Number(default=400)

    style_opts = ['row_headers', 'selectable', 'editable',
                  'sortable', 'fit_columns', 'width', 'height']

    finalize_hooks = param.HookList(default=[], doc="""
        Optional list of hooks called when finalizing a column.
        The hook is passed the plot object and the displayed
        object, and other plotting handles can be accessed via plot.handles.""")

    _update_handles = ['source', 'glyph']

    def __init__(self, element, plot=None, **params):
        super(TablePlot, self).__init__(element, **params)
        self.handles = {} if plot is None else self.handles['plot']
        element_ids = self.hmap.traverse(lambda x: id(x), [Dataset, ItemTable])
        self.static = len(set(element_ids)) == 1 and len(self.keys) == len(self.hmap)
        self.callbacks = [] # Callback support on tables not implemented


    def _execute_hooks(self, element):
        """
        Executes finalize hooks
        """
        for hook in self.finalize_hooks:
            try:
                hook(self, element)
            except Exception as e:
                self.warning("Plotting hook %r could not be applied:\n\n %s" % (hook, e))


    def get_data(self, element, ranges, style):
        dims = element.dimensions()
        mapping = {d.name: d.name for d in dims}
        data = {d: element.dimension_values(d) for d in dims}
        data = {d.name: values if values.dtype.kind in "if" else list(map(d.pprint_value, values))
                for d, values in data.items()}
        return data, mapping, style


    def initialize_plot(self, ranges=None, plot=None, plots=None, source=None):
        """
        Initializes a new plot object with the last available frame.
        """
        # Get element key and ranges for frame
        element = self.hmap.last
        key = self.keys[-1]
        self.current_frame = element
        self.current_key = key

        style = self.lookup_options(element, 'style')[self.cyclic_index]
        data, _, style = self.get_data(element, ranges, style)
        if source is None:
            source = self._init_datasource(data)
        self.handles['source'] = source

        dims = element.dimensions()
        columns = [TableColumn(field=d.name, title=d.pprint_label) for d in dims]
        if bokeh_version > '0.12.7':
            style['reorderable'] = False
        table = DataTable(source=source, columns=columns, height=self.height,
                          width=self.width, **style)
        self.handles['plot'] = table
        self.handles['glyph_renderer'] = table
        self._execute_hooks(element)
        self.drawn = True

        return table


    @property
    def current_handles(self):
        """
        Returns a list of the plot objects to update.
        """
        handles = []
        if self.static and not self.dynamic:
            return handles

        element = self.current_frame
        for handle in self._update_handles:
            if (handle == 'source' and self.static_source):
                continue
            if handle in self.handles:
                handles.append(self.handles[handle])
        return handles


    def update_frame(self, key, ranges=None, plot=None):
        """
        Updates an existing plot with data corresponding
        to the key.
        """
        element = self._get_frame(key)

        # Cache frame object id to skip updating data if unchanged
        previous_id = self.handles.get('previous_id', None)
        current_id = element._plot_id
        self.handles['previous_id'] = current_id
        self.static_source = (self.dynamic and (current_id == previous_id))

        if self.static_source:
            return
        source = self.handles['source']
        style = self.lookup_options(element, 'style')[self.cyclic_index]
        data, _, style = self.get_data(element, ranges, style)
        self._update_datasource(source, data)
