# python 3.7
import nltk
import re
import warnings
import os
import sys
import argparse
from pprint import pprint

########
# args #
########

debug_files=[
	'input/comm/P106438.conll',
	'input/comm/P330559.conll'
]	

parser = argparse.ArgumentParser(description='parse transactions from Ur-III admin texts, using pre-annotations for POS, MORPH and COMM(o[d]dities)\n'+
	"We expect the following tab structure: WORD SEGM POS MORPH CODE CHK ...\n"+
	"\tWORD  transcription\n"+
	"\tSEGM  morpheme segmentation\n"+
	"\tPOS   part-of-speech tag, MTAAC schema\n"+
	"\tMORPH morphosyntactic analysis, MTAAC schema\n"+
	"\tCODE  (ignored)\n"+
	"\tCHK   IOB-coded chunk structure, expected labels B-COUNT, I-COUNT, B-COM, I-COM, B-MOD, I-MOD\n"+
	"\t...   following columns are ignored")
parser.add_argument('files', metavar='FILE.conll', type=str, nargs='*',
                    help='CoNLL/TSV files, without arguments, use '+", ".join(debug_files))
parser.add_argument("--debug", help="write base grammar and original text, entails --ptb", action="store_true")				
parser.add_argument("--conll", help="if --debug, --ptb, or --rawDoc: return CoNLL output in addition to PTB output", action="store_true")				
parser.add_argument("--ptb", help="return a PTB parse instead of the default (CoNLL) output. This is informative only and lossy, to enable CoNLL output in addition to --ptb, use --conll", action="store_true")
parser.add_argument("--rawDoc", help="for debugging: return the raw document parse as produced by parse_doc.cfg, entails --ptb",action="store_true")

args = parser.parse_args()
if args.debug:
	args.ptb=True
if args.rawDoc:
	args.ptb=True

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

	if(type(tree)==str):
		tree=nltk.Tree.fromstring(tree)
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
	
def drop_nonbranching_nodes(tree, label, branching_replacement=None):
	"""
	remove non-branching nodes with that particular label from the tree
	if branching_replacement is other than None, replace branching nodes with branching_replacement
	"""
	#print("dnn("+str(tree)+", "+label+")")
	if(type(tree)==str):
		return tree
	elif(len(tree.leaves())<1):
		return tree
	elif(len(tree)==1 and str(tree.label())==label):
		return drop_nonbranching_nodes(tree[0],label)
	else:
		children=None
		if(len(tree)>0):
			children=[]
			for x in range(len(tree)):
				child=drop_nonbranching_nodes(tree[x],label)
				children.append(child)
		if tree.label()==label and branching_replacement:
			return nltk.Tree(branching_replacement, children)
		return nltk.Tree(tree.label(), children)
	
def write_grammar(grammar):
	"""
	return compact string representation
	"""
	rules={}
	for rule in sorted(list(set(str(base_grammar).split("\n")))):
		sides=rule.split("->")
		if(len(sides)>1):
			lhs=sides[0].strip()
			rhs=sides[1].strip()
			if(lhs in rules):
				rules[lhs].append(rhs)
			else:
				rules[lhs]=[rhs]
	rules={ k : " | ".join(v) for (k,v) in rules.items() }
	rules=[ k+" -> "+v for (k,v) in rules.items() ]
	return "\n".join(rules)

def decode_parse(parse, preparsed):
	"""
	merge parse into preparsed.
	preparsed is a sequence of phrase-level dictionaries, with every element corresponding to an input token provided to the parser. Structure of non-terminals is { "NODE": label, "children": [...] }
	integrate the result of an CFG parse into this data structure and return it.	
	"""
	
	# print("dp(\n",parse,"\n",preparsed,")")
	
	if(len(parse)==0):
		return parse
	elif type(parse)==str: # terminal node: return preparsed
		return preparsed

	children=[]
	start=0
	for i in range(len(parse)):
		if type(parse[i])==str:
			# print("terminal: "+str(preparsed[start]))
			children.append(preparsed[start])
			start=start+1
		else:
#			pprint("nonterminal: "+str(preparsed[start:start+len(parse[i].leaves())]))
			children.append(decode_parse(parse[i],preparsed[start:start+len(parse[i].leaves())])[0])
			start=start+len(parse[i].leaves())
