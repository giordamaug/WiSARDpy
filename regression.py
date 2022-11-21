#
# WiSARD in python: 
# Classification and Regression
# by Maurizio Giordano (2022)
#
import numpy as np
from utilities import *
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
import ram
mypowers = 2**np.arange(32, dtype = np.uint32)[::]

class Encoder():

    def _genCode(self, n):
        if n == 0:
            return ['']
        code1 = self._genCode(n-1)
        code2 = []
        for codeWord in code1:
            code2 = [codeWord] + code2
        for i in range(len(code1)):
            code1[i] += '0'
        for i in range(len(code2)):
            code2[i] += '1'
        return code1 + code2   

    def _binarize(self, X, code='t', scale=True):
        # dataset normalization (scaling to 0-1)
        if scale:
            scaler = MinMaxScaler(feature_range=(0.0, 1.0))
            X = scaler.fit_transform(X)
            X = X.astype(np.float)

        # binarize (histogram)
        tX = (X * self._retina_size).astype(np.int32)

        if code == 'g':
            ticsize = self._retina_size.bit_length()
            nX = np.zeros([tX.shape[0],tX.shape[1]*ticsize], dtype=np.int)
            graycode = genCode(ticsize)
            for r in range(tX.shape[0]):
                newRow = [int(e) for e in list(''.join([graycode[tX[r,i]] for i in range(tX.shape[1])]))]
                for i in range(tX.shape[1]*ticsize):
                    nX[r,i] = newRow[i]
        elif code == 't':
            nX = np.zeros([tX.shape[0],tX.shape[1]*self._retina_size], dtype=np.int)
            for r in range(tX.shape[0]):
                for i in range(tX.shape[1]*self._retina_size):
                    if i % self._retina_size < tX[r,int(i / self._retina_size)]:
                        nX[r,i] = 1
        elif code == 'c':
            nX = np.zeros([tX.shape[0],tX.shape[1]*size], dtype=np.int)
            for r in range(tX.shape[0]):
                for i in range(tX.shape[1]*self._retina_size):
                    if i % self._retina_size + 1== tX[r,int(i / self._retina_size)]:
                        nX[r,i] = 1
        else:
            raise Exception('Unsupported data code!')
        return nX
        
    def _mk_tuple(self, X):
        addresses = [0]*self._nrams
        for i in range(self._nrams):
            for j in range(self._nobits):
                addresses[i] += mypowers[self._nobits -1 - j] * X[self._mapping[((i * self._nobits) + j) % self._retina_size]]
        return addresses

