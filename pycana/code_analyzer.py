from inspect import *
from pygraphviz import AGraph
from collections import defaultdict
from itertools import chain

from relations import *

def is_container(var):
    return isinstance(var, list) or isinstance(var, dict) or isinstance(var, set)

def itercontainer(c):
    assert is_container(c)
    if isinstance(c, list):
        return ([e] for e in c)
    elif isinstance(c, dict):
        return c.iteritems()
    elif isinstance(c, set):
        return ([e] for e in c)

class CodeAnalyzer(object):
    def __init__(self, base_module):
        self.base_module= base_module

    def analyze(self, exceptions=None):
        variables= currentframe(1).f_locals
        module_vars= []
        for varname, var in variables.iteritems():
            if self._belongs_to_module(var):
                module_vars.append(var)

        aggregation_relations= defaultdict(set)
        for var in module_vars:
            self._get_aggregation_relations(var, module_vars, aggregation_relations)

        if exceptions is not None:
            for klass in exceptions:
                if klass in aggregation_relations: aggregation_relations.pop(klass)

                for other_klass, related in aggregation_relations.iteritems():
                    aggregation_relations[other_klass]= set(r for r in related if not r.object2 == klass)
        

        all_classes= set(aggregation_relations.keys())
        for related in aggregation_relations.itervalues():
            all_classes.update(i.object2 for i in related)

        relations= aggregation_relations
        inheritance_relations= self._build_inheritance_relations(all_classes)
        for klass, related in inheritance_relations.iteritems():
            relations[klass].update(related)

        return relations

    def _build_inheritance_relations(self, all_classes):
        inheritance_relations= defaultdict(list)
 
        new_classes= set()
        for n1 in all_classes:
            super_n1= n1.mro()[1]
            if super_n1 == object: continue
            if super_n1 not in all_classes: 
                new_classes.add(super_n1)
            relation= InheritanceRelation(n1, super_n1)
            inheritance_relations[n1].append(relation)

        all_classes.update(new_classes) 

        for n1 in all_classes:
            for n2 in all_classes:
                if n1 == n2: continue
                if issubclass(n1, n2):
                    for relation in inheritance_relations[n1]:
                        if issubclass(n2, relation.object2): break
                    else:
                        inheritance_relations[n1].append(InheritanceRelation(n1, n2))

        return inheritance_relations

    def _belongs_to_module(self, var):
        var_module= getmodule(var.__class__)
        return var_module.__name__.startswith(self.base_module.__name__)
        
    def _get_aggregation_relations(self, module_var, module_vars, aggregation_relations):
        assert module_var in module_vars
        aggregation_relations[module_var.__class__]

        for attrname, attrvalue in getmembers(module_var):
            if not self._is_member_interesting(attrname): continue
            if self._belongs_to_module(attrvalue):
                if attrvalue not in module_vars:
                    module_vars.append(attrvalue)
                    self._get_aggregation_relations(attrvalue, module_vars, aggregation_relations)

                relation= AggregationRelation(module_var.__class__, attrvalue.__class__, attrname, is_multiple=False)
                aggregation_relations[module_var.__class__].add(relation)

            if is_container(attrvalue):
                container_module_vars= self._container_relations(attrvalue, module_vars, aggregation_relations)
                for container_module_var in container_module_vars:
                    relation= AggregationRelation(module_var.__class__, container_module_var.__class__, attrname, is_multiple=True)
                    aggregation_relations[module_var.__class__].add(relation)

    def _container_relations(self, container, module_vars, aggregation_relations):
        container_module_vars= []
        for iterable in itercontainer(container):
            for e in iterable:
                if self._belongs_to_module(e):
                    container_module_vars.append(e)
                    if not e in module_vars: module_vars.append(e)
                    self._get_aggregation_relations(e, module_vars, aggregation_relations)
                elif is_container(e):
                    container_module_vars.extend(self._container_relations(e, module_vars, aggregation_relations))
        return container_module_vars                    

    def draw_relations(self, relations, fname):
        def get_node_name(n):
            return n.__name__

        g= AGraph(directed=True)
        for n in relations:
            n_name= get_node_name(n)
            g.add_node(n_name)

        for relation in chain(*relations.itervalues()):
            n1_name= get_node_name(relation.object1)
            n2_name= get_node_name(relation.object2)
            g.add_edge(n1_name, n2_name)

            e= g.get_edge(n1_name, n2_name)
            relation.set_edge_attributes(e)

        for n in g.nodes():
            n.attr['shape']= 'box'

        g.draw(fname, prog='dot', args='-Grankdir=TB')
        
    def _is_member_interesting(self, attrname):
        return not attrname in ['__setattr__',
                                '__reduce_ex__',
                                '__new__',
                                '__reduce__',
                                '__str__',
                                '__getattribute__',
                                '__class__',
                                '__delattr__',
                                '__repr__',
                                '__hash__',
                                '__doc__',
                                '__init__',
                                '__dict__',
                                '__module__',
                                '__weakref__']

                                            
    