#			pprint(preparsed[start:start+len(parse[i].leaves())])

	return [ { "NODE": parse.label(), "children": children }]	
	
def abandon_nodes(parses, labels, remove_dependents=False):
	"""
	given an array of parses (sequences of dicts), abandon nodes with any of the defined labels, e.g., FRAG or PARSE nodes.
	note that children are preserved
	if remove_dependents is True, the entire subtree is wiped out
	"""
	result=[]
	for p in parses:
		if "NODE" in p and p["NODE"] in labels:
			if not remove_dependents:
				result.extend(abandon_nodes(p["children"],labels))
		elif "NODE" in p:
			result.append({ "NODE":p["NODE"], "children":abandon_nodes(p["children"],labels)})
		else:
			result.append(p)
	return result
	
def parsed2conll(parsed, keys, pre="",post=""):
	"""
	parse is a sequence of dicts that contain the annotation (as produced by decode_parse()), add parse structure as another column after keys.
	pre and post are for internal use, only
	"""
	
#	print("p2c(",parsed,")")
#	pprint(parsed)
	
	if(len(parsed)==0):
		return ""

	result=""
	
	for nr, parse in enumerate(parsed):
		mypost=""
		if(nr==len(parsed)-1):
			mypost=post
		if(not "children" in parse or len(parse["children"])==0):
			for k in keys:
				if(not k in parse):
					result=result+"_\t"
				else:
					result=result+parse[k]+"\t"
			result=result+pre+"*"+mypost+"\n"
		else:
			result=result+parsed2conll(parse["children"],keys,pre=pre+"("+parse["NODE"]+" ",post=")"+mypost)
		pre=""
	return result
	

def move_up(parse,label, parentlabel):
	"""
	in a parse tree (list object), move a node the label to its great-parent if the parent has the parent label
	"""
	
	if(len(parse)==0):
		return parse
	
	for granny in parse:
		if "children" in granny:
			children=[]
			for mother in granny["children"]:
				if "children" in mother and "NODE" in mother and mother["NODE"]==parentlabel:
					for daughter in mother["children"]:
						if "NODE" in daughter and daughter["NODE"]==label:
							children.append(daughter)
							mother["children"].remove(daughter)
				children.append(mother)
			granny["children"]=move_up(children,label,parentlabel)
	
	return(parse)

def under_next(parse,label,nextlabel):
	"""
	transform a node with label into child of the following sibling node if it has nextlabel
	operates on list objects
	"""
	
	if(len(parse)==0):
		return parse
	
	if(type(parse)==dict):
		if "children" in parse:
			parse["children"]=under_next(parse["children"],label,nextlabel)
			return parse
		else:
			return parse
	
	# back to front
	result=[under_next(parse[len(parse)-1],label,nextlabel)]
	for pos in range(len(parse)-2,-1,-1):
		node=under_next(parse[pos],label,nextlabel)
		#print(node)
		sibling=result[0]
		if "NODE" in node and (node["NODE"]==label) and ("NODE" in sibling) and (sibling["NODE"]==nextlabel):
			result[0]["children"]=[node]+result[0]["children"]
		else:
			result=[node]+result
	
	return result

def flat_tree(parse):
	"""
	eliminate recurrent nonterminals.
	reimplements flatten_tree, but for list objects rather than CFG nodes
	"""
	if(len(parse)==0): return parse

	if(type(parse)==list):
		return [ flat_tree(p) for p in parse ]
		
	# we're in a dict
	if(not "children" in parse or not "NODE" in parse):
		return parse
		
	children=[]
	label=parse["NODE"]
	for c in parse["children"]:
		c=flat_tree(c)
		if "NODE" in c and c["NODE"]==label:
			children.extend(c["children"])
		else:
			children.append(c)
	parse["children"]=children
	return parse
	
def rename_nodes(parse, old2new):
	"""
	replace NODE labels in list structure, old2new is a dict
	"""
	if(type(parse)==list):
		return [ rename_nodes(p, old2new) for p in parse]
	
	if "NODE" in parse and parse["NODE"] in old2new:
		parse["NODE"]=old2new[parse["NODE"]]
	
	if "children" in parse and len(parse["children"])>0:
		parse["children"]=rename_nodes(parse["children"], old2new)
	
	return parse
	
