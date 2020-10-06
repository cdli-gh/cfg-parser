# python 3.7
import nltk
import re
import warnings
import os
import sys
import argparse

########
# args #
########

debug_files=[
	# 'P106438-raw.conll', 	# CoNLL-C format, without actual annotations, but using original IDs
	# 'P106438-morph.conll',	# CoNLL-C format with morphological annotations and original IDs
	'P106438.conll'		# CoNLL-U format as produced by syntactic preannotation, without original IDs
]	


parser = argparse.ArgumentParser(description='parse transactions from Ur-III admin texts, CoNLL formats')
parser.add_argument('files', metavar='FILE.conll', type=str, nargs='*',
                    help='conll files, CDLI-CoNLL or CoNLL-U formats, morphological and syntactic annotations are optional, without arguments, use '+", ".join(debug_files))

args = parser.parse_args()
files=args.files
if(len(files)==0):
	files=debug_files

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

def init_parser(PARSER, grammar):
	"""
	return an object of PARSER class, suppress warnings written to stdout
	"""
	with open(os.devnull, "w") as devnull:
		old_stdout = sys.stdout
		sys.stdout = devnull
		try:  
			parser=PARSER(grammar)
		finally:
			sys.stdout = old_stdout
	return parser

def flatten_tree(tree):
	"""
	eliminate recurrent nonterminals (note that this is very different from nltk.Tree.flatten()
	"""
#	print("flatten_tree(",tree,")")
	if(len(tree.leaves())<=1):
		return tree
	children=None
	if(len(tree)>0):
		children=[]
		for x in range(len(tree)):
			child=flatten_tree(tree[x])
			if(child.label()==tree.label() and len(child)>0):
				for y in range(len(child)):
					children.append(child[y])
			else:
				children.append(child)
					
	return nltk.Tree(tree.label(), children)
	
####################
# parse conll file #
####################

# extensions for CoNLL:
# - (re)split CoNLL-C and CoNLL-U data into lines starting with numerals (= possible transactions) and everything else
# - flatten resulting parses into trees without recursive nodes
# - incorporate pre-annotations (CoNLL-U or CoNLL-C, incl. syntax)
# - can be run over two-column generic CoNLL data (ID WORD), CoNLL-U (with MTAAC XPOS), CoNLL-C

# notes:
# - the use of () in the text is somewhat problematic because NLTK doesn't provide proper object structure for trees but only an object view on strings
# brackets get mis-parsed as phrase delimiters. However, don't fix that *here* unless the CFG grammar is fixed for that, too. 
# - this is not optimized for speed nor coverage, but for mining gold data from morphological gold annotations
# - parsing failures are marked by FRAG, these result from either
#   a) UNKNOWN words (then, we provide a partial parse of known content), or
#	b) an unseen combination of parseable phrases (then, terminal node labels are returned, possible alternatives separated by |)
# - this is fairly slow: 
#   P106438-raw.conll real 0m52,458s	[CoNLL-C]
#	P106438.conll	real   1m6,782s		[CoNLL-U]
#	BUT: this is for diagnostic reasons only, as we actually perform a large number of parsing iterations for every single sentence
#	to speed up in production mode, disable the iterations and support for out of vocabulary items:
#	+ use *only* TRANSACTION as start symbol (no iteration)
#	+ use *only* nltk.parse.IncrementalLeftCornerChartParser
#	+ disable re-initialization of the parser with OOV vocabulary

base_grammar = nltk.data.load("jaworski.cfg")

# stack of parsers
PARSERS=[ 
	nltk.parse.ShiftReduceParser, 					# lossy, but efficient
	nltk.parse.IncrementalLeftCornerChartParser,	# less lossy, but still somewhat efficient
#	nltk.parse.chart.BottomUpLeftCornerChartParser,	# 
#	nltk.parse.IncrementalBottomUpChartParser,		# this one gives better partial parses
#	nltk.parse.ChartParser							# 
#	nltk.parse.RecursiveDescentParser				# ran into infinite loop
#	nltk.parse.BllipParser							# BLLIP/Charniak parser # couldn't import
	]
parsers={} # created on demand

# defines a preference ranking for possible analyses, should not include FRAG
TARGETS = ["EPILOG", "DATED_TRANSACTION", "TRANSACTION", "SUMMARY", "NUMBER_PRODUCT_LIST", "MU_PERSON_sze3", "PERSON_maszkim", "MUDU_PERSON", "BALA_PERSON", "GIRI3_PERSON", "KISZIB_PERSON", "PERSON", "NATIONALITY", "CITY", "FILIATION", "UNIT", "GOD", "COPY", "GABARI", "GOD_NAME", "JOB", "JOBNAME", "NUMBER_PRODUCT", "KISZIBA", "NUMBERS", "MU", "MUDU", "NUMBER", "PN_SZE3", "PN", "PRODUCT", "PRODUCT_NAME", "PRODUCT_PARAM", "SZU_NIGIN", "SZUNIGIN"]

