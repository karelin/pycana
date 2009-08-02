from inspect import *
from collections import defaultdict

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

        instance_aggregation_relations= defaultdict(set)
        for var in module_vars:
            self._get_instance_aggregate_relations(var, module_vars, instance_aggregation_relations)

        class_aggregation_relations= self._build_class_relations(instance_aggregation_relations)

        if exceptions is not None:
            for klass in exceptions:
                if klass in class_aggregation_relations: class_aggregation_relations.pop(klass)

                for other_klass, related in class_aggregation_relations.iteritems():
                    class_aggregation_relations[other_klass]= set((yet_another_klass, attrname) 
                                        for (yet_another_klass, attrname) in related 
                                            if not yet_another_klass == klass)
        

        all_classes= set(class_aggregation_relations.keys())
        for related in class_aggregation_relations.itervalues():
            all_classes.update(i[0] for i in related)

        inheritance_relations= self._build_inheritance_relations(all_classes)

        return inheritance_relations, class_aggregation_relations                                 

    def _build_class_relations(self, aggregation_relations):
        ans= defaultdict(set)
        for k, v in aggregation_relations.iteritems():
            ans[k.__class__].update((e[0].__class__, e[1]) for e in v)
        return ans            
    
    def _build_inheritance_relations(self, all_classes):
        inheritance_relations= defaultdict(list)
 
        new_classes= set()
        for n1 in all_classes:
            for super_n1 in n1.mro()[1:-1]:
                if super_n1 not in all_classes: new_classes.add(super_n1)
                inheritance_relations[n1].append(super_n1)

        all_classes.update(new_classes) 

        for n1 in all_classes:
            for n2 in all_classes:
                if n1 == n2: continue
                if issubclass(n1, n2):
                    inheritance_relations[n1].append(n2)

        return inheritance_relations

    def _belongs_to_module(self, var):
        var_module= getmodule(var.__class__)
        return var_module.__name__.startswith(self.base_module.__name__)
        
    def _get_instance_aggregate_relations(self, module_var, module_vars, aggregation_relations):
        assert module_var in module_vars
        aggregation_relations[module_var]

        for attrname, attrvalue in getmembers(module_var):
            if not self._is_member_interesting(attrname): continue
            if self._belongs_to_module(attrvalue):
                if attrvalue not in module_vars:
                    module_vars.append(attrvalue)
                    self._get_instance_aggregate_relations(attrvalue, module_vars, aggregation_relations)
                aggregation_relations[module_var].add((attrvalue, attrname))

            if is_container(attrvalue):
                container_module_variables= self._container_relations(attrvalue, module_vars, aggregation_relations)
                aggregation_relations[module_var].update((cmv, attrname) for cmv in container_module_variables)

    def _container_relations(self, container, module_vars, aggregation_relations):
        container_module_variables= []
        for iterable in itercontainer(container):
            for e in iterable:
                if self._belongs_to_module(e):
                    container_module_variables.append(e)
                    if not e in module_vars: module_vars.append(e)
                    self._get_instance_aggregate_relations(e, module_vars, aggregation_relations)
                elif is_container(e):
                    container_module_variables.extend(self._container_relations(e, module_vars, aggregation_relations))
        return container_module_variables                    

    def draw_relations(self, aggregation_relations, inheritance_relations, fname):
        from pygraphviz import AGraph

        g= AGraph(directed=True)
        for n1, related in aggregation_relations.iteritems():
            for n2, attrname in related:
                g.add_edge(n1, n2)
                e= g.get_edge(n1, n2)
                e.attr['arrowhead']= 'odiamond'
                e.attr['label']= attrname
        
        for n1, subclasses in inheritance_relations.iteritems():
            for n2 in subclasses:
                g.add_edge(n1, n2)
                e= g.get_edge(n1, n2)
                e.attr['arrowhead']= 'empty'

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

                                            
    
