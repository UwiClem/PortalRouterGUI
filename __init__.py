# -*- coding: utf-8 -*-

def classFactory(iface):
    from .portal_router_gui import PortalRouterGUI
    return PortalRouterGUI(iface)