def get_parse(parse):
	"""
	take sequence-based full parse, retrieve PTB representation
	"""
	
	result=""
	if len(parse)==0:
		result="()"
	elif(len(parse)>0):
		for node in parse:
			if "NODE" in node or "WORD" in node: 
				result=result+"("
				if type(node)==str:
					result=result+node
				else:
					if "NODE" in node:
						result=result+node["NODE"]
					else:
						result=result+node["POS"]
					result=result+" "
					if "children" in node:
						result=result+get_parse(node["children"])
					else:
						result=result+re.sub(r"\s*\([^\)]*\)\s*","",node["WORD"])
				result=result+")"
			else:
				result="()"
	#print(str(parse),"=>",result)
	#return result
	result=str(nltk.Tree.fromstring("("+result+")"))
	result=result.strip()
	result=result[1:len(result)-1].strip()
	# result=re.sub(r"\([^\)]*\)$","",result)	# where does THAT come from?
	# if(len(result)==0):
		# return "()"
	return result	
	
####################
# parse conll file #
####################

base_grammar = nltk.data.load("parse_comm.cfg")

# add dictionary
lexical_rules=nltk.data.load("parse_dict.cfg")

grammar_additions=str(lexical_rules).split("\n")
grammar_aditions=list(map(lambda x: x.lstrip(), grammar_additions))
grammar_additions=list(filter(lambda x: "->" in x, grammar_additions))

# # extend all nonterminals with a following GAP
lhss=set(map(lambda x: str(x.lhs()), base_grammar.productions()))
# for lhs in lhss:
	# grammar_additions.append(lhs+" -> GAP")
	# grammar_additions.append(lhs+" -> "+lhs+" GAP")

# add generic start symbol (unless provided, already): PARSE, i.e., every LHS
if(not "PARSE" in lhss):
	for lhs in lhss:
		grammar_additions.append("PARSE -> "+lhs)

grammar_additions.append("PARSE -> PARSE FRAG")	# preposed GAPs only for PARSE
# grammar_additions.append("PARSE -> GAP PARSE")	# preposed GAPs only for PARSE
if len(grammar_additions)>0:
	tmp="# "+str(base_grammar)+"\n"+("\n".join(grammar_additions))
	# initial # is required to comment out the first line about the start symbol
	base_grammar=nltk.grammar.CFG.fromstring(tmp)

if args.debug:
	print("\n# base grammar")
	print("#", re.sub(r"\n","\n# ",write_grammar(base_grammar)))

# initialize document grammar
doc_grammar = nltk.data.load("parse_doc.cfg")
	
# stack of parsers
PARSERS=[ 
	#nltk.parse.ChartParser
	nltk.parse.IncrementalLeftCornerChartParser
	]
parsers={} # created on demand

# use different parsers for document-level parsing if necessary
DOCPARSERS=PARSERS
docparsers={} # created on demand

