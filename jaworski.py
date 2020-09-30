# python 3.7
import nltk

#
# aux functions
#

def get_missing_words(grammar, tokens):
    """
    Find list of missing tokens not covered by grammar
    """
    missing = [tok for tok in tokens
               if not grammar._lexical_index.get(tok)]
    return missing

#
# demo
# 

grammar = nltk.data.load("jaworski.cfg")
# print(grammar)
parser=nltk.parse.IncrementalBottomUpChartParser(grammar)
# for tree in parser.parse(["ur-mes"]): print(tree)										# ok
# for tree in parser.parse(['gu3-de2-a','lugal', 'lagasz{ki}-ke4']): print(tree)		# ok
# for tree in parser.parse("gu3-de2-a lugal lagasz{ki}-ke4".split(" ")): print(tree)	# ok
# for tree in parser.parse("1(disz) sila4 ur-mes ensi2".split(" ")): print(tree)		# nok

# parser=nltk.parse.BottomUpChartParser(grammar)
sentences=["...", "sila4", "sila3", "lugal", "lagasz{ki}-ke4", "gu3-de2-a lugal lagasz{ki}-ke4", "1(disz) sila4 ur-mes ensi2" ,  "1(disz) ... x ensi2", "x",  
	"3(disz) sila4 2(u) 1(disz) masz2", "mu-kux(DU) {d}szara2 |KI.AN|{ki}",
	"3(disz) sila4 2(u) 1(disz) masz2 mu-kux(DU) {d}szara2 |KI.AN|{ki}" ]

# last sentence is incomplete

#PARSER_CLASS=nltk.parse.BottomUpChartParser
PARSER_CLASS=nltk.parse.IncrementalBottomUpChartParser
regular_parser=parser # used for fragments without OOV

# dynamically add unseen words to dummy category
for s in sentences:
	print(s)
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
		
		lhss=set(map(lambda x: x.lhs(), grammar.productions()))
		# print(lhss)
		if not "UNKNOWN" in lhss:
#			new_grammar=new_grammar+"\nFRAG -> UNKNOWN | FRAG UNKNOWN"
			for lhs in lhss:
				new_grammar=new_grammar+"\nFRAG -> "+str(lhs)+ " FRAG | FRAG "+str(lhs)
			# print(new_grammar)
#		print(lhss)
#		print(str(grammar.productions()))
		#new_grammar=nltk.grammar.CFG.fromstring(new_grammar)
		new_grammar=nltk.grammar.CFG.fromstring(new_grammar.split('\n')[1:])
		new_grammar._start = nltk.grammar.Nonterminal("FRAG") #grammar.start()
		# print(new_grammar)
		parser=PARSER_CLASS(new_grammar)
			
		# print(parser.grammar().productions())
	for start in set(map(lambda x: x.lhs(), parser.grammar().productions())):
	# for start in [ "BALA_PERSON", "COPY", "FILIATION", "GIRI3_PERSON", "KISZIB_PERSON","MU_PERSON_sze3","MUDU_PERSON","NATIONALITY","NUMBER_PRODUCT_LIST","PARSE", "PERSON", "PERSON_maszkim", "PRODUCT", "SUMMARY", "UNIT" , "FRAG"]:	
		parser.grammar()._start = nltk.grammar.Nonterminal(str(start))
		parses=list(parser.parse(s))
		if(len(parses)>0):
			print(parses[0])
	print()
		
# parse a real text
with open('P106438.txt',"r") as text:
	line = text.readline()
	while line:
		s=line.strip()
		
		print(s)
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
			
			lhss=set(map(lambda x: x.lhs(), grammar.productions()))
			# print(lhss)
			if not "UNKNOWN" in lhss:
	#			new_grammar=new_grammar+"\nFRAG -> UNKNOWN | FRAG UNKNOWN"
				for lhs in lhss:
					new_grammar=new_grammar+"\nFRAG -> "+str(lhs)+ " FRAG | FRAG "+str(lhs)
				# print(new_grammar)
	#		print(lhss)
	#		print(str(grammar.productions()))
			#new_grammar=nltk.grammar.CFG.fromstring(new_grammar)
			new_grammar=nltk.grammar.CFG.fromstring(new_grammar.split('\n')[1:])
			new_grammar._start = nltk.grammar.Nonterminal("FRAG") #grammar.start()
			# print(new_grammar)
			parser=PARSER_CLASS(new_grammar)
				
			# print(parser.grammar().productions())
		for start in set(map(lambda x: x.lhs(), parser.grammar().productions())):
		# for start in [ "BALA_PERSON", "COPY", "FILIATION", "GIRI3_PERSON", "KISZIB_PERSON","MU_PERSON_sze3","MUDU_PERSON","NATIONALITY","NUMBER_PRODUCT_LIST","PARSE", "PERSON", "PERSON_maszkim", "PRODUCT", "SUMMARY", "UNIT" , "FRAG"]:	
			parser.grammar()._start = nltk.grammar.Nonterminal(str(start))
			parses=list(parser.parse(s))
			if(len(parses)>0):
				print(parses[0])
		print()
		line=text.readline()