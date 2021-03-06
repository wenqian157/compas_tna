from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from ast import literal_eval

import compas
import compas_rhino

from compas.utilities import flatten
from compas.utilities import geometric_key

from compas_rhino.geometry import RhinoPoint
from compas_rhino.geometry import RhinoCurve

from compas_rhino.modifiers import VertexModifier
from compas_rhino.modifiers import EdgeModifier
from compas_rhino.modifiers import FaceModifier

from compas_rhino.selectors import VertexSelector
from compas_rhino.selectors import EdgeSelector
from compas_rhino.selectors import FaceSelector

try:
    import Rhino
    from Rhino.Geometry import Point3d
    import rhinoscriptsyntax as rs

except ImportError:
    compas.raise_if_ironpython()


__all__ = ['DiagramHelper']


def match_edges(diagram, keys):
    temp = compas_rhino.get_objects(name="{}.edge.*".format(diagram.name))
    names = compas_rhino.get_object_names(temp)
    guids = []
    for guid, name in zip(temp, names):
        parts = name.split('.')[2].split('-')
        u = literal_eval(parts[0])
        v = literal_eval(parts[1])
        if (u, v) in keys or (v, u) in keys:
            guids.append(guid)
    return guids


def match_vertices(diagram, keys):
    temp = compas_rhino.get_objects(name="{}.vertex.*".format(diagram.name))
    names = compas_rhino.get_object_names(temp)
    guids = []
    for guid, name in zip(temp, names):
        parts = name.split('.')
        key = literal_eval(parts[2])
        if key in keys:
            guids.append(guid)
    return guids


