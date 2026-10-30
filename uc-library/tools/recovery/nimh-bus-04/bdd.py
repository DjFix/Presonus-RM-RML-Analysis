"""Canonical Boolean functions over explicit state/pad/primitive boundaries."""
from functools import lru_cache

class BDD:
    def __init__(self,eq,aliases=None,limit=500000,replacements=None):
        self.eq=eq;self.aliases=aliases or {};self.nodes=[None,None];self.unique={};self.memo={};self.limit=limit
        self.leaves=sorted(n for n,r in eq.items() if r['op'] in ('ff','latch','gap','pad'))
        self.order={n:i for i,n in enumerate(self.leaves)}
        self.replacements=replacements or {}
    def rep(self,n):
        while n in self.aliases:n=self.aliases[n]
        return n
    def node(self,v,l,h):
        if l==h:return l
        key=(v,l,h)
        if key not in self.unique:
            if len(self.nodes)>=self.limit:raise OverflowError('BDD budget')
            self.unique[key]=len(self.nodes);self.nodes.append(key)
        return self.unique[key]
    def var(self,n):return self.node(self.order[self.rep(n)],0,1)
    @lru_cache(maxsize=None)
    def ite(self,s,h,l):
        if s==1:return h
        if s==0 or h==l:return l
        if h==1 and l==0:return s
        v=min(self.nodes[x][0] for x in (s,h,l) if x>1)
        def branch(x,k):return self.nodes[x][k] if x>1 and self.nodes[x][0]==v else x
        low=self.ite(branch(s,1),branch(h,1),branch(l,1))
        high=self.ite(branch(s,2),branch(h,2),branch(l,2))
        return self.node(v,low,high)
    def inv(self,x):return self.ite(x,0,1)
    def build(self,n):
        if n.startswith('~'):return self.inv(self.build(n[1:]))
        if n in ('0','1'):return int(n)
        n=self.rep(n)
        if n in self.memo:return self.memo[n]
        if n in self.replacements:
            x=self.build(self.replacements[n]);self.memo[n]=x;return x
        r=self.eq[n];op=r['op']
        if op in ('ff','latch','gap','pad'):out=self.var(n)
        elif op=='alias':out=self.build(r['args'][0])
        elif op=='xor':
            a,b=map(self.build,r['args']);out=self.ite(a,self.inv(b),b)
        elif op=='mux':
            s,a,b=map(self.build,r['args']);out=self.ite(s,b,a)
        elif op=='lut':
            args=[self.build(x) for x in r['args']]
            def lut(table,ix):
                if ix==len(args):return table&1
                low=sum(((table>>j)&1)<<k for k,j in enumerate(range(0,1<<(len(args)-ix),2)))
                high=sum(((table>>j)&1)<<k for k,j in enumerate(range(1,1<<(len(args)-ix),2)))
                return self.ite(args[ix],lut(high,ix+1),lut(low,ix+1))
            out=lut(r['init'],0)
        else:raise ValueError(op)
        self.memo[n]=out;return out
    def cubes(self,n,limit=100):
        out=[]
        def walk(x,path):
            if len(out)>limit:raise OverflowError('Cube budget')
            if x==0:return
            if x==1:out.append(dict(path));return
            v,l,h=self.nodes[x];name=self.leaves[v]
            path[name]=0;walk(l,path);path[name]=1;walk(h,path);path.pop(name)
        walk(n,{})
        return out
    def signature(self,n):
        import hashlib
        @lru_cache(maxsize=None)
        def rec(x):
            if x<2:return str(x)
            v,l,h=self.nodes[x]
            return hashlib.sha256((self.leaves[v]+':'+rec(l)+':'+rec(h)).encode()).hexdigest()
        return rec(n)
    def restrict(self,root,assignment):
        byindex={self.order[self.rep(k)]:v for k,v in assignment.items()}
        @lru_cache(maxsize=None)
        def walk(x):
            if x<2:return x
            v,l,h=self.nodes[x]
            if v in byindex:return walk(h if byindex[v] else l)
            return self.node(v,walk(l),walk(h))
        return walk(root)
    def support(self,root):
        seen=set();variables=set();todo=[root]
        while todo:
            x=todo.pop()
            if x<2 or x in seen:continue
            seen.add(x);v,l,h=self.nodes[x];variables.add(self.leaves[v]);todo.extend([l,h])
        return variables
