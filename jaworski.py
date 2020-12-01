# python 3.7
import nltk
import re
import argparse
import io

# line-based parser for plain text and ATF formats
# text: default mode, parse one line at a time (these lines don't necessarily contain complete information)
# atf: use this if file ends in '.atf', extracts text before running in text mode

# use jaworsky4conll.py if you want to take existing annotations into account, e.g., to deduce an alternative segmentation or exploit morphology annotation
# unlike jaworsky4conll.py which iterates multiple times (to implement a preference over different start symbols), this is optimised for speed, but it may return a dispreferred analysis

########
# init #
########

parser = argparse.ArgumentParser(description='parse transactions from Ur-III admin texts, plain text format')
parser.add_argument('files', metavar='FILE.txt', type=str, nargs='+',
                    help='text (default) or ATF files (ending in ".atf"); text mode: expect one sentence per line, newline-separated; ATF mode: extract text before running analysis')

args = parser.parse_args()
files=args.files

#################
# aux functions #
#################

def get_missing_words(grammar, tokens):
    """
    Find list of missing tokens not covered by grammar
    """
    missing = [tok for tok in tokens
               if not grammar._lexical_index.get(tok)]
    return missing

##########
# config #
##########

grammar = nltk.data.load("jaworski.cfg")
# print(grammar)

# runtime eval on sample data (P106438.txt; note that these runtimes aren't absolute, all left-corner parsers seem to be runtime-equivalent)
PARSER_CLASS=nltk.parse.IncrementalLeftCornerChartParser						# 11.5 s
# PARSER_CLASS=nltk.parse.earleychart.IncrementalLeftCornerChartParser			# 12.0 s
# PARSER_CLASS=nltk.parse.chart.LeftCornerChartParser							# 12.1 s
# PARSER_CLASS=nltk.parse.chart.BottomUpLeftCornerChartParser					# 13.7 s
# PARSER_CLASS=nltk.parse.earleychart.IncrementalBottomUpLeftCornerChartParser	# 13.9 s

# PARSER_CLASS=nltk.parse.ChartParser											# 14.1 s
# PARSER_CLASS=nltk.parse.earleychart.IncrementalChartParser					# 14.1 s
# PARSER_CLASS=nltk.parse.earleychart.IncrementalBottomUpChartParser			# 15.7 s
# PARSER_CLASS=nltk.parse.BottomUpChartParser									# 15.8 s
# PARSER_CLASS=nltk.parse.IncrementalBottomUpChartParser						# 16.6 s
# PARSER_CLASS=nltk.parse.earleychart.EarleyChartParser							# 25.2 s
# PARSER_CLASS=nltk.parse.earleychart.IncrementalTopDownChartParser 			# 25.6 s
# PARSER_CLASS=nltk.parse.chart.TopDownChartParser								# 27.7 s

## failed
# PARSER_CLASS=nltk.parse.ShiftReduceParser 						# lossy; numerous "will never be used" warnings
# PARSER_CLASS=nltk.parse.RecursiveDescentParser					# ran into infinite loop
# PARSER_CLASS=nltk.parse.recursivedescent.RecursiveDescentParser	# interrupted after 17 s

parser=PARSER_CLASS(grammar)

new_grammar=str(grammar)
for rhs in set(map(lambda x: x.lhs(), grammar.productions())): #[ "DATED_TRANSACTION", "TRANSACTION", "NUMBER_PRODUCT_LIST", "AGENT" ]: 
	new_grammar=new_grammar+"\nLINE -> "+str(rhs)
new_grammar=nltk.grammar.CFG.fromstring(new_grammar.split('\n')[1:])
parser=PARSER_CLASS(new_grammar)
grammar=new_grammar

for file in files:
	text=None
	
	if file.endswith(".atf"):
		tmpfile=io.StringIO()
		with open(file, "r") as atf:
			line=atf.readline()
			textline=re.compile(r"^[0-9]+\.?\s+")
			while line:
				line=line.strip()
				if(textline.match(line)):
					tmpfile.write(re.sub(textline,"",line)+"\n")
				elif(line.startswith("#") or len(line)==0):
					tmpfile.write(line+"\n")
				else:
					tmpfile.write("# "+line+"\n")
					tmpfile.flush()
				line=atf.readline()
		text=tmpfile.getvalue()
		tmpfile.close()
	else:
		with open(file,"r") as input:
			text=input.read()

	for line in text.split("\n"):
		s=line.strip()
		
		if(s.startswith("#")):
			print(s+"\n")
		elif(len(s)==0):
			print()
		else:
			print('# '+s)
			s=re.sub(r"[#!\[\]\?]","",s)	# remove special characters that are reserved characters in URIs
			s=s.split(" ")
			OOVrules=[]
			for w in  get_missing_words(grammar, s):
				lhs = nltk.grammar.Nonterminal('UNKNOWN')
				new_production=nltk.grammar.Production(lhs, [w])
				OOVrules.append(new_production)
			if len(OOVrules)>0:
				new_grammar=str(grammar)
				for r in OOVrules:
					new_grammar=new_grammar+"\n"+str(r)
				
				lhss=set(map(lambda x: str(x.lhs()), grammar.productions()))
				if not "UNKNOWN" in lhss:
					for lhs in lhss:
						if lhs!="LINE":
							new_grammar=new_grammar+"\nFRAG -> "+str(lhs)+ " FRAG | FRAG "+str(lhs)
				new_grammar=nltk.grammar.CFG.fromstring(new_grammar.split('\n')[1:])
				new_grammar._start = nltk.grammar.Nonterminal("LINE") #grammar.start()
				# print(new_grammar)
				parser=PARSER_CLASS(new_grammar)
					
			parses=[]
			# print(parser.grammar().productions())
			#for start in set(map(lambda x: x.lhs(), parser.grammar().productions())):
			if(len(parses)==0):
				#parser.grammar()._start = nltk.grammar.Nonterminal(str(start))
				parses=list(parser.parse(s))
				if(len(parses)>0):
					print(parses[0])
			if(len(parses)==0):		# cannot happen anymore
				parse="(FRAG\n"
				for w in s:
					nterms=set(map(lambda x: str(x.lhs()),grammar.productions(rhs=w)))
					nterms=sorted(list(nterms))
					parse=parse+"  ("+"|".join(nterms)+ " "+w+")\n"
				parse=parse+")"
				#parse=nltk.Tree.fromstring(parse)
				#print("# unseen combination of parseable phrases")
				print(parse)
			print()