TARGETS=list(map(lambda x: nltk.grammar.Nonterminal(x), TARGETS))
FRAG=nltk.grammar.Nonterminal("FRAG")

# preprocessing: undo sentence splitting, split
# - before lines starting with a number (= candidate transaction) [CoNLL-C], or
# - between verbs/proper nouns and numbers [CoNLL-U, line information lost]

sentences=[]

for file in files:

	print("##"+re.sub(r".","#",file)+"##")
	print("#",file,"#")
	print("##"+re.sub(r".","#",file)+"##")
	print()
	grammar=base_grammar		# with every text, we forget what we learned from earlier annotations
	grammar_additions=set([])	# from CoNLL-U annotations
	rhss=set([])
	for rhs in set(map(lambda x: str(x.rhs()), grammar.productions())):		# this is a list!
		core=str(rhs)
		if "'" in core:
			core=re.sub(r"[(]'(.+)'[,]?[)]$",r"\1",core)
			core=core.split("', '")
			core=set(map(lambda x: re.sub(r"'","",x), core))
		else:
			core=re.sub(r"[(](.+)[,]?[)]$",r"\1",core)
			core=set(core.split(", "))
		rhss.update(core)
	
	with open(file, "r") as conll:
		sentence=""
		lastline=None		# should be a list of strings, not just a string
		line=conll.readline()
		while(line):
			#print(sentences,line)
			line=line.rstrip()
			if(line.strip().startswith("#")):
				print(line);
			else:
				line=re.sub(r"^#.*","",line)
				line=re.sub(r"([^\\\\])#.*","$1",line)
				fields=line.split("\t")

				if(len(fields)>1):
					split=False
					if(fields[1]=="szunigin"):		#TODO: split before szunigin
						split=True
					else:
						if(len(fields)>1):
							if(re.match(r"[0-9]+",fields[0])):	# CoNLL-U format: break between verbs and following number
								if(len(fields)>9):
									if((fields[3]=="NUM" or 						# CoNLL-U UPOS
										"NU" in fields[3] or							# CoNLL-C
										"NU" in fields[4] or							# CoNLL-U XPOS
										re.match(r"^[0-9].*",fields[1]))			# string match for number
										and lastline!=None 
										and (lastline[3] in ["VERB","PROPN"] or		# CoNLL-U UPOS
											 re.match(r"^(V\.*|.*\.V\..*|.*\.V|V|^[A-Z]N(\..*)?)$", lastline[3]))	# CoNLL-C XPOS 
										and not(lastline[1]=="la2")):	# this would be "minus"  
											split=True
							else:								# try sentence splitting for an CoNLL-C format
								if(fields[0].endswith(".1") and re.match("^[0-9].*",fields[1])):
									split=True
				
					if split:
						if(len(sentence)>0):
							sentences.append(sentence)
						sentence=fields[1]
					else:
						sentence=sentence+" "+fields[1]
					lastline=fields

				# if(len(fields)>1):
					# if(re.match(r"[0-9]+",fields[0])):	# CoNLL-U format: break between verbs and following number
						# if(len(fields)>9):
							# if((fields[3]=="NUM" or 						# CoNLL-U UPOS
							    # "NU" in fields[3] or							# CoNLL-C
								# "NU" in fields[4] or							# CoNLL-U XPOS
							    # re.match(r"^[0-9].*",fields[1]))			# string match for number
								# and lastline!=None 
								# and (lastline[3] in ["VERB","PROPN"] or		# CoNLL-U UPOS
									 # re.match(r"^(V\.*|.*\.V\..*|.*\.V|V|^[A-Z]N(\..*)?)$", lastline[3]))	# CoNLL-C XPOS 
								# and not(lastline[1]=="la2")):	# this would be "minus"  
									# if(len(sentence)>0):
										# sentences.append(sentence)
									# sentence=fields[1]
							# else:
								# sentence=sentence+" "+fields[1]
							# lastline=fields						
														
					# else:								# try sentence splitting for an CoNLL-C format
						# if(fields[0].endswith(".1") and re.match("^[0-9].*",fields[1])):
							# if(len(sentence)>0):
								# sentences.append(sentence)
							# sentence=fields[1]
						# else:
							# sentence=sentence+" "+fields[1]
				
					
					# enrich grammar
					# CoNLL-C and CoNLL-U (leads to different results, though)
					if(not fields[1] in rhss):
						if((len(fields)>3 and (fields[3] == "NUM" or "NU" in fields[3])) or	# CoNLL-U UPOS or CoNLL-C POS
						   re.match(r"^[0-9].*",fields[1])):								# string match
							grammar_additions.add('NUMBER -> "'+fields[1]+'"')
						elif((len(fields)>4 and "DN" in fields[4]) or 	# CoNLL-U XPOS
							 (len(fields)>3 and "DN" in fields[3])):	# CoNLL-C POS
							grammar_additions.add('GOD_NAME -> "'+fields[1]+'"')
						elif((len(fields)>4 and "PN" in fields[4]) or 	# CoNLL-U XPOS
							 (len(fields)>3 and "PN" in fields[3])):	# CoNLL-C POS
							grammar_additions.add('PN -> "'+fields[1]+'"')
						elif((len(fields)>4 and "SN" in fields[4]) or
							 (len(fields)>3 and "SN" in fields[3])):
							grammar_additions.add('CITY -> "'+fields[1]+'"')
						elif((len(fields)>7 and fields[7]=="amod") or 
						     (len(fields)>5 and fields[5]=="amod")):	# adjectives can be parameters of anything	# col5 in CoNLL-C currently not used, but would be for DEP
							grammar_additions.add('PRODUCT_PARAM -> "'+fields[1]+'"')
						elif(len(fields)>3 and re.match(r"^[A-Z\.]+$",fields[3])):		# provide (UD or MTAAC) POS for unknown words
							label=fields[3]
							label=re.sub(r"\.","_",label)
							grammar_additions.add(label+ ' -> "'+fields[1]+'"')
							if(not label in rhss):
								grammar_additions.add("UNKNOWN -> "+label)

			line=conll.readline()
		if(len(sentence)>0):
			sentences.append(sentence)