class DiagramHelper(VertexSelector,
                    EdgeSelector,
                    FaceSelector,
                    VertexModifier,
                    EdgeModifier,
                    FaceModifier):

    @staticmethod
    def highlight_edges(diagram, keys):
        guids = match_edges(diagram, keys)
        rs.EnableRedraw(False)
        rs.SelectObjects(guids)
        rs.EnableRedraw(True)

    @staticmethod
    def unhighlight_edges(diagram, keys):
        guids = match_edges(diagram, keys)
        rs.EnableRedraw(False)
        rs.UnselectObjects(guids)
        rs.EnableRedraw(True)

    @staticmethod
    def highlight_vertices(diagram, keys):
        guids = match_vertices(diagram, keys)
        rs.EnableRedraw(False)
        rs.SelectObjects(guids)
        rs.EnableRedraw(True)

    @staticmethod
    def unhighlight_vertices(diagram, keys):
        guids = match_vertices(diagram, keys)
        rs.EnableRedraw(False)
        rs.UnselectObjects(guids)
        rs.EnableRedraw(True)

    @staticmethod
    def select_vertices_where(diagram, keys):
        rs.UnselectAllObjects()
        DiagramHelper.highlight_vertices(diagram, keys)

    @staticmethod
    def select_vertices_on_boundary(diagram):
        rs.UnselectAllObjects()
        key = DiagramHelper.select_vertex(diagram)
        if key is None:
            return
        boundaries = diagram.vertices_on_boundaries()
        for boundary in boundaries:
            if key in boundary:
                DiagramHelper.highlight_vertices(diagram, boundary)
                return boundary

    @staticmethod
    def select_vertices_on_curve(diagram):
        rs.UnselectAllObjects()
        guid = compas_rhino.select_curve()
        keys = DiagramHelper.identify_vertices_on_curve(diagram, guid)
        DiagramHelper.highlight_vertices(diagram, keys)
        return keys

    @staticmethod
    def select_vertices_on_curves(diagram):
        rs.UnselectAllObjects()
        guids = compas_rhino.select_curves()
        keys = DiagramHelper.identify_vertices_on_curves(diagram, guids)
        DiagramHelper.highlight_vertices(diagram, keys)
        return keys

    @staticmethod
    def select_edges_on_curves(diagram):
        rs.UnselectAllObjects()
        guids = compas_rhino.select_curves()
        keys = DiagramHelper.identify_edges_on_curves(diagram, guids)
        DiagramHelper.highlight_edges(diagram, keys)
        return keys

    @staticmethod
    def select_continuous_edges(diagram):
        rs.UnselectAllObjects()
        keys = DiagramHelper.select_edges(diagram)
        if not keys:
            return
        keys = [diagram.get_continuous_edges(key) for key in keys]
        keys = list(set(list(flatten(keys))))
        DiagramHelper.highlight_edges(diagram, keys)
        return keys

    @staticmethod
    def select_parallel_edges(diagram):
        rs.UnselectAllObjects()
        keys = DiagramHelper.select_edges(diagram)
        if not keys:
            return
        keys = [diagram.get_parallel_edges(key) for key in keys]
        keys = list(set(list(flatten(keys))))
        DiagramHelper.highlight_edges(diagram, keys)
        return keys

    @staticmethod
    def identify_vertices_on_points(diagram, guids):
        gkey_key = diagram.gkey_key()
        keys = []
        for guid in guids:
            point = RhinoPoint.from_guid(guid)
            gkey = geometric_key(point.xyz)
            if gkey in gkey_key:
                key = gkey_key[gkey]
                keys.append(key)
        return keys

    @staticmethod
    def identify_vertices_on_curve(diagram, guid):
        gkey_key = diagram.gkey_key()
        keys = []
        curve = RhinoCurve.from_guid(guid)
        for key in diagram.vertices():
            xyz = diagram.vertex_coordinates(key)
            closest = curve.closest_point(xyz)
            gkey = geometric_key(closest)
            if gkey in gkey_key:
                if key == gkey_key[gkey]:
                    keys.append(key)
        return keys

    @staticmethod
    def identify_vertices_on_curves(diagram, guids):
        gkey_key = diagram.gkey_key()
        keys = []
        for guid in guids:
            curve = RhinoCurve.from_guid(guid)
            for key in diagram.vertices():
                xyz = diagram.vertex_coordinates(key)
                closest = curve.closest_point(xyz)
                gkey = geometric_key(closest)
                if gkey in gkey_key:
                    if key == gkey_key[gkey]:
                        keys.append(key)
        return keys

    @staticmethod
    def identify_edges_on_curves(diagram, guids):
        edges = []
        for guid in guids:
            keys = DiagramHelper.identify_vertices_on_curve(diagram, guid)
            if keys:
                vertices = set(keys)
                for u, v in diagram.edges():
                    if u in vertices and v in vertices:
                        edges.append((u, v))
        return edges

    @staticmethod
    def move(diagram):
        color  = Rhino.ApplicationSettings.AppearanceSettings.FeedbackColor
        origin = {key: diagram.vertex_coordinates(key) for key in diagram.vertices()}
        vertex = {key: diagram.vertex_coordinates(key) for key in diagram.vertices()}
        edges  = list(diagram.edges())
        start  = compas_rhino.pick_point('Point to move from?')

        if not start:
            return False

        def OnDynamicDraw(sender, e):
            current = list(e.CurrentPoint)
            vec = [current[i] - start[i] for i in range(3)]

            for key in vertex:
                vertex[key] = [origin[key][i] + vec[i] for i in range(3)]

            for u, v in iter(edges):
                sp = vertex[u]
                ep = vertex[v]
                sp = Point3d(*sp)
                ep = Point3d(*ep)
                e.Display.DrawDottedLine(sp, ep, color)

        gp = Rhino.Input.Custom.GetPoint()
        gp.SetCommandPrompt('Point to move to?')
        gp.DynamicDraw += OnDynamicDraw

        gp.Get()

        if gp.CommandResult() == Rhino.Commands.Result.Success:
            end = list(gp.Point())
            vec = [end[i] - start[i] for i in range(3)]

            for key, attr in diagram.vertices(True):
                attr['x'] += vec[0]
                attr['y'] += vec[1]
                attr['z'] += vec[2]

            return True
        return False