class WiSARDRegressor(BaseEstimator, RegressorMixin, Encoder):
    """WiSARD Regressor """
    
    #def __init__(self,  nobits, size, map=-1, classes=[0,1], dblvl=0):
    def __init__(self,  n_bits=8, n_tics=256, random_state=0, mapping='random', code='t', scale=True, debug=False):
        if (not isinstance(n_bits, int) or n_bits<1 or n_bits>64):
            raise Exception('number of bits must be an integer between 1 and 64')
        if (not isinstance(n_tics, int) or n_tics<1):
            raise Exception('number of bits must be an integer greater than 1')
        if (not isinstance(debug, bool)):
            raise Exception('debug flag must be a boolean')
        if (not isinstance(mapping, str)) or (not (mapping=='random' or mapping=='linear')):
            raise Exception('mapping must either \"random\" or \"linear\"')
        if (not isinstance(code, str)) or (not (code=='g' or code=='t' or code=='c')):
            raise Exception('code must either \"t\" (termometer) or \"g\" (graycode) or \"c\" (cursor)')
        if (not isinstance(random_state, int)) or random_state<0:
            raise Exception('random state must be an integer greater than 0')
        self._nobits = n_bits
        self._notics = n_tics
        self._code = code
        self._scale = scale
        self._nrams = 0
        self._maptype = mapping
        self._seed = random_state
        if self._seed > -1: np.random.seed(self._seed) 
        self._debug = debug
        self._nloc = mypowers[self._nobits]
        
    def train(self, X, y):
        ''' Learning '''
        addresses = self._mk_tuple(X)
        for i in range(self._nrams):
            self._rams[i].updEntry(addresses[i], y)

    def test(self, X):
        ''' Testing '''
        addresses = self._mk_tuple(X)
        res = [sum(i) for i in zip(*[self._rams[i].getEntry(addresses[i]) for i in range(self._nrams)])]
        return float(res[1])/float(res[0]) if res[0] != 0 else 0.0
    
    def fit(self, X, y):
        self._retina_size = self._notics * len(X[0])   # set retin size (# feature x # of tics)
        self._nrams = int(self._retina_size/self._nobits) if self._retina_size % self._nobits == 0 else int(self._retina_size/self._nobits + 1)
        self._mapping = np.arange(self._retina_size, dtype=int)
        self._rams = [ram.Ram() for _ in range(self._nrams)] 
        if self._maptype=="random":                 # random mapping
            np.random.shuffle(self._mapping)
        X = self._binarize(X, code=self._code, scale=self._scale)
        if self._debug: timing_init()
        delta = 0                                   # inizialize error
        for i,sample in enumerate(X):
            if self._debug:  print("Target %d"%y[i], end='')
            self.train(sample, y[i])        
            res = self.test(sample)
            delta += abs(y[i] - res)
            if self._debug: timing_update(i,y[i]==res,title='train ',size=len(X),error=delta/float(i+1))
        if self._debug: print()
        return self

    def predict(self,X):
        if self._debug: timing_init()
        X = self._binarize(X, code=self._code, scale=self._scale)
        y_pred = np.array([])
        for i,sample in enumerate(X):
            y_pred = np.append(y_pred,[self.test(sample)])
            if self._debug: timing_update(i,True,title='test  ',clr=color.GREEN,size=len(X))
        if self._debug: print()
        return y_pred

    def __str__(self):
        ''' Printing function'''
        rep = "WiSARD (Size: %d, NoBits: %d, Seed: %d, RAMs: %r)\n"%(self._retina_size, self._nobits,self._seed,self._nrams)
        for i,l in enumerate(self._rams):  
            rep += "[%d] "%(i)
            c = 0
            for r in l:
                if c == 0: 
                    rep += ""
                else:
                    rep += "    "
                c += 1
                for e in r:
                    if e == 1:
                        rep += '\x1b[5;34;46m' + '%s'%(self._skip) + '\x1b[0m'   # light blue
                    else:
                        rep += '\x1b[2;35;40m' + '%s'%(self._skip) + '\x1b[0m'   # black
                rep += "\n"
            rep += "\n"
        return rep   

    def get_params(self, deep=True):
        """Get parameters for this estimator."""
        return {"n_bits": self._nobits, "n_tics": self._notics, "mapping": self._mapping, "debug": self._debug, "code" : self._code, "random_state": self._seed
              #,"bleaching": self.bleaching, "default_bleaching": self.b_def, "confidence_bleaching": self.conf_def, , "n_jobs": self.njobs
              }

    def getDataType(self):
        return self._datatype

    def getMapping(self):
        return self._mapping

    def getNoBits(self):
        return self._nobits

    def getNoTics(self):
        return self._notics

    def getNoRams(self):
        return self._nrams