# pre-defined column labels 
annotations=["WORD","SEGM","POS","MORPH","CODE","CHK"]

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
		sentences=[]
		sentence=[]				# sequence of dictionaries
		line=conll.readline()

		#################################
		# aggregate and split sentences #
		#################################
		split=False
		lasttoken={ "WORD": "" }
		while(line):
			line=line.rstrip()
			if(line.strip().startswith("#")):
				if not args.rawDoc:	# suppress for step-by-step debugging
					print(line);
			elif(line.strip().startswith("FORM\t")):
				pass
			else:
				if(len(line)==0):
					split=True
				else:
					line=re.sub(r"^#.*","",line)
					line=re.sub(r"([^\\\\])#.*","$1",line)
					fields=line.split("\t")

					token={}
					for pos,k in enumerate(annotations):
						if len(fields)>pos:
							token[k]=fields[pos]
						else:
							token[k]=""	# all keys defined
					
					# annotation normalization: set placeholders to empty strings
					for k in token.keys():
						if(re.match("^(\*.*|_|\?)$",token[k])):
							token[k]=""
					if(token["MORPH"]==""):
						token["MORPH"]=token["POS"]
					
					# do we start a new segment? 
					# split=split or 							# split after empty line
						  # token["WORD"]=="szunigin"	or		# split before szunigin
						  # token["CHK"]=="B-COUNT"			# split before (the start of) a numeral
					split=split or token["WORD"]=="szunigin"	or		token["CHK"]=="B-COUNT"			
					# if the last token was empty, then overwrite all annotations with those of the last token 
					if(lasttoken["WORD"]==""):
						for k in lasttoken.keys():
							if(lasttoken[k]!=""):
								token[k]=lasttoken[k]
						
					if split:
						if(len(sentence)>0):
							sentences.append(sentence)
							sentence=[]
							split=False
					
					if(token["WORD"]!=""):
						sentence.append(token)
						lasttoken=token

			line=conll.readline()
		if(len(sentence)>0):
			sentences.append(sentence)
			
		# contains segments-level parses, for subsequent document-level parsing
		parses=[]
		for s in sentences:
			grammar_additions=set([])
			if args.debug:
				print("#"," ".join(list(map(lambda x: x["WORD"], s))))

			##############
			# prep input #
			##############
			
			preparsed=[]	# array of dict arrays, corresponding to preparsed constituents each
			parser_in=[]    # for every element of preparsed, parser_in provides the WORD or the category label
			for token in s:
				if token["CHK"].startswith("B-"):
					preparsed.append({"NODE":token["CHK"][2:], "children":[token]})
					parser_in.append(token["CHK"][2:])
				elif token["CHK"].startswith("I-"):
					if(len(preparsed)==0):
						preparsed.append({"NODE":token["CHK"][2:], "children":[token]})
						parser_in.append(token["CHK"][2:])
					else:
						preparsed[len(preparsed)-1]["children"].append(token)
				else:
					preparsed.append({"NODE":"word", "children":[token]})
					# for mu.PN-sze3 (not capturing phrases!)
					# if(token["POS"] in ["PN","DN","RN"] and 
						# (token["WORD"].endswith("sze3") or
						 # "TERM" in token["MORPH"])):
						 # parser_in.append("PN_SZE3")
					#el
					if((token["POS"].endswith("N") and token["POS"]!="N") or token["POS"].startswith("NU")):
						parser_in.append(token["POS"])
					else:
						parser_in.append(token["WORD"])
						
			# print("#"," ".join(parser_in))

			for t in parser_in:
				if(not t in rhss):	
					# print("add "+t+" as UNKNOWN")
					grammar_additions.add("UNKNOWN -> \""+t+"\"")
			if len(grammar_additions)>0:
				tmp="# "+str(grammar)+"\n"+("\n".join(grammar_additions))
				# initial # is required to comment out the first line about the start symbol
				grammar=nltk.grammar.CFG.fromstring(tmp)

			grammar._start = nltk.grammar.Nonterminal("PARSE")
			# print(grammar)
			
			#############
			# CFG parse #
			#############
			
			parse=None
			for PARSER in PARSERS:
				if(parse==None):
					if(not PARSER in parsers or len(grammar_additions) > 0):
						parsers[PARSER]=init_parser(PARSER, grammar)
					parser=parsers[PARSER]
