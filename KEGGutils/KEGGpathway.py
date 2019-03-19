import networkx as nx
import xml.etree.ElementTree as et
import logging
import matplotlib.pylab as plt

from KEGGutils import draw
from KEGGutils.KEGGapi import keggapi_get

class KEGGpathway(nx.DiGraph):
    
    title = ""
    labels = {}
    reactions = {}
    relations = {}
    idcode = ""
    pos = dict()
    nodedict = {}
    genelist = []
    tree = None
    kgml_file = None
    kegg_image = []
    
    def __init__(self, *args, **kwargs):
        
        for arg in args:
            if type(arg) == str:
                if arg.find(".xml") != -1:
                    self.kgml_file = arg
                    logging.debug("found {} in args".format(self.kgml_file))
                    
                    newargs = [argument for argument in args if argument != arg]
                    args = newargs
                    break

        if 'kgml_file' in kwargs:
            self.kgml_file = kwargs.pop('kgml_file')

        super().__init__(self, *args, **kwargs)
        
        if self.kgml_file is not None:
            self.parse_kgml(self.kgml_file)
            
  
    def calc_pos(self): 
        for n in self.nodes():
            self.pos.update({n: self.node[n]['xy']})
        
    def _parse_graphics(self, graphics):
        x = int(graphics.get('x'))
        y = -int( graphics.get('y'))
        name = graphics.get('name')
        
        return name, x, y
    
    def _parse_substrate_product(self, substrate):
        id_ = int(substrate.get("id"))
        name = substrate.get("name")
        
        return id_, name
    
    def _parse_entry(self, entry):
        g_name = None
        g_x = None
        g_y = None
        component_id = None
        
        node_id = entry.get('id')
        node_name = entry.get('name')
        node_type = entry.get('type')
        node_kegglink = entry.get('link') #implied
    #    node_reaction = entry.get('reaction') #implied
    
        for child in entry.getchildren():
            if child.tag == "graphics":
                #this should happen only once
                g_name, g_x, g_y = self._parse_graphics(child)
            if child.tag == "component":
                component_id = child.get('component')
            
        node_title = g_name if g_name is not None else node_name
        self.labels[node_id] = node_title
        
        
        xy = (g_x, g_y) if ((g_x is not None) and (g_y is not None)) else None
        
        
        nodes_to_add = node_name.split()
        for i, node in enumerate(nodes_to_add):
            node_index = node_id
            if i > 1:
                node_index = node_id + "_" + str(i-1)
                
            xy = (g_x- 10*i, 10*i + g_y) if ((g_x is not None) and (g_y is not None)) else None
            self.add_node(node_index, name = node, label= node_title, nodetype = node_type, xy = xy,
                      kegglink = node_kegglink, component_id = component_id)
            
            self.nodedict[node_index] = (node, node_title, node_type)
        
        

    
    def _parse_reaction(self, reaction):
        reaction_id = reaction.get("id")
        reaction_name = reaction.get("name")
        reaction_type = reaction.get("type")
        
        reaction_alt = None
        substrates = []
        products = []
        alts = []

        for child in reaction.getchildren():
            if child.tag == "substrate":
                substrate_id, substrate_name = self._parse_substrate_product(child)
                substrates.append((substrate_id, substrate_name))
            if child.tag == "product":
                product_id, product_name = self._parse_substrate_product(child)
                products.append((product_id, product_name))
                 
            if (reaction_alt is None) and (child.find("alt") is not None):
                reaction_alt = child.find("alt").get("name")
                alts.append(reaction_alt)
        
        self.reactions[reaction_id] = {"id": reaction_id, "name": reaction_name, "type": reaction_type, "substrates": substrates, "products": products}
        
    def _parse_relation(self, relation):
        relation_type = relation.get("type")
        relation_entry1 = relation.get("entry1")
        relation_entry2 = relation.get("entry2")
        subtypes = []
        
        for subtype in relation.getchildren():
            subtype_name = subtype.get("name")
            
            if subtype_name in ("compound", "hidden compound"):
                subtype_value = int(subtype.get("value"))
            else:
                subtype_value = subtype.get("value")
            subtypes.append((subtype_name, subtype_value))
                
        self.add_edge(relation_entry1, relation_entry2, relation_type = relation_type, subtypes = subtypes)

        
        self.relations[relation_entry1+"_"+relation_entry2] = relation
        
        
        all_entry1 = [i for i in list(self.nodes) if i.startswith(relation_entry1+"_")]
        all_entry1.insert(0,relation_entry1)
        all_entry2 = [i for i in list(self.nodes) if i.startswith(relation_entry2+"_")]
        all_entry2.insert(0,relation_entry2)
        
        for e1 in all_entry1:
            for e2 in all_entry2:
                self.add_edge(e1, e2, relation_type = relation_type, subtypes = subtypes)
                self.relations[e1+"_"+e2] = (self.node[e1]['name'], self.node[e2]['name'])
            
            
        
    def parse_kgml(self, kgml_file):
        
        tree = et.parse(kgml_file)
        self.tree = tree
        
        self.title = tree.getroot().get('title')
        self.name = tree.getroot().get('name')
        self.idcode = tree.getroot().get('id')
        
        for entry in tree.getiterator('entry'):
            self._parse_entry(entry)
        for relation in tree.getiterator('relation'):
            self._parse_relation(relation)
        for reaction in tree.getiterator('reaction'):
            self._parse_reaction(reaction)

        self.calc_pos()
    
    def draw(self):
        draw(graph = self, title = self.title, pos = self.pos)
    
    def kegg_image(self):
        self.kegg_image = keggapi_get(dbentry = self.name, option = "image", show_result_image = False)
        plt.figure()
        plt.title(self.title)
        plt.imshow(self.kegg_image)
        
        
    

        