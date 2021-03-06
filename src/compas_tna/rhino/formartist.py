from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import compas
import compas_rhino

from compas.geometry import scale_vector
from compas.utilities import i_to_green

from compas_rhino.artists import MeshArtist


__all__ = ['FormArtist']


class FormArtist(MeshArtist):

    __module__ = 'compas_tna.rhino'


    def __init__(self, form, layer=None):
        super(FormArtist, self).__init__(form, layer=layer)
        self.settings.update({
            'color.vertex'     : (255, 255, 255),
            'color.edge'       : (0, 0, 0),
            'color.face'       : (210, 210, 210),
            'color.reaction'   : (0, 255, 0),
            'color.residual'   : (0, 255, 255),
            'color.load'       : (0, 255, 0),
            'color.selfweight' : (0, 0, 255),
            'color.force'      : (0, 0, 255),
            'scale.reaction'   : 1.0,
            'scale.residual'   : 1.0,
            'scale.load'       : 1.0,
            'scale.force'      : 1.0,
            'scale.selfweight' : 1.0,
            'tol.reaction'     : 1e-3,
            'tol.residual'     : 1e-3,
            'tol.load'         : 1e-3,
            'tol.force'        : 1e-3,
            'tol.selfweight'   : 1e-3,
        })

    @property
    def form(self):
        return self.mesh

    def clear(self):
        super(FormArtist, self).clear()
        self.clear_loads()
        self.clear_selfweight()
        self.clear_reactions()
        self.clear_forces()
        self.clear_residuals()
        self.clear_angles()

    def clear_loads(self):
        compas_rhino.delete_objects_by_name(name='{}.load.*'.format(self.form.name))

    def clear_selfweight(self):
        compas_rhino.delete_objects_by_name(name='{}.selfweight.*'.format(self.form.name))

    def clear_reactions(self):
        compas_rhino.delete_objects_by_name(name='{}.reaction.*'.format(self.form.name))

    def clear_forces(self):
        compas_rhino.delete_objects_by_name(name='{}.force.*'.format(self.form.name))

    def clear_residuals(self):
        compas_rhino.delete_objects_by_name(name='{}.residual.*'.format(self.form.name))

    def clear_angles(self):
        compas_rhino.delete_objects_by_name(name='{}.angle.*'.format(self.form.name))

    def draw_loads(self, scale=None, color=None):
        self.clear_loads()

        lines = []
        color = color or self.settings['color.load']
        scale = scale or self.settings['scale.load']
        tol   = self.settings['tol.load']
        tol2  = tol ** 2

        for key, attr in self.form.vertices_where({'is_anchor': False, 'is_external': False}, True):
            px = scale * attr['px']
            py = scale * attr['py']
            pz = scale * attr['pz']

            if px ** 2 + py ** 2 + pz ** 2 < tol2:
                continue

            sp = self.form.vertex_coordinates(key)
            ep = sp[0] + px, sp[1] + py, sp[2] + pz

            lines.append({
                'start' : sp,
                'end'   : ep,
                'color' : color,
                'arrow' : 'end',
                'name'  : "{}.load.{}".format(self.form.name, key)
            })

        compas_rhino.draw_lines(lines, layer=self.layer, clear=False, redraw=False)

    def draw_selfweight(self, scale=None, color=None):
        self.clear_selfweight()

        lines = []
        color = color or self.settings['color.selfweight']
        scale = scale or self.settings['scale.selfweight']
        tol   = self.settings['tol.selfweight']
        tol2  = tol ** 2

        for key, attr in self.form.vertices_where({'is_anchor': False, 'is_external': False}, True):
            t = attr['t']
            a = self.form.vertex_area(key)
            sp = self.form.vertex_coordinates(key)

            dz = scale * t * a

            if dz ** 2 < tol2:
                continue

            ep = sp[0], sp[1], sp[2] - dz

            lines.append({
                'start' : sp,
                'end'   : ep,
                'color' : color,
                'arrow' : 'end',
                'name'  : "{}.selfweight.{}".format(self.form.name, key)
            })

        compas_rhino.draw_lines(lines, layer=self.layer, clear=False, redraw=False)

    def draw_reactions(self, scale=None, color=None):
        self.clear_reactions()

        lines = []
        color = color or self.settings['color.reaction']
        scale = scale or self.settings['scale.reaction']
        tol   = self.settings['tol.reaction']
        tol2  = tol ** 2

        for key, attr in self.form.vertices_where({'is_anchor': True}, True):
            rx = attr['rx']
            ry = attr['ry']
            rz = attr['rz']

            for nbr in self.form.vertex_neighbors(key):
                is_external = self.form.edge_attribute((key, nbr), 'is_external')

                if is_external:
                    f = self.form.edge_attribute((key, nbr), 'f')
                    u = self.form.edge_direction(key, nbr)
                    u[2] = 0
                    v = scale_vector(u, f)

                    rx += v[0]
                    ry += v[1]

            rx = scale * rx
            ry = scale * ry
            rz = scale * rz

            sp = self.form.vertex_coordinates(key)

            if rx ** 2 + ry ** 2 > tol2:
                e1 = sp[0] + rx, sp[1] + ry, sp[2]
                lines.append({
                    'start' : sp,
                    'end'   : e1,
                    'color' : color,
                    'arrow' : 'start',
                    'name'  : "{}.reaction.{}".format(self.form.name, key)
                })

            if rz ** 2 > tol2:
                e2 = sp[0], sp[1], sp[2] + rz
                lines.append({
                    'start' : sp,
                    'end'   : e2,
                    'color' : color,
                    'arrow' : 'start',
                    'name'  : "{}.reaction.{}".format(self.form.name, key)
                })

        compas_rhino.draw_lines(lines, layer=self.layer, clear=False, redraw=False)

    def draw_forces(self, scale=None, color=None):
        self.clear_forces()

        lines = []
        color = color or self.settings['color.force']
        scale = scale or self.settings['scale.force']
        tol   = self.settings['tol.force']
        tol2  = tol ** 2

        for u, v, attr in self.form.edges_where({'is_edge': True, 'is_external': False}, True):
            sp, ep = self.form.edge_coordinates(u, v)
            radius = scale * attr['f']

            if radius ** 2 < tol2:
                continue

            lines.append({
                'start'  : sp,
                'end'    : ep,
                'radius' : radius,
                'color'  : color,
                'name'   : "{}.force.{}-{}".format(self.form.name, u, v)
            })

        compas_rhino.draw_cylinders(lines, layer=self.layer, clear=False, redraw=False)

    def draw_residuals(self, scale=None, color=None):
        self.clear_residuals()

        lines = []
        color = color or self.settings['color.residual']
        scale = scale or self.settings['scale.residual']
        tol   = self.settings['tol.residual']
        tol2  = tol ** 2

        for key, attr in self.form.vertices_where({'is_anchor': False, 'is_external': False}, True):
            rx = scale * attr['rx']
            ry = scale * attr['ry']
            rz = scale * attr['rz']

            if rx ** 2 + ry ** 2 + rz ** 2 < tol2:
                continue

            sp = self.form.vertex_coordinates(key)
            ep = sp[0] + rx, sp[1] + ry, sp[2] + rz

            lines.append({
                'start' : sp,
                'end'   : ep,
                'color' : color,
                'arrow' : 'start',
                'name'  : "{}.residual.{}".format(self.form.name, key)
            })

        compas_rhino.draw_lines(lines, layer=self.layer, clear=False, redraw=False)

    def draw_angles(self, tol=5.0):
        self.clear_angles()

        a = self.form.edges_attribute('a')
        a_max = tol
        a_min = 0
        a_range = a_max - a_min

        if a_range:
            labels = []
            for u, v, attr in self.form.edges(True):
                a = 180 * attr['a'] / 3.14159
                if a > tol:
                    labels.append({
                        'pos'   : self.form.edge_midpoint(u, v),
                        'text'  : "{:.2f}".format(attr['a'] / 3.14159 * 180),
                        'color' : i_to_green((attr['a'] - a_min) / a_range),
                        'name'  : "{}.angle.{}-{}".format(self.form.name, u, v)
                    })

            compas_rhino.draw_labels(labels, layer=self.layer, clear=False, redraw=False)

# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    pass