class WiSARDClassifier(BaseEstimator, ClassifierMixin, Encoder):
    """WiSARD Regressor """
    
    def __init__(self,  n_bits=8, n_tics=256, random_state=0, mapping='random', code='t', scale=True, debug=False):
        if (not isinstance(n_bits, int) or n_bits<1 or n_bits>64):
            raise Exception('number of bits must be an integer between 1 and 64')
        if (not isinstance(n_tics, int) or n_tics<1):
            raise Exception('number of bits must be an integer greater than 1')
        if (not isinstance(debug, bool)):
            raise Exception('debug flag must be a boolean')
        if (not isinstance(mapping, str)) or (not (mapping=='random' or mapping=='linear')):
            raise Exception('mapping must either \"random\" or \"linear\"')
        if (not isinstance(code, str)) or (not (code=='g' or code=='t' or code=='c')):
            raise Exception('code must either \"t\" (termometer) or \"g\" (graycode) or \"c\" (cursor)')
        if (not isinstance(random_state, int)) or random_state<0:
            raise Exception('random state must be an integer greater than 0')
        self._nobits = n_bits
        self._notics = n_tics
        self._code = code
        self._scale = scale
        self._nrams = 0
        self._maptype = mapping
        self._seed = random_state
        if self._seed > -1: np.random.seed(self._seed) 
        self._debug = debug
        self._nloc = mypowers[self._nobits]
        self._wiznet = {}
        
    def train(self, X, y):
        ''' Learning '''
        addresses = self._mk_tuple(X)
        for i in range(self._nrams):
            self._wiznet[y][i].updEntry(addresses[i], y)

    def test(self, X):
        ''' Testing '''
        addresses = self._mk_tuple(X)
        res = [[1 if self._wiznet[y][i].getEntry(addresses[i]) > 0 else 0 for i in range(self._nrams)].count(1) for y in self._classes]
        print(res)
        return max(enumerate(res), key=(lambda x: x[1]))[0]
    
    def fit(self, X, y):
        self._retina_size = self._notics * len(X[0])   # set retins size (# feature x # of tics)
        self._nrams = int(self._retina_size/self._nobits) if self._retina_size % self._nobits == 0 else int(self._retina_size/self._nobits + 1)
        self._mapping = np.arange(self._retina_size, dtype=int)
        self._classes, y = np.unique(y, return_inverse=True)
        self._nclasses = len(self._classes)
        for cl in self._classes:
            self._wiznet[cl] = [ram.WRam() for _ in range(self._nrams)] 
        if self._maptype=="random":                 # random mapping
            np.random.shuffle(self._mapping)
        X = self._binarize(X, code=self._code, scale=self._scale)
        if self._debug: timing_init()
        delta = 0                                   # inizialize error
        for i,sample in enumerate(X):
            if self._debug:  print("Label %d"%y[i], end='')
            self.train(sample, y[i])        
            res = self.test(sample)
            delta += abs(y[i] - res)
            if self._debug: timing_update(i,y[i]==res,title='train ',size=len(X),error=delta/float(i+1))
        if self._debug: print()
        return self

    def predict(self,X):
        if self._debug: timing_init()
        X = self._binarize(X, code=self._code, scale=self._scale)
        y_pred = np.array([])
        for i,sample in enumerate(X):
            y_pred = np.append(y_pred,[self.test(sample)])
            if self._debug: timing_update(i,True,title='test  ',clr=color.GREEN,size=len(X))
        if self._debug: print()
        return y_pred

    def __str__(self):
        ''' Printing function'''
        rep = "WiSARD (Size: %d, NoBits: %d, Seed: %d, RAMs: %r)\n"%(self._retina_size, self._nobits,self._seed,self._nrams)
        for k,v in self._wiznet.items():
            for ram in v:  
                rep += f"{ram.wentry}"
        return f'{rep}'   

    def get_params(self, deep=True):
        """Get parameters for this estimator."""
            
        return {"n_bits": self._nobits, "n_tics": self._notics, "mapping": self._maptype, "debug": self._debug, "code" : self._code, "random_state": self._seed
              #,"bleaching": self.bleaching, "default_bleaching": self.b_def, "confidence_bleaching": self.conf_def, , "n_jobs": self.njobs
              }

    def getMapping(self):
        return self._mapping

    def getCode(self):
        return self._code

    def getNoBits(self):
        return self._nobits

    def getNoTics(self):
        return self._notics

    def getNoRams(self):
        return self._nrams

    def getClasses(self):
        return self._classes