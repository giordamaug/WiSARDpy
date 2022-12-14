#
# WiSARD in python: 
# Classification and Regression
# by Maurizio Giordano (2022)
#
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn import preprocessing
from sklearn.model_selection import train_test_split, cross_val_predict
from sklearn.linear_model import LinearRegression
import sklearn.metrics as metrics
from lightgbm import LGBMRegressor
from wisardpy.base import WiSARDRegressor
from sklearn.ensemble import RandomForestRegressor
import time 
import argparse

parser = argparse.ArgumentParser(description='WiSARD in python')
parser.add_argument('-i', "--inputfile", dest='inputfile', metavar='<input file>', help='input file name', required=True)
parser.add_argument('-b', "--nbits", dest='nbits', metavar='<no of bits>', type=int, help='number of bits (default: 4)' , default=4, required=False)
parser.add_argument('-z', "--ntics", dest='ntics', metavar='<no of tics>', type=int, help='number of tics (default: 128)' , default=128, required=False)
parser.add_argument('-c', "--cvfold", dest='cvfold', metavar='<no of cv folds>', type=int, help='number of folds' , required=False)
parser.add_argument('-t', "--testsize", dest='testsize', metavar='<testsize>', type=int, default=10, help='testsize (in %)' , required=False)
parser.add_argument('-p', "--jobs", dest='jobs', metavar='<no of parallel jobs>', type=int, help='number of parallel jobs' , required=False)
parser.add_argument('-s', "--seed", dest='seed', metavar='<seed>', type=int, help='seed (default: 0)' , default=0, required=False)
parser.add_argument('-m', "--maptype", dest='maptype', metavar='<maptype>', type=str, help='mapping type (default: random, choice: random|linear)', choices=['random', 'linear'], default='random', required=False)
parser.add_argument('-T', "--targetname", dest='targetname', metavar='<targetname>', type=str, help='target name (default: class)', default='class', required=False)
parser.add_argument('-M', "--method", dest='method', metavar='<method>', type=str, help='classifier name (default: RF, choice: RF|LGBM|WNN)', choices=['RF', 'WNN', 'LGBM'], default='WNN', required=False)
parser.add_argument('-D', "--debug", action='store_true', required=False)
parser.add_argument('-S', "--save-embedding", dest='saveembedding',  action='store_true', required=False)
parser.add_argument('-X', "--display", action='store_true', required=False)
args = parser.parse_args()

df = pd.read_csv(args.inputfile)
print(df.head())

labelname = args.targetname
X = np.array(df.drop(labelname, axis=1))
y = np.array(df[labelname])

if args.method == 'RF':
	regr = RandomForestRegressor()
elif args.method == 'LGBM':
	regr = LGBMRegressor()
elif args.method == 'WNN':
	regr = WiSARDRegressor(n_bits=args.nbits, n_tics=args.ntics, random_state=args.seed, mapping=args.maptype, code='t', scale=True, debug=True)
else:
	raise Exception("Wron regression method")

start = time.time()
if args.cvfold is None:
	print(f"Train/Test split ({args.testsize / 100.0}) ...")
	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=args.testsize / 100.0) 
	y_pred = regr.fit(X_train, y_train).predict(X_test)
	targets = y_test
else:
	print(f"{args.cvfold}-fold Cross Validation...")
	y_pred = cross_val_predict(regr, X, y, cv=args.cvfold)
	targets = y
print("--- %s seconds ---" % (time.time() - start))
print(regr)

print(f"Mean squared error: {round(metrics.mean_squared_error(targets, y_pred),3)}")
print(f"Coefficient of determination: {round(metrics.r2_score(targets, y_pred)*100,2)} %")
if args.display:
	# visualizing in a plot
	x_ax = range(len(targets))
	plt.figure(figsize=(12, 6))
	plt.plot(x_ax, targets, label="original")
	plt.plot(x_ax, y_pred, label="predicted")
	plt.title("Dataset test and predicted data")
	plt.xlabel('X')
	plt.ylabel('Price')
	plt.legend(loc='best',fancybox=True, shadow=True)
	plt.grid(True)
	plt.show()  