#					parser.grammar()._start = nltk.grammar.Nonterminal("PARSE")
					
					
					# print(parser_in)
					parse=parser.parse_one(parser_in)
			if(parse==None):
				parse="(FRAG\n"
				for w in parser_in:
					nterms=set(map(lambda x: str(x.lhs()),grammar.productions(rhs=w)))
					nterms=sorted(list(nterms))
					parse=parse+"  ("+"|".join(nterms)+ " "+w+")\n"
				parse=parse+")"
				parse=nltk.Tree.fromstring(parse)
			
			parse=drop_nonbranching_nodes(parse,"PARSE", branching_replacement="FRAG")
			parse=flatten_tree(parse)
			parses.extend(decode_parse(parse,preparsed))
			
		##########################
		# document-level parsing #
		##########################
		preparsed=parses
		preparsed=[{"NODE":"START", "children":[]}]+preparsed # for REG parsing
		preparsed=abandon_nodes(preparsed,["PARSE"])
		# if you do abandon_nodes(preparsed,["FRAG"]), you need to extend the rule set in parse_doc.cfg
		
		nonterminals=set([ p["NODE"] for p in preparsed if "NODE" in p ])
		doc_grammar_additions=[]
		doc_lhss = set(map(lambda x: str(x.lhs()), doc_grammar.productions()))
		for n in nonterminals:
			if not n in doc_lhss:
				if "|" in n:
					for part in n.split("|"):
						doc_grammar_additions.append(part+" -> '"+n+"'")
				else:
					doc_grammar_additions.append("UNKNOWN -> '"+n+"'")
		if len(doc_grammar_additions)>0:
			tmp="# "+str(doc_grammar)+"\n"+("\n".join(doc_grammar_additions))
			# initial # is required to comment out the first line about the start symbol
			doc_grammar=nltk.grammar.CFG.fromstring(tmp)
		# print(doc_grammar_additions)
		
		#pprint(preparsed)
		parser_in=[ p["NODE"] for p in preparsed ]
		
		if(args.rawDoc):
			print("\n".join(parser_in)+"\n")

		# pprint(parser_in)
		parse=None
		for PARSER in DOCPARSERS:
			if(parse==None):
				if(not PARSER in docparsers or len(doc_grammar_additions) > 0):
					docparsers[PARSER]=init_parser(PARSER, doc_grammar)
				parser=docparsers[PARSER]
				parser.grammar()._start = nltk.grammar.Nonterminal("DOC")
				#print(parser.grammar())
				parse=parser.parse_one(parser_in)
		if(parse==None):
			parse="(FRAG\n"
			for w in parser_in:
				nterms=set(map(lambda x: str(x.lhs()),doc_grammar.productions(rhs=w)))
				nterms=sorted(list(nterms))
				parse=parse+"  ("+"|".join(nterms)+ " "+w+")\n"
			parse=parse+")"
			parse=parse=nltk.Tree.fromstring(parse)
		parse=flatten_tree(parse)
				
		parse=decode_parse(parse,preparsed)
	
		if not args.rawDoc:
			# restructuring of the regular parse tree
			# (be careful, can create non-projectivit)
			parse=move_up(parse,"S_TRANSACTION","S_NUMBER_PRODUCT_LIST")
			parse=flat_tree(parse)
			parse=under_next(parse,"S_NUMBER_PRODUCT_LIST","TRANSACTION")
			parse=under_next(parse,"S_NUMBER_PRODUCT_LIST","NUMBER_PRODUCT_LIST")
			
			# move FRAG up to narrow down consistently recognized elements
			# (moving FRAG up allows to connect NPLs with following TRANSACTIONS, however, this will be incorrect if the FRAG represents the original transition)
			parse=move_up(parse,"S_FRAG","S_NUMBER_PRODUCT_LIST")
			parse=move_up(parse,"S_FRAG","S_TRANSACTION")
			parse=flat_tree(parse)

			parse=under_next(parse,"S_NUMBER_PRODUCT_LIST","S_TRANSACTION")
			parse=under_next(parse,"S_NUMBER_PRODUCT","S_TRANSACTION")
			parse=under_next(parse,"S_NUMBER_PRODUCT","S_NUMBER_PRODUCT_LIST")			
			parse=move_up(parse,"S_TRANSACTION","S_NUMBER_PRODUCT_LIST")

			parse=move_up(parse,"S_TRANSACTION","S_EPILOG")
			# parse=flat_tree(parse)
			# parse=move_up(parse,"S_TRANSACTION","S_FRAG")
			parse=flat_tree(parse)
			parse=move_up(parse,"S_FRAG","S_EPILOG")	# can only happen if a fragment precedes a EPILOG, but that must be first element
			parse=rename_nodes(parse, { 
				# constituents marked for being initial
				"S_TRANSACTION":"TRANSACTIONS", 
				"S_NUMBER_PRODUCT_LIST":"NUMBER_PRODUCT_LIST",
				"S_FRAG":"FRAG",
				"S_EPILOG":"EPILOG",
				# simplify CFG parse
				"NUMBERS":"NUMBER",	
				"DATED_TRANSACTION":"TRANSACTION"
			})
			
			parse=under_next(parse,"NUMBER","NUMBER_PRODUCT")
			parse=under_next(parse,"NUMBER_PRODUCT_LIST","NUMBER_PRODUCT_LIST")
			parse=flat_tree(parse)
			
			parse=abandon_nodes(parse,["START"],remove_dependents=True)
			parse=flat_tree(parse)
		
		# for debugging only
		if args.ptb:
			print(get_parse(parse))
		
		# regular output
		if args.conll or not args.ptb:
			print(parsed2conll(parse, annotations))