#	print("additions:",grammar_additions)
			
	# add to grammar (note that we change the overall grammar!)
	if len(grammar_additions)>0:
		tmp="# "+str(grammar)+"\n"+("\n".join(grammar_additions))
		# initial # is required to comment out the first line about the start symbol
		grammar=nltk.grammar.CFG.fromstring(tmp)
			
	# parse a real text
	for s in sentences:
		s=s.strip()
		s=re.sub(r"[ \t]+"," ",s)
		if(len(s)>0):	
			print("#",s)
			s=s.split(" ")
			OOVrules=[]
			for w in  get_missing_words(grammar, s):
				lhs = nltk.grammar.Nonterminal('UNKNOWN')
				new_production=nltk.grammar.Production(lhs, [w])
				OOVrules.append(new_production)
			new_grammar=None
			if len(OOVrules)>0:
				new_grammar=str(grammar)
				for r in OOVrules:
					new_grammar=new_grammar+"\n"+str(r)
				
				lhss=set(map(lambda x: x.lhs(), grammar.productions()))
				if not "UNKNOWN" in lhss:
					for lhs in lhss:
						new_grammar=new_grammar+"\nFRAG -> "+str(lhs)+ " FRAG | FRAG "+str(lhs)
				new_grammar=nltk.grammar.CFG.fromstring(new_grammar.split('\n')[1:])
				new_grammar._start = nltk.grammar.Nonterminal("FRAG") #grammar.start()
				parsers.clear()
					
			parse=None
			if(new_grammar==None and len(OOVrules)==0):
				new_grammar=grammar
				for PARSER in PARSERS:
					if(parse==None):
						if(not PARSER in parsers):
							parsers[PARSER]=init_parser(PARSER, grammar)
						parser=parsers[PARSER]				
		#				print("#",parser.__class__.__name__)
						for start in TARGETS:
							if(parse==None):
								parser.grammar()._start = start
								parse=parser.parse_one(s)
								if(parse):
		#							print("#",parser.__class__.__name__,str(start))
									print(flatten_tree(parse))
			if(parse==None):	# FRAG only if everything else failed, but nothing else possible when UNKNOWN words
				for PARSER in PARSERS:
					if(parse==None):
						if(not PARSER in parsers):
							parsers[PARSER]=init_parser(PARSER, new_grammar)
						parser=parsers[PARSER]
						parser.grammar()._start = FRAG
						parse=parser.parse_one(s)
						if(parse):
							# print("#",parser.__class__.__name__,str(FRAG))
							# print("# out of vocabulary items")
							print(flatten_tree(parse))

			if(parse==None):
				# this can happen only if we arrive at parseable constituents in an unforeseen order
				# so, we return the results of the lexical lookup
				parse="(FRAG\n"
				for w in s:
					nterms=set(map(lambda x: str(x.lhs()),grammar.productions(rhs=w)))
					nterms=sorted(list(nterms))
					parse=parse+"  ("+"|".join(nterms)+ " "+w+")\n"
				parse=parse+")"
				#parse=nltk.Tree.fromstring(parse)
				#print("# unseen combination of parseable phrases")
				print(parse)
			
			print("",end="\n",flush=True)

	print